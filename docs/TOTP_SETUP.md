# TOTP (Two-Factor Authentication) Setup Guide

## Overview

The Personal Agent supports TOTP (Time-based One-Time Password) authentication for enhanced security. This document covers the implementation, setup process, and security considerations.

## Architecture

### Backend Implementation

The TOTP functionality is implemented using the **Simple Authentication System** (`SimpleAuthService`) which:

- Uses environment variables for admin account configuration
- Stores TOTP secrets and recovery codes in files (not database)
- Provides JWT-based authentication with TOTP verification

### Key Components

#### Backend Files
- `backend/core/simple_auth_service.py` - Core TOTP functionality
- `backend/api/simple_auth_api.py` - TOTP API endpoints

#### Frontend Files
- `frontend/src/components/TOTPSetup.jsx` - TOTP setup wizard
- `frontend/src/components/SettingsModal.jsx` - Access point for TOTP setup

## TOTP Setup Process

### Step 1: Password Verification
- User enters their account password
- Backend verifies the password before generating TOTP secret

### Step 2: QR Code Generation
- Backend generates a new TOTP secret using `pyotp.random_base32()`
- Creates a QR code as base64 data URL
- Generates 10 recovery codes
- Returns QR code and recovery codes to frontend

### Step 3: TOTP Verification
- User scans QR code with authenticator app
- User enters 6-digit code from app
- Backend verifies the code to confirm setup

### Step 4: Recovery Codes
- User saves recovery codes securely
- Each code can only be used once
- Codes are hashed and stored on the server

## API Endpoints

### Setup TOTP
```
POST /auth/totp/setup
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "password": "user_password"
}

Response:
{
  "success": true,
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "recovery_codes": ["ABCD1234", "EFGH5678", ...],
  "message": "TOTP setup successful. Save your recovery codes!"
}
```

### Verify TOTP Setup
```
POST /auth/totp/verify
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "totp_code": "123456"
}

Response:
{
  "success": true,
  "message": "TOTP verification successful"
}
```

### Login with TOTP
```
POST /auth/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "password",
  "totp_code": "123456"  // Optional: TOTP code
  "recovery_code": "ABCD1234"  // Alternative: recovery code
}
```

## Security Considerations

### TOTP Secret Storage
- Secrets are stored as base32 strings in environment files
- Files are created with restricted permissions (600)
- Secrets are never transmitted in plain text (except during initial setup)

### Recovery Codes
- 10 recovery codes are generated using `pyotp.random_base32()[:8]`
- Codes are hashed using bcrypt before storage
- Each code can only be used once
- Used codes are marked and removed from available codes

### QR Code Handling
- QR codes are generated server-side using the `qrcode` library
- Returned as base64 data URLs to avoid file storage
- Frontend cleans up QR code URLs after use

### Password Requirements
- User must verify their password before TOTP setup
- Password verification uses bcrypt for hashing
- No password storage in frontend (entered fresh each time)

## File Structure

### TOTP Storage Files
```
/app/.auth_data/
├── totp_secret.txt          # Base32 TOTP secret
├── recovery_codes.json      # Hashed recovery codes
└── failed_attempts.json     # Failed login attempt tracking
```

### Permissions
All auth data files are created with 600 permissions (read/write for owner only).

## Frontend Integration

### Settings Modal Integration
1. Open Settings (gear icon)
2. Click "Set Up Two-Factor Authentication (TOTP)"
3. Follow the 4-step wizard:
   - Enter password
   - Scan QR code
   - Verify with TOTP code
   - Save recovery codes

### Error Handling
- Invalid password: "Invalid password"
- Invalid TOTP code: "Invalid TOTP code"
- Network errors: Detailed error messages displayed
- Failed attempts tracking: Account lockout after repeated failures

## Supported Authenticator Apps

The generated QR codes work with any TOTP-compatible authenticator app:

- **Google Authenticator** (iOS/Android)
- **Microsoft Authenticator** (iOS/Android)
- **Authy** (iOS/Android/Desktop)
- **1Password** (with TOTP support)
- **Bitwarden** (with TOTP support)
- **Any RFC 6238 compliant app**

## Recovery Process

### Using Recovery Codes
1. On login, if TOTP code is unavailable
2. Use a recovery code instead of TOTP code
3. Each recovery code works only once
4. Used codes are automatically removed

### Regenerating Recovery Codes
```
POST /auth/recovery-codes/regenerate
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "password": "user_password"
}
```

## Troubleshooting

### Common Issues

1. **QR Code Won't Scan**
   - Ensure good lighting and stable camera
   - Try manual entry using the secret key
   - Check authenticator app compatibility

2. **TOTP Codes Don't Work**
   - Verify device time synchronization
   - Check for clock drift (±30 seconds tolerance)
   - Ensure using current code (changes every 30 seconds)

3. **Recovery Codes Don't Work**
   - Verify exact code entry (case-sensitive)
   - Check if code was already used
   - Regenerate codes if necessary

### Time Synchronization
TOTP relies on synchronized time between server and client device:
- Server uses UTC time
- 30-second time windows
- ±1 window tolerance (90 seconds total)
- Ensure device time is accurate

## Production Deployment

### Environment Variables
```bash
# Required for TOTP functionality
JWT_SECRET=your-secret-key-here
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=secure-password
ADMIN_NAME=Your Name

# Optional TOTP settings
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Security Checklist
- [ ] JWT_SECRET is cryptographically secure (32+ bytes)
- [ ] Admin password is strong and unique
- [ ] Auth data directory has proper permissions
- [ ] HTTPS is enabled in production
- [ ] Time synchronization is configured
- [ ] Backup recovery codes are stored securely

## Testing

### Manual Testing Steps
1. Set up TOTP through settings
2. Log out and log back in with TOTP
3. Test recovery code functionality
4. Verify time-based code rotation
5. Test failed attempt lockout

### Automated Testing
- Unit tests for TOTP generation and verification
- Integration tests for full setup flow
- Security tests for timing attacks and replay protection

## Migration Notes

If migrating from the full auth system to simple auth:
1. Existing TOTP setups will need to be reconfigured
2. Users will need to regenerate QR codes
3. Recovery codes will be regenerated
4. No automatic migration path exists

## Best Practices

### For Users
- Use a reputable authenticator app
- Save recovery codes in multiple secure locations
- Don't share TOTP codes or recovery codes
- Keep device time synchronized
- Report suspicious login attempts immediately

### For Administrators
- Monitor failed authentication attempts
- Regularly audit auth data file permissions
- Implement proper backup for auth data
- Keep JWT secrets secure and rotated
- Monitor for unusual access patterns

## Support

For TOTP-related issues:
1. Check server logs for authentication errors
2. Verify environment variable configuration
3. Test time synchronization
4. Check file permissions in auth data directory
5. Review network connectivity between components