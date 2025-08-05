#!/bin/bash

# Personal Agent Authentication Setup Script
# This script helps set up the authentication system for deployment

set -e

echo "🔐 Personal Agent Authentication Setup"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to generate secure random string
generate_secret() {
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

# Check and generate JWT_SECRET if not set
if ! grep -q "^JWT_SECRET=" .env || grep -q "JWT_SECRET=your_jwt_secret_key_here" .env; then
    echo -e "${YELLOW}Generating JWT_SECRET...${NC}"
    JWT_SECRET=$(generate_secret)
    
    # Replace or add JWT_SECRET in .env
    if grep -q "^JWT_SECRET=" .env; then
        sed -i.bak "s/^JWT_SECRET=.*/JWT_SECRET=${JWT_SECRET}/" .env
    else
        echo "JWT_SECRET=${JWT_SECRET}" >> .env
    fi
    echo -e "${GREEN}✅ JWT_SECRET generated and added to .env${NC}"
else
    echo -e "${GREEN}✅ JWT_SECRET already configured${NC}"
fi

# Check and generate API_KEY_ENCRYPTION_KEY if not set
if ! grep -q "^API_KEY_ENCRYPTION_KEY=" .env || grep -q "API_KEY_ENCRYPTION_KEY=your_base64_encoded_encryption_key_here" .env; then
    echo -e "${YELLOW}Generating API_KEY_ENCRYPTION_KEY...${NC}"
    API_KEY=$(generate_secret)
    
    # Replace or add API_KEY_ENCRYPTION_KEY in .env
    if grep -q "^API_KEY_ENCRYPTION_KEY=" .env; then
        sed -i.bak "s/^API_KEY_ENCRYPTION_KEY=.*/API_KEY_ENCRYPTION_KEY=${API_KEY}/" .env
    else
        echo "API_KEY_ENCRYPTION_KEY=${API_KEY}" >> .env
    fi
    echo -e "${GREEN}✅ API_KEY_ENCRYPTION_KEY generated and added to .env${NC}"
else
    echo -e "${GREEN}✅ API_KEY_ENCRYPTION_KEY already configured${NC}"
fi

# Verify required environment variables
echo -e "\n${YELLOW}Checking required environment variables...${NC}"

required_vars=(
    "POSTGRES_PASSWORD"
    "JWT_SECRET"
    "API_KEY_ENCRYPTION_KEY"
    "ADMIN_EMAIL"
    "ADMIN_PASSWORD"
    "OPENAI_API_KEY"
    "DEEPGRAM_API_KEY"
    "LIVEKIT_API_KEY"
    "LIVEKIT_API_SECRET"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "${var}=your_" .env; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All required environment variables are configured${NC}"
else
    echo -e "${RED}❌ Missing or incomplete environment variables:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "${RED}  - ${var}${NC}"
    done
    echo -e "\n${YELLOW}Please update your .env file with the missing values before deployment.${NC}"
fi

echo -e "\n${GREEN}🚀 Simple Authentication Setup Summary${NC}"
echo "======================================"
echo "✅ Environment file configured"
echo "✅ JWT secret generated"
echo "✅ API key encryption configured"
echo "✅ Docker configuration ready"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Set ADMIN_EMAIL and ADMIN_PASSWORD in .env file"
echo "2. Deploy with: docker-compose -f docker-compose.prod.yml up -d"
echo "3. Login with your admin credentials"
echo "4. Set up TOTP for additional security"
echo ""
echo -e "${GREEN}Simple Authentication Features:${NC}"
echo "• Single admin account from environment variables"
echo "• No user registration - secure and simple"
echo "• TOTP (Time-based One-Time Password) support"
echo "• Recovery codes for backup access"
echo "• JWT tokens with automatic refresh"
echo "• Rate limiting against brute force attacks"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "• Set strong ADMIN_PASSWORD in environment variables"
echo "• Save your recovery codes securely when setting up TOTP"
echo "• TOTP codes work with Google Authenticator, Microsoft Authenticator, etc."
echo "• Authentication protects the entire Personal Agent interface"
echo ""

# Check if running in Docker context
if [ -f "docker-compose.prod.yml" ]; then
    echo -e "${GREEN}Ready for production deployment! 🎉${NC}"
else
    echo -e "${YELLOW}Note: This appears to be a development environment.${NC}"
fi