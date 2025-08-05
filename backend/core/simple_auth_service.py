"""
Simplified Authentication Service for Personal Agent
Single admin user configured via environment variables - no database needed
"""

import os
import bcrypt
import jwt
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from PIL import Image
from pydantic import BaseModel, EmailStr

# Pydantic models for API validation
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None
    recovery_code: Optional[str] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserResponse(BaseModel):
    email: str
    name: str
    totp_enabled: bool

class TOTPSetupRequest(BaseModel):
    password: str

class TOTPVerifyRequest(BaseModel):
    totp_code: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class SimpleAuthService:
    """Simplified authentication service using environment variables"""
    
    def __init__(self):
        # Load admin credentials from environment
        self.admin_email = os.getenv("ADMIN_EMAIL", "").strip()
        self.admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
        self.admin_name = os.getenv("ADMIN_NAME", "Admin").strip()
        
        if not self.admin_email or not self.admin_password:
            raise ValueError("ADMIN_EMAIL and ADMIN_PASSWORD must be set in environment variables")
        
        # Hash the admin password for secure storage
        self.admin_password_hash = bcrypt.hashpw(
            self.admin_password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # JWT settings
        self.jwt_secret = os.getenv("JWT_SECRET")
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET must be set in environment variables")
        
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
        
        # TOTP settings (stored in memory/filesystem)
        self.totp_secret_file = "/tmp/totp_secret.txt"
        self.recovery_codes_file = "/tmp/recovery_codes.txt"
        
        # Rate limiting (simple in-memory counter)
        self.failed_attempts = 0
        self.lockout_until = None
    
    def _is_locked_out(self) -> bool:
        """Check if account is locked due to too many failed attempts"""
        if self.lockout_until and datetime.now(timezone.utc) < self.lockout_until:
            return True
        if self.lockout_until and datetime.now(timezone.utc) >= self.lockout_until:
            # Reset after lockout period
            self.failed_attempts = 0
            self.lockout_until = None
        return False
    
    def _record_failed_attempt(self):
        """Record a failed login attempt"""
        self.failed_attempts += 1
        if self.failed_attempts >= 5:
            # Lock out for 15 minutes
            self.lockout_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    def _reset_failed_attempts(self):
        """Reset failed attempts on successful login"""
        self.failed_attempts = 0
        self.lockout_until = None
    
    def _load_totp_secret(self) -> Optional[str]:
        """Load TOTP secret from file"""
        try:
            if os.path.exists(self.totp_secret_file):
                with open(self.totp_secret_file, 'r') as f:
                    return f.read().strip()
        except Exception:
            pass
        return None
    
    def _save_totp_secret(self, secret: str):
        """Save TOTP secret to file"""
        try:
            with open(self.totp_secret_file, 'w') as f:
                f.write(secret)
        except Exception as e:
            raise RuntimeError(f"Failed to save TOTP secret: {e}")
    
    def _load_recovery_codes(self) -> list[str]:
        """Load recovery codes from file"""
        try:
            if os.path.exists(self.recovery_codes_file):
                with open(self.recovery_codes_file, 'r') as f:
                    return [line.strip() for line in f.readlines() if line.strip()]
        except Exception:
            pass
        return []
    
    def _save_recovery_codes(self, codes: list[str]):
        """Save recovery codes to file"""
        try:
            with open(self.recovery_codes_file, 'w') as f:
                for code in codes:
                    f.write(f"{code}\n")
        except Exception as e:
            raise RuntimeError(f"Failed to save recovery codes: {e}")
    
    def _verify_password(self, password: str) -> bool:
        """Verify password against admin password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.admin_password_hash.encode('utf-8'))
    
    def _create_jwt_token(self, email: str, expires_delta: timedelta, token_type: str = "access") -> str:
        """Create a JWT token"""
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode = {
            "sub": email,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": token_type
        }
        return jwt.encode(to_encode, self.jwt_secret, algorithm="HS256")
    
    def _verify_jwt_token(self, token: str, expected_type: str = None) -> Optional[str]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            email: str = payload.get("sub")
            token_type: str = payload.get("type")
            
            if email != self.admin_email:
                return None
                
            # For backward compatibility: if no type field exists, treat as valid for both access and refresh
            # This allows existing tokens to continue working
            if token_type is None:
                return email
                
            # Check token type if specified
            if expected_type and token_type != expected_type:
                return None
                
            return email
        except jwt.PyJWTError:
            return None
    
    def authenticate(self, email: str, password: str, totp_code: Optional[str] = None, 
                    recovery_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Authenticate user with email/password and optional TOTP"""
        
        # Check for lockout
        if self._is_locked_out():
            raise ValueError("Account is temporarily locked due to too many failed attempts")
        
        # Verify email and password
        if email.lower() != self.admin_email.lower() or not self._verify_password(password):
            self._record_failed_attempt()
            raise ValueError("Invalid email or password")
        
        # Check if TOTP is enabled
        totp_secret = self._load_totp_secret()
        
        if totp_secret:
            # TOTP is enabled - require either TOTP code or recovery code
            if not totp_code and not recovery_code:
                raise ValueError("TOTP code or recovery code required")
            
            if recovery_code:
                # Validate recovery code
                recovery_codes = self._load_recovery_codes()
                if recovery_code not in recovery_codes:
                    self._record_failed_attempt()
                    raise ValueError("Invalid recovery code")
                
                # Remove used recovery code
                recovery_codes.remove(recovery_code)
                self._save_recovery_codes(recovery_codes)
                
            elif totp_code:
                # Validate TOTP code
                totp = pyotp.TOTP(totp_secret)
                if not totp.verify(totp_code, valid_window=1):
                    self._record_failed_attempt()
                    raise ValueError("Invalid TOTP code")
        
        # Successful authentication
        self._reset_failed_attempts()
        
        # Create tokens
        access_token = self._create_jwt_token(
            email, timedelta(minutes=self.access_token_expire_minutes), "access"
        )
        refresh_token = self._create_jwt_token(
            email, timedelta(days=self.refresh_token_expire_days), "refresh"
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60,
            "user": {
                "email": self.admin_email,
                "name": self.admin_name,
                "totp_enabled": bool(totp_secret)
            }
        }
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token"""
        email = self._verify_jwt_token(refresh_token, "refresh")
        if not email:
            raise ValueError("Invalid refresh token")
        
        # Create new access token
        access_token = self._create_jwt_token(
            email, timedelta(minutes=self.access_token_expire_minutes), "access"
        )
        
        # Create new refresh token (token rotation for security)
        new_refresh_token = self._create_jwt_token(
            email, timedelta(days=self.refresh_token_expire_days), "refresh"
        )
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer", 
            "expires_in": self.access_token_expire_minutes * 60
        }
    
    def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """Get current user from JWT token"""
        email = self._verify_jwt_token(token, "access")
        if not email:
            return None
        
        totp_secret = self._load_totp_secret()
        return {
            "email": self.admin_email,
            "name": self.admin_name,
            "totp_enabled": bool(totp_secret)
        }
    
    def setup_totp(self, password: str) -> Dict[str, Any]:
        """Set up TOTP for the admin account"""
        if not self._verify_password(password):
            raise ValueError("Invalid password")
        
        # Generate new TOTP secret
        secret = pyotp.random_base32()
        
        # Create TOTP URI for QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=self.admin_email,
            issuer_name="Personal Agent"
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Generate recovery codes
        recovery_codes = [pyotp.random_base32()[:8] for _ in range(10)]
        
        # Save TOTP secret and recovery codes
        self._save_totp_secret(secret)
        self._save_recovery_codes(recovery_codes)
        
        return {
            "qr_code": f"data:image/png;base64,{qr_code_base64}",
            "secret": secret,
            "recovery_codes": recovery_codes
        }
    
    def verify_totp_setup(self, totp_code: str) -> bool:
        """Verify TOTP setup with a test code"""
        totp_secret = self._load_totp_secret()
        if not totp_secret:
            raise ValueError("TOTP not set up")
        
        totp = pyotp.TOTP(totp_secret)
        return totp.verify(totp_code, valid_window=1)
    
    def get_recovery_codes(self, password: str) -> list[str]:
        """Get remaining recovery codes"""
        if not self._verify_password(password):
            raise ValueError("Invalid password")
        
        return self._load_recovery_codes()
    
    def regenerate_recovery_codes(self, password: str) -> list[str]:
        """Regenerate recovery codes"""
        if not self._verify_password(password):
            raise ValueError("Invalid password")
        
        recovery_codes = [pyotp.random_base32()[:8] for _ in range(10)]
        self._save_recovery_codes(recovery_codes)
        return recovery_codes