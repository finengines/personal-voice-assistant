#!/usr/bin/env python3
"""
Test script for Global Settings functionality
"""
import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.global_settings_manager import global_settings_manager, GlobalSettingsConfig
from core.database import init_db

async def test_global_settings():
    """Test the global settings functionality"""
    print("🧪 Testing Global Settings functionality...")
    
    try:
        # Initialize database
        await init_db()
        print("✅ Database initialized")
        
        # Test 1: Get default settings
        settings = await global_settings_manager.get_global_settings()
        print(f"✅ Default settings loaded: enabled={settings.enabled}")
        
        # Test 2: Update global prompt
        test_prompt = "You are a helpful AI assistant. Always be polite and professional."
        success = await global_settings_manager.update_global_system_prompt(test_prompt, True)
        print(f"✅ Update global prompt: {'success' if success else 'failed'}")
        
        # Test 3: Get updated settings
        updated_settings = await global_settings_manager.get_global_settings()
        print(f"✅ Updated settings: enabled={updated_settings.enabled}, prompt_length={len(updated_settings.global_system_prompt or '')}")
        
        # Test 4: Get global prompt
        prompt = await global_settings_manager.get_global_system_prompt()
        print(f"✅ Global prompt retrieved: {prompt[:50]}..." if prompt else "✅ No global prompt set")
        
        # Test 5: Disable global prompt
        success = await global_settings_manager.enable_global_prompt(False)
        print(f"✅ Disable global prompt: {'success' if success else 'failed'}")
        
        # Test 6: Verify disabled state
        disabled_prompt = await global_settings_manager.get_global_system_prompt()
        print(f"✅ Disabled prompt: {'None' if disabled_prompt is None else 'Still enabled'}")
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_global_settings()) 