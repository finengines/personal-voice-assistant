#!/usr/bin/env python3
"""
Authentication Server Startup Script

This script starts the FastAPI authentication server.
"""

import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.auth_api import router as auth_router
from core.database import init_db


def create_app() -> FastAPI:
    """Create FastAPI application with authentication routes"""
    app = FastAPI(
        title="Personal Agent Authentication API",
        description="Secure authentication service with TOTP and recovery codes",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],  # Add your frontend URLs
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include authentication routes
    app.include_router(auth_router)
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize database on startup"""
        await init_db()
        print("🚀 Authentication server started successfully")
        print("📚 API docs available at: http://localhost:8001/docs")
    
    @app.get("/")
    async def root():
        return {
            "service": "Personal Agent Authentication API",
            "status": "running",
            "docs": "/docs"
        }
    
    return app


if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("AUTH_API_PORT", 8001))
    host = os.getenv("AUTH_API_HOST", "0.0.0.0")
    
    print("🔐 Starting Personal Agent Authentication Server...")
    print(f"🌐 Server will be available at: http://{host}:{port}")
    
    app = create_app()
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=os.getenv("ENV") != "production",  # Disable reload in production
        log_level="info"
    )