#!/usr/bin/env python3
"""
API Key Manager

This module provides secure storage and retrieval of API keys for various
AI service providers with encryption and database persistence.
"""

import os
import logging
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime

from core.database import Base, get_db_session

logger = logging.getLogger("api-key-manager")

# Encryption key from environment or generate one
ENCRYPTION_KEY = os.getenv("API_KEY_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Generate a key and save it to environment for production
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    logger.warning("⚠️  Generated new encryption key. Save this to API_KEY_ENCRYPTION_KEY environment variable!")
    logger.warning(f"API_KEY_ENCRYPTION_KEY={ENCRYPTION_KEY}")

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


class APIKey(Base):
    """API Key storage model with encryption"""
    __tablename__ = "api_keys"
    
    __table_args__ = {'extend_existing': True}

    provider = Column(String(100), primary_key=True)  # openai, deepgram, elevenlabs, etc.
    encrypted_key = Column(Text, nullable=False)  # Encrypted API key
    key_name = Column(String(200), nullable=True)  # Optional name/description
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class APIKeyManager:
    """Secure API key management"""
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
    
    def _encrypt_key(self, api_key: str) -> str:
        """Encrypt an API key"""
        return fernet.encrypt(api_key.encode()).decode()
    
    def _decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt an API key"""
        return fernet.decrypt(encrypted_key.encode()).decode()
    
    async def store_api_key(
        self, 
        provider: str, 
        api_key: str, 
        key_name: Optional[str] = None
    ) -> bool:
        """Store an encrypted API key"""
        try:
            encrypted_key = self._encrypt_key(api_key)
            
            async with get_db_session() as session:
                # Check if key exists
                result = await session.execute(
                    select(APIKey).where(APIKey.provider == provider)
                )
                existing_key = result.scalar_one_or_none()
                
                if existing_key:
                    # Update existing key
                    await session.execute(
                        update(APIKey)
                        .where(APIKey.provider == provider)
                        .values(
                            encrypted_key=encrypted_key,
                            key_name=key_name,
                            updated_at=datetime.utcnow()
                        )
                    )
                    logger.info(f"Updated API key for provider: {provider}")
                else:
                    # Create new key
                    new_key = APIKey(
                        provider=provider,
                        encrypted_key=encrypted_key,
                        key_name=key_name
                    )
                    session.add(new_key)
                    logger.info(f"Stored new API key for provider: {provider}")
                
                await session.commit()
                
                # Update cache
                self._cache[provider] = api_key
                return True
                
        except Exception as e:
            logger.error(f"Error storing API key for {provider}: {e}")
            return False
    
    async def get_api_key(self, provider: str) -> Optional[str]:
        """Retrieve and decrypt an API key"""
        # Check cache first
        if provider in self._cache:
            if not self._cache[provider]:
                logger.warning(f"API key for {provider} is empty or None in cache")
            return self._cache[provider]
        
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(APIKey).where(APIKey.provider == provider)
                )
                api_key_record = result.scalar_one_or_none()
                
                if api_key_record:
                    decrypted_key = self._decrypt_key(api_key_record.encrypted_key)
                    # Cache the decrypted key
                    self._cache[provider] = decrypted_key
                    return decrypted_key
                    
        except Exception as e:
            logger.error(f"Error retrieving API key for {provider}: {e}")
        
        # Fallback to environment variable
        env_key = os.getenv(f"{provider.upper()}_API_KEY")
        if env_key:
            logger.info(f"Using environment variable for {provider} API key")
            return env_key
            
        return None
    
    async def delete_api_key(self, provider: str) -> bool:
        """Delete an API key"""
        try:
            async with get_db_session() as session:
                await session.execute(
                    delete(APIKey).where(APIKey.provider == provider)
                )
                await session.commit()
                
                # Remove from cache
                self._cache.pop(provider, None)
                
                logger.info(f"Deleted API key for provider: {provider}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting API key for {provider}: {e}")
            return False
    
    async def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """List all providers with key information (without exposing keys)"""
        providers = {}
        
        try:
            async with get_db_session() as session:
                result = await session.execute(select(APIKey))
                api_keys = result.scalars().all()
                
                for api_key in api_keys:
                    providers[api_key.provider] = {
                        'key_name': api_key.key_name,
                        'created_at': api_key.created_at.isoformat(),
                        'updated_at': api_key.updated_at.isoformat(),
                        'has_key': True,
                        'source': 'database'
                    }
                    
        except Exception as e:
            logger.error(f"Error listing providers: {e}")
        
        # Also check environment variables
        env_providers = [
            'OPENAI', 'DEEPGRAM', 'ELEVENLABS', 'CARTESIA', 'GROQ', 
            'ANTHROPIC', 'GOOGLE', 'OPENROUTER', 'AZURE', 'AWS'
        ]
        
        for provider in env_providers:
            env_key = os.getenv(f"{provider}_API_KEY")
            if env_key and provider.lower() not in providers:
                providers[provider.lower()] = {
                    'key_name': f"Environment Variable ({provider}_API_KEY)",
                    'created_at': None,
                    'updated_at': None,
                    'has_key': True,
                    'source': 'environment'
                }
        
        return providers
    
    async def test_api_key(self, provider: str) -> Dict[str, Any]:
        """Test if an API key is working (basic validation)"""
        api_key = await self.get_api_key(provider)
        
        if not api_key:
            return {
                'valid': False,
                'error': 'No API key found',
                'provider': provider
            }
        
        # Basic format validation
        valid_formats = {
            'openai': lambda k: k.startswith('sk-') and len(k) > 40,
            'deepgram': lambda k: len(k) > 30,
            'elevenlabs': lambda k: len(k) > 20,
            'cartesia': lambda k: len(k) > 20,
            'groq': lambda k: k.startswith('gsk_') and len(k) > 40,
            'anthropic': lambda k: k.startswith('sk-ant-') and len(k) > 40,
            'google': lambda k: len(k) > 30,
            'openrouter': lambda k: len(k) > 20,
        }
        
        format_check = valid_formats.get(provider, lambda k: len(k) > 10)
        
        if not format_check(api_key):
            return {
                'valid': False,
                'error': 'Invalid API key format',
                'provider': provider
            }
        
        return {
            'valid': True,
            'provider': provider,
            'key_preview': f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        }


# Global instance
api_key_manager = APIKeyManager()