#!/usr/bin/env python3
"""
Authentication Setup Verification Script

This script verifies that the authentication system is properly configured
and all dependencies are available.
"""

import sys
import importlib.util
import os

def check_dependency(module_name, pip_name=None):
    """Check if a Python module is available"""
    try:
        importlib.import_module(module_name)
        return True, f"✅ {module_name} is available"
    except ImportError:
        pip_name = pip_name or module_name
        return False, f"❌ {module_name} not found. Install with: pip install {pip_name}"

def check_environment_variable(var_name, required=True):
    """Check if an environment variable is set"""
    value = os.getenv(var_name)
    if value and not value.startswith('your_'):
        return True, f"✅ {var_name} is configured"
    elif required:
        return False, f"❌ {var_name} is missing or has default value"
    else:
        return True, f"⚠️  {var_name} is optional and not set"

def main():
    print("🔐 Personal Agent Authentication Setup Verification")
    print("=" * 55)
    
    all_good = True
    
    # Check Python dependencies
    print("\n📦 Checking Python Dependencies:")
    dependencies = [
        ("fastapi", "fastapi"),
        ("pydantic", "pydantic[email]"),
        ("bcrypt", "bcrypt"),
        ("jwt", "PyJWT"),
        ("pyotp", "pyotp"),
        ("qrcode", "qrcode[pil]"),
        ("email_validator", "email-validator"),
    ]
    
    for module, pip_name in dependencies:
        success, message = check_dependency(module, pip_name)
        print(f"  {message}")
        if not success:
            all_good = False
    
    # Check environment variables
    print("\n🔧 Checking Environment Variables:")
    env_vars = [
        ("JWT_SECRET", True),
        ("API_KEY_ENCRYPTION_KEY", True),
        ("DATABASE_URL", False),  # Optional for verification
        ("POSTGRES_PASSWORD", True),
        ("OPENAI_API_KEY", True),
        ("DEEPGRAM_API_KEY", True),
        ("LIVEKIT_API_KEY", True),
        ("LIVEKIT_API_SECRET", True),
        ("AUTH_API_PORT", False),
    ]
    
    for var_name, required in env_vars:
        success, message = check_environment_variable(var_name, required)
        print(f"  {message}")
        if not success:
            all_good = False
    
    # Check file structure
    print("\n📁 Checking File Structure:")
    required_files = [
        "core/auth_service.py",
        "api/auth_api.py", 
        "start_auth_server.py",
        "start_auth_api.py",
        "requirements/requirements-agent.txt",
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path} exists")
        else:
            print(f"  ❌ {file_path} not found")
            all_good = False
    
    # Check Docker files
    print("\n🐳 Checking Docker Configuration:")
    docker_files = [
        ("../docker-compose.prod.yml", "Production Docker Compose"),
        ("../docker-compose.yml", "Development Docker Compose"),
        ("Dockerfile", "Backend Dockerfile"),
    ]
    
    for file_path, description in docker_files:
        if os.path.exists(file_path):
            print(f"  ✅ {description} exists")
        else:
            print(f"  ❌ {description} not found")
            all_good = False
    
    # Summary
    print("\n" + "=" * 55)
    if all_good:
        print("🎉 All checks passed! Authentication system is ready for deployment.")
        print("\nNext steps:")
        print("1. Deploy with: docker-compose -f docker-compose.prod.yml up -d")
        print("2. Create your first admin account via the frontend")
        print("3. Set up TOTP and save your recovery codes")
        return 0
    else:
        print("⚠️  Some issues found. Please resolve them before deployment.")
        print("\nRun the setup script to fix common issues:")
        print("  ./scripts/setup_auth.sh")
        return 1

if __name__ == "__main__":
    sys.exit(main())