#!/bin/bash

# Personal Agent Database Setup Script
# This script helps set up the database and migrate from JSON storage

set -e

echo "🚀 Personal Agent Database Setup"
echo "================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Function to check if PostgreSQL is ready
wait_for_postgres() {
    echo "⏳ Waiting for PostgreSQL to be ready..."
    until docker exec personal_agent_db pg_isready -U postgres > /dev/null 2>&1; do
        sleep 2
    done
    echo "✅ PostgreSQL is ready!"
}

# Function to check if LiveKit is ready
wait_for_livekit() {
    echo "⏳ Waiting for LiveKit to be ready..."
    until docker exec personal_agent_livekit wget --quiet --tries=1 --spider http://localhost:7882/health > /dev/null 2>&1; do
        sleep 2
    done
    echo "✅ LiveKit is ready!"
}

# Function to run migration
run_migration() {
    echo "🔄 Running database migration..."
    docker exec personal_agent_backend python migrate_to_db.py migrate
}

# Function to create default servers
create_defaults() {
    echo "🔄 Creating default server configurations..."
    docker exec personal_agent_backend python migrate_to_db.py create-defaults
}

# Function to verify database
verify_database() {
    echo "🔍 Verifying database setup..."
    docker exec personal_agent_backend python migrate_to_db.py verify
}

# Main setup process
echo "📦 Starting services with Docker Compose..."
docker-compose up -d postgres livekit

# Wait for PostgreSQL to be ready
wait_for_postgres

# Wait for LiveKit to be ready
wait_for_livekit

echo "📦 Starting backend service..."
docker-compose up -d backend

# Wait a moment for the backend to start
sleep 10

# Check if we should migrate from existing JSON file
if [ -f "backend/mcp_servers.json" ]; then
    echo "📄 Found existing mcp_servers.json file"
    read -p "Do you want to migrate data from the JSON file? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_migration
    fi
fi

# Create default servers if database is empty
echo "🔍 Checking if database has any servers..."
if docker exec personal_agent_backend python -c "
import asyncio
from db_manager import db_manager
servers = asyncio.run(db_manager.load_all_servers())
print(len(servers))
" | grep -q "0"; then
    echo "📝 Database is empty, creating default servers..."
    create_defaults
fi

# Verify the setup
verify_database

echo ""
echo "✅ Database setup complete!"
echo ""
echo "🌐 Services are running:"
echo "  - Frontend: http://localhost:8080"
echo "  - Backend API: http://localhost:8082"
echo "  - LiveKit Server: ws://localhost:7880"
echo "  - Database: localhost:5433"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - Access database: docker exec -it personal_agent_db psql -U postgres -d personal_agent"
echo ""
echo "🔧 To add your API keys, edit the .env file or set environment variables:"
echo "  - OPENAI_API_KEY"
echo "  - DEEPGRAM_API_KEY"
echo "  - LIVEKIT_URL"
echo "  - LIVEKIT_API_KEY"
echo "  - LIVEKIT_API_SECRET" 