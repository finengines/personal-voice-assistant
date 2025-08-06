#!/usr/bin/env python3
"""
API Key Management API

This module provides REST API endpoints for managing encrypted API keys
for various AI service providers.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator

from core.api_key_manager import api_key_manager

logger = logging.getLogger("api-key-api")

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


class APIKeyRequest(BaseModel):
    """Request model for storing API keys"""
    provider: str
    api_key: str
    key_name: Optional[str] = None
    
    @validator('provider')
    def validate_provider(cls, v):
        allowed_providers = [
            'openai', 'deepgram', 'elevenlabs', 'cartesia', 'groq',
            'anthropic', 'google', 'azure', 'aws'
        ]
        if v.lower() not in allowed_providers:
            raise ValueError(f"Provider must be one of: {', '.join(allowed_providers)}")
        return v.lower()
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("API key must be at least 10 characters long")
        return v.strip()


class APIKeyResponse(BaseModel):
    """Response model for API key operations"""
    success: bool
    message: str
    provider: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@router.get("/", response_model=Dict[str, Any])
async def list_api_keys():
    """List all API key providers with status"""
    try:
        providers = await api_key_manager.list_providers()
        return {
            "success": True,
            "providers": providers,
            "message": f"Found {len(providers)} providers with API keys"
        }
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to list API keys")


@router.post("/", response_model=APIKeyResponse)
async def store_api_key(request: APIKeyRequest):
    """Store an encrypted API key"""
    try:
        success = await api_key_manager.store_api_key(
            provider=request.provider,
            api_key=request.api_key,
            key_name=request.key_name
        )
        
        if success:
            return APIKeyResponse(
                success=True,
                message=f"API key stored successfully for {request.provider}",
                provider=request.provider
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to store API key")
            
    except Exception as e:
        logger.error(f"Error storing API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{provider}/test", response_model=Dict[str, Any])
async def test_api_key(provider: str):
    """Test if an API key is valid"""
    try:
        result = await api_key_manager.test_api_key(provider.lower())
        return {
            "success": True,
            "test_result": result
        }
    except Exception as e:
        logger.error(f"Error testing API key for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to test API key")


@router.delete("/{provider}", response_model=APIKeyResponse)
async def delete_api_key(provider: str):
    """Delete an API key"""
    try:
        success = await api_key_manager.delete_api_key(provider.lower())
        
        if success:
            return APIKeyResponse(
                success=True,
                message=f"API key deleted successfully for {provider}",
                provider=provider.lower()
            )
        else:
            raise HTTPException(status_code=404, detail="API key not found")
            
    except Exception as e:
        logger.error(f"Error deleting API key for {provider}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{provider}/status", response_model=Dict[str, Any])
async def get_api_key_status(provider: str):
    """Get status of an API key without revealing the key"""
    try:
        providers = await api_key_manager.list_providers()
        provider_info = providers.get(provider.lower())
        
        if provider_info:
            return {
                "success": True,
                "provider": provider.lower(),
                "status": provider_info
            }
        else:
            return {
                "success": False,
                "provider": provider.lower(),
                "message": "No API key found for this provider"
            }
            
    except Exception as e:
        logger.error(f"Error getting API key status for {provider}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get API key status")