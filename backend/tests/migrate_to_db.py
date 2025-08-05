#!/usr/bin/env python3
"""
Migration script to transition from JSON file storage to PostgreSQL database

This script helps migrate existing MCP server configurations from JSON files
to the new PostgreSQL database storage system.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, health_check, create_tables_sync
from db_manager import db_manager


async def migrate_from_json(json_file_path: str):
    """Migrate data from JSON file to database"""
    print(f"🔄 Starting migration from {json_file_path}")
    
    # Check if JSON file exists
    if not os.path.exists(json_file_path):
        print(f"❌ JSON file not found: {json_file_path}")
        return False
    
    try:
        # Initialize database
        print("📊 Initializing database...")
        await init_db()
        
        # Check database health
        if not await health_check():
            print("❌ Database health check failed")
            return False
        
        # Migrate data
        print("🔄 Migrating data from JSON to database...")
        success = await db_manager.migrate_from_json(json_file_path)
        
        if success:
            print("✅ Migration completed successfully!")
            
            # Verify migration
            servers = await db_manager.load_all_servers()
            print(f"📊 Migrated {len(servers)} servers to database")
            
            for server_id, config in servers.items():
                print(f"  - {server_id}: {config.name}")
            
            return True
        else:
            print("❌ Migration failed")
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False


async def create_default_servers():
    """Create default server configurations in database"""
    print("🔄 Creating default server configurations...")
    
    from mcp_config_db import MCPServerConfig, MCPServerType, AuthType, AuthConfig
    
    default_servers = [
        MCPServerConfig(
            id="example-sse",
            name="Example SSE Server",
            description="Example MCP server using Server-Sent Events",
            server_type=MCPServerType.SSE,
            url="http://localhost:8000/sse",
            auth=AuthConfig(type=AuthType.NONE),
            enabled=False
        ),
        MCPServerConfig(
            id="example-http",
            name="Example HTTP Server",
            description="Example MCP server using streamable HTTP",
            server_type=MCPServerType.HTTP,
            url="http://localhost:8000/mcp",
            auth=AuthConfig(type=AuthType.NONE),
            enabled=False
        ),
        MCPServerConfig(
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
    ]
    
    try:
        for config in default_servers:
            success = await db_manager.save_server(config)
            if success:
                print(f"✅ Created server: {config.id}")
            else:
                print(f"❌ Failed to create server: {config.id}")
        
        return True
    except Exception as e:
        print(f"❌ Error creating default servers: {e}")
        return False


async def verify_database():
    """Verify database setup and connectivity"""
    print("🔍 Verifying database setup...")
    
    try:
        # Initialize database
        await init_db()
        
        # Check health
        if await health_check():
            print("✅ Database is healthy")
        else:
            print("❌ Database health check failed")
            return False
        
        # Check if we have any servers
        servers = await db_manager.load_all_servers()
        print(f"📊 Found {len(servers)} servers in database")
        
        return True
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False


async def main():
    """Main migration function"""
    print("🚀 Personal Agent Database Migration Tool")
    print("=" * 50)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "migrate":
            json_file = sys.argv[2] if len(sys.argv) > 2 else "mcp_servers.json"
            success = await migrate_from_json(json_file)
            sys.exit(0 if success else 1)
            
        elif command == "create-defaults":
            success = await create_default_servers()
            sys.exit(0 if success else 1)
            
        elif command == "verify":
            success = await verify_database()
            sys.exit(0 if success else 1)
            
        else:
            print(f"❌ Unknown command: {command}")
            print_usage()
            sys.exit(1)
    else:
        print_usage()
        sys.exit(1)


def print_usage():
    """Print usage information"""
    print("\nUsage:")
    print("  python migrate_to_db.py migrate [json_file]  - Migrate from JSON file")
    print("  python migrate_to_db.py create-defaults      - Create default servers")
    print("  python migrate_to_db.py verify               - Verify database setup")
    print("\nExamples:")
    print("  python migrate_to_db.py migrate")
    print("  python migrate_to_db.py migrate mcp_servers.json")
    print("  python migrate_to_db.py create-defaults")
    print("  python migrate_to_db.py verify")


if __name__ == "__main__":
    asyncio.run(main()) 