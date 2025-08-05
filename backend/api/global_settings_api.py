#!/usr/bin/env python3
"""
Global Settings API

This module provides FastAPI endpoints for managing global application settings,
including the global system prompt that applies to all agents.
"""

import logging
from typing import Optional, Any
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.global_settings_manager import global_settings_manager, GlobalSettingsConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("global-settings-api")

# FastAPI app
app = FastAPI(
    title="Global Settings API",
    description="API for managing global application settings",
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
class GlobalSettingsAPI(BaseModel):
    global_system_prompt: Optional[str] = Field(None, description="Global system prompt applied to all agents")
    enabled: bool = Field(True, description="Whether the global prompt is enabled")

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

# Dependency
async def get_global_settings_manager():
    """Dependency to get global settings manager"""
    return global_settings_manager

@app.on_event("startup")
async def startup():
    """Initialize the API on startup"""
    logger.info("🚀 Global Settings API starting up...")
    
    # Initialize database and create default settings if needed
    try:
        from core.database import init_db
        await init_db()
        logger.info("✅ Database initialized")
        
        # Create default global settings if none exist
        settings = await global_settings_manager.get_global_settings()
        logger.info(f"✅ Global settings loaded: enabled={settings.enabled}")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Global Settings API: {e}")
        raise

@app.get("/health", response_model=APIResponse)
async def health_endpoint():
    """Health check endpoint"""
    try:
        from core.database import health_check
        db_healthy = await health_check()
        
        if db_healthy:
            return APIResponse(
                success=True,
                message="Global Settings API is healthy",
                data={"database": "healthy"}
            )
        else:
            return APIResponse(
                success=False,
                message="Database health check failed",
                data={"database": "unhealthy"}
            )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Health check failed: {str(e)}",
            data={"error": str(e)}
        )

@app.get("/settings", response_model=APIResponse)
async def get_global_settings(manager = Depends(get_global_settings_manager)):
    """Get current global settings"""
    try:
        settings = await manager.get_global_settings()
        return APIResponse(
            success=True,
            message="Global settings retrieved successfully",
            data=settings.to_dict()
        )
    except Exception as e:
        logger.error(f"Failed to get global settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get global settings: {str(e)}")

@app.put("/settings", response_model=APIResponse)
async def update_global_settings(
    settings_data: GlobalSettingsAPI,
    manager = Depends(get_global_settings_manager)
):
    """Update global settings"""
    try:
        config = GlobalSettingsConfig(
            global_system_prompt=settings_data.global_system_prompt,
            enabled=settings_data.enabled
        )
        
        success = await manager.update_global_settings(config)
        
        if success:
            return APIResponse(
                success=True,
                message="Global settings updated successfully",
                data=config.to_dict()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to update global settings")
            
    except Exception as e:
        logger.error(f"Failed to update global settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update global settings: {str(e)}")

@app.get("/settings/prompt", response_model=APIResponse)
async def get_global_system_prompt(manager = Depends(get_global_settings_manager)):
    """Get the current global system prompt"""
    try:
        prompt = await manager.get_global_system_prompt()
        return APIResponse(
            success=True,
            message="Global system prompt retrieved successfully",
            data={"global_system_prompt": prompt}
        )
    except Exception as e:
        logger.error(f"Failed to get global system prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get global system prompt: {str(e)}")

@app.put("/settings/prompt", response_model=APIResponse)
async def update_global_system_prompt(
    prompt_data: GlobalSettingsAPI,
    manager = Depends(get_global_settings_manager)
):
    """Update the global system prompt"""
    try:
        success = await manager.update_global_system_prompt(
            prompt_data.global_system_prompt,
            prompt_data.enabled
        )
        
        if success:
            return APIResponse(
                success=True,
                message="Global system prompt updated successfully",
                data={
                    "global_system_prompt": prompt_data.global_system_prompt,
                    "enabled": prompt_data.enabled
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to update global system prompt")
            
    except Exception as e:
        logger.error(f"Failed to update global system prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update global system prompt: {str(e)}")

@app.post("/settings/prompt/enable", response_model=APIResponse)
async def enable_global_prompt(
    enabled: bool = True,
    manager = Depends(get_global_settings_manager)
):
    """Enable or disable the global system prompt"""
    try:
        success = await manager.enable_global_prompt(enabled)
        
        if success:
            return APIResponse(
                success=True,
                message=f"Global system prompt {'enabled' if enabled else 'disabled'} successfully",
                data={"enabled": enabled}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to update global prompt status")
            
    except Exception as e:
        logger.error(f"Failed to update global prompt status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update global prompt status: {str(e)}")

@app.get("/settings/preview", response_model=APIResponse)
async def preview_combined_prompt(
    agent_prompt: str,
    manager = Depends(get_global_settings_manager)
):
    """Preview how the global prompt would be combined with an agent prompt"""
    try:
        global_prompt = await manager.get_global_system_prompt()
        
        if global_prompt:
            combined = f"{global_prompt}\n\n{agent_prompt}"
            return APIResponse(
                success=True,
                message="Combined prompt preview generated successfully",
                data={
                    "global_prompt": global_prompt,
                    "agent_prompt": agent_prompt,
                    "combined_prompt": combined
                }
            )
        else:
            return APIResponse(
                success=True,
                message="No global prompt set",
                data={
                    "global_prompt": None,
                    "agent_prompt": agent_prompt,
                    "combined_prompt": agent_prompt
                }
            )
            
    except Exception as e:
        logger.error(f"Failed to generate prompt preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate prompt preview: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084) 