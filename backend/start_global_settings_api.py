#!/usr/bin/env python3
"""
Global Settings API Server Startup Script
"""
import uvicorn
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.global_settings_api import app

if __name__ == "__main__":
    port = int(os.getenv("GLOBAL_SETTINGS_API_PORT", 8084))
    host = os.getenv("GLOBAL_SETTINGS_API_HOST", "0.0.0.0")
    
    print(f"🚀 Starting Global Settings API on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info") 