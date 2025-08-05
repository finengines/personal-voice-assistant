# Personal Voice Assistant

A comprehensive, open-source personal voice assistant built with LiveKit, featuring advanced AI capabilities, MCP (Model Context Protocol) integration, and a modern web interface.

## 🚀 Features

- **Real-time Voice Interaction**: LiveKit-powered voice communication with sub-second latency
- **Advanced AI Integration**: OpenAI GPT models with multiple provider support (Anthropic, Groq, etc.)
- **MCP Server Support**: Extensible tool ecosystem via Model Context Protocol
- **Memory & Context**: Built-in memory management with Graphiti integration
- **Web Interface**: Modern React-based UI with real-time status indicators
- **Multi-Provider TTS/STT**: Support for multiple speech providers (Deepgram, ElevenLabs, Cartesia)
- **Database Persistence**: PostgreSQL for configuration and conversation history
- **Docker Ready**: Complete containerized deployment with development and production configs

## 🏗️ Architecture

### Core Components

- **Dynamic Agent**: Configurable AI agent with preset system prompts and capabilities
- **MCP Integration**: Plugin architecture for extending functionality with external services
- **LiveKit Backend**: Real-time voice/video communication engine
- **Web Frontend**: React-based interface for voice interaction and management
- **Database Layer**: PostgreSQL for persistent storage and configuration management

### Key Technologies

- **Backend**: Python 3.8+, FastAPI, LiveKit Agents Framework
- **Frontend**: HTML5, JavaScript, CSS3 with modern browser APIs
- **Database**: PostgreSQL 15+
- **Containerization**: Docker & Docker Compose
- **AI/ML**: OpenAI API, Deepgram STT, Various TTS providers

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- API keys for your chosen AI services (OpenAI, Deepgram, etc.)
- (Optional) LiveKit Cloud account or self-hosted LiveKit server

### 1. Clone and Setup

```bash
git clone https://github.com/your-username/personal-agent.git
cd personal-agent
cp env.example .env
```

### 2. Configure Environment

Edit `.env` with your API keys:

```bash
# Required API Keys
OPENAI_API_KEY=your_openai_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# LiveKit Configuration (use provided dev values for local testing)
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=your_secret_key_at_least_32_characters_long

# Security
JWT_SECRET=your_jwt_secret_here
API_KEY_ENCRYPTION_KEY=your_base64_encryption_key_here

# Admin Account
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change_me_secure_password
```

### 3. Start Development Environment

```bash
# Start all services (includes local LiveKit server)
docker compose up -d

# Check status
docker compose ps
```

### 4. Access the Application

- **Web Interface**: http://localhost:8080
- **API Documentation**: http://localhost:8001/docs
- **LiveKit Server**: ws://localhost:7883

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM | Yes | - |
| `DEEPGRAM_API_KEY` | Deepgram API key for STT | Yes | - |
| `LIVEKIT_API_KEY` | LiveKit API key | Yes | `devkey` |
| `LIVEKIT_API_SECRET` | LiveKit API secret | Yes | - |
| `JWT_SECRET` | JWT signing secret | Yes | - |
| `API_KEY_ENCRYPTION_KEY` | API key encryption key | Yes | - |
| `ADMIN_EMAIL` | Admin account email | Yes | - |
| `ADMIN_PASSWORD` | Admin account password | Yes | - |

### Production Deployment

For production deployment, use the production Docker Compose configuration:

```bash
# Production deployment (requires external LiveKit)
docker compose -f docker-compose.prod.yml up -d
```

**Production Requirements:**
- External LiveKit server or LiveKit Cloud
- SSL/TLS certificates for HTTPS
- Secure database with backups
- Environment-specific secrets management

## 📖 Usage

### Basic Voice Interaction

1. Open the web interface at http://localhost:8080
2. Click "Connect" to establish voice communication
3. Start speaking - the AI will respond in real-time
4. Use the mute button to temporarily disable microphone input

### MCP Server Management

1. Navigate to the MCP management interface
2. Add custom MCP servers for extended functionality
3. Configure authentication and endpoints
4. Enable/disable servers as needed

### Agent Presets

1. Access the presets management interface
2. Create custom agent personalities and capabilities
3. Configure different system prompts and tool sets
4. Switch between presets for different use cases

## 🛠️ Development

### Adding Custom Tools

```python
@function_tool
async def custom_tool(query: str) -> str:
    """Your custom tool description."""
    # Implementation
    return "Result"
```

### Creating MCP Servers

The system supports Model Context Protocol for extending functionality:

1. **SSE-based servers**: Server-Sent Events for real-time communication
2. **OpenAI Tools format**: Standard OpenAI function calling interface
3. **Custom authentication**: Bearer tokens, API keys, or custom headers

### Local Development

```bash
# Install dependencies
cd backend
pip install -r requirements-*.txt

# Run individual services for development
python start_auth_api.py
python start_mcp_api.py
python start_preset_server.py
```

## 🔒 Security Considerations

- **API Key Management**: All API keys are encrypted before database storage
- **Authentication**: JWT-based authentication with configurable expiration
- **Input Validation**: All user inputs are validated and sanitized
- **CORS Configuration**: Properly configured for production deployment
- **Environment Isolation**: Clear separation between development and production configs

## 📊 Monitoring and Logging

- **Health Checks**: All services include health check endpoints
- **Structured Logging**: JSON-formatted logs for production monitoring
- **Metrics**: Built-in metrics collection for performance monitoring
- **Error Tracking**: Comprehensive error handling and reporting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- Follow Python PEP 8 style guidelines
- Include tests for new functionality
- Update documentation for API changes
- Ensure Docker builds succeed
- Test with both development and production configurations

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LiveKit](https://livekit.io) for the real-time communication framework
- [Model Context Protocol](https://github.com/modelcontextprotocol) for the plugin architecture
- OpenAI, Anthropic, and other AI providers for language model capabilities
- The open-source community for various dependencies and tools

## 📞 Support

- **Documentation**: Check the `docs/` directory for detailed guides
- **Issues**: Open an issue on GitHub for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and community support

## 🗺️ Roadmap

- [ ] Enhanced multi-modal capabilities (vision, document processing)
- [ ] Advanced memory and context management
- [ ] Mobile app development
- [ ] Plugin marketplace for MCP servers
- [ ] Advanced analytics and insights
- [ ] Multi-user support and collaboration features

---

**Note**: This is an open-source project. Please ensure you comply with all relevant API provider terms of service when using their services.