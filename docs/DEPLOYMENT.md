# Personal Agent Deployment Guide

This guide covers deploying your Personal Agent to production environments.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Domain name with SSL certificates
- API keys for OpenAI, DeepGram, etc.

### 1. Environment Setup

Create a `.env` file with your production values:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:your_secure_password@postgres:5432/personal_agent
POSTGRES_PASSWORD=your_secure_password

# LiveKit
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_secret_key_at_least_32_characters_long

# AI Services
OPENAI_API_KEY=your_openai_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key

# Your Domain
DOMAIN=your-domain.com
```

### 2. Production Configuration

Update `livekit.prod.yaml` with your domain:

```yaml
# Production LiveKit Configuration
domain: your-domain.com
tls:
  cert_file: /etc/livekit/certs/cert.pem
  key_file: /etc/livekit/certs/key.pem
```

### 3. Deploy

```bash
# Start production services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check status
docker compose ps
```

## 🔧 Configuration Details

### LiveKit Server

The LiveKit server handles WebRTC voice/video communication:

- **Ports**: 7880 (HTTP), 7881 (WebRTC TCP), 7882 (Health)
- **SSL**: Required for production (HTTPS/WSS)
- **TURN**: Optional for firewall traversal

### Token Server

Generates JWT tokens for LiveKit authentication:

- **Port**: 8081
- **Environment**: `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- **CORS**: Enabled for cross-origin requests

### Database

PostgreSQL for persistent data storage:

- **Port**: 5432 (internal), 5433 (external)
- **Data**: Stored in `postgres_data` volume
- **Backup**: Configure regular backups

### Backend API

MCP server management and AI integration:

- **Port**: 8082
- **Features**: Database persistence, MCP server management
- **Health**: `/health` endpoint

### Frontend

Web interface for voice assistant:

- **Port**: 80 (HTTP), 443 (HTTPS)
- **Features**: Voice interface, MCP management
- **SSL**: Required for microphone access

## 🌐 Domain Configuration

### SSL Certificates

For production, you need SSL certificates:

```bash
# Example with Let's Encrypt
certbot certonly --webroot -w /var/www/html -d your-domain.com

# Copy certificates to LiveKit
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /path/to/livekit/certs/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem /path/to/livekit/certs/key.pem
```

### Reverse Proxy (Optional)

For better SSL termination and load balancing:

```nginx
# Nginx configuration example
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://frontend:80;
    }
    
    location /api/ {
        proxy_pass http://backend:8082/;
    }
    
    location /tokens/ {
        proxy_pass http://token-server:8081/;
    }
    
    location /livekit/ {
        proxy_pass http://livekit:7880/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 🔒 Security Considerations

### API Keys
- Store securely in environment variables
- Rotate regularly
- Use different keys for development/production

### Database
- Use strong passwords
- Enable SSL connections
- Regular backups
- Consider managed database service

### Network
- Firewall configuration
- VPN for admin access
- Rate limiting
- DDoS protection

### LiveKit
- Secure token generation
- Room access control
- Participant limits
- Recording permissions

## 📊 Monitoring

### Health Checks

```bash
# Check all services
curl http://your-domain.com/health
curl http://your-domain.com:7882/health
curl http://your-domain.com:8081/

# Database
docker exec personal_agent_db pg_isready -U postgres
```

### Logs

```bash
# View all logs
docker compose logs -f

# Service-specific logs
docker compose logs -f livekit
docker compose logs -f backend
docker compose logs -f token-server
```

### Metrics

Consider adding monitoring:

- **Prometheus**: Metrics collection
- **Grafana**: Dashboards
- **AlertManager**: Alerts
- **ELK Stack**: Log aggregation

## 🔄 Updates

### Rolling Updates

```bash
# Update with zero downtime
docker compose pull
docker compose up -d --no-deps backend
docker compose up -d --no-deps frontend
docker compose up -d --no-deps token-server
```

### Database Migrations

```bash
# Run migrations
docker exec personal_agent_backend python migrate_to_db.py verify
```

## 🚨 Troubleshooting

### Common Issues

1. **Token Generation Fails**
   - Check token server logs
   - Verify API key/secret
   - Check CORS configuration

2. **LiveKit Connection Fails**
   - Verify SSL certificates
   - Check firewall rules
   - Test WebSocket connectivity

3. **Database Connection Issues**
   - Check PostgreSQL logs
   - Verify connection string
   - Test network connectivity

4. **Frontend Not Loading**
   - Check nginx configuration
   - Verify SSL certificates
   - Check browser console

### Debug Commands

```bash
# Test token generation
curl http://your-domain.com:8081/

# Test LiveKit connection
curl http://your-domain.com:7882/health

# Check service status
docker compose ps

# View real-time logs
docker compose logs -f
```

## 📈 Scaling

### Horizontal Scaling

For high-traffic deployments:

1. **Load Balancer**: Distribute traffic
2. **Multiple LiveKit Instances**: Redis for coordination
3. **Database Clustering**: Read replicas
4. **CDN**: Static asset delivery

### Resource Limits

```yaml
# Example resource limits
services:
  livekit:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

## 🔧 Maintenance

### Regular Tasks

- **Backups**: Daily database backups
- **Updates**: Monthly security updates
- **Monitoring**: Weekly health checks
- **Logs**: Monthly log rotation

### Backup Script

```bash
#!/bin/bash
# Backup script example

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Database backup
docker exec personal_agent_db pg_dump -U postgres personal_agent > $BACKUP_DIR/db_$DATE.sql

# Configuration backup
tar -czf $BACKUP_DIR/config_$DATE.tar.gz docker-compose*.yml *.yaml .env

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

## 📞 Support

For deployment issues:

1. Check logs: `docker compose logs`
2. Verify configuration: `docker compose config`
3. Test connectivity: Use the test scripts
4. Review security: Check firewall and SSL

---

**Your Personal Agent is now ready for production deployment!** 🚀 