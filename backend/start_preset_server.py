#!/usr/bin/env python3
"""
Direct server for Preset API - runs without uvicorn CLI to avoid reload issues
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, '/app')

def main():
    try:
        from api.preset_api import app
        import uvicorn
        
        port = int(os.getenv("PRESET_API_PORT", "8083"))
        print(f"🚀 Starting Preset API server on port {port}...")
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=port,
            reload=False,
            access_log=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Error starting Preset API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 