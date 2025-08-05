#!/usr/bin/env python3
"""
Global Settings Manager

This module provides management for global application settings,
including the global system prompt that applies to all agents.
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from dataclasses import dataclass

from core.database import get_db_session, GlobalSettings


@dataclass
class GlobalSettingsConfig:
    """Global settings configuration"""
    global_system_prompt: Optional[str] = None
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'global_system_prompt': self.global_system_prompt,
            'enabled': self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalSettingsConfig':
        """Create from dictionary"""
        return cls(
            global_system_prompt=data.get('global_system_prompt'),
            enabled=data.get('enabled', True)
        )


class GlobalSettingsManager:
    """Manager for global application settings"""
    
    def __init__(self):
        self._cache: Optional[GlobalSettingsConfig] = None
        self._cache_dirty = True
    
    async def get_global_settings(self) -> GlobalSettingsConfig:
        """Get current global settings"""
        if not self._cache_dirty and self._cache:
            return self._cache
        
        async with get_db_session() as session:
            result = await session.execute(
                select(GlobalSettings).where(GlobalSettings.id == "main")
            )
            db_settings = result.scalar_one_or_none()
            
            if db_settings:
                settings = GlobalSettingsConfig(
                    global_system_prompt=db_settings.global_system_prompt,
                    enabled=db_settings.enabled
                )
            else:
                # Create default settings if none exist
                settings = GlobalSettingsConfig()
                await self._create_default_settings(session, settings)
            
            self._cache = settings
            self._cache_dirty = False
            return settings
    
    async def get_global_system_prompt(self) -> Optional[str]:
        """Get the global system prompt if enabled"""
        settings = await self.get_global_settings()
        if settings.enabled and settings.global_system_prompt:
            return settings.global_system_prompt
        return None
    
    async def update_global_settings(self, config: GlobalSettingsConfig) -> bool:
        """Update global settings"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(GlobalSettings).where(GlobalSettings.id == "main")
                )
                db_settings = result.scalar_one_or_none()
                
                if db_settings:
                    # Update existing settings
                    await session.execute(
                        update(GlobalSettings)
                        .where(GlobalSettings.id == "main")
                        .values(
                            global_system_prompt=config.global_system_prompt,
                            enabled=config.enabled,
                            updated_at=datetime.utcnow()
                        )
                    )
                else:
                    # Create new settings
                    db_settings = GlobalSettings(
                        id="main",
                        global_system_prompt=config.global_system_prompt,
                        enabled=config.enabled
                    )
                    session.add(db_settings)
                
                await session.commit()
                self._cache_dirty = True
                return True
                
        except Exception as e:
            print(f"Error updating global settings: {e}")
            return False
    
    async def update_global_system_prompt(self, prompt: Optional[str], enabled: bool = True) -> bool:
        """Update just the global system prompt"""
        settings = await self.get_global_settings()
        settings.global_system_prompt = prompt
        settings.enabled = enabled
        return await self.update_global_settings(settings)
    
    async def enable_global_prompt(self, enabled: bool = True) -> bool:
        """Enable or disable the global system prompt"""
        settings = await self.get_global_settings()
        settings.enabled = enabled
        return await self.update_global_settings(settings)
    
    async def _create_default_settings(self, session: AsyncSession, settings: GlobalSettingsConfig):
        """Create default global settings"""
        db_settings = GlobalSettings(
            id="main",
            global_system_prompt=settings.global_system_prompt,
            enabled=settings.enabled
        )
        session.add(db_settings)
        await session.commit()


# Global instance
global_settings_manager = GlobalSettingsManager() 