#!/usr/bin/env python3
"""
Authentication Service

This module provides comprehensive authentication services including:
- User registration and login
- TOTP (Time-based One-Time Password) setup and verification
- Recovery codes generation and validation
- JWT token management with refresh tokens
- Rate limiting for security
"""

import os
import secrets
import uuid
import bcrypt
import base64
import pyotp
import qrcode
import io
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from pydantic import BaseModel, EmailStr
import jwt
from fastapi import HTTPException, status

from core.database import get_db_session, User, RecoveryCode


# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# TOTP Configuration
TOTP_ISSUER = "Personal Agent"
MAX_TOTP_ATTEMPTS = 5
TOTP_LOCKOUT_MINUTES = 15
RECOVERY_CODES_COUNT = 10


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None
    recovery_code: Optional[str] = None


class TOTPSetup(BaseModel):
    totp_code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    requires_totp: bool = False
    totp_setup_required: bool = False


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code_url: str
    recovery_codes: List[str]


class AuthService:
    """Service for handling authentication operations"""
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def _verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def _generate_recovery_codes() -> List[str]:
        """Generate recovery codes for TOTP"""
        codes = []
        for _ in range(RECOVERY_CODES_COUNT):
            # Generate 8-character alphanumeric codes
            code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
            codes.append(code)
        return codes
    
    @staticmethod
    def _hash_recovery_code(code: str) -> str:
        """Hash recovery code using bcrypt"""
        return bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def _verify_recovery_code(code: str, hashed: str) -> bool:
        """Verify recovery code against hash"""
        return bcrypt.checkpw(code.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def _create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def _verify_jwt_token(token: str) -> Optional[dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None
    
    @staticmethod
    async def _is_totp_locked(user: User) -> bool:
        """Check if user is locked out from TOTP attempts"""
        if user.totp_locked_until and datetime.utcnow() < user.totp_locked_until:
            return True
        return False
    
    @staticmethod
    async def _increment_totp_attempts(session: AsyncSession, user_id: str) -> bool:
        """Increment TOTP failed attempts and lock if necessary"""
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        user.failed_totp_attempts += 1
        
        # Lock account if max attempts reached
        if user.failed_totp_attempts >= MAX_TOTP_ATTEMPTS:
            user.totp_locked_until = datetime.utcnow() + timedelta(minutes=TOTP_LOCKOUT_MINUTES)
        
        await session.commit()
        return user.failed_totp_attempts >= MAX_TOTP_ATTEMPTS
    
    @staticmethod
    async def _reset_totp_attempts(session: AsyncSession, user_id: str):
        """Reset TOTP failed attempts"""
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(failed_totp_attempts=0, totp_locked_until=None)
        )
        await session.commit()
    
    @classmethod
    async def register_user(cls, user_data: UserCreate) -> dict:
        """Register a new user"""
        async with get_db_session() as session:
            # Check if user already exists
            result = await session.execute(
                select(User).where(User.email == user_data.email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            
            # Create new user
            user_id = str(uuid.uuid4())
            password_hash = cls._hash_password(user_data.password)
            
            new_user = User(
                id=user_id,
                email=user_data.email,
                password_hash=password_hash,
                totp_enabled=False
            )
            
            session.add(new_user)
            await session.commit()
            
            return {
                "id": user_id,
                "email": user_data.email,
                "message": "User registered successfully. Please set up TOTP for enhanced security."
            }
    
    @classmethod
    async def login_user(cls, login_data: UserLogin) -> TokenResponse:
        """Authenticate user and return tokens"""
        async with get_db_session() as session:
            # Get user by email
            result = await session.execute(
                select(User).where(User.email == login_data.email)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            # Verify password
            if not cls._verify_password(login_data.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            # If TOTP is not enabled, suggest setup but allow login
            if not user.totp_enabled:
                access_token = cls._create_jwt_token(
                    data={"sub": user.id, "email": user.email, "totp_verified": False}
                )
                refresh_token = cls._create_jwt_token(
                    data={"sub": user.id, "type": "refresh"},
                    expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
                )
                
                return TokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    totp_setup_required=True
                )
            
            # Check if TOTP is locked
            if await cls._is_totp_locked(user):
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Account locked due to too many failed TOTP attempts. Try again after {TOTP_LOCKOUT_MINUTES} minutes."
                )
            
            # TOTP is enabled - require TOTP code or recovery code
            if not login_data.totp_code and not login_data.recovery_code:
                # Return partial token that requires TOTP
                partial_token = cls._create_jwt_token(
                    data={"sub": user.id, "email": user.email, "totp_verified": False, "temp": True},
                    expires_delta=timedelta(minutes=5)  # Short expiry for partial tokens
                )
                return TokenResponse(
                    access_token=partial_token,
                    refresh_token="",
                    requires_totp=True
                )
            
            # Verify TOTP code
            if login_data.totp_code:
                totp = pyotp.TOTP(user.totp_secret)
                if not totp.verify(login_data.totp_code, valid_window=1):
                    # Increment failed attempts
                    locked = await cls._increment_totp_attempts(session, user.id)
                    if locked:
                        raise HTTPException(
                            status_code=status.HTTP_423_LOCKED,
                            detail=f"Account locked due to too many failed TOTP attempts. Try again after {TOTP_LOCKOUT_MINUTES} minutes."
                        )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid TOTP code"
                    )
            
            # Verify recovery code
            elif login_data.recovery_code:
                # Get unused recovery codes for user
                recovery_result = await session.execute(
                    select(RecoveryCode).where(
                        and_(
                            RecoveryCode.user_id == user.id,
                            RecoveryCode.used == False
                        )
                    )
                )
                recovery_codes = recovery_result.scalars().all()
                
                code_valid = False
                used_code = None
                
                for recovery_code in recovery_codes:
                    if cls._verify_recovery_code(login_data.recovery_code, recovery_code.code_hash):
                        code_valid = True
                        used_code = recovery_code
                        break
                
                if not code_valid:
                    # Increment failed attempts for recovery code too
                    await cls._increment_totp_attempts(session, user.id)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid recovery code"
                    )
                
                # Mark recovery code as used
                used_code.used = True
                used_code.used_at = datetime.utcnow()
                await session.commit()
            
            # Reset failed attempts on successful auth
            await cls._reset_totp_attempts(session, user.id)
            
            # Update last login
            user.last_login = datetime.utcnow()
            await session.commit()
            
            # Generate full tokens
            access_token = cls._create_jwt_token(
                data={"sub": user.id, "email": user.email, "totp_verified": True}
            )
            refresh_token = cls._create_jwt_token(
                data={"sub": user.id, "type": "refresh"},
                expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            )
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token
            )
    
    @classmethod
    async def setup_totp(cls, user_id: str, totp_data: TOTPSetup) -> TOTPSetupResponse:
        """Setup TOTP for user"""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Generate TOTP secret if not exists
            if not user.totp_secret:
                user.totp_secret = pyotp.random_base32()
            
            # Verify the provided TOTP code
            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(totp_data.totp_code, valid_window=1):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid TOTP code"
                )
            
            # Enable TOTP
            user.totp_enabled = True
            
            # Generate recovery codes
            recovery_codes = cls._generate_recovery_codes()
            
            # Delete existing recovery codes
            await session.execute(
                update(RecoveryCode)
                .where(RecoveryCode.user_id == user_id)
                .values(used=True, used_at=datetime.utcnow())
            )
            
            # Save new recovery codes
            for code in recovery_codes:
                recovery_code = RecoveryCode(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    code_hash=cls._hash_recovery_code(code)
                )
                session.add(recovery_code)
            
            await session.commit()
            
            # Generate QR code URL
            qr_url = totp.provisioning_uri(
                name=user.email,
                issuer_name=TOTP_ISSUER
            )
            
            return TOTPSetupResponse(
                secret=user.totp_secret,
                qr_code_url=qr_url,
                recovery_codes=recovery_codes
            )
    
    @classmethod
    async def generate_qr_code(cls, user_id: str) -> bytes:
        """Generate QR code image for TOTP setup"""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.totp_secret:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found or TOTP not initialized"
                )
            
            totp = pyotp.TOTP(user.totp_secret)
            qr_url = totp.provisioning_uri(
                name=user.email,
                issuer_name=TOTP_ISSUER
            )
            
            # Generate QR code image
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return img_buffer.getvalue()
    
    @classmethod
    async def refresh_token(cls, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token"""
        payload = cls._verify_jwt_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            # Generate new access token
            access_token = cls._create_jwt_token(
                data={"sub": user.id, "email": user.email, "totp_verified": user.totp_enabled}
            )
            
            # Generate new refresh token (token rotation)
            new_refresh_token = cls._create_jwt_token(
                data={"sub": user.id, "type": "refresh"},
                expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            )
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token
            )
    
    @classmethod
    async def verify_token(cls, token: str) -> Optional[dict]:
        """Verify access token and return user info"""
        payload = cls._verify_jwt_token(token)
        
        if not payload or payload.get("type") == "refresh":
            return None
        
        # Check if it's a temporary token that needs TOTP
        if payload.get("temp") and not payload.get("totp_verified"):
            return None
        
        user_id = payload.get("sub")
        
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.is_active:
                return None
            
            return {
                "user_id": user.id,
                "email": user.email,
                "totp_verified": payload.get("totp_verified", False)
            }
    
    @classmethod
    async def regenerate_recovery_codes(cls, user_id: str) -> List[str]:
        """Regenerate recovery codes for user"""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Mark all existing recovery codes as used
            await session.execute(
                update(RecoveryCode)
                .where(RecoveryCode.user_id == user_id)
                .values(used=True, used_at=datetime.utcnow())
            )
            
            # Generate new recovery codes
            recovery_codes = cls._generate_recovery_codes()
            
            # Save new recovery codes
            for code in recovery_codes:
                recovery_code = RecoveryCode(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    code_hash=cls._hash_recovery_code(code)
                )
                session.add(recovery_code)
            
            await session.commit()
            
            return recovery_codes