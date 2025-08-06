#!/usr/bin/env python3
"""
Agent Preset Configuration Management

This module provides configuration classes and management for agent presets
with support for customizable system prompts, voice configurations, and MCP server selections.
"""

import os
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, asdict
from enum import Enum
import json

@dataclass
class VoiceConfig:
    """Voice/TTS configuration for an agent preset"""
    provider: Literal["openai", "cartesia", "elevenlabs", "deepgram"] = "openai"
    voice: str = "ash"  # Voice ID or name
    model: Optional[str] = None  # TTS model (if supported)
    speed: float = 1.0  # Speech speed multiplier
    stability: Optional[float] = None  # Voice stability (ElevenLabs)
    similarity_boost: Optional[float] = None  # Similarity boost (ElevenLabs)
    style: Optional[str] = None  # Voice style/emotion
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoiceConfig':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class LLMConfig:
    """LLM configuration for an agent preset"""
    provider: Literal["openai", "anthropic", "groq", "google", "openrouter"] = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    parallel_tool_calls: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class STTConfig:
    """STT configuration for an agent preset"""
    provider: Literal["deepgram", "openai", "groq"] = "deepgram"
    model: str = "nova-3"
    language: str = "multi"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'STTConfig':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class AgentConfig:
    """Additional agent behavior configuration"""
    allow_interruptions: bool = True
    preemptive_generation: bool = False
    max_tool_steps: int = 10
    user_away_timeout: Optional[float] = None  # Seconds before considering user away
    speed_config: Optional['SpeedConfig'] = None
    
    def __post_init__(self):
        if self.speed_config is None:
            self.speed_config = SpeedConfig()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        if self.speed_config:
            result['speed_config'] = self.speed_config.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """Create from dictionary"""
        speed_config_data = data.pop('speed_config', None)
        config = cls(**data)
        if speed_config_data:
            config.speed_config = SpeedConfig.from_dict(speed_config_data)
        return config

# Speed optimization configuration
@dataclass
class SpeedConfig:
    """Speed optimization configuration"""
    preemptive_generation: bool = False  # Generate responses before user finishes
    fast_preresponse: bool = False  # Quick acknowledgment responses
    advanced_turn_detection: bool = False  # Use LiveKit's turn detection model
    audio_speedup: float = 1.0  # Audio output speedup (1.0-2.0)
    audio_speed_factor: float = 1.0  # Unified audio speed factor for processing
    min_interruption_duration: float = 0.3  # Minimum duration before allowing interruption
    min_endpointing_delay: float = 0.4  # Faster response timing
    max_endpointing_delay: float = 3.0  # Allow longer pauses for complex thoughts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpeedConfig':
        """Create from dictionary while ignoring unsupported legacy keys"""
        # Filter out keys that are not defined in the dataclass (e.g., legacy "memory_mode")
        allowed_fields = set(cls.__annotations__.keys())
        filtered = {k: v for k, v in data.items() if k in allowed_fields}
        return cls(**filtered)

@dataclass
class AgentPresetConfig:
    """Complete configuration for an agent preset"""
    id: str
    name: str
    description: str
    system_prompt: str
    voice_config: VoiceConfig
    mcp_server_ids: List[str]
    llm_config: LLMConfig
    stt_config: STTConfig
    agent_config: AgentConfig
    enabled: bool = True
    is_default: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'system_prompt': self.system_prompt,
            'voice_config': self.voice_config.to_dict(),
            'mcp_server_ids': self.mcp_server_ids,
            'llm_config': self.llm_config.to_dict(),
            'stt_config': self.stt_config.to_dict(),
            'agent_config': self.agent_config.to_dict(),
            'enabled': self.enabled,
            'is_default': self.is_default
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentPresetConfig':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            system_prompt=data['system_prompt'],
            voice_config=VoiceConfig.from_dict(data['voice_config']),
            mcp_server_ids=data.get('mcp_server_ids', []),
            llm_config=LLMConfig.from_dict(data.get('llm_config', {})),
            stt_config=STTConfig.from_dict(data.get('stt_config', {})),
            agent_config=AgentConfig.from_dict(data.get('agent_config', {})),
            enabled=data.get('enabled', True),
            is_default=data.get('is_default', False)
        )

# Predefined voice options for different providers
VOICE_OPTIONS = {
    "openai": {
        "alloy": "Alloy - Balanced and versatile",
        "ash": "Ash - Warm and engaging", 
        "ballad": "Ballad - Calm and soothing",
        "coral": "Coral - Upbeat and energetic",
        "sage": "Sage - Wise and thoughtful",
        "verse": "Verse - Creative and expressive"
    },
    "cartesia": {
        "794f9389-aac1-45b6-b726-9d9369183238": "Greeter - Professional and welcoming",
        "156fb8d2-335b-4950-9cb3-a2d33befec77": "Assistant - Helpful and clear",
        "6f84f4b8-58a2-430c-8c79-688dad597532": "Casual - Friendly and relaxed",
        "39b376fc-488e-4d0c-8b37-e00b72059fdd": "Formal - Business-appropriate"
    },
    "elevenlabs": {
        "21m00Tcm4TlvDq8ikWAM": "Rachel - American female",
        "AZnzlk1XvdvUeBnXmlld": "Domi - American female", 
        "EXAVITQu4vr4xnSDxMaL": "Bella - American female",
        "ErXwobaYiN019PkySvjV": "Antoni - American male",
        "MF3mGyEYCl7XYWbV9V6O": "Elli - American female",
        "TxGEqnHWrfWFTfGW9XjX": "Josh - American male"
    }
}

def create_default_presets() -> List[AgentPresetConfig]:
    """Create a set of default agent presets"""
    presets = []
    
    # Default Assistant with Memory
    memory_aware_prompt = """You are a helpful AI assistant with access to your personal knowledge base that contains memories and information across multiple AI applications.

You communicate via voice and provide accurate, concise, and friendly responses. You are curious, engaging, and maintain a professional yet warm tone.

Memory Guidelines:
- Use your knowledge base strategically when it can provide relevant context or personalization
- When you access memories, mention it naturally (e.g., "I remember you mentioned..." or "Based on what I know about you...")
- Store important conversation insights for future reference
- Focus on facts about the user, their preferences, projects, and important context
- Be selective about memory usage to maintain natural conversation flow

Always prioritize being helpful while building a contextual understanding of the user over time."""

    presets.append(AgentPresetConfig(
        id="default-assistant",
        name="Default Assistant",
        description="A helpful and friendly general-purpose assistant with memory capabilities",
        system_prompt=memory_aware_prompt,
        voice_config=VoiceConfig(provider="openai", voice="ash"),
        mcp_server_ids=["graphiti-memory"],  # Graphiti memory system (also loaded automatically from env vars)
        llm_config=LLMConfig(model="gpt-4o-mini", temperature=0.7),
        stt_config=STTConfig(provider="deepgram", model="nova-3", language="multi"),
        agent_config=AgentConfig(allow_interruptions=True, max_tool_steps=5),
        is_default=True
    ))
    
    # Technical Support Agent
    presets.append(AgentPresetConfig(
        id="technical-support",
        name="Technical Support",
        description="Specialized in technical troubleshooting and IT support",
        system_prompt="You are a technical support specialist. You help users troubleshoot technical issues, explain complex concepts in simple terms, and provide step-by-step solutions. You are patient, methodical, and always ask clarifying questions to better understand the problem.",
        voice_config=VoiceConfig(provider="openai", voice="sage"),
        mcp_server_ids=[],
        llm_config=LLMConfig(model="gpt-4o", temperature=0.3),
        stt_config=STTConfig(provider="deepgram", model="nova-3", language="multi"),
        agent_config=AgentConfig(allow_interruptions=True, max_tool_steps=8),
        enabled=True
    ))
    
    # Creative Storyteller
    presets.append(AgentPresetConfig(
        id="storyteller",
        name="Creative Storyteller",
        description="An engaging storyteller for creative narratives and entertainment",
        system_prompt="You are a creative storyteller with a vivid imagination. You craft engaging narratives, create interesting characters, and weave compelling stories. You adapt your storytelling style to your audience and can create both original stories and reimagine classics. You use descriptive language and maintain good pacing.",
        voice_config=VoiceConfig(provider="openai", voice="verse"),
        mcp_server_ids=[],
        llm_config=LLMConfig(model="gpt-4o", temperature=0.9),
        stt_config=STTConfig(provider="deepgram", model="nova-3", language="multi"),
        agent_config=AgentConfig(allow_interruptions=True, max_tool_steps=3),
        enabled=True
    ))
    
    # Business Professional
    presets.append(AgentPresetConfig(
        id="business-professional",
        name="Business Professional",
        description="Formal business assistant for meetings and professional communication",
        system_prompt="You are a professional business assistant. You maintain a formal yet approachable tone, provide structured responses, and focus on efficiency and clarity. You excel at summarizing information, managing schedules, and facilitating business communications.",
        voice_config=VoiceConfig(provider="cartesia", voice="39b376fc-488e-4d0c-8b37-e00b72059fdd"),
        mcp_server_ids=[],
        llm_config=LLMConfig(model="gpt-4o-mini", temperature=0.4),
        stt_config=STTConfig(provider="deepgram", model="nova-3", language="multi"),
        agent_config=AgentConfig(allow_interruptions=False, max_tool_steps=6),
        enabled=True
    ))
    
    return presets 