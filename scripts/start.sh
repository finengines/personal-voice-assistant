#!/bin/bash
set -e

# Start the agent worker in the background
echo "🚀 Starting LiveKit Agent Worker in production mode..."
python simple_agent.py start &

# Start the MCP API server in the foreground
echo "🚀 Starting MCP API Server..."
python start_mcp_api.py 