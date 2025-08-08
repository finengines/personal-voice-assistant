#!/usr/bin/env python3
"""
Agent Preset Database Manager

This module provides database operations for agent preset management,
handling CRUD operations and configuration loading.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from core.database import get_db_session, AgentPreset
from core.agent_config import AgentPresetConfig, VoiceConfig, LLMConfig, STTConfig, AgentConfig, create_default_presets


class PresetManager:
    """Database manager for agent preset operations"""
    
    def __init__(self):
        self._cache: Dict[str, AgentPresetConfig] = {}
        self._cache_dirty = True
    
    async def load_all_presets(self) -> Dict[str, AgentPresetConfig]:
        """Load all agent presets from database"""
        if not self._cache_dirty and self._cache:
            return self._cache.copy()
        
        async with get_db_session() as session:
            result = await session.execute(select(AgentPreset))
            db_presets = result.scalars().all()
            
            presets = {}
            for db_preset in db_presets:
                config = self._db_to_config(db_preset)
                presets[config.id] = config
            
            self._cache = presets
            self._cache_dirty = False
            return presets

    async def load_all_presets_fresh(self) -> Dict[str, AgentPresetConfig]:
        """Force refresh the preset cache and return latest presets.
        Used by the agent worker at session start to avoid stale IDs."""
        self._cache_dirty = True
        return await self.load_all_presets()
    
    async def get_preset(self, preset_id: str) -> Optional[AgentPresetConfig]:
        """Get a specific preset by ID"""
        presets = await self.load_all_presets()
        return presets.get(preset_id)
    
    async def get_default_preset(self) -> Optional[AgentPresetConfig]:
        """Get the default preset"""
        presets = await self.load_all_presets()
        for preset in presets.values():
            if preset.is_default:
                return preset
        return None
    
    async def save_preset(self, config: AgentPresetConfig) -> bool:
        """Save or update a preset configuration"""
        try:
            async with get_db_session() as session:
                # Check if preset exists
                result = await session.execute(
                    select(AgentPreset).where(AgentPreset.id == config.id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing preset
                    update_data = self._config_to_dict(config)
                    update_data['updated_at'] = datetime.utcnow()
                    
                    await session.execute(
                        update(AgentPreset)
                        .where(AgentPreset.id == config.id)
                        .values(**update_data)
                    )
                else:
                    # Create new preset
                    db_preset = AgentPreset(**self._config_to_dict(config))
                    session.add(db_preset)
                
                await session.commit()
                self._cache_dirty = True
                return True
                
        except Exception as e:
            print(f"Error saving preset {config.id}: {e}")
            return False
    
    async def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset configuration"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    delete(AgentPreset).where(AgentPreset.id == preset_id)
                )
                
                if result.rowcount > 0:
                    await session.commit()
                    self._cache_dirty = True
                    return True
                return False
                
        except Exception as e:
            print(f"Error deleting preset {preset_id}: {e}")
            return False
    
    async def set_default_preset(self, preset_id: str) -> bool:
        """Set a preset as the default"""
        try:
            async with get_db_session() as session:
                # First, unset all defaults
                await session.execute(
                    update(AgentPreset).values(is_default=False)
                )
                
                # Then set the new default
                result = await session.execute(
                    update(AgentPreset)
                    .where(AgentPreset.id == preset_id)
                    .values(is_default=True, updated_at=datetime.utcnow())
                )
                
                if result.rowcount > 0:
                    await session.commit()
                    self._cache_dirty = True
                    return True
                return False
                
        except Exception as e:
            print(f"Error setting default preset {preset_id}: {e}")
            return False
    
    async def list_enabled_presets(self) -> List[AgentPresetConfig]:
        """Get all enabled presets"""
        presets = await self.load_all_presets()
        return [preset for preset in presets.values() if preset.enabled]
    
    async def enable_preset(self, preset_id: str, enabled: bool = True) -> bool:
        """Enable or disable a preset"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    update(AgentPreset)
                    .where(AgentPreset.id == preset_id)
                    .values(enabled=enabled, updated_at=datetime.utcnow())
                )
                
                if result.rowcount > 0:
                    await session.commit()
                    self._cache_dirty = True
                    return True
                return False
                
        except Exception as e:
            print(f"Error updating preset {preset_id}: {e}")
            return False
    
    async def create_default_presets(self) -> bool:
        """Create default preset configurations"""
        try:
            default_presets = create_default_presets()
            
            for preset in default_presets:
                # Check if preset already exists
                existing = await self.get_preset(preset.id)
                if not existing:
                    await self.save_preset(preset)
                    print(f"✅ Created default preset: {preset.name}")
                else:
                    print(f"ℹ️  Preset already exists: {preset.name}")
            
            return True
            
        except Exception as e:
            print(f"Error creating default presets: {e}")
            return False
    
    def _db_to_config(self, db_preset: AgentPreset) -> AgentPresetConfig:
        """Convert database model to AgentPresetConfig"""
        return AgentPresetConfig(
            id=db_preset.id,
            name=db_preset.name,
            description=db_preset.description,
            system_prompt=db_preset.system_prompt,
            voice_config=VoiceConfig.from_dict(db_preset.voice_config),
            mcp_server_ids=db_preset.mcp_server_ids or [],
            llm_config=LLMConfig.from_dict(db_preset.llm_config or {}),
            stt_config=STTConfig.from_dict(db_preset.stt_config or {}),
            agent_config=AgentConfig.from_dict(db_preset.agent_config or {}),
            enabled=db_preset.enabled,
            is_default=db_preset.is_default
        )
    
    def _config_to_dict(self, config: AgentPresetConfig) -> Dict[str, Any]:
        """Convert AgentPresetConfig to database dictionary"""
        return {
            'id': config.id,
            'name': config.name,
            'description': config.description,
            'system_prompt': config.system_prompt,
            'voice_config': config.voice_config.to_dict(),
            'mcp_server_ids': config.mcp_server_ids,
            'llm_config': config.llm_config.to_dict(),
            'stt_config': config.stt_config.to_dict(),
            'agent_config': config.agent_config.to_dict(),
            'enabled': config.enabled,
            'is_default': config.is_default
        }


# Global preset manager instance
preset_manager = PresetManager() 