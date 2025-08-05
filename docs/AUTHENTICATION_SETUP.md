# Authentication Setup Guide

This document provides setup instructions for the new TOTP-based authentication system.

## Features

✅ **Email/Password Authentication** - Secure user registration and login  
✅ **TOTP (Time-based One-Time Password)** - Compatible with Google Authenticator, Microsoft Authenticator, etc.  
✅ **Recovery Codes** - 10 single-use recovery codes for account recovery  
✅ **JWT Tokens** - Stateless authentication with automatic refresh  
✅ **Rate Limiting** - Protection against brute force attacks  
✅ **Secure Storage** - Passwords and recovery codes are bcrypt hashed  

## Quick Start

### 1. Install Dependencies

```bash
cd personal_agent/backend
pip install bcrypt PyJWT pyotp qrcode[pil] python-multipart
```

### 2. Set Environment Variables

Copy `env.example` to `.env` and set these required variables:

```bash
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET=your_jwt_secret_here

# Your database and other existing config...
```

### 3. Run Database Migrations

The new User and RecoveryCode tables will be created automatically when you start the backend.

### 4. Start the Application

```bash
# Development
cd personal_agent/backend
python start_all.py

# Production (Docker)
docker-compose -f docker-compose.prod.yml up -d
```

### 5. Create Your Account

1. Navigate to your Personal Agent frontend
2. Click "Sign up" to create an account
3. After registration, you'll be prompted to set up TOTP
4. Scan the QR code with your authenticator app
5. Enter the 6-digit code to verify setup
6. **Save your recovery codes securely!**

## Authentication Flow

1. **Registration**: Create account with email/password
2. **TOTP Setup**: Scan QR code, verify with authenticator app
3. **Login**: Email/password + TOTP code (or recovery code)
4. **Access**: JWT tokens provide access to the application

## Security Features

### TOTP Protection
- Maximum 5 failed attempts before 15-minute lockout
- Codes valid for 30 seconds with 1-window tolerance
- QR codes generated with cryptographically secure secrets

### Recovery Codes
- 10 single-use 8-character alphanumeric codes
- Bcrypt hashed storage
- Can be regenerated if needed

### JWT Security
- Short-lived access tokens (30 minutes)
- Longer-lived refresh tokens (7 days) with rotation
- Secure token storage in localStorage

## API Endpoints

### Authentication Service (Port 8001)

- `POST /auth/register` - Create new user account
- `POST /auth/login` - Authenticate user
- `POST /auth/setup-totp` - Set up TOTP authentication
- `GET /auth/qr-code` - Generate QR code for TOTP setup
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user info
- `POST /auth/regenerate-recovery-codes` - Generate new recovery codes

## Environment Variables

```bash
# Required
JWT_SECRET=your_secure_jwt_secret
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/personal_agent

# Optional (with defaults)
AUTH_API_PORT=8001
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## Database Schema

### Users Table
- `id` - UUID primary key
- `email` - Unique email address
- `password_hash` - Bcrypt hashed password
- `totp_secret` - Base32 encoded TOTP secret
- `totp_enabled` - Boolean flag
- `failed_totp_attempts` - Rate limiting counter
- `totp_locked_until` - Lockout timestamp

### Recovery Codes Table
- `id` - UUID primary key
- `user_id` - Foreign key to users
- `code_hash` - Bcrypt hashed recovery code
- `used` - Boolean flag
- `used_at` - Usage timestamp

## Troubleshooting

### Common Issues

1. **"Invalid TOTP code"** - Check device time synchronization
2. **"Account locked"** - Wait 15 minutes or use recovery code
3. **QR code not loading** - Check authentication service is running on port 8001
4. **Token refresh failing** - Clear localStorage and log in again

### Development

```bash
# Check service health
curl http://localhost:8001/auth/health

# View API documentation
open http://localhost:8001/docs
```

### Production Deployment

The authentication service runs as a separate container in production:
- Internal port: 8001
- Health check: `/auth/health`
- Logs: `docker-compose logs auth`

## Security Considerations

1. **HTTPS Required** - Always use HTTPS in production
2. **Secure Secrets** - Use cryptographically secure random secrets
3. **Regular Backups** - Backup recovery codes securely
4. **Monitor Logs** - Watch for failed authentication attempts
5. **Update Dependencies** - Keep authentication libraries updated

## Recovery Procedures

### Lost Authenticator Device
1. Use one of your saved recovery codes to log in
2. Go to settings and regenerate new recovery codes
3. Set up TOTP again with your new device

### Lost Recovery Codes
1. If still logged in, regenerate codes in settings
2. If locked out, database admin intervention required

### Reset User Password (Admin)
```python
# Database admin script needed - not implemented yet
# Would require direct database access
```

## Migration Notes

This is a new authentication system. Existing users will need to:
1. Register new accounts
2. Set up TOTP authentication
3. Save their recovery codes

The system is designed to be secure by default with no legacy authentication methods.