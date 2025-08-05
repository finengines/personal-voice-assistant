#!/usr/bin/env python3
"""
Authentication API Server (Production Entry Point)

This is the standalone authentication server entry point for production deployment.
"""

import uvicorn
import os
from start_simple_auth_server import create_app

def main():
    """Main entry point for production authentication server"""
    # Get configuration from environment
    port = int(os.getenv("AUTH_API_PORT", 8001))
    host = os.getenv("AUTH_API_HOST", "0.0.0.0")
    
    print("🔐 Starting Production Simple Authentication Server...")
    print(f"🌐 Server will be available at: http://{host}:{port}")
    
    # Verify required environment variables
    required_vars = ["ADMIN_EMAIL", "ADMIN_PASSWORD", "JWT_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    admin_email = os.getenv("ADMIN_EMAIL")
    print(f"✅ Admin account configured for: {admin_email}")
    
    app = create_app()
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=False,  # No reload in production
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()