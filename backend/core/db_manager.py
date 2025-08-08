#!/usr/bin/env python3
"""
Database Manager for Personal Agent

This module provides database operations for MCP server management,
replacing the JSON file storage with PostgreSQL persistence.
"""

import asyncio
from typing import Dict, List, Optional, Any  # noqa: F401
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from .database import get_db_session, MCPServer, ServerStatus, ToolInfo
from typing import Any, Dict, Optional, List

# Lazy import to avoid circular dependency between
# config.mcp_config_db -> core.db_manager -> config.mcp_config_db
def _get_mcp_types():
    from importlib import import_module
    mod = import_module('config.mcp_config_db')
    return (
        getattr(mod, 'MCPServerConfig'),
        getattr(mod, 'MCPServerType'),
        getattr(mod, 'AuthType'),
        getattr(mod, 'AuthConfig'),
    )


class DatabaseManager:
    """Database manager for MCP server operations"""
    
    def __init__(self):
        # Use Any in annotations to avoid import-time NameError for MCPServerConfig
        self._cache: Dict[str, Any] = {}
        self._cache_dirty = True
    
    async def load_all_servers(self) -> Dict[str, Any]:
        """Load all MCP servers from database"""
        if not self._cache_dirty and self._cache:
            return self._cache.copy()
        
        async with get_db_session() as session:
            result = await session.execute(select(MCPServer))
            db_servers = result.scalars().all()
            
            servers: Dict[str, Any] = {}
            for db_server in db_servers:
                _MCPServerConfig, _MCPServerType, _AuthType, _AuthConfig = _get_mcp_types()
                config = self._db_to_config(db_server, _MCPServerConfig, _MCPServerType, _AuthType, _AuthConfig)
                servers[config.id] = config
            
            self._cache = servers
            self._cache_dirty = False
            return servers
    
    async def save_server(self, config: Any) -> bool:
        """Save MCP server configuration to database"""
        try:
            async with get_db_session() as session:
                # Check if server exists
                result = await session.execute(
                    select(MCPServer).where(MCPServer.id == config.id)
                )
                db_server = result.scalar_one_or_none()
                
                if db_server:
                    # Update existing server
                    await session.execute(
                        update(MCPServer)
                        .where(MCPServer.id == config.id)
                        .values(
                            name=config.name,
                            description=config.description,
                            server_type=config.server_type.value,
                            url=config.url,
                            command=config.command,
                            args=config.args,
                            env=config.env,
                            auth=self._auth_to_dict(config.auth) if config.auth else None,
                            enabled=config.enabled,
                            timeout=config.timeout,
                            sse_read_timeout=config.sse_read_timeout,
                            retry_count=config.retry_count,
                            health_check_interval=config.health_check_interval,
                            updated_at=datetime.utcnow()
                        )
                    )
                else:
                    # Create new server
                    db_server = MCPServer(
                        id=config.id,
                        name=config.name,
                        description=config.description,
                        server_type=config.server_type.value,
                        url=config.url,
                        command=config.command,
                        args=config.args,
                        env=config.env,
                        auth=self._auth_to_dict(config.auth) if config.auth else None,
                        enabled=config.enabled,
                        timeout=config.timeout,
                        sse_read_timeout=config.sse_read_timeout,
                        retry_count=config.retry_count,
                        health_check_interval=config.health_check_interval
                    )
                    session.add(db_server)
                
                await session.commit()
                self._cache_dirty = True
                return True
                
        except Exception as e:
            print(f"Error saving server {config.id}: {e}")
            return False
    
    async def delete_server(self, server_id: str) -> bool:
        """Delete MCP server from database"""
        try:
            async with get_db_session() as session:
                # Delete server status
                await session.execute(
                    delete(ServerStatus).where(ServerStatus.server_id == server_id)
                )
                
                # Delete tool info
                await session.execute(
                    delete(ToolInfo).where(ToolInfo.server_id == server_id)
                )
                
                # Delete server
                result = await session.execute(
                    delete(MCPServer).where(MCPServer.id == server_id)
                )
                
                await session.commit()
                self._cache_dirty = True
                return result.rowcount > 0
                
        except Exception as e:
            print(f"Error deleting server {server_id}: {e}")
            return False
    
    async def get_server(self, server_id: str) -> Optional[Any]:
        """Get specific MCP server configuration"""
        servers = await self.load_all_servers()
        return servers.get(server_id)
    
    async def update_server_status(self, server_id: str, active: bool, error_message: Optional[str] = None) -> bool:
        """Update server status in database"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(ServerStatus).where(ServerStatus.server_id == server_id)
                )
                db_status = result.scalar_one_or_none()
                
                now = datetime.utcnow()
                
                if db_status:
                    # Update existing status
                    await session.execute(
                        update(ServerStatus)
                        .where(ServerStatus.server_id == server_id)
                        .values(
                            active=active,
                            error_message=error_message,
                            last_health_check=now,
                            last_started=now if active else db_status.last_started,
                            last_stopped=now if not active else db_status.last_stopped,
                            updated_at=now
                        )
                    )
                else:
                    # Create new status
                    db_status = ServerStatus(
                        server_id=server_id,
                        active=active,
                        error_message=error_message,
                        last_health_check=now,
                        last_started=now if active else None,
                        last_stopped=now if not active else None
                    )
                    session.add(db_status)
                
                await session.commit()
                return True
                
        except Exception as e:
            print(f"Error updating server status {server_id}: {e}")
            return False
    
    async def get_server_status(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get server status from database"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(ServerStatus).where(ServerStatus.server_id == server_id)
                )
                db_status = result.scalar_one_or_none()
                
                if db_status:
                    return {
                        "server_id": db_status.server_id,
                        "active": db_status.active,
                        "last_health_check": db_status.last_health_check.isoformat() if db_status.last_health_check else None,
                        "error_message": db_status.error_message,
                        "last_started": db_status.last_started.isoformat() if db_status.last_started else None,
                        "last_stopped": db_status.last_stopped.isoformat() if db_status.last_stopped else None,
                        "updated_at": db_status.updated_at.isoformat()
                    }
                return None
                
        except Exception as e:
            print(f"Error getting server status {server_id}: {e}")
            return None
    
    async def save_tool_info(self, server_id: str, tool_name: str, tool_description: str, tool_schema: Optional[Dict[str, Any]] = None) -> bool:
        """Save tool information to database"""
        try:
            async with get_db_session() as session:
                tool_id = f"{server_id}:{tool_name}"
                
                result = await session.execute(
                    select(ToolInfo).where(ToolInfo.id == tool_id)
                )
                db_tool = result.scalar_one_or_none()
                
                if db_tool:
                    # Update existing tool
                    await session.execute(
                        update(ToolInfo)
                        .where(ToolInfo.id == tool_id)
                        .values(
                            tool_description=tool_description,
                            tool_schema=tool_schema,
                            updated_at=datetime.utcnow()
                        )
                    )
                else:
                    # Create new tool
                    db_tool = ToolInfo(
                        id=tool_id,
                        server_id=server_id,
                        tool_name=tool_name,
                        tool_description=tool_description,
                        tool_schema=tool_schema
                    )
                    session.add(db_tool)
                
                await session.commit()
                return True
                
        except Exception as e:
            print(f"Error saving tool info {server_id}:{tool_name}: {e}")
            return False
    
    async def get_tools_for_server(self, server_id: str) -> List[Dict[str, Any]]:
        """Get all tools for a specific server"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(ToolInfo).where(ToolInfo.server_id == server_id)
                )
                db_tools = result.scalars().all()
                
                tools = []
                for db_tool in db_tools:
                    tools.append({
                        "name": db_tool.tool_name,
                        "description": db_tool.tool_description,
                        "schema": db_tool.tool_schema,
                        "server_id": db_tool.server_id
                    })
                
                return tools
                
        except Exception as e:
            print(f"Error getting tools for server {server_id}: {e}")
            return []
    
    async def migrate_from_json(self, json_file_path: str) -> bool:
        """Migrate data from JSON file to database"""
        try:
            import json
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            servers = data.get('servers', {})
            migrated_count = 0
            
            for server_id, server_data in servers.items():
                # Convert to MCPServerConfig via lazy types
                _MCPServerConfig, _MCPServerType, _AuthType, _AuthConfig = _get_mcp_types()
                config = _MCPServerConfig(
                    id=server_id,
                    name=server_data['name'],
                    description=server_data['description'],
                    server_type=_MCPServerType(server_data['server_type']),
                    url=server_data.get('url'),
                    command=server_data.get('command'),
                    args=server_data.get('args'),
                    env=server_data.get('env'),
                    auth=self._dict_to_auth(server_data.get('auth'), _AuthType, _AuthConfig) if server_data.get('auth') else None,
                    enabled=server_data.get('enabled', True),
                    timeout=server_data.get('timeout', 5.0),
                    sse_read_timeout=server_data.get('sse_read_timeout', 300.0),
                    retry_count=server_data.get('retry_count', 3),
                    health_check_interval=server_data.get('health_check_interval', 60)
                )
                
                if await self.save_server(config):
                    migrated_count += 1
            
            print(f"Migrated {migrated_count} servers from JSON file")
            return True
            
        except Exception as e:
            print(f"Error migrating from JSON: {e}")
            return False
    
    def _db_to_config(self, db_server: MCPServer, MCPServerConfig, MCPServerType, AuthType, AuthConfig):
        """Convert database model to MCPServerConfig"""
        return MCPServerConfig(
            id=db_server.id,
            name=db_server.name,
            description=db_server.description,
            server_type=MCPServerType(db_server.server_type),
            url=db_server.url,
            command=db_server.command,
            args=db_server.args,
            env=db_server.env,
            auth=self._dict_to_auth(db_server.auth, AuthType, AuthConfig) if db_server.auth else None,
            enabled=db_server.enabled,
            timeout=db_server.timeout,
            sse_read_timeout=db_server.sse_read_timeout,
            retry_count=db_server.retry_count,
            health_check_interval=db_server.health_check_interval
        )
    
    def _auth_to_dict(self, auth: Any) -> Dict[str, Any]:
        """Convert AuthConfig to dictionary"""
        if not auth:
            return None
        
        return {
            "type": auth.type.value,
            "token": auth.token,
            "username": auth.username,
            "password": auth.password,
            "header_name": auth.header_name,
            "header_value": auth.header_value
        }
    
    def _dict_to_auth(self, auth_dict: Dict[str, Any], AuthType, AuthConfig):
        """Convert dictionary to AuthConfig"""
        if not auth_dict:
            return None
        
        return AuthConfig(
            type=AuthType(auth_dict.get('type', 'none')),
            token=auth_dict.get('token'),
            username=auth_dict.get('username'),
            password=auth_dict.get('password'),
            header_name=auth_dict.get('header_name'),
            header_value=auth_dict.get('header_value')
        )

# Global database manager instance
db_manager = DatabaseManager() 