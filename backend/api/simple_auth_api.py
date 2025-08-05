"""
Simplified Authentication API for Personal Agent
Single admin account - no registration, no database required
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

from core.simple_auth_service import (
    SimpleAuthService, 
    LoginRequest, 
    Token, 
    UserResponse, 
    TOTPSetupRequest,
    TOTPVerifyRequest,
    RefreshTokenRequest
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Initialize the simplified auth service
try:
    auth_service = SimpleAuthService()
except ValueError as e:
    print(f"❌ Authentication service initialization failed: {e}")
    print("Please set ADMIN_EMAIL, ADMIN_PASSWORD, and JWT_SECRET environment variables")
    raise

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to get current authenticated user"""
    user = auth_service.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "success": True,
        "service": "auth",
        "message": "Simple authentication API is healthy"
    }

# Login endpoint
@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """Login with email/password and optional TOTP"""
    try:
        result = auth_service.authenticate(
            email=request.email,
            password=request.password,
            totp_code=request.totp_code,
            recovery_code=request.recovery_code
        )
        return Token(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

# Refresh token endpoint
@router.post("/refresh", response_model=Token)
async def refresh_access_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    try:
        result = auth_service.refresh_token(request.refresh_token)
        return Token(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

# Get current user info
@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(**current_user)

# TOTP Setup
@router.post("/totp/setup")
async def setup_totp(
    request: TOTPSetupRequest,
    current_user: dict = Depends(get_current_user)
):
    """Set up TOTP for the admin account"""
    try:
        result = auth_service.setup_totp(request.password)
        return {
            "success": True,
            "qr_code": result["qr_code"],
            "recovery_codes": result["recovery_codes"],
            "message": "TOTP setup successful. Save your recovery codes!"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# TOTP Verification
@router.post("/totp/verify")
async def verify_totp(
    request: TOTPVerifyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify TOTP setup with a test code"""
    try:
        success = auth_service.verify_totp_setup(request.totp_code)
        if success:
            return {
                "success": True,
                "message": "TOTP verification successful"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid TOTP code"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Get Recovery Codes
@router.post("/recovery-codes")
async def get_recovery_codes(
    request: TOTPSetupRequest,  # Reuse password request model
    current_user: dict = Depends(get_current_user)
):
    """Get remaining recovery codes"""
    try:
        codes = auth_service.get_recovery_codes(request.password)
        return {
            "success": True,
            "recovery_codes": codes,
            "count": len(codes)
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Regenerate Recovery Codes
@router.post("/recovery-codes/regenerate")
async def regenerate_recovery_codes(
    request: TOTPSetupRequest,  # Reuse password request model
    current_user: dict = Depends(get_current_user)
):
    """Regenerate recovery codes"""
    try:
        codes = auth_service.regenerate_recovery_codes(request.password)
        return {
            "success": True,
            "recovery_codes": codes,
            "message": "Recovery codes regenerated successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Logout endpoint (client-side token removal)
@router.post("/logout")
async def logout():
    """Logout endpoint (tokens are stateless, so this is just for client cleanup)"""
    return {
        "success": True,
        "message": "Logged out successfully"
    }