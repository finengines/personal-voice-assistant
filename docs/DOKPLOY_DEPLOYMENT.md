# Personal Agent - Dokploy Production Deployment Guide

This guide provides step-by-step instructions for deploying your Personal Voice Assistant to production using Dokploy, following the [official Dokploy best practices](https://docs.dokploy.com/docs/core/applications/going-production).

## 🎯 Dokploy Deployment Strategy

This deployment uses Dokploy's recommended approach:
- **Multi-stage Docker builds** for optimized container images
- **Environment variable externalization** for secure configuration
- **Internal container networking** (no exposed ports except frontend)
- **Health checks and proper startup ordering**
- **Pre-built images** to avoid server resource strain

## 📋 Prerequisites

### 1. Dokploy Server Setup
- Dokploy installed and running on your server
- GitHub repository access configured in Dokploy
- Domain name configured (optional, Dokploy can provide one)

### 2. Required Environment Variables
Set these in your Dokploy application's environment tab:

```bash
# Database Configuration
POSTGRES_DB=personal_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here

# LiveKit Configuration
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_secret_at_least_32_chars

# AI Service API Keys
OPENAI_API_KEY=your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
CARTESIA_API_KEY=your_cartesia_api_key
GROQ_API_KEY=your_groq_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

# Security
API_KEY_ENCRYPTION_KEY=base64_encoded_43_char_encryption_key

# Optional Configuration
TZ=Europe/London
MCP_API_PORT=8082
PRESET_API_PORT=8083
GLOBAL_SETTINGS_API_PORT=8084
DATA_PATH=/app/data
```

## 🚀 Deployment Steps

### Step 1: Repository Configuration
1. **Push your code** to GitHub with all the optimizations
2. **In Dokploy**, create a new application
3. **Select Docker Compose** as deployment type
4. **Configure Git Source**:
   - Repository: `https://github.com/yourusername/your-repo`
   - Branch: `main`
   - Build Path: `/`

### Step 2: Docker Configuration
1. **Set Docker Compose file** to: `docker-compose.prod.yml`
2. **Build Args** (if needed): None required
3. **Dockerfile**: Auto-detected from multi-stage builds

### Step 3: Environment Variables
1. **Go to Environment tab** in your Dokploy application
2. **Add all required environment variables** listed above
3. **Ensure sensitive values** like API keys are properly set

### Step 4: Network Configuration
1. **Frontend will be exposed** on port 80
2. **Dokploy will handle** domain mapping and SSL
3. **Internal services** communicate via Docker network

### Step 5: Deploy
1. **Click Deploy** in Dokploy
2. **Monitor build logs** for any issues
3. **Check health status** of all services

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────┐
│                Dokploy                  │
│  ┌─────────────────────────────────┐   │
│  │         Frontend (Port 80)      │◄──┼─── Your Domain (HTTPS)
│  └─────────────────────────────────┘   │
│             │                           │
│             ▼                           │
│  ┌─────────────────────────────────┐   │
│  │         Internal Network        │   │
│  │  ┌─────────┐ ┌─────────────┐   │   │
│  │  │Backend  │ │Token Server │   │   │
│  │  │         │ │             │   │   │
│  │  └─────────┘ └─────────────┘   │   │
│  │  ┌─────────┐ ┌─────────────┐   │   │
│  │  │LiveKit  │ │PostgreSQL   │   │   │
│  │  │         │ │             │   │   │
│  │  └─────────┘ └─────────────┘   │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## 🔍 Monitoring & Health Checks

### Built-in Health Checks
All services include comprehensive health checks:

- **Frontend**: HTTP GET on `/`
- **Backend**: HTTP GET on `/health` (port 8082)
- **Token Server**: HTTP GET on `/health` (port 8081)
- **PostgreSQL**: `pg_isready` command
- **LiveKit**: HTTP GET on `/health` (port 7882)

### Accessing Logs
```bash
# View all service logs in Dokploy
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

## 🚨 Troubleshooting

### Common Issues

1. **Build Timeouts**
   - The multi-stage builds are optimized to prevent this
   - Model files are pre-downloaded during build phase

2. **Environment Variable Issues**
   - Verify all required env vars are set in Dokploy
   - Check that sensitive values don't contain special characters

3. **Database Connection Issues**
   - Ensure PostgreSQL is healthy before backend starts
   - Check DATABASE_URL format matches container networking

4. **Frontend API Connection Issues**
   - Frontend automatically detects container environment
   - API calls route to internal container network

### Debug Commands
```bash
# Check container status
docker-compose ps

# Test internal connectivity
# LiveKit health check is now external
# curl https://your-livekit-instance.com/health
docker-compose exec frontend curl http://backend:8082/health

# Check database connectivity
docker-compose exec backend python -c "
from core.database import health_check
import asyncio
print('DB Health:', asyncio.run(health_check()))
"
```

## 🔒 Security Considerations

### 1. Environment Variables
- **Never commit** API keys to Git
- **Use Dokploy's environment** variable management
- **Rotate keys** regularly

### 2. Container Security
- **All services run** as non-root users
- **No unnecessary ports** exposed to host
- **Minimal base images** (Alpine Linux)

### 3. Network Security
- **Internal network** isolates services
- **Only frontend exposed** externally
- **Dokploy handles** SSL termination

## 📊 Performance Optimization

### Build Optimization
- **Multi-stage builds** reduce image size
- **Layer caching** speeds up rebuilds
- **Model pre-download** eliminates runtime delays

### Runtime Optimization
- **Health checks** ensure service reliability
- **Proper dependency ordering** prevents startup issues
- **Resource limits** can be set in Dokploy

## 🔄 CI/CD Integration

For automated deployments, add this to your GitHub Actions:

```yaml
name: Deploy to Dokploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Trigger Dokploy Deployment
        run: |
          curl -X 'POST' \
            'https://your-dokploy-domain/api/trpc/application.deploy' \
            -H 'accept: application/json' \
            -H 'x-api-key: ${{ secrets.DOKPLOY_API_KEY }}' \
            -H 'Content-Type: application/json' \
            -d '{
                "json":{
                    "applicationId": "${{ secrets.DOKPLOY_APP_ID }}"
                }
            }'
```

## 🎉 Post-Deployment

### 1. Verify Deployment
1. **Access your application** via the domain
2. **Test voice functionality** end-to-end
3. **Check all management interfaces** (MCP, Presets, Settings)

### 2. Configure MCP Servers
1. **Access MCP management** via the web interface
2. **Add your MCP servers** with proper authentication
3. **Test connectivity** to external tools

### 3. Set Up Monitoring
1. **Enable Dokploy monitoring** for your application
2. **Set up alerts** for service failures
3. **Monitor resource usage** and scale as needed

## 📚 Additional Resources

- [Dokploy Documentation](https://docs.dokploy.com/)
- [LiveKit Deployment Guide](https://docs.livekit.io/realtime/self-hosting/deployment/)
- [Container Security Best Practices](https://snyk.io/blog/10-docker-image-security-best-practices/)

---

## 🆘 Support

If you encounter issues:
1. **Check the troubleshooting section** above
2. **Review Dokploy logs** in the dashboard
3. **Verify environment variables** are correctly set
4. **Test local deployment** with `docker-compose.prod.yml` 