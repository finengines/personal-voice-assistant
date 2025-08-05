#!/usr/bin/env python3
"""
MCP Server Configuration Management

This module provides a configuration management system for MCP (Model Context Protocol) servers
with support for different server types and authentication methods.
"""

import os
import json
import aiohttp
from typing import Dict, List, Optional, Union, Any, Literal
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from livekit.agents.llm import mcp
from livekit.agents.llm.tool_context import function_tool, ToolError


class MCPServerType(Enum):
    """Supported MCP server types"""
    SSE = "sse"                    # Server-Sent Events
    HTTP = "http"                  # Streamable HTTP
    OPENAI_TOOLS = "openai_tools"  # OpenAI format tool server
    STDIO = "stdio"                # Standard I/O (for local servers)


class AuthType(Enum):
    """Supported authentication types"""
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    CUSTOM_HEADER = "custom_header"


@dataclass
class AuthConfig:
    """Authentication configuration for MCP servers"""
    type: AuthType
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    header_name: Optional[str] = None
    header_value: Optional[str] = None


@dataclass 
class MCPServerConfig:
    """Configuration for an MCP server"""
    id: str
    name: str
    description: str
    server_type: MCPServerType
    url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    auth: Optional[AuthConfig] = None
    enabled: bool = True
    timeout: float = 5.0
    sse_read_timeout: float = 300.0  # 5 minutes
    retry_count: int = 3
    health_check_interval: int = 60  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        if self.server_type:
            result['server_type'] = self.server_type.value
        if self.auth and self.auth.type:
            result['auth']['type'] = self.auth.type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPServerConfig':
        """Create from dictionary"""
        if 'server_type' in data:
            data['server_type'] = MCPServerType(data['server_type'])
        if 'auth' in data and data['auth'] and 'type' in data['auth']:
            auth_data = data['auth'].copy()
            auth_data['type'] = AuthType(auth_data['type'])
            data['auth'] = AuthConfig(**auth_data)
        return cls(**data)


class OpenAIToolsServer:
    """Adapter for OpenAI format tool servers"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
    
    async def initialize(self):
        """Initialize the OpenAI tools server"""
        headers = self._build_headers()
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        
        # Test connection by listing tools
        await self.list_tools()
    
    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers based on auth config"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "LiveKit-PersonalAgent/1.0"
        }
        
        if not self.config.auth:
            return headers
            
        auth = self.config.auth
        if auth.type == AuthType.BEARER and auth.token:
            headers["Authorization"] = f"Bearer {auth.token}"
        elif auth.type == AuthType.API_KEY and auth.token:
            headers["X-API-Key"] = auth.token
        elif auth.type == AuthType.BASIC and auth.username and auth.password:
            import base64
            credentials = base64.b64encode(f"{auth.username}:{auth.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        elif auth.type == AuthType.CUSTOM_HEADER and auth.header_name and auth.header_value:
            headers[auth.header_name] = auth.header_value
            
        return headers
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from OpenAI format server"""
        if not self.session:
            raise RuntimeError("Server not initialized")
            
        if self._tools_cache is not None:
            return self._tools_cache
            
        try:
            # Try common OpenAI tool endpoints
            endpoints = ["/v1/tools", "/tools", "/api/v1/tools", "/api/tools"]
            
            for endpoint in endpoints:
                url = f"{self.config.url.rstrip('/')}{endpoint}"
                try:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Handle different response formats
                            if isinstance(data, list):
                                tools = data
                            elif isinstance(data, dict) and "tools" in data:
                                tools = data["tools"]
                            elif isinstance(data, dict) and "data" in data:
                                tools = data["data"]
                            else:
                                tools = [data]
                            
                            self._tools_cache = tools
                            return tools
                except aiohttp.ClientError:
                    continue
                    
            # If no standard endpoint works, return empty list
            self._tools_cache = []
            return []
            
        except Exception as e:
            raise ToolError(f"Failed to list tools from {self.config.name}: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the OpenAI format server"""
        if not self.session:
            raise RuntimeError("Server not initialized")
            
        try:
            # Try common OpenAI tool execution endpoints
            endpoints = [
                f"/v1/tools/{tool_name}",
                f"/tools/{tool_name}",
                f"/api/v1/tools/{tool_name}",
                f"/api/tools/{tool_name}",
                "/v1/tools/execute",
                "/tools/execute"
            ]
            
            for endpoint in endpoints:
                url = f"{self.config.url.rstrip('/')}{endpoint}"
                
                # Prepare payload in different formats
                payloads = [
                    {"tool": tool_name, "arguments": arguments},
                    {"name": tool_name, "parameters": arguments},
                    {"function": tool_name, "args": arguments},
                    arguments  # Direct arguments for single tool endpoints
                ]
                
                for payload in payloads:
                    try:
                        async with self.session.post(url, json=payload) as response:
                            if response.status == 200:
                                result = await response.json()
                                return self._format_tool_result(result)
                            elif response.status == 404:
                                break  # Try next endpoint
                    except aiohttp.ClientError:
                        continue
                        
            raise ToolError(f"Tool '{tool_name}' not found or not accessible on {self.config.name}")
            
        except Exception as e:
            raise ToolError(f"Failed to call tool '{tool_name}' on {self.config.name}: {e}")
    
    def _format_tool_result(self, result: Any) -> str:
        """Format tool result for consistent output"""
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            # Handle common OpenAI response formats
            if "content" in result:
                return str(result["content"])
            elif "result" in result:
                return str(result["result"])
            elif "response" in result:
                return str(result["response"])
            else:
                return json.dumps(result, indent=2)
        else:
            return str(result)
    
    async def aclose(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None


class MCPServerManager:
    """Manager for MCP server configurations and instances"""
    
    def __init__(self, config_file: str = "mcp_servers.json"):
        # Use absolute path to ensure we're using the correct config file
        if not Path(config_file).is_absolute():
            self.config_file = Path("/app") / config_file
        else:
            self.config_file = Path(config_file)
        self.servers: Dict[str, MCPServerConfig] = {}
        self.active_servers: Dict[str, Union[mcp.MCPServer, OpenAIToolsServer]] = {}
        
    def load_config(self):
        """Load server configurations from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.servers = {
                        server_id: MCPServerConfig.from_dict(server_data)
                        for server_id, server_data in data.get('servers', {}).items()
                    }
            except Exception as e:
                print(f"Error loading MCP config: {e}")
                self.servers = {}
        else:
            # Create default configuration
            self._create_default_config()
    
    def save_config(self):
        """Save server configurations to file"""
        try:
            config_data = {
                'servers': {
                    server_id: server.to_dict()
                    for server_id, server in self.servers.items()
                }
            }
            
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"Error saving MCP config: {e}")
    
    def _create_default_config(self):
        """Create default MCP server configurations"""
        # Example SSE MCP server
        self.servers["example-sse"] = MCPServerConfig(
            id="example-sse",
            name="Example SSE Server",
            description="Example MCP server using Server-Sent Events",
            server_type=MCPServerType.SSE,
            url="http://localhost:8000/sse",
            auth=AuthConfig(type=AuthType.NONE),
            enabled=False
        )
        
        # Example HTTP MCP server
        self.servers["example-http"] = MCPServerConfig(
            id="example-http",
            name="Example HTTP Server", 
            description="Example MCP server using streamable HTTP",
            server_type=MCPServerType.HTTP,
            url="http://localhost:8000/mcp",
            auth=AuthConfig(type=AuthType.NONE),
            enabled=False
        )
        
        # Example OpenAI tools server
        self.servers["example-openai-tools"] = MCPServerConfig(
            id="example-openai-tools",
            name="Example OpenAI Tools Server",
            description="Example server with OpenAI format tools",
            server_type=MCPServerType.OPENAI_TOOLS,
            url="http://localhost:9000/api",
            auth=AuthConfig(
                type=AuthType.BEARER,
                token="your-api-token-here"
            ),
            enabled=False
        )
        
        # Save the default config
        self.save_config()
    
    def add_server(self, config: MCPServerConfig) -> bool:
        """Add a new server configuration"""
        try:
            self.servers[config.id] = config
            self.save_config()
            return True
        except Exception as e:
            print(f"Error adding server {config.id}: {e}")
            return False
    
    def remove_server(self, server_id: str) -> bool:
        """Remove a server configuration"""
        try:
            if server_id in self.servers:
                # Stop the server if it's running (sync version)
                if server_id in self.active_servers:
                    try:
                        server = self.active_servers[server_id]
                        # Use asyncio.run if needed, but for now just remove from active_servers
                        del self.active_servers[server_id]
                    except Exception as e:
                        print(f"Warning: Could not stop server {server_id}: {e}")
                
                del self.servers[server_id]
                self.save_config()
                return True
            return False
        except Exception as e:
            print(f"Error removing server {server_id}: {e}")
            return False
    
    def update_server(self, server_id: str, config: MCPServerConfig) -> bool:
        """Update a server configuration"""
        try:
            if server_id in self.servers:
                # Stop the server if it's running and restart with new config
                was_running = server_id in self.active_servers
                if was_running:
                    self.stop_server(server_id)
                
                self.servers[server_id] = config
                self.save_config()
                
                if was_running and config.enabled:
                    # Restart with new config
                    self.start_server(server_id)
                
                return True
            return False
        except Exception as e:
            print(f"Error updating server {server_id}: {e}")
            return False
    
    def get_server(self, server_id: str) -> Optional[MCPServerConfig]:
        """Get a server configuration"""
        return self.servers.get(server_id)
    
    def list_servers(self) -> Dict[str, MCPServerConfig]:
        """List all server configurations"""
        return self.servers.copy()
    
    def get_enabled_servers(self) -> Dict[str, MCPServerConfig]:
        """Get only enabled server configurations"""
        return {
            server_id: config
            for server_id, config in self.servers.items()
            if config.enabled
        }
    
    async def start_server(self, server_id: str) -> bool:
        """Start an MCP server"""
        try:
            if server_id not in self.servers:
                print(f"Server {server_id} not found")
                return False
                
            config = self.servers[server_id]
            if not config.enabled:
                print(f"Server {server_id} is disabled")
                return False
                
            if server_id in self.active_servers:
                print(f"Server {server_id} is already running")
                return True
            
            # Create the appropriate server instance
            if config.server_type == MCPServerType.OPENAI_TOOLS:
                server = OpenAIToolsServer(config)
                await server.initialize()
            elif config.server_type in [MCPServerType.SSE, MCPServerType.HTTP]:
                headers = {}
                if config.auth:
                    if config.auth.type == AuthType.BEARER and config.auth.token:
                        headers["Authorization"] = f"Bearer {config.auth.token}"
                    elif config.auth.type == AuthType.API_KEY and config.auth.token:
                        headers["X-API-Key"] = config.auth.token
                    elif config.auth.type == AuthType.CUSTOM_HEADER and config.auth.header_name and config.auth.header_value:
                        headers[config.auth.header_name] = config.auth.header_value
                
                server = mcp.MCPServerHTTP(
                    url=config.url,
                    headers=headers,
                    timeout=config.timeout,
                    sse_read_timeout=config.sse_read_timeout
                )
                await server.initialize()
            elif config.server_type == MCPServerType.STDIO:
                server = mcp.MCPServerStdio(
                    command=config.command,
                    args=config.args or [],
                    env=config.env
                )
                await server.initialize()
            else:
                print(f"Unsupported server type: {config.server_type}")
                return False
            
            self.active_servers[server_id] = server
            print(f"Started MCP server: {config.name}")
            return True
            
        except Exception as e:
            print(f"Error starting server {server_id}: {e}")
            return False
    
    async def stop_server(self, server_id: str) -> bool:
        """Stop an MCP server"""
        try:
            if server_id in self.active_servers:
                server = self.active_servers[server_id]
                await server.aclose()
                del self.active_servers[server_id]
                print(f"Stopped MCP server: {server_id}")
                return True
            return False
        except Exception as e:
            print(f"Error stopping server {server_id}: {e}")
            return False
    
    async def start_all_enabled_servers(self):
        """Start all enabled MCP servers"""
        for server_id, config in self.servers.items():
            if config.enabled:
                await self.start_server(server_id)
    
    async def stop_all_servers(self):
        """Stop all running MCP servers"""
        for server_id in list(self.active_servers.keys()):
            await self.stop_server(server_id)
    
    async def get_all_tools(self) -> List[Any]:
        """Get all tools from all active servers"""
        all_tools = []
        
        for server_id, server in self.active_servers.items():
            try:
                if isinstance(server, OpenAIToolsServer):
                    # Convert OpenAI tools to MCP tool format
                    openai_tools = await server.list_tools()
                    for tool in openai_tools:
                        # Create function tool wrapper
                        tool_name = tool.get('name', f'tool_{server_id}')
                        
                        async def make_tool_caller(srv, tn):
                            async def tool_caller(**kwargs):
                                return await srv.call_tool(tn, kwargs)
                            return tool_caller
                        
                        caller = await make_tool_caller(server, tool_name)
                        
                        mcp_tool = function_tool(
                            caller,
                            name=f"{server_id}_{tool_name}",
                            description=tool.get('description', f'Tool from {server_id}')
                        )
                        all_tools.append(mcp_tool)
                        
                elif hasattr(server, 'list_tools'):
                    # Standard MCP server
                    tools = await server.list_tools()
                    all_tools.extend(tools)
                    
            except Exception as e:
                print(f"Error getting tools from server {server_id}: {e}")
        
        return all_tools
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all servers"""
        status = {}
        for server_id, config in self.servers.items():
            status[server_id] = {
                'config': config.to_dict(),
                'active': server_id in self.active_servers,
                'type': config.server_type.value
            }
        return status


# Global instance
mcp_manager = MCPServerManager() 