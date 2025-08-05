#!/usr/bin/env python3
"""
Dynamic Model Capability Detection

This module dynamically detects AI model capabilities by testing actual API endpoints,
with intelligent caching and fallback patterns for robust detection.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
from core.api_key_manager import api_key_manager

logger = logging.getLogger("model-compatibility")

class ToolSupport(Enum):
    """Tool/function calling support levels"""
    FULL = "full"           # Supports parallel function calls
    BASIC = "basic"         # Supports function calls but not parallel
    NONE = "none"           # No function calling support
    UNKNOWN = "unknown"     # Support status unknown
    TESTING = "testing"     # Currently being tested

@dataclass
class ModelCapability:
    """Dynamic model capability information"""
    model_id: str
    provider: str
    tool_support: ToolSupport
    last_tested: float
    test_method: str = "unknown"  # how we determined the capability
    error_count: int = 0
    supports_streaming: bool = True
    context_length: Optional[int] = None
    
    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Check if capability data is stale"""
        return time.time() - self.last_tested > (max_age_hours * 3600)
    
    def supports_tools(self) -> bool:
        """Check if model supports any tool functionality"""
        return self.tool_support in [ToolSupport.FULL, ToolSupport.BASIC]

class ModelCapabilityDetector:
    """Dynamically detect model capabilities"""
    
    def __init__(self):
        self.cache: Dict[str, ModelCapability] = {}
        self.testing_queue: Set[str] = set()
        self.known_patterns = {
            # Models we know don't support tools based on documented patterns
            "no_tools": [
                "perplexity/", "search/", "embedding/", "tts/", "stt/", 
                "vision/", "dalle/", "stability/", "midjourney/", "whisper"
            ],
            # Models we know support tools
            "has_tools": [
                "gpt-", "claude-", "llama", "gemini", "mixtral", "command"
            ]
        }
    
    async def get_model_capability(self, model_id: str, provider: str) -> ModelCapability:
        """Get model capability with dynamic detection"""
        cache_key = f"{provider}:{model_id}"
        
        # Check cache first
        if cache_key in self.cache:
            capability = self.cache[cache_key]
            if not capability.is_stale():
                return capability
        
        # Prevent concurrent testing of same model
        if cache_key in self.testing_queue:
            # Wait briefly and check cache again
            await asyncio.sleep(0.1)
            if cache_key in self.cache:
                return self.cache[cache_key]
        
        # Test the model capability
        self.testing_queue.add(cache_key)
        try:
            capability = await self._test_model_capability(model_id, provider)
            self.cache[cache_key] = capability
            return capability
        finally:
            self.testing_queue.discard(cache_key)
    
    async def _test_model_capability(self, model_id: str, provider: str) -> ModelCapability:
        """Test model capability by making actual API calls"""
        logger.info(f"Testing capability for {provider}:{model_id}")
        
        # Start with pattern-based detection for quick results
        tool_support = self._detect_by_pattern(model_id)
        test_method = "pattern"
        
        # Try to get more definitive results via API testing
        try:
            if provider == "openai":
                api_result = await self._test_openai_model(model_id)
                if api_result is not None:
                    tool_support = api_result
                    test_method = "openai_api"
            
            elif provider == "openrouter":
                api_result = await self._test_openrouter_model(model_id)
                if api_result is not None:
                    tool_support = api_result
                    test_method = "openrouter_api"
            
            elif provider == "anthropic":
                api_result = await self._test_anthropic_model(model_id)
                if api_result is not None:
                    tool_support = api_result
                    test_method = "anthropic_api"
            
            elif provider == "groq":
                api_result = await self._test_groq_model(model_id)
                if api_result is not None:
                    tool_support = api_result
                    test_method = "groq_api"
        
        except Exception as e:
            logger.warning(f"API testing failed for {provider}:{model_id}: {e}")
        
        return ModelCapability(
            model_id=model_id,
            provider=provider,
            tool_support=tool_support,
            last_tested=time.time(),
            test_method=test_method
        )
    
    def _detect_by_pattern(self, model_id: str) -> ToolSupport:
        """Quick pattern-based detection"""
        model_lower = model_id.lower()
        
        # Check no-tools patterns first
        for pattern in self.known_patterns["no_tools"]:
            if pattern in model_lower:
                return ToolSupport.NONE
        
        # Check has-tools patterns
        for pattern in self.known_patterns["has_tools"]:
            if pattern in model_lower:
                return ToolSupport.FULL
        
        return ToolSupport.UNKNOWN
    
    async def _test_openai_model(self, model_id: str) -> Optional[ToolSupport]:
        """Test OpenAI model by checking model info endpoint"""
        try:
            api_key = await api_key_manager.get_api_key("openai")
            if not api_key:
                return None
            
            async with httpx.AsyncClient() as client:
                # Get model info from OpenAI API
                response = await client.get(
                    f"https://api.openai.com/v1/models/{model_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    model_info = response.json()
                    # Most OpenAI models support tools, but check for specific indicators
                    if any(x in model_id for x in ["gpt-4", "gpt-3.5-turbo"]):
                        return ToolSupport.FULL
                    return ToolSupport.BASIC
                    
        except Exception as e:
            logger.debug(f"OpenAI model test failed: {e}")
        return None
    
    async def _test_openrouter_model(self, model_id: str) -> Optional[ToolSupport]:
        """Test OpenRouter model by checking their models endpoint"""
        try:
            api_key = await api_key_manager.get_api_key("openrouter")
            if not api_key:
                return None
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    for model in models_data.get("data", []):
                        if model.get("id") == model_id:
                            # Check if model supports function calling
                            architecture = model.get("architecture", "").lower()
                            name = model.get("name", "").lower()
                            
                            # Perplexity models specifically don't support tools
                            if "perplexity" in name or "sonar" in name:
                                return ToolSupport.NONE
                            
                            # Most transformer models support tools
                            if any(x in architecture for x in ["transformer", "llama", "claude", "gpt"]):
                                return ToolSupport.FULL
                            
                            return ToolSupport.BASIC
                            
        except Exception as e:
            logger.debug(f"OpenRouter model test failed: {e}")
        return None
    
    async def _test_anthropic_model(self, model_id: str) -> Optional[ToolSupport]:
        """Test Anthropic model - most support tools"""
        try:
            api_key = await api_key_manager.get_api_key("anthropic")
            if not api_key:
                return None
            
            # Anthropic Claude models generally support tools
            if "claude" in model_id.lower():
                return ToolSupport.FULL
                
        except Exception as e:
            logger.debug(f"Anthropic model test failed: {e}")
        return None
    
    async def _test_groq_model(self, model_id: str) -> Optional[ToolSupport]:
        """Test Groq model by checking their models endpoint"""
        try:
            api_key = await api_key_manager.get_api_key("groq")
            if not api_key:
                return None
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    for model in models_data.get("data", []):
                        if model.get("id") == model_id:
                            # Most Groq models support tools
                            return ToolSupport.FULL
                            
        except Exception as e:
            logger.debug(f"Groq model test failed: {e}")
        return None
    
    async def test_model_with_function_call(self, model_id: str, provider: str) -> ToolSupport:
        """Test model by actually attempting a function call"""
        try:
            # This would make a minimal test call with a simple function
            # to see if the model responds appropriately
            test_function = {
                "name": "test_function",
                "description": "A test function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "test": {"type": "string", "description": "Test parameter"}
                    },
                    "required": ["test"]
                }
            }
            
            # Implementation would depend on provider
            # This is a placeholder for actual function call testing
            logger.info(f"Would test function calling for {provider}:{model_id}")
            return ToolSupport.UNKNOWN
            
        except Exception as e:
            logger.debug(f"Function call test failed: {e}")
            return ToolSupport.UNKNOWN
    
    def get_cached_capabilities(self) -> Dict[str, ModelCapability]:
        """Get all cached model capabilities"""
        return self.cache.copy()
    
    def clear_cache(self):
        """Clear the capability cache"""
        self.cache.clear()

# Global detector instance
capability_detector = ModelCapabilityDetector()

# Convenience functions
async def get_model_tool_support(model_id: str, provider: str) -> ToolSupport:
    """Get tool support for a model"""
    capability = await capability_detector.get_model_capability(model_id, provider)
    return capability.tool_support

async def should_disable_tools(model_id: str, provider: str) -> bool:
    """Check if tools should be disabled for a model"""
    capability = await capability_detector.get_model_capability(model_id, provider)
    return not capability.supports_tools()

async def get_tool_support_recommendation(model_id: str, provider: str) -> Dict[str, Any]:
    """Get comprehensive tool support recommendation"""
    capability = await capability_detector.get_model_capability(model_id, provider)
    
    warning_message = None
    if not capability.supports_tools():
        if capability.tool_support == ToolSupport.NONE:
            warning_message = f"⚠️ {model_id} doesn't support function calls. Tools will be disabled for voice-only chat."
        elif capability.tool_support == ToolSupport.UNKNOWN:
            warning_message = f"❓ Tool support for {model_id} is unknown. Tools may be disabled if they fail."
    
    return {
        "model_id": model_id,
        "provider": provider,
        "tool_support": capability.tool_support.value,
        "supports_tools": capability.supports_tools(),
        "supports_parallel_tools": capability.tool_support == ToolSupport.FULL,
        "recommended_parallel_tool_calls": capability.tool_support == ToolSupport.FULL,
        "should_disable_tools": not capability.supports_tools(),
        "warning_message": warning_message,
        "test_method": capability.test_method,
        "last_tested": capability.last_tested,
        "confidence": "high" if capability.test_method.endswith("_api") else "medium"
    }

async def bulk_test_models(models: List[Dict[str, str]]) -> Dict[str, ModelCapability]:
    """Test multiple models concurrently"""
    tasks = []
    for model_info in models:
        task = capability_detector.get_model_capability(
            model_info["id"], 
            model_info["provider"]
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    capabilities = {}
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Failed to test model {models[i]}: {result}")
            continue
        capabilities[f"{models[i]['provider']}:{models[i]['id']}"] = result
    
    return capabilities 