#!/usr/bin/env python3
"""
Authentication API endpoints

This module provides FastAPI endpoints for user authentication including:
- User registration and login
- TOTP setup and verification
- Recovery code management
- JWT token refresh
"""

from fastapi import APIRouter, HTTPException, Depends, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
import io
from typing import List, Optional

from core.auth_service import (
    AuthService, 
    UserCreate, 
    UserLogin, 
    TOTPSetup,
    TokenResponse,
    TOTPSetupResponse
)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])

# Security scheme
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    user_info = await AuthService.verify_token(token)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user
    
    - **email**: Valid email address
    - **password**: Secure password (minimum 8 characters recommended)
    
    Returns user ID and success message.
    """
    try:
        result = await AuthService.register_user(user_data)
        return {
            "success": True,
            "data": result,
            "message": "User registered successfully. Please set up TOTP for enhanced security."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """
    Authenticate user and return JWT tokens
    
    - **email**: User's email address
    - **password**: User's password
    - **totp_code**: Optional TOTP code (required if TOTP is enabled)
    - **recovery_code**: Optional recovery code (alternative to TOTP)
    
    Returns access token, refresh token, and authentication status.
    """
    try:
        return await AuthService.login_user(login_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/setup-totp", response_model=TOTPSetupResponse)
async def setup_totp(
    totp_data: TOTPSetup,
    current_user: dict = Depends(get_current_user)
):
    """
    Set up TOTP (Time-based One-Time Password) for the current user
    
    - **totp_code**: 6-digit code from authenticator app to verify setup
    
    Returns TOTP secret, QR code URL, and recovery codes.
    """
    try:
        result = await AuthService.setup_totp(current_user["user_id"], totp_data)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TOTP setup failed: {str(e)}"
        )


@router.get("/qr-code")
async def get_qr_code(current_user: dict = Depends(get_current_user)):
    """
    Generate QR code image for TOTP setup
    
    Returns PNG image that can be scanned by authenticator apps.
    """
    try:
        qr_image = await AuthService.generate_qr_code(current_user["user_id"])
        return StreamingResponse(
            io.BytesIO(qr_image),
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=totp-qr-code.png"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"QR code generation failed: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token_data: dict):
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token and refresh token.
    """
    refresh_token = refresh_token_data.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token is required"
        )
    
    try:
        return await AuthService.refresh_token(refresh_token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current user information
    
    Returns user ID, email, and TOTP verification status.
    """
    return {
        "success": True,
        "data": current_user
    }


@router.post("/regenerate-recovery-codes")
async def regenerate_recovery_codes(current_user: dict = Depends(get_current_user)):
    """
    Regenerate recovery codes for the current user
    
    Returns new set of recovery codes. Previous codes will be invalidated.
    """
    try:
        recovery_codes = await AuthService.regenerate_recovery_codes(current_user["user_id"])
        return {
            "success": True,
            "data": {
                "recovery_codes": recovery_codes
            },
            "message": "Recovery codes regenerated successfully. Please save them securely."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recovery code regeneration failed: {str(e)}"
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout user (client-side token invalidation)
    
    Note: Since JWTs are stateless, actual invalidation happens on the client side.
    This endpoint is for consistency and potential future server-side token blacklisting.
    """
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.get("/check-auth")
async def check_auth(current_user: dict = Depends(get_current_user)):
    """
    Check if the current token is valid
    
    Returns authentication status and user information.
    """
    return {
        "success": True,
        "authenticated": True,
        "data": current_user
    }


# Health check endpoint
@router.get("/health")
async def health_check():
    """
    Health check for authentication service
    """
    return {
        "success": True,
        "service": "authentication",
        "status": "healthy"
    }