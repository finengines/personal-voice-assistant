#!/usr/bin/env python3
"""
MCP Server Configuration Management with Database Persistence

This module provides a configuration management system for MCP (Model Context Protocol) servers
with PostgreSQL database persistence instead of JSON files.
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

# Delay heavy imports to avoid circular import during module import
def _lazy_db_stuff():
    from core.database import init_db, health_check
    from core.db_manager import db_manager
    return init_db, health_check, db_manager


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
    
    def _build_headers(self) -> Dict[str, str]:
        """Build headers for API requests"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.config.auth:
            if self.config.auth.type == AuthType.BEARER:
                headers['Authorization'] = f"Bearer {self.config.auth.token}"
            elif self.config.auth.type == AuthType.API_KEY:
                headers['X-API-Key'] = self.config.auth.token
            elif self.config.auth.type == AuthType.BASIC:
                import base64
                credentials = f"{self.config.auth.username}:{self.config.auth.password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                headers['Authorization'] = f"Basic {encoded}"
            elif self.config.auth.type == AuthType.CUSTOM_HEADER:
                if self.config.auth.header_name and self.config.auth.header_value:
                    headers[self.config.auth.header_name] = self.config.auth.header_value
        
        return headers
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the server"""
        if not self.session:
            await self.initialize()
        
        try:
            async with self.session.get(f"{self.config.url}/tools") as response:
                if response.status == 200:
                    tools = await response.json()
                    # Cache tools and save to database
                    for tool in tools:
                        await db_manager.save_tool_info(
                            self.config.id,
                            tool.get('name', ''),
                            tool.get('description', ''),
                            tool
                        )
                    return tools
                else:
                    print(f"Error listing tools: {response.status}")
                    return []
        except Exception as e:
            print(f"Error listing tools from {self.config.url}: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a specific tool with arguments"""
        if not self.session:
            await self.initialize()
        
        try:
            payload = {
                "tool": tool_name,
                "arguments": arguments
            }
            
            async with self.session.post(f"{self.config.url}/call", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('result', result)
                else:
                    error_text = await response.text()
                    raise ToolError(f"Tool call failed: {response.status} - {error_text}")
        except Exception as e:
            if isinstance(e, ToolError):
                raise
            raise ToolError(f"Error calling tool {tool_name}: {e}")
    
    def _format_tool_result(self, result: Any) -> str:
        """Format tool result for display"""
        if isinstance(result, str):
            return result
        elif isinstance(result, (dict, list)):
            return json.dumps(result, indent=2)
        else:
            return str(result)
    
    async def aclose(self):
        """Close the server session"""
        if self.session:
            await self.session.close()
            self.session = None


class MCPServerManager:
    """Manager for MCP server configurations with database persistence"""
    
    def __init__(self):
        self.active_servers: Dict[str, Union[mcp.MCPServer, OpenAIToolsServer]] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the database and load configurations"""
        if self._initialized:
            return
        
        # Initialize database (lazy to avoid circular at import time)
        init_db, health_check, _db_manager = _lazy_db_stuff()
        await init_db()
        
        # Check database health
        if not await health_check():
            print("Warning: Database health check failed")
        
        # Load configurations from database
        await self.load_config()
        self._initialized = True
    
    async def load_config(self):
        """Load server configurations from database"""
        try:
            _init_db, _health_check, db_manager = _lazy_db_stuff()
            self.servers = await db_manager.load_all_servers()
        except Exception as e:
            print(f"Error loading MCP config from database: {e}")
            self.servers = {}
    
    async def save_config(self):
        """Save server configurations to database"""
        # This is now handled by individual save operations
        pass
    
    async def add_server(self, config: MCPServerConfig) -> bool:
        """Add a new server configuration"""
        try:
            _init_db, _health_check, db_manager = _lazy_db_stuff()
            success = await db_manager.save_server(config)
            if success:
                self.servers[config.id] = config
            return success
        except Exception as e:
            print(f"Error adding server {config.id}: {e}")
            return False
    
    async def remove_server(self, server_id: str) -> bool:
        """Remove a server configuration"""
        try:
            # Stop the server if it's running
            if server_id in self.active_servers:
                await self.stop_server(server_id)
            
            _init_db, _health_check, db_manager = _lazy_db_stuff()
            success = await db_manager.delete_server(server_id)
            if success and server_id in self.servers:
                del self.servers[server_id]
            return success
        except Exception as e:
            print(f"Error removing server {server_id}: {e}")
            return False
    
    async def update_server(self, server_id: str, config: MCPServerConfig) -> bool:
        """Update a server configuration"""
        try:
            _init_db, _health_check, db_manager = _lazy_db_stuff()
            success = await db_manager.save_server(config)
            if success:
                self.servers[server_id] = config
            return success
        except Exception as e:
            print(f"Error updating server {server_id}: {e}")
            return False
    
    def get_server(self, server_id: str) -> Optional[MCPServerConfig]:
        """Get a specific server configuration"""
        return self.servers.get(server_id)
    
    def list_servers(self) -> Dict[str, MCPServerConfig]:
        """List all server configurations"""
        return self.servers.copy()
    
    def get_enabled_servers(self) -> Dict[str, MCPServerConfig]:
        """Get all enabled server configurations"""
        return {
            server_id: config
            for server_id, config in self.servers.items()
            if config.enabled
        }
    
    async def start_server(self, server_id: str) -> bool:
        """Start a specific MCP server"""
        if server_id in self.active_servers:
            print(f"Server {server_id} is already running")
            return True
        
        config = self.get_server(server_id)
        if not config:
            print(f"Server {server_id} not found")
            return False
        
        try:
            if config.server_type == MCPServerType.OPENAI_TOOLS:
                server = OpenAIToolsServer(config)
                await server.initialize()
                self.active_servers[server_id] = server
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
                self.active_servers[server_id] = server
            elif config.server_type == MCPServerType.STDIO:
                server = mcp.MCPServerStdio(
                    command=config.command,
                    args=config.args or [],
                    env=config.env
                )
                await server.initialize()
                self.active_servers[server_id] = server
            else:
                print(f"Unsupported server type: {config.server_type}")
                return False
            
            # Update status in database
            await db_manager.update_server_status(server_id, True)
            print(f"Started MCP server: {config.name}")
            return True
            
        except Exception as e:
            print(f"Error starting server {server_id}: {e}")
            await db_manager.update_server_status(server_id, False, str(e))
            return False
    
    async def stop_server(self, server_id: str) -> bool:
        """Stop a specific MCP server"""
        if server_id not in self.active_servers:
            print(f"Server {server_id} is not running")
            return True
        
        try:
            server = self.active_servers[server_id]
            if hasattr(server, 'aclose'):
                await server.aclose()
            del self.active_servers[server_id]
            
            # Update status in database
            await db_manager.update_server_status(server_id, False)
            print(f"Stopped server {server_id}")
            return True
            
        except Exception as e:
            print(f"Error stopping server {server_id}: {e}")
            return False
    
    async def start_all_enabled_servers(self):
        """Start all enabled servers"""
        enabled_servers = self.get_enabled_servers()
        for server_id in enabled_servers:
            await self.start_server(server_id)
    
    async def stop_all_servers(self):
        """Stop all active servers"""
        for server_id in list(self.active_servers.keys()):
            await self.stop_server(server_id)
    
    async def get_all_tools(self) -> List[Any]:
        """Get all available tools from all active servers"""
        tools = []
        
        for server_id, server in self.active_servers.items():
            try:
                if isinstance(server, OpenAIToolsServer):
                    server_tools = await server.list_tools()
                    for tool in server_tools:
                        tool_name = tool.get('name', '')
                        
                        async def make_tool_caller(srv, tn):
                            async def tool_caller(**kwargs):
                                result = await srv.call_tool(tn, kwargs)
                                return srv._format_tool_result(result)
                            return tool_caller
                        
                        tools.append(function_tool(
                            name=tool_name,
                            description=tool.get('description', ''),
                            func=await make_tool_caller(server, tool_name)
                        ))
                else:
                    # Handle other server types
                    pass
                    
            except Exception as e:
                print(f"Error getting tools from server {server_id}: {e}")
        
        return tools
    
    async def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all servers"""
        status = {}
        
        _init_db, _health_check, db_manager = _lazy_db_stuff()
        for server_id, config in self.servers.items():
            db_status = await db_manager.get_server_status(server_id)
            status[server_id] = {
                "name": config.name,
                "enabled": config.enabled,
                "active": server_id in self.active_servers,
                "server_type": config.server_type.value,
                "url": config.url,
                "error": db_status.get('error_message') if db_status else None,
                "last_health_check": db_status.get('last_health_check') if db_status else None,
                "last_started": db_status.get('last_started') if db_status else None,
                "last_stopped": db_status.get('last_stopped') if db_status else None
            }
        
        return status


# Global MCP manager instance
mcp_manager = MCPServerManager() 