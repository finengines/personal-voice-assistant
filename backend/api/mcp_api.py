#!/usr/bin/env python3
"""
MCP Server Management API

FastAPI endpoints for managing MCP server configurations.
"""

import os
from dotenv import load_dotenv
import asyncio
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

try:
    from config.mcp_config_db import (
        mcp_manager,
        MCPServerConfig,
        MCPServerType,
        AuthType,
        AuthConfig
    )
    USE_DATABASE = True
except ImportError as e:
    print(f"Warning: Database MCP config not available: {e}")
    print("Falling back to JSON file configuration")
    USE_DATABASE = False
    from config.mcp_config import (
        mcp_manager,
        MCPServerConfig,
        MCPServerType,
        AuthType,
        AuthConfig
    )

# Pydantic models for API
class AuthConfigAPI(BaseModel):
    type: AuthType
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    header_name: Optional[str] = None
    header_value: Optional[str] = None

class MCPServerConfigAPI(BaseModel):
    id: str = Field(..., description="Unique identifier for the server")
    name: str = Field(..., description="Human-readable name for the server")
    description: str = Field(..., description="Description of the server functionality")
    server_type: MCPServerType = Field(..., description="Type of MCP server")
    url: Optional[str] = Field(None, description="URL for HTTP/SSE servers")
    command: Optional[str] = Field(None, description="Command for STDIO servers")
    args: Optional[List[str]] = Field(None, description="Arguments for STDIO servers")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables for STDIO servers")
    auth: Optional[AuthConfigAPI] = Field(None, description="Authentication configuration")
    enabled: bool = Field(True, description="Whether the server is enabled")
    timeout: float = Field(5.0, description="Connection timeout in seconds")
    sse_read_timeout: float = Field(300.0, description="SSE read timeout in seconds")
    retry_count: int = Field(3, description="Number of connection retries")
    health_check_interval: int = Field(60, description="Health check interval in seconds")

class MCPServerStatusResponse(BaseModel):
    server_id: str
    name: str
    enabled: bool
    active: bool
    server_type: str
    url: Optional[str] = None
    error: Optional[str] = None

class MCPToolInfo(BaseModel):
    name: str
    description: str
    server_id: str
    server_name: str

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

# Create lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle - startup and shutdown events"""
    # Startup
    print("🚀 Starting MCP API server...")
    try:
        # Initialize and load configuration
        await mcp_manager.initialize()
        # Start all enabled servers
        await mcp_manager.start_all_enabled_servers()
        print("✅ MCP API server started successfully")
    except Exception as e:
        print(f"Error initializing MCP manager: {e}")
        print("MCP API will run in read-only mode.")
    
    yield  # Application is running
    
    # Shutdown
    print("🛑 Shutting down MCP API server...")
    await mcp_manager.stop_all_servers()
    print("✅ MCP API server shutdown complete")

# Load environment variables from .env when running outside Docker
load_dotenv()

# Create FastAPI app with lifespan
app = FastAPI(
    title="Personal Agent MCP API",
    description="API for managing MCP (Model Context Protocol) servers and API keys",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API key management router
try:
    from api.api_key_api import router as api_key_router
    app.include_router(api_key_router)
    print("✅ API Key management endpoints loaded")
except ImportError as e:
    print(f"⚠️  API Key management not available: {e}")
    # Try alternative import path
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from api_key_api import router as api_key_router
        app.include_router(api_key_router)
        print("✅ API Key management endpoints loaded (alternative path)")
    except ImportError as e2:
        print(f"⚠️  API Key management still not available: {e2}")

# Dependency to ensure MCP manager is loaded
async def get_mcp_manager():
    if not mcp_manager._initialized:
        await mcp_manager.initialize()
    return mcp_manager

# API Endpoints

@app.get("/", response_model=APIResponse)
async def root():
    """Root endpoint with API information"""
    return APIResponse(
        success=True,
        message="Personal Agent MCP API is running",
        data={
            "version": "1.0.0",
            "endpoints": [
                "/servers - List all MCP servers",
                "/servers/{server_id} - Get specific server",
                "/servers/{server_id}/start - Start server",
                "/servers/{server_id}/stop - Stop server",
                "/tools - List all available tools"
            ]
        }
    )

@app.get("/servers", response_model=APIResponse)
async def list_servers(manager = Depends(get_mcp_manager)):
    """List all MCP server configurations"""
    try:
        servers = manager.list_servers()
        
        # Handle both sync and async get_server_status methods
        import asyncio
        if asyncio.iscoroutinefunction(manager.get_server_status):
            status = await manager.get_server_status()
        else:
            status = manager.get_server_status()
        
        server_list = []
        for server_id, config in servers.items():
            server_status = status.get(server_id, {})
            server_list.append(MCPServerStatusResponse(
                server_id=server_id,
                name=config.name,
                enabled=config.enabled,
                active=server_status.get('active', False),
                server_type=config.server_type.value,
                url=config.url
            ))
        
        return APIResponse(
            success=True,
            message=f"Found {len(server_list)} servers",
            data=server_list
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing servers: {e}")

@app.get("/servers/{server_id}", response_model=APIResponse)
async def get_server(server_id: str, manager = Depends(get_mcp_manager)):
    """Get a specific MCP server configuration"""
    try:
        config = manager.get_server(server_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
        
        # Get server status
        import asyncio
        if asyncio.iscoroutinefunction(manager.get_server_status):
            status = await manager.get_server_status()
        else:
            status = manager.get_server_status()
        server_status = status.get(server_id, {})
        
        return APIResponse(
            success=True,
            message=f"Server {server_id} found",
            data={
                "config": config.to_dict(),
                "active": server_status.get('active', False),
                "status": server_status
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting server: {e}")

@app.post("/servers", response_model=APIResponse)
async def create_server(server_config: MCPServerConfigAPI, manager = Depends(get_mcp_manager)):
    """Create a new MCP server configuration"""
    try:
        # Check if server ID already exists
        if manager.get_server(server_config.id):
            raise HTTPException(status_code=409, detail=f"Server {server_config.id} already exists")
        
        # Convert API model to internal model
        auth_config = None
        if server_config.auth:
            auth_config = AuthConfig(
                type=server_config.auth.type,
                token=server_config.auth.token,
                username=server_config.auth.username,
                password=server_config.auth.password,
                header_name=server_config.auth.header_name,
                header_value=server_config.auth.header_value
            )
        
        config = MCPServerConfig(
            id=server_config.id,
            name=server_config.name,
            description=server_config.description,
            server_type=server_config.server_type,
            url=server_config.url,
            command=server_config.command,
            args=server_config.args,
            env=server_config.env,
            auth=auth_config,
            enabled=server_config.enabled,
            timeout=server_config.timeout,
            sse_read_timeout=server_config.sse_read_timeout,
            retry_count=server_config.retry_count,
            health_check_interval=server_config.health_check_interval
        )
        
        success = await manager.add_server(config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add server")
        
        return APIResponse(
            success=True,
            message=f"Server {server_config.id} created successfully",
            data=config.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating server: {e}")

@app.put("/servers/{server_id}", response_model=APIResponse)
async def update_server(server_id: str, server_config: MCPServerConfigAPI, manager = Depends(get_mcp_manager)):
    """Update an existing MCP server configuration"""
    try:
        # Check if server exists
        if not manager.get_server(server_id):
            raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
        
        # Convert API model to internal model
        auth_config = None
        if server_config.auth:
            auth_config = AuthConfig(
                type=server_config.auth.type,
                token=server_config.auth.token,
                username=server_config.auth.username,
                password=server_config.auth.password,
                header_name=server_config.auth.header_name,
                header_value=server_config.auth.header_value
            )
        
        config = MCPServerConfig(
            id=server_config.id,
            name=server_config.name,
            description=server_config.description,
            server_type=server_config.server_type,
            url=server_config.url,
            command=server_config.command,
            args=server_config.args,
            env=server_config.env,
            auth=auth_config,
            enabled=server_config.enabled,
            timeout=server_config.timeout,
            sse_read_timeout=server_config.sse_read_timeout,
            retry_count=server_config.retry_count,
            health_check_interval=server_config.health_check_interval
        )
        
        success = await manager.update_server(server_id, config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update server")
        
        return APIResponse(
            success=True,
            message=f"Server {server_id} updated successfully",
            data=config.to_dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating server: {e}")

@app.delete("/servers/{server_id}", response_model=APIResponse)
async def delete_server(server_id: str, manager = Depends(get_mcp_manager)):
    """Delete an MCP server configuration"""
    try:
        # Check if server exists
        if not manager.get_server(server_id):
            raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
        
        success = await manager.remove_server(server_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete server")
        
        return APIResponse(
            success=True,
            message=f"Server {server_id} deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting server: {e}")

@app.post("/servers/{server_id}/start", response_model=APIResponse)
async def start_server(server_id: str, background_tasks: BackgroundTasks, manager = Depends(get_mcp_manager)):
    """Start an MCP server"""
    try:
        # Check if server exists
        config = manager.get_server(server_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
        
        if not config.enabled:
            raise HTTPException(status_code=400, detail=f"Server {server_id} is disabled")
        
        # Start server in background
        async def start_server_task():
            await manager.start_server(server_id)
        
        background_tasks.add_task(start_server_task)
        
        return APIResponse(
            success=True,
            message=f"Starting server {server_id}..."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting server: {e}")

@app.post("/servers/{server_id}/stop", response_model=APIResponse)
async def stop_server(server_id: str, background_tasks: BackgroundTasks, manager = Depends(get_mcp_manager)):
    """Stop an MCP server"""
    try:
        # Check if server exists
        if not manager.get_server(server_id):
            raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
        
        # Stop server in background
        async def stop_server_task():
            await manager.stop_server(server_id)
        
        background_tasks.add_task(stop_server_task)
        
        return APIResponse(
            success=True,
            message=f"Stopping server {server_id}..."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping server: {e}")

@app.post("/servers/{server_id}/restart", response_model=APIResponse)
async def restart_server(server_id: str, background_tasks: BackgroundTasks, manager = Depends(get_mcp_manager)):
    """Restart an MCP server"""
    try:
        # Check if server exists
        config = manager.get_server(server_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
        
        if not config.enabled:
            raise HTTPException(status_code=400, detail=f"Server {server_id} is disabled")
        
        # Restart server in background
        async def restart_server_task():
            await manager.stop_server(server_id)
            await asyncio.sleep(1)  # Brief delay
            await manager.start_server(server_id)
        
        background_tasks.add_task(restart_server_task)
        
        return APIResponse(
            success=True,
            message=f"Restarting server {server_id}..."
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error restarting server: {e}")

@app.get("/servers/{server_id}/status", response_model=APIResponse)
async def get_server_status(server_id: str, manager = Depends(get_mcp_manager)):
    """Get detailed status of an MCP server"""
    try:
        config = manager.get_server(server_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
        
        # Get server status
        import asyncio
        if asyncio.iscoroutinefunction(manager.get_server_status):
            status = await manager.get_server_status()
        else:
            status = manager.get_server_status()
        server_status = status.get(server_id, {})
        
        # Try to get tools if server is active
        tools = []
        if server_status.get('active', False):
            try:
                if server_id in manager.active_servers:
                    server_instance = manager.active_servers[server_id]
                    if hasattr(server_instance, 'list_tools'):
                        tools_list = await server_instance.list_tools()
                        tools = [{"name": tool.name if hasattr(tool, 'name') else str(tool)} for tool in tools_list]
            except Exception:
                pass  # Ignore tool listing errors
        
        return APIResponse(
            success=True,
            message=f"Status for server {server_id}",
            data={
                "config": config.to_dict(),
                "active": server_status.get('active', False),
                "type": server_status.get('type', config.server_type.value),
                "tools_count": len(tools),
                "tools": tools
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting server status: {e}")

@app.get("/tools", response_model=APIResponse)
async def list_tools(manager = Depends(get_mcp_manager)):
    """List all available tools from all active MCP servers"""
    try:
        tools_info = []
        
        for server_id, server in manager.active_servers.items():
            try:
                config = manager.get_server(server_id)
                server_name = config.name if config else server_id
                
                if hasattr(server, 'list_tools'):
                    tools = await server.list_tools()
                    for tool in tools:
                        tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                        tool_desc = tool.description if hasattr(tool, 'description') else "No description available"
                        
                        tools_info.append(MCPToolInfo(
                            name=tool_name,
                            description=tool_desc,
                            server_id=server_id,
                            server_name=server_name
                        ))
            except Exception as e:
                print(f"Error listing tools from server {server_id}: {e}")
        
        return APIResponse(
            success=True,
            message=f"Found {len(tools_info)} tools from {len(manager.active_servers)} active servers",
            data=tools_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tools: {e}")

@app.post("/servers/{server_id}/toggle", response_model=APIResponse)
async def toggle_server(server_id: str, toggle_data: dict, manager = Depends(get_mcp_manager)):
    """Toggle server enabled/disabled status"""
    try:
        config = manager.get_server(server_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Server {server_id} not found")
        
        enabled = toggle_data.get('enabled', not config.enabled)
        
        # Update the server configuration
        config.enabled = enabled
        # Support both sync and async manager implementations
        import asyncio
        if asyncio.iscoroutinefunction(manager.update_server):
            success = await manager.update_server(server_id, config)
        else:
            success = manager.update_server(server_id, config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update server")
        
        action = "enabled" if enabled else "disabled"
        return APIResponse(
            success=True,
            message=f"Server {server_id} {action} successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling server: {e}")

@app.post("/servers/start-all", response_model=APIResponse)
async def start_all_servers(background_tasks: BackgroundTasks, manager = Depends(get_mcp_manager)):
    """Start all enabled MCP servers"""
    try:
        enabled_servers = manager.get_enabled_servers()
        
        # Start all servers in background
        async def start_all_task():
            await manager.start_all_enabled_servers()
        
        background_tasks.add_task(start_all_task)
        
        return APIResponse(
            success=True,
            message=f"Starting {len(enabled_servers)} enabled servers..."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting all servers: {e}")

@app.post("/servers/stop-all", response_model=APIResponse)
async def stop_all_servers(background_tasks: BackgroundTasks, manager = Depends(get_mcp_manager)):
    """Stop all running MCP servers"""
    try:
        active_count = len(manager.active_servers)
        
        # Stop all servers in background
        async def stop_all_task():
            await manager.stop_all_servers()
        
        background_tasks.add_task(stop_all_task)
        
        return APIResponse(
            success=True,
            message=f"Stopping {active_count} active servers..."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping all servers: {e}")

@app.get("/health", response_model=APIResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Basic health check
        servers_count = 0
        if hasattr(mcp_manager, 'servers'):
            try:
                servers_count = len(mcp_manager.servers) if mcp_manager.servers else 0
            except:
                servers_count = 0
        
        health_data = {
            "status": "healthy",
            "service": "mcp-api",
            "database_mode": "database" if USE_DATABASE else "json_file",
            "servers_count": servers_count
        }
        
        return APIResponse(
            success=True,
            message="MCP API is healthy",
            data=health_data
        )
    except Exception as e:
        # Even if there are issues, we want the health check to succeed
        # so the container doesn't get killed
        return APIResponse(
            success=True,
            message="MCP API is running with limited functionality",
            data={
                "status": "degraded",
                "service": "mcp-api",
                "error": str(e)
            }
        )

@app.get("/memory-status", response_model=APIResponse)
async def memory_status():
    """Check memory system connectivity and status"""
    try:
        import requests
        
        status_data = {
            "graphiti_api": {"status": "unknown", "url": ""},
            "graphiti_mcp": {"status": "unknown", "url": ""},
            "servers": [],
            "tools_count": 0
        }
        
        # Check Graphiti API
        graphiti_api_url = os.getenv("GRAPHITI_API_URL", "https://your-graphiti-instance.com")
        status_data["graphiti_api"]["url"] = graphiti_api_url
        try:
            resp = requests.get(f"{graphiti_api_url}/healthcheck", timeout=3)
            if resp.ok:
                status_data["graphiti_api"]["status"] = "connected"
            else:
                status_data["graphiti_api"]["status"] = f"error_{resp.status_code}"
        except Exception as e:
            status_data["graphiti_api"]["status"] = f"failed_{str(e)[:50]}"
        
        # Check Graphiti MCP
        graphiti_mcp_url = os.getenv("GRAPHITI_MCP_URL", "https://your-graphiti-instance.com/sse")
        status_data["graphiti_mcp"]["url"] = graphiti_mcp_url
        try:
            resp = requests.get(graphiti_mcp_url.replace('/sse', '/healthcheck'), timeout=3)
            if resp.ok:
                status_data["graphiti_mcp"]["status"] = "connected"
            else:
                status_data["graphiti_mcp"]["status"] = f"error_{resp.status_code}"
        except Exception as e:
            status_data["graphiti_mcp"]["status"] = f"failed_{str(e)[:50]}"
        
        # Check MCP servers
        manager = await get_mcp_manager()
        if hasattr(manager, 'active_servers'):
            for server_id, server in manager.active_servers.items():
                server_info = {
                    "id": server_id,
                    "type": type(server).__name__,
                    "url": getattr(server, 'url', 'N/A'),
                    "status": "active"
                }
                status_data["servers"].append(server_info)
                
                # Try to count tools
                try:
                    if hasattr(server, 'list_tools'):
                        tools = await server.list_tools()
                        status_data["tools_count"] += len(tools) if tools else 0
                        server_info["tools_count"] = len(tools) if tools else 0
                except:
                    server_info["tools_count"] = "unknown"
        
        overall_status = "healthy"
        if status_data["graphiti_api"]["status"] != "connected":
            overall_status = "degraded"
        if status_data["graphiti_mcp"]["status"] != "connected":
            overall_status = "degraded"
        if not status_data["servers"]:
            overall_status = "no_servers"
        
        return APIResponse(
            success=True,
            message=f"Memory system status: {overall_status}",
            data={
                "overall_status": overall_status,
                **status_data
            }
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message="Failed to check memory status",
            data={"error": str(e)}
        )

# Development server
def main():
    """Run the MCP API server"""
    port = int(os.environ.get("MCP_API_PORT", 8082))
    
    # Check if we're in development mode
    debug = os.environ.get("DEBUG", "").lower() in ("true", "1", "yes")
    
    if debug:
        # Use module string for reload to work properly
        uvicorn.run(
            "mcp_api:app",  # Use module:app format for reload
            host="0.0.0.0", 
            port=port, 
            reload=True,
            log_level="info"
        )
    else:
        # Production mode - use app instance directly
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=port, 
            reload=False
        )

if __name__ == "__main__":
    main() 