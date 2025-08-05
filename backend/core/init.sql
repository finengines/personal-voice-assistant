-- Database initialization script for Personal Agent
-- This script runs when the PostgreSQL container starts

-- Create the database if it doesn't exist
-- (PostgreSQL creates the database automatically based on POSTGRES_DB env var)

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE personal_agent TO postgres;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- The actual tables will be created by SQLAlchemy when the application starts 