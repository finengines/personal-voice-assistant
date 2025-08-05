#!/usr/bin/env python3
"""
Agent Preset API

This module provides FastAPI endpoints for managing agent presets,
including CRUD operations and voice configuration options.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Literal
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from .preset_manager import preset_manager
from core.agent_config import (
    AgentPresetConfig, VoiceConfig, LLMConfig, STTConfig, AgentConfig,
    VOICE_OPTIONS, create_default_presets
)
from core.database import init_db, health_check

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("preset-api")

# FastAPI app
app = FastAPI(
    title="Agent Preset API",
    description="API for managing voice agent preset configurations",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:8081", "http://localhost:8082", "http://localhost:8083"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class VoiceConfigAPI(BaseModel):
    provider: Literal["openai", "cartesia", "elevenlabs", "deepgram"] = "openai"
    voice: str = "ash"
    model: Optional[str] = None
    speed: float = Field(1.0, ge=0.5, le=2.0)
    stability: Optional[float] = Field(None, ge=0.0, le=1.0)
    similarity_boost: Optional[float] = Field(None, ge=0.0, le=1.0)
    style: Optional[str] = None

class LLMConfigAPI(BaseModel):
    provider: Literal["openai", "anthropic", "groq", "google", "openrouter"] = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    parallel_tool_calls: bool = True

class STTConfigAPI(BaseModel):
    provider: Literal["deepgram", "openai", "groq"] = "deepgram"
    model: str = "nova-3"
    language: str = "multi"

# ---------------------------------------------------------------------------
# Nested Speed config
# ---------------------------------------------------------------------------

class SpeedConfigAPI(BaseModel):
    preemptive_generation: bool = False
    fast_preresponse: bool = False
    advanced_turn_detection: bool = False
    audio_speedup: float = Field(1.0, ge=1.0, le=2.0)
    min_interruption_duration: float = Field(0.3, ge=0.0)
    min_endpointing_delay: float = Field(0.4, ge=0.0)
    max_endpointing_delay: float = Field(3.0, ge=0.0)

# ---------------------------------------------------------------------------
# Agent config (behavior + speed)
# ---------------------------------------------------------------------------

class AgentConfigAPI(BaseModel):
    allow_interruptions: bool = True
    preemptive_generation: bool = False
    max_tool_steps: int = Field(10, ge=1, le=20)
    user_away_timeout: Optional[float] = Field(None, gt=0)
    speed_config: SpeedConfigAPI = SpeedConfigAPI()

class AgentPresetAPI(BaseModel):
    id: str = Field(..., pattern=r'^[a-z0-9-]+$', description="Lowercase alphanumeric with hyphens")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    system_prompt: str = Field(..., min_length=10)
    voice_config: VoiceConfigAPI
    mcp_server_ids: List[str] = Field(default_factory=list)
    llm_config: LLMConfigAPI
    stt_config: STTConfigAPI
    agent_config: AgentConfigAPI
    enabled: bool = True
    is_default: bool = False

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

# Global manager
async def get_preset_manager():
    """Dependency to get preset manager"""
    return preset_manager

@app.on_event("startup")
async def startup():
    """Initialize database and preset manager on startup"""
    try:
        await init_db()
        logger.info("Database initialized")
        
        # Create default presets if none exist
        presets = await preset_manager.load_all_presets()
        if not presets:
            logger.info("No presets found, creating defaults...")
            await preset_manager.create_default_presets()
        
        logger.info("🚀 Agent Preset API started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("Preset API will run with limited functionality")
        # Don't raise the exception - let the server start anyway

@app.get("/health", response_model=APIResponse)
async def health_endpoint():
    """Health check endpoint"""
    try:
        db_healthy = await health_check()
        return APIResponse(
            success=True,
            message="Preset API is healthy" if db_healthy else "Preset API running with limited functionality",
            data={
                "status": "healthy" if db_healthy else "degraded",
                "service": "preset-api",
                "database_connected": db_healthy
            }
        )
    except Exception as e:
        return APIResponse(
            success=True,
            message="Preset API is running with limited functionality",
            data={
                "status": "degraded",
                "service": "preset-api",
                "error": str(e)
            }
        )

@app.get("/presets", response_model=APIResponse)
async def list_presets(manager = Depends(get_preset_manager)):
    """List all agent presets"""
    try:
        presets = await manager.load_all_presets()
        return APIResponse(
            success=True,
            message=f"Found {len(presets)} presets",
            data=list(presets.values())
        )
    except Exception as e:
        logger.error(f"Error listing presets: {e}")
        # Return empty list instead of raising exception
        return APIResponse(
            success=True,
            message="Database not available - returning empty preset list",
            data=[]
        )

@app.get("/presets/{preset_id}", response_model=APIResponse)
async def get_preset(preset_id: str, manager = Depends(get_preset_manager)):
    """Get a specific preset by ID"""
    try:
        preset = await manager.get_preset(preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")
        
        return APIResponse(
            success=True,
            message=f"Preset {preset_id} found",
            data=preset.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preset {preset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting preset: {e}")

@app.post("/presets", response_model=APIResponse)
async def create_preset(preset_data: AgentPresetAPI, manager = Depends(get_preset_manager)):
    """Create a new agent preset"""
    try:
        # Check if preset ID already exists
        existing = await manager.get_preset(preset_data.id)
        if existing:
            raise HTTPException(status_code=409, detail=f"Preset {preset_data.id} already exists")
        
        # Convert API model to internal model
        config = AgentPresetConfig(
            id=preset_data.id,
            name=preset_data.name,
            description=preset_data.description,
            system_prompt=preset_data.system_prompt,
            voice_config=VoiceConfig(**preset_data.voice_config.dict()),
            mcp_server_ids=preset_data.mcp_server_ids,
            llm_config=LLMConfig(**preset_data.llm_config.dict()),
            stt_config=STTConfig(**preset_data.stt_config.dict()),
            agent_config=AgentConfig(**preset_data.agent_config.dict()),
            enabled=preset_data.enabled,
            is_default=preset_data.is_default
        )
        
        # If this is set as default, handle default switching
        if preset_data.is_default:
            await manager.set_default_preset(preset_data.id)
        
        success = await manager.save_preset(config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save preset")
        
        return APIResponse(
            success=True,
            message=f"Preset {preset_data.id} created successfully",
            data=config.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating preset: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating preset: {e}")

@app.put("/presets/{preset_id}", response_model=APIResponse)
async def update_preset(preset_id: str, preset_data: AgentPresetAPI, manager = Depends(get_preset_manager)):
    """Update an existing preset"""
    try:
        # Check if preset exists
        existing = await manager.get_preset(preset_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")
        
        # Ensure ID matches
        if preset_data.id != preset_id:
            raise HTTPException(status_code=400, detail="Preset ID mismatch")
        
        # Convert API model to internal model
        config = AgentPresetConfig(
            id=preset_data.id,
            name=preset_data.name,
            description=preset_data.description,
            system_prompt=preset_data.system_prompt,
            voice_config=VoiceConfig(**preset_data.voice_config.dict()),
            mcp_server_ids=preset_data.mcp_server_ids,
            llm_config=LLMConfig(**preset_data.llm_config.dict()),
            stt_config=STTConfig(**preset_data.stt_config.dict()),
            agent_config=AgentConfig.from_dict(preset_data.agent_config.dict()),
            enabled=preset_data.enabled,
            is_default=preset_data.is_default
        )
        
        # If this is set as default, handle default switching
        if preset_data.is_default:
            await manager.set_default_preset(preset_data.id)
        
        success = await manager.save_preset(config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update preset")
        
        return APIResponse(
            success=True,
            message=f"Preset {preset_id} updated successfully",
            data=config.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preset {preset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating preset: {e}")

@app.delete("/presets/{preset_id}", response_model=APIResponse)
async def delete_preset(preset_id: str, manager = Depends(get_preset_manager)):
    """Delete a preset"""
    try:
        # Check if preset exists
        existing = await manager.get_preset(preset_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")
        
        # Don't allow deleting the default preset
        if existing.is_default:
            raise HTTPException(status_code=400, detail="Cannot delete the default preset")
        
        success = await manager.delete_preset(preset_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete preset")
        
        return APIResponse(
            success=True,
            message=f"Preset {preset_id} deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting preset {preset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting preset: {e}")

@app.post("/presets/{preset_id}/set-default", response_model=APIResponse)
async def set_default_preset(preset_id: str, manager = Depends(get_preset_manager)):
    """Set a preset as the default"""
    try:
        # Check if preset exists
        existing = await manager.get_preset(preset_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")
        
        success = await manager.set_default_preset(preset_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set default preset")
        
        return APIResponse(
            success=True,
            message=f"Preset {preset_id} set as default"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting default preset {preset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error setting default preset: {e}")

@app.get("/presets/{preset_id}/enable", response_model=APIResponse)
async def toggle_preset(preset_id: str, enabled: bool = True, manager = Depends(get_preset_manager)):
    """Enable or disable a preset"""
    try:
        success = await manager.enable_preset(preset_id, enabled)
        if not success:
            raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")
        
        action = "enabled" if enabled else "disabled"
        return APIResponse(
            success=True,
            message=f"Preset {preset_id} {action}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling preset {preset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error toggling preset: {e}")

@app.get("/voice-options", response_model=APIResponse)
async def get_voice_options():
    """Get available voice options for different providers"""
    return APIResponse(
        success=True,
        message="Voice options retrieved",
        data=VOICE_OPTIONS
    )

# ---------------------------------------------------------------------------
# Model listing endpoint
# ---------------------------------------------------------------------------

# Static mapping for now. In the future this can query providers' real APIs.
MODEL_OPTIONS: Dict[str, List[str]] = {
    # Static fallbacks if live fetch fails
    "anthropic": [
        "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", 
        "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"
    ],
    "groq": [
        "llama3-70b-8192", "llama-3.1-8b-instant", "gemma-7b-it", "mixtral-8x7b-32768"
    ],
    "google": [
        "gemini-1.5-pro", "gemini-pro"
    ],
}

# ---------------------------------------------------------------------------
# Helper functions to fetch models dynamically
# ---------------------------------------------------------------------------

from core.api_key_manager import api_key_manager
import sys
sys.path.append('/app')
from utils.model_cache import get_models
import httpx, asyncio


async def _fetch_openai_models() -> List[str]:
    api_key = await api_key_manager.get_api_key("openai")
    if not api_key:
        return ["gpt-4o", "gpt-3.5-turbo"]
    from livekit.plugins import openai as lk_openai
    client = httpx.AsyncClient(headers={"Authorization": f"Bearer {api_key}"})
    resp = await client.get("https://api.openai.com/v1/models")
    await client.aclose()
    if resp.status_code != 200:
        return ["gpt-4o", "gpt-3.5-turbo"]
    data = resp.json()
    # Filter chat/completions models
    models = [m["id"] for m in data.get("data", []) if any(p in m["id"] for p in ("gpt", "davinci", "llama", "mixtral"))]
    return sorted(set(models))


async def _fetch_openrouter_models() -> List[str]:
    api_key = await api_key_manager.get_api_key("openrouter")
    if not api_key:
        return ["mistral/mistral-large", "meta-llama/llama-3-70b-instruct"]
    client = httpx.AsyncClient(headers={"Authorization": f"Bearer {api_key}"})
    resp = await client.get("https://openrouter.ai/api/v1/models")
    await client.aclose()
    if resp.status_code != 200:
        return ["mistral/mistral-large", "meta-llama/llama-3-70b-instruct"]
    data = resp.json()
    models = [m["id"] for m in data.get("data", [])]
    return sorted(set(models))


async def _fetch_groq_models() -> List[str]:
    api_key = await api_key_manager.get_api_key("groq")
    if not api_key:
        return ["llama3-70b-8192", "gemma-7b-it", "mixtral-8x7b-32768"]
    try:
        client = httpx.AsyncClient(headers={"Authorization": f"Bearer {api_key}"})
        resp = await client.get("https://api.groq.com/openai/v1/models")
        await client.aclose()
        if resp.status_code != 200:
            return ["llama3-70b-8192", "gemma-7b-it", "mixtral-8x7b-32768"]
        data = resp.json()
        models = [m["id"] for m in data.get("data", [])]
        return sorted(set(models))
    except Exception as e:
        logger.warning(f"Failed to fetch Groq models: {e}")
        return ["llama3-70b-8192", "gemma-7b-it", "mixtral-8x7b-32768"]


async def _fetch_anthropic_models() -> List[str]:
    api_key = await api_key_manager.get_api_key("anthropic")
    if not api_key:
        return ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3-5-sonnet-20241022"]
    try:
        # Anthropic doesn't have a public models endpoint, so we return the known models
        # These are updated as of late 2024
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022", 
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]
    except Exception as e:
        logger.warning(f"Failed to fetch Anthropic models: {e}")
        return ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]


@app.get("/models/{provider}", response_model=APIResponse)
async def list_models(provider: str):
    """Return list of model names for a given provider"""
    provider = provider.lower()

    async def _fallback():
        return MODEL_OPTIONS.get(provider, [])

    # Get base model list
    if provider == "openai":
        models = await get_models("openai", _fetch_openai_models)
    elif provider == "openrouter":
        models = await get_models("openrouter", _fetch_openrouter_models)
    elif provider == "groq":
        models = await get_models("groq", _fetch_groq_models)
    elif provider == "anthropic":
        models = await get_models("anthropic", _fetch_anthropic_models)
    else:
        models = await _fallback()

    if not models:
        return APIResponse(success=False, message="Provider not supported", data=[])

    return APIResponse(success=True, message="Model list retrieved", data=models)


@app.get("/voices/{provider}", response_model=APIResponse)
async def list_voices(provider: str):
    """Fetch available voices for a given provider"""
    provider = provider.lower()
    
    try:
        if provider == "elevenlabs":
            return await _get_elevenlabs_voices()
        elif provider == "openai":
            return APIResponse(success=True, message="OpenAI voices", data={
                "alloy": "Alloy - Balanced and versatile",
                "ash": "Ash - Warm and engaging", 
                "ballad": "Ballad - Calm and soothing",
                "coral": "Coral - Upbeat and energetic",
                "sage": "Sage - Wise and thoughtful",
                "verse": "Verse - Creative and expressive"
            })
        elif provider == "cartesia":
            return await _get_cartesia_voices()
        else:
            return APIResponse(success=False, message="Provider not supported", data={})
    except Exception as e:
        logger.error(f"Error fetching voices for {provider}: {e}")
        return APIResponse(success=False, message=f"Failed to fetch voices: {str(e)}", data={})


async def _get_elevenlabs_voices():
    """Get available voices from ElevenLabs API"""
    from core.api_key_manager import api_key_manager
    
    try:
        api_key = await api_key_manager.get_api_key("elevenlabs")
        if not api_key:
            return APIResponse(success=False, message="No ElevenLabs API key configured", data={})
        
        from livekit.plugins import elevenlabs
        tts = elevenlabs.TTS(api_key=api_key)
        voices = await tts.list_voices()
        
        voice_dict = {}
        for voice in voices:
            # Include voice name and category for better UX
            voice_dict[voice.id] = f"{voice.name} - {voice.category or 'Custom'}"
        
        return APIResponse(success=True, message="ElevenLabs voices", data=voice_dict)
        
    except Exception as e:
        logger.warning(f"Failed to fetch ElevenLabs voices: {e}")
        # Return fallback voices that should work with most accounts
        fallback_voices = {
            "21m00Tcm4TlvDq8ikWAM": "Rachel - American female",
            "AZnzlk1XvdvUeBnXmlld": "Domi - American female", 
            "EXAVITQu4vr4xnSDxMaL": "Bella - American female",
            "ErXwobaYiN019PkySvjV": "Antoni - American male",
            "MF3mGyEYCl7XYWbV9V6O": "Elli - American female",
            "TxGEqnHWrfWFTfGW9XjX": "Josh - American male"
        }
        return APIResponse(success=True, message="ElevenLabs voices (fallback)", data=fallback_voices)


async def _get_cartesia_voices():
    """Get available voices from Cartesia API or return fallback"""
    from core.api_key_manager import api_key_manager
    
    try:
        api_key = await api_key_manager.get_api_key("cartesia")
        if not api_key:
            return APIResponse(success=False, message="No Cartesia API key configured", data={})
        
        # Try to fetch from API - Cartesia has a voices endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.cartesia.ai/voices",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Cartesia-Version": "2025-04-16"
                }
            )
            
            if response.status_code == 200:
                voices_data = response.json()
                logger.info(f"Cartesia API response type: {type(voices_data)}")
                logger.info(f"Cartesia API response sample: {str(voices_data)[:200]}...")
                
                voice_dict = {}
                
                # Handle different response formats
                if isinstance(voices_data, list):
                    for voice in voices_data:
                        if isinstance(voice, dict) and 'id' in voice:
                            voice_dict[voice["id"]] = f"{voice.get('name', 'Voice')} - {voice.get('description', 'Custom voice')}"
                elif isinstance(voices_data, dict) and 'voices' in voices_data:
                    for voice in voices_data['voices']:
                        if isinstance(voice, dict) and 'id' in voice:
                            voice_dict[voice["id"]] = f"{voice.get('name', 'Voice')} - {voice.get('description', 'Custom voice')}"
                
                if voice_dict:
                    return APIResponse(success=True, message="Cartesia voices", data=voice_dict)
        
    except Exception as e:
        logger.warning(f"Failed to fetch Cartesia voices: {e}")
    
    # Return fallback voices that should work with most accounts
    fallback_voices = {
        "794f9389-aac1-45b6-b726-9d9369183238": "Greeter - Professional and welcoming",
        "156fb8d2-335b-4950-9cb3-a2d33befec77": "Assistant - Helpful and clear", 
        "6f84f4b8-58a2-430c-8c79-688dad597532": "Casual - Friendly and relaxed",
        "39b376fc-488e-4d0c-8b37-e00b72059fdd": "Formal - Business-appropriate"
    }
    return APIResponse(success=True, message="Cartesia voices (fallback)", data=fallback_voices)


async def _get_cartesia_models():
    """Get available TTS models from Cartesia or return fallback"""
    from core.api_key_manager import api_key_manager
    
    try:
        api_key = await api_key_manager.get_api_key("cartesia")
        if not api_key:
            return APIResponse(success=False, message="No Cartesia API key configured", data={})
        
        # Cartesia models are documented in their TTS docs - they don't have a models endpoint
        # So we return the current available models with API validation
        async with httpx.AsyncClient() as client:
            # Test the API key by making a simple request to check if it's valid
            test_response = await client.get(
                "https://api.cartesia.ai/voices", 
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Cartesia-Version": "2025-04-16"
                }
            )
            
            if test_response.status_code == 200:
                # API key is valid, return the current models
                models = {
                    "sonic-2": "Sonic 2 - Balanced quality and speed (recommended)",
                    "sonic-lite": "Sonic Lite - Fast generation",
                    "sonic-turbo": "Sonic Turbo - Fastest generation (40ms latency)",
                    "sonic-2-2025-03-07": "Sonic 2 (2025-03-07) - Latest with voice controls"
                }
                return APIResponse(success=True, message="Cartesia TTS models", data=models)
        
    except Exception as e:
        logger.warning(f"Failed to validate Cartesia API key for models: {e}")
    
    # Return fallback models
    fallback_models = {
        "sonic-2": "Sonic 2 - Balanced quality and speed",
        "sonic-lite": "Sonic Lite - Fast generation", 
        "sonic-turbo": "Sonic Turbo - Fastest generation",
        "sonic-2-2025-03-07": "Sonic 2 (2025-03-07) - Latest with voice controls"
    }
    return APIResponse(success=True, message="Cartesia TTS models (fallback)", data=fallback_models)


@app.get("/models/tts/{provider}", response_model=APIResponse)
async def list_tts_models(provider: str):
    """Get available TTS models for a given provider"""
    provider = provider.lower()
    
    try:
        if provider == "elevenlabs":
            # ElevenLabs models as of late 2024
            models = {
                "eleven_turbo_v2_5": "Turbo v2.5 - Fast and efficient (supports multiple languages)",
                "eleven_turbo_v2": "Turbo v2 - Fast generation",
                "eleven_multilingual_v2": "Multilingual v2 - Multiple language support",
                "eleven_multilingual_v1": "Multilingual v1 - Legacy multilingual",
                "eleven_monolingual_v1": "Monolingual v1 - English only",
                "eleven_flash_v2": "Flash v2 - Ultra-fast generation"
            }
            return APIResponse(success=True, message="ElevenLabs TTS models", data=models)
            
        elif provider == "cartesia":
            return await _get_cartesia_models()
            
        elif provider == "openai":
            # OpenAI only has one TTS model series
            models = {
                "tts-1": "TTS-1 - Standard quality",
                "tts-1-hd": "TTS-1-HD - High definition quality"
            }
            return APIResponse(success=True, message="OpenAI TTS models", data=models)
            
        else:
            return APIResponse(success=False, message="Provider not supported for TTS models", data={})
            
    except Exception as e:
        logger.error(f"Error fetching TTS models for {provider}: {e}")
        return APIResponse(success=False, message=f"Failed to fetch TTS models: {str(e)}", data={})

@app.get("/models/{provider}/{model_id}/compatibility", response_model=APIResponse)
async def check_model_compatibility(provider: str, model_id: str):
    """Check tool compatibility and get recommendations for a specific model"""
    try:
        from utils.model_compatibility import get_tool_support_recommendation
        
        recommendation = await get_tool_support_recommendation(model_id, provider)
        
        return APIResponse(
            success=True,
            message=f"Compatibility info for {provider}:{model_id}",
            data=recommendation
        )
    except Exception as e:
        logger.error(f"Error checking model compatibility: {e}")
        return APIResponse(
            success=False,
            message=f"Failed to check compatibility: {str(e)}",
            data={}
        )

@app.post("/presets/{preset_id}/validate", response_model=APIResponse)
async def validate_preset_configuration(preset_id: str, manager = Depends(get_preset_manager)):
    """Validate a preset configuration and suggest improvements"""
    try:
        preset = await manager.get_preset(preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail="Preset not found")
        
        from utils.model_compatibility import get_tool_support_recommendation
        
        # Check LLM compatibility
        llm_recommendation = await get_tool_support_recommendation(
            preset.llm_config.model, 
            preset.llm_config.provider
        )
        
        # Generate validation results
        validation = {
            "preset_id": preset_id,
            "model_compatibility": llm_recommendation,
            "recommendations": [],
            "warnings": [],
            "auto_fixes": {}
        }
        
        # Add recommendations based on compatibility
        if not llm_recommendation["supports_tools"]:
            validation["warnings"].append(
                f"Model {preset.llm_config.model} doesn't support function calls"
            )
            if preset.llm_config.parallel_tool_calls:
                validation["recommendations"].append(
                    "Disable parallel_tool_calls for better compatibility"
                )
                validation["auto_fixes"]["parallel_tool_calls"] = False
                
            if preset.mcp_server_ids:
                validation["recommendations"].append(
                    "Consider removing MCP servers as they won't be accessible without tool support"
                )
        
        elif not llm_recommendation["supports_parallel_tools"]:
            if preset.llm_config.parallel_tool_calls:
                validation["recommendations"].append(
                    "Disable parallel_tool_calls - this model only supports basic tool calls"
                )
                validation["auto_fixes"]["parallel_tool_calls"] = False
        
        return APIResponse(
            success=True,
            message="Preset validation complete",
            data=validation
        )
        
    except Exception as e:
        logger.error(f"Error validating preset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-defaults", response_model=APIResponse)
async def create_default_presets_endpoint(manager = Depends(get_preset_manager)):
    """Create default preset configurations"""
    try:
        success = await manager.create_default_presets()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create default presets")
        
        return APIResponse(
            success=True,
            message="Default presets created successfully"
        )
    except Exception as e:
        logger.error(f"Error creating default presets: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating default presets: {e}")

if __name__ == "__main__":
    port = int(os.getenv("PRESET_API_PORT", 8083))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)  # disable auto-reload to avoid crashes 