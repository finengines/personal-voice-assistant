#!/usr/bin/env python3
"""
Startup script for the MCP API server
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get the backend directory
    backend_dir = Path(__file__).parent
    
    # Check if MCP API exists
    mcp_api_file = backend_dir / "mcp_api.py"
    if not mcp_api_file.exists():
        print("❌ MCP API file not found. Please ensure mcp_api.py exists in the backend directory.")
        return 1
    
    # Set environment variables
    os.environ.setdefault("MCP_API_PORT", "8082")
    os.environ.setdefault("DEBUG", "false")  # Disable debug mode to fix binding issues
    
    print("🚀 Starting MCP API Server...")
    print(f"📁 Working directory: {backend_dir}")
    print(f"🌐 Port: {os.environ.get('MCP_API_PORT', '8082')}")
    print(f"🔧 Debug mode: {os.environ.get('DEBUG', 'false')}")
    print("━" * 50)
    
    try:
        # Change to backend directory
        os.chdir(backend_dir)
        
        # Start the API server
        cmd = [
            sys.executable, "-m", "uvicorn", "mcp_api:app", 
            "--host", "0.0.0.0", 
            "--port", os.environ.get('MCP_API_PORT', '8082')
        ]
        
        # Only add reload flag if debug mode is enabled
        if os.environ.get('DEBUG', 'false').lower() == 'true':
            cmd.append("--reload")
            
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 MCP API server stopped by user")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting MCP API server: {e}")
        return 1
    except FileNotFoundError:
        print("❌ Python executable not found. Please ensure Python is installed and available.")
        return 1

if __name__ == "__main__":
    exit(main()) 