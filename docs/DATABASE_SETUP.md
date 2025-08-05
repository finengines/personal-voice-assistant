# Database Setup for Personal Agent

This document explains how to set up PostgreSQL database persistence for your Personal Agent, replacing the JSON file storage system.

## 🎯 Why PostgreSQL?

- **Reliability**: ACID compliance ensures data integrity
- **Performance**: Optimized for concurrent access
- **Backup Support**: Your deployment platform supports PostgreSQL
- **JSON Support**: Native JSONB for flexible schema evolution
- **Production Ready**: Battle-tested for production deployments

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)

```bash
# Make the setup script executable
chmod +x setup_database.sh

# Run the automated setup
./setup_database.sh
```

This will:
1. Start PostgreSQL container
2. Start the backend service
3. Migrate existing JSON data (if found)
4. Create default server configurations
5. Verify the setup

### Option 2: Manual Setup

#### 1. Start the Database

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker exec personal_agent_db pg_isready -U postgres
```

#### 2. Install Database Dependencies

```bash
cd backend
pip install -r requirements-db.txt
```

#### 3. Initialize Database

```bash
# Initialize tables
python -c "
import asyncio
from database import init_db
asyncio.run(init_db())
"

# Verify database health
python -c "
import asyncio
from database import health_check
print('Database healthy:', asyncio.run(health_check()))
"
```

#### 4. Migrate Existing Data

```bash
# Migrate from JSON file (if exists)
python migrate_to_db.py migrate

# Or create default servers
python migrate_to_db.py create-defaults
```

#### 5. Start the Backend

```bash
# Start the backend service
docker-compose up -d backend
```

## 📊 Database Schema

### Tables

1. **mcp_servers**: MCP server configurations
   - `id`: Primary key (server identifier)
   - `name`: Human-readable name
   - `description`: Server description
   - `server_type`: Type of server (sse, http, openai_tools, stdio)
   - `url`: Server URL
   - `command`: Command for STDIO servers
   - `args`: Command arguments (JSONB)
   - `env`: Environment variables (JSONB)
   - `auth`: Authentication configuration (JSONB)
   - `enabled`: Whether server is enabled
   - `timeout`: Connection timeout
   - `sse_read_timeout`: SSE read timeout
   - `retry_count`: Number of retries
   - `health_check_interval`: Health check interval
   - `created_at`: Creation timestamp
   - `updated_at`: Last update timestamp

2. **server_status**: Server status tracking
   - `server_id`: Foreign key to mcp_servers
   - `active`: Whether server is currently active
   - `last_health_check`: Last health check timestamp
   - `error_message`: Last error message
   - `last_started`: Last start timestamp
   - `last_stopped`: Last stop timestamp
   - `updated_at`: Last update timestamp

3. **tool_info**: Tool information from MCP servers
   - `id`: Primary key (server_id:tool_name)
   - `server_id`: Foreign key to mcp_servers
   - `tool_name`: Name of the tool
   - `tool_description`: Tool description
   - `tool_schema`: Tool schema/parameters (JSONB)
   - `created_at`: Creation timestamp
   - `updated_at`: Last update timestamp

## 🔧 Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/personal_agent

# API Keys (required)
OPENAI_API_KEY=your-openai-api-key
DEEPGRAM_API_KEY=your-deepgram-api-key

# LiveKit Configuration
LIVEKIT_URL=ws://127.0.0.1:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# MCP API Configuration
MCP_API_PORT=8082
```

### Docker Compose

The `docker-compose.yml` file includes:
- PostgreSQL 15 with persistent storage
- Backend service with database support
- Frontend service
- Health checks and proper dependencies

## 🔄 Migration from JSON

### Automatic Migration

The setup script automatically detects and migrates existing JSON files:

```bash
./setup_database.sh
```

### Manual Migration

```bash
# Migrate specific JSON file
python migrate_to_db.py migrate mcp_servers.json

# Create default servers
python migrate_to_db.py create-defaults

# Verify database
python migrate_to_db.py verify
```

## 🛠️ Database Management

### Access Database

```bash
# Connect to PostgreSQL
docker exec -it personal_agent_db psql -U postgres -d personal_agent

# View tables
\dt

# View server configurations
SELECT id, name, server_type, enabled FROM mcp_servers;

# View server status
SELECT server_id, active, last_health_check FROM server_status;
```

### Backup and Restore

```bash
# Backup database
docker exec personal_agent_db pg_dump -U postgres personal_agent > backup.sql

# Restore database
docker exec -i personal_agent_db psql -U postgres personal_agent < backup.sql
```

### Reset Database

```bash
# Drop all tables
python -c "
import asyncio
from database import drop_db
asyncio.run(drop_db())
"

# Reinitialize
python -c "
import asyncio
from database import init_db
asyncio.run(init_db())
"
```

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check if PostgreSQL is running
   docker ps | grep postgres
   
   # Check logs
   docker-compose logs postgres
   ```

2. **Migration Failed**
   ```bash
   # Check database health
   python migrate_to_db.py verify
   
   # Check JSON file format
   python -c "import json; json.load(open('mcp_servers.json'))"
   ```

3. **Backend Won't Start**
   ```bash
   # Check backend logs
   docker-compose logs backend
   
   # Check database connectivity
   docker exec personal_agent_backend python -c "
   import asyncio
   from database import health_check
   print(asyncio.run(health_check()))
   "
   ```

### Health Checks

```bash
# Database health
python -c "
import asyncio
from database import health_check
print('Database healthy:', asyncio.run(health_check()))
"

# API health
curl http://localhost:8082/health
```

## 📈 Performance Considerations

- **Connection Pooling**: Configured with 10 connections, 20 overflow
- **Indexes**: Primary keys and foreign keys are automatically indexed
- **JSONB**: Efficient JSON storage and querying
- **Caching**: Application-level caching for server configurations

## 🔒 Security

- **Environment Variables**: Sensitive data stored in environment variables
- **Database User**: Non-root database user with minimal privileges
- **Network Isolation**: Services communicate via Docker network
- **Volume Persistence**: Database data persisted in Docker volumes

## 🚀 Deployment

### Production Checklist

- [ ] Set strong database password
- [ ] Configure proper environment variables
- [ ] Set up database backups
- [ ] Configure SSL/TLS for database connections
- [ ] Set up monitoring and logging
- [ ] Test migration process
- [ ] Verify all API endpoints work

### Environment Variables for Production

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# API Keys
OPENAI_API_KEY=your-production-key
DEEPGRAM_API_KEY=your-production-key

# LiveKit
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your-production-key
LIVEKIT_API_SECRET=your-production-secret
```

## 📚 API Changes

The API endpoints remain the same, but now use database persistence:

- `GET /servers` - List all servers (from database)
- `POST /servers` - Create server (saved to database)
- `PUT /servers/{id}` - Update server (updated in database)
- `DELETE /servers/{id}` - Delete server (removed from database)
- `GET /servers/{id}/status` - Get server status (from database)

## 🔄 Rollback

If you need to rollback to JSON storage:

1. Stop the services
2. Restore the original `mcp_config.py`
3. Restore the original `mcp_api.py`
4. Restart without database dependencies

```bash
# Stop services
docker-compose down

# Restore original files (if you have backups)
# cp mcp_config.py.backup mcp_config.py
# cp mcp_api.py.backup mcp_api.py

# Start without database
docker-compose up -d
``` 