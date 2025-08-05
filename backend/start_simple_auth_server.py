#!/usr/bin/env python3
"""
Simplified Authentication Server for Personal Agent
Single admin account configured via environment variables
"""

import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.simple_auth_api import router as auth_router

def create_app():
    """Create FastAPI application"""
    app = FastAPI(
        title="Personal Agent Simple Authentication API",
        description="Simplified authentication API for single admin user",
        version="2.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify your domain
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include authentication router
    app.include_router(auth_router)
    
    @app.get("/")
    async def root():
        return {
            "service": "Personal Agent Simple Authentication API",
            "version": "2.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/auth/health"
        }
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "ok", 
            "message": "Simple Auth API is healthy",
            "service": "auth"
        }
    
    return app

if __name__ == "__main__":
    # Get configuration from environment
    port = int(os.getenv("AUTH_API_PORT", 8001))
    host = os.getenv("AUTH_API_HOST", "0.0.0.0")
    
    print("🔐 Starting Personal Agent Simple Authentication Server...")
    print(f"🌐 Server will be available at: http://{host}:{port}")
    print("📋 Features:")
    print("  • Single admin account from environment variables")
    print("  • TOTP support with recovery codes")
    print("  • JWT tokens with automatic refresh")
    print("  • No database required")
    print("  • No user registration")
    
    # Verify required environment variables
    required_vars = ["ADMIN_EMAIL", "ADMIN_PASSWORD", "JWT_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables before starting the server.")
        exit(1)
    
    admin_email = os.getenv("ADMIN_EMAIL")
    print(f"✅ Admin account configured for: {admin_email}")
    print("📚 API docs available at: http://localhost:8001/docs")
    
    app = create_app()
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=os.getenv("ENV") != "production",
        log_level="info"
    )