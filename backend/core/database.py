#!/usr/bin/env python3
"""
Database configuration and models for Personal Agent

This module provides database setup, models, and connection management
for the personal agent's data persistence layer.
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, String, Boolean, Float, Integer, Text, DateTime, JSON, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from contextlib import asynccontextmanager

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/personal_agent")
SYNC_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/personal_agent")

# Create async engine
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for debugging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# Create sync engine for migrations
sync_engine = create_engine(SYNC_DATABASE_URL)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Database models
class MCPServer(Base):
    """MCP Server configuration model"""
    __tablename__ = "mcp_servers"
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    server_type = Column(String(50), nullable=False)  # sse, http, openai_tools, stdio
    url = Column(String(500), nullable=True)
    command = Column(String(500), nullable=True)
    args = Column(JSONB, nullable=True)  # List of strings
    env = Column(JSONB, nullable=True)   # Dict of environment variables
    auth = Column(JSONB, nullable=True)  # Auth configuration
    enabled = Column(Boolean, default=True)
    timeout = Column(Float, default=5.0)
    sse_read_timeout = Column(Float, default=300.0)
    retry_count = Column(Integer, default=3)
    health_check_interval = Column(Integer, default=60)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ServerStatus(Base):
    """MCP Server status tracking"""
    __tablename__ = "server_status"
    
    server_id = Column(String(255), primary_key=True)
    active = Column(Boolean, default=False)
    last_health_check = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    last_started = Column(DateTime, nullable=True)
    last_stopped = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ToolInfo(Base):
    """Tool information from MCP servers"""
    __tablename__ = "tool_info"
    
    id = Column(String(255), primary_key=True)  # server_id:tool_name
    server_id = Column(String(255), nullable=False)
    tool_name = Column(String(255), nullable=False)
    tool_description = Column(Text, nullable=True)
    tool_schema = Column(JSONB, nullable=True)  # Tool schema/parameters
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AgentPreset(Base):
    """Agent preset configuration model"""
    __tablename__ = "agent_presets"
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=False)
    voice_config = Column(JSONB, nullable=False)  # Voice configuration (provider, model, settings)
    mcp_server_ids = Column(JSONB, nullable=True)  # List of enabled MCP server IDs
    llm_config = Column(JSONB, nullable=True)  # LLM configuration (model, temperature, etc.)
    stt_config = Column(JSONB, nullable=True)  # STT configuration (provider, model, language)
    agent_config = Column(JSONB, nullable=True)  # Additional agent settings
    enabled = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GlobalSettings(Base):
    """Global application settings"""
    __tablename__ = "global_settings"
    
    id = Column(String(255), primary_key=True, default="main")
    global_system_prompt = Column(Text, nullable=True)  # Global system prompt applied to all agents
    enabled = Column(Boolean, default=True)  # Whether global prompt is enabled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    """User authentication model"""
    __tablename__ = "users"
    
    id = Column(String(255), primary_key=True)  # UUID
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hashed password
    totp_secret = Column(String(255), nullable=True)  # Base32 encoded TOTP secret
    totp_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    failed_totp_attempts = Column(Integer, default=0)
    totp_locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RecoveryCode(Base):
    """TOTP recovery codes for account recovery"""
    __tablename__ = "recovery_codes"
    
    id = Column(String(255), primary_key=True)  # UUID
    user_id = Column(String(255), nullable=False, index=True)  # Foreign key to User.id
    code_hash = Column(String(255), nullable=False)  # bcrypt hashed recovery code
    used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database session management
@asynccontextmanager
async def get_db_session():
    """Get database session with automatic cleanup"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Import models to ensure they're registered with Base.metadata
try:
    from core.api_key_manager import APIKey
    print("✅ APIKey model imported for database creation")
except ImportError as e:
    print(f"⚠️  Could not import APIKey model: {e}")

# Database initialization
async def init_db():
    """Initialize database tables"""
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        # Handle duplicate table/type errors gracefully
        error_msg = str(e).lower()
        if 'already exists' in error_msg or 'duplicate key' in error_msg:
            print(f"ℹ️ Database objects already exist (this is normal during concurrent startup): {e}")
        else:
            print(f"❌ Database initialization error: {e}")
            raise

async def drop_db():
    """Drop all database tables (use with caution)"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Database utilities
async def health_check():
    """Check database connectivity"""
    try:
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False

# Migration utilities
def create_tables_sync():
    """Create tables synchronously (for migrations)"""
    Base.metadata.create_all(sync_engine)

def drop_tables_sync():
    """Drop tables synchronously (for migrations)"""
    Base.metadata.drop_all(sync_engine) 