#!/usr/bin/env python3
"""
Unified startup script for MCP API, Preset API, and LiveKit agent worker.
"""
import subprocess
import sys
import os
import time
import signal

# Global process references for cleanup
proc_mcp = None
proc_preset = None
proc_global_settings = None
proc_auth = None

def cleanup_processes():
    """Clean up child processes on exit"""
    global proc_mcp, proc_preset, proc_global_settings, proc_auth
    if proc_mcp:
        proc_mcp.terminate()
    if proc_preset:
        proc_preset.terminate()
    if proc_global_settings:
        proc_global_settings.terminate()
    if proc_auth:
        proc_auth.terminate()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n🛑 Received signal {signum}, shutting down...")
    cleanup_processes()
    sys.exit(0)

# Set up signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

try:
    # 1. Start Authentication API Server
    print("🔐 Starting Authentication API server...")
    proc_auth = subprocess.Popen([sys.executable, "start_simple_auth_server.py"])
    
    # 2. Give Auth API a moment to initialize
    time.sleep(2)
    # 3. Start MCP API Server
    print("🚀 Starting MCP API server...")
    proc_mcp = subprocess.Popen([sys.executable, "api/start_mcp_api.py"])
    
    # 4. Give MCP API a moment to initialize
    time.sleep(2)
    
    # 5. Start Preset API Server using dedicated script
    print("🚀 Starting Preset API server...")
    proc_preset = subprocess.Popen([sys.executable, "start_preset_server.py"])
    
    # 6. Give Preset API a moment to initialize
    time.sleep(3)
    
    # 7. Start Global Settings API Server
    print("🚀 Starting Global Settings API server...")
    proc_global_settings = subprocess.Popen([sys.executable, "start_global_settings_api.py"])
    
    # 8. Give Global Settings API a moment to initialize
    time.sleep(2)
    
    # 9. Start LiveKit Agent Worker (this will block)
    print("🚀 Starting LiveKit Agent Worker (single-agent)...")
    # Use the LiveKit CLI subcommand to prevent immediate exit (which triggers container restarts)
    subprocess.call([sys.executable, "core/agent_worker.py", "start"]) 

except KeyboardInterrupt:
    print("\n🛑 Interrupted by user")
except Exception as e:
    print(f"❌ Error in startup: {e}")
finally:
    cleanup_processes() 