# Personal Agent - Production Deployment Guide

## 🔐 Simple Authentication System Overview

The Personal Agent includes a simplified authentication system designed for personal use:

- **Single Admin Account** configured via environment variables
- **No User Registration** - secure and simple
- **TOTP (Time-based One-Time Password)** support compatible with Google Authenticator, Microsoft Authenticator, Authy
- **Recovery Codes** - 10 single-use backup codes for account recovery
- **JWT Tokens** with automatic refresh and rotation
- **Rate Limiting** to prevent brute force attacks
- **No Database Required** for user management

## 🚀 Quick Deployment Steps

### 1. Set Up Environment Variables

Run the setup script to generate secure secrets:

```bash
cd personal_agent
./scripts/setup_auth.sh
```

Or manually configure these required variables in your deployment environment:

```bash
# Database (Required)
POSTGRES_DB=personal_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_database_password

# Authentication (Required)
JWT_SECRET=your_generated_jwt_secret_here
API_KEY_ENCRYPTION_KEY=your_generated_encryption_key_here

# AI Services (Required)
OPENAI_API_KEY=your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_secret

# Optional Services
ELEVENLABS_API_KEY=your_elevenlabs_api_key
CARTESIA_API_KEY=your_cartesia_api_key
GROQ_API_KEY=your_groq_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

# Production Configuration
ENV=production
```

### 2. Generate Secrets

Use Python to generate secure secrets:

```bash
# Generate JWT Secret
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"

# Generate Encryption Key
python3 -c "import secrets; print('API_KEY_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
```

### 3. Deploy with Docker Compose

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check health
docker-compose -f docker-compose.prod.yml ps
```

## 📋 Production Architecture

### Single Container Approach

The production deployment now uses a **unified backend container** that includes:

- **Authentication Service** (Port 8001) - User registration, login, TOTP
- **MCP API Service** (Port 8082) - Model Context Protocol management
- **Preset API Service** (Port 8083) - Agent preset management  
- **Global Settings API** (Port 8084) - Application settings
- **LiveKit Agent Worker** - Voice agent processing

### Service Dependencies

```
Frontend (Nginx) → Backend Container (All APIs) → Database (PostgreSQL)
                 ↘ Token Server ↗
```

## 🔧 Configuration Details

### Docker Compose Services

```yaml
services:
  postgres:     # Database
  backend:      # Unified API services + Authentication
  token-server: # LiveKit token generation
  frontend:     # React application
```

### Port Mapping (Internal)

- `8001` - Authentication API
- `8082` - MCP Management API  
- `8083` - Preset Management API
- `8084` - Global Settings API
- `8081` - Token Server
- `80` - Frontend (Nginx)

## 🛡️ Security Features

### Authentication Flow

1. **User Registration** → Email validation → Strong password requirements
2. **TOTP Setup** → QR code generation → Authenticator app integration
3. **Login Process** → Email/password + TOTP code validation
4. **Token Management** → JWT access tokens (30min) + refresh tokens (7 days)
5. **Session Persistence** → Automatic token refresh + secure storage

### Rate Limiting

- **Maximum 5 failed TOTP attempts** before 15-minute account lockout
- **Protection against brute force attacks** on authentication endpoints
- **Secure recovery options** using single-use recovery codes

### Data Protection

- **Passwords**: bcrypt hashed with salt
- **Recovery Codes**: bcrypt hashed, single-use only
- **JWT Tokens**: Cryptographically signed, short-lived
- **API Keys**: Encrypted storage with Fernet encryption

## 🔍 Health Checks

The backend container includes comprehensive health checks:

```bash
# Authentication service health
curl http://localhost:8001/auth/health

# API services health  
curl http://localhost:8082/health
curl http://localhost:8083/health
curl http://localhost:8084/health
```

## 📝 First-Time Setup

### 1. Access the Application

After deployment, navigate to your domain (configured in Dokploy).

### 2. Create Admin Account

1. Click **"Sign up"** to create your account
2. Enter email and secure password
3. Complete TOTP setup:
   - Scan QR code with authenticator app
   - Enter verification code
   - **Save recovery codes securely!**

### 3. Verify Authentication

- Log out and log back in with TOTP
- Test recovery code functionality
- Confirm all app features are accessible

## 🚨 Troubleshooting

### Common Issues

**"email-validator is not installed"**
```bash
# The requirements are updated to include pydantic[email]
# Rebuild the container:
docker-compose -f docker-compose.prod.yml build --no-cache backend
```

**"Invalid TOTP code"**
- Check device time synchronization
- Verify authenticator app setup
- Use recovery code as alternative

**"Account locked"**
- Wait 15 minutes for automatic unlock
- Use recovery code to bypass lockout

**Health check failures**
```bash
# Check container logs
docker-compose -f docker-compose.prod.yml logs backend

# Verify environment variables
docker-compose -f docker-compose.prod.yml exec backend env | grep -E "(JWT_SECRET|AUTH_API_PORT)"

# Test manual health check
docker-compose -f docker-compose.prod.yml exec backend curl http://localhost:8001/auth/health
```

### Database Issues

**Authentication tables not created**
```bash
# Connect to database and verify tables
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d personal_agent -c "\dt"

# Should show: users, recovery_codes tables
```

### Container Rebuild

If you need to rebuild with new dependencies:

```bash
# Clean rebuild
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Monitoring

### Key Metrics

- Authentication success/failure rates
- TOTP verification attempts
- Token refresh frequency
- Account lockout incidents
- API response times

### Log Analysis

```bash
# Authentication events
docker-compose logs backend | grep "auth"

# Failed login attempts
docker-compose logs backend | grep "Invalid.*code\|Authentication failed"

# Health check status
docker-compose logs backend | grep "health"
```

## 🔄 Updates and Maintenance

### Updating the Application

1. **Backup Database**
   ```bash
   docker-compose exec postgres pg_dump -U postgres personal_agent > backup.sql
   ```

2. **Update Code**
   ```bash
   git pull origin main
   ```

3. **Rebuild and Deploy**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```

### Recovery Procedures

**Lost TOTP Device**
1. Use saved recovery codes to log in
2. Regenerate new recovery codes in settings
3. Set up TOTP on new device

**Database Recovery**
```bash
# Restore from backup
docker-compose exec postgres psql -U postgres personal_agent < backup.sql
```

## 🎯 Production Checklist

- [ ] All environment variables configured
- [ ] JWT_SECRET and API_KEY_ENCRYPTION_KEY generated
- [ ] Database passwords set securely
- [ ] HTTPS enabled (handled by Dokploy)
- [ ] Health checks passing
- [ ] Admin account created and tested
- [ ] TOTP setup completed
- [ ] Recovery codes saved securely
- [ ] Backup procedures established
- [ ] Monitoring configured

## 📚 API Documentation

Once deployed, access the interactive API documentation:

- **Authentication API**: `https://your-domain/docs` (will redirect after auth)
- **Health Endpoints**: Available for monitoring integration

The authentication system protects all application routes - users must log in before accessing any Personal Agent features.

---

**Security Note**: This authentication system provides enterprise-grade security for your Personal Agent. Always use HTTPS in production and keep your recovery codes in a secure, offline location.