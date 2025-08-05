# Personal Voice Assistant

A comprehensive web application for a personal voice assistant using the LiveKit framework, with Deepgram for STT/TTS and OpenAI for LLM. Now enhanced with configurable MCP (Model Context Protocol) server support for extending functionality with external tools and services.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+ (for development)
- Docker and Docker Compose (for database setup)
- LiveKit server running locally

### 1. Setup Environment Variables

Create a `.env` file in the `backend` directory with your API keys:

```bash
# Database Configuration (for production)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/personal_agent

# LiveKit Configuration (for dev server)
LIVEKIT_URL=ws://127.0.0.1:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Deepgram Configuration
DEEPGRAM_API_KEY=your-deepgram-api-key

# MCP API Configuration (optional)
MCP_API_PORT=8082
```

### 2. Install Dependencies

```bash
cd personal_agent/backend
pip install -r requirements-mcp.txt
pip install -r requirements-db.txt
```

### 3. Setup Database (Recommended)

For production deployment with data persistence, set up PostgreSQL:

```bash
# Automated setup (recommended)
./setup_database.sh

# Or manual setup
docker-compose up -d postgres
cd backend
python migrate_to_db.py create-defaults
```

For development without database, you can skip this step.

### 4. Start LiveKit Server

In a terminal, start the LiveKit development server:

```bash
livekit-server --dev
```

### 5. Start the MCP API Server (Optional but Recommended)

In a new terminal, start the MCP management API:

```bash
cd personal_agent/backend
python start_mcp_api.py
```

The MCP API will be available at: http://localhost:8082

### 6. Start the Backend Agent

In another terminal, navigate to the project root and start the agent:

```bash
cd /Users/fin/Documents/AI/agents
source venv/bin/activate
cd personal_agent/backend
python simple_agent.py dev
```

### 7. Start the Token Server

In a third terminal, start the token generation server:

```bash
cd personal_agent/backend
python token_server.py
```

### 8. Start the Frontend

In a fourth terminal, start the frontend server:

```bash
cd personal_agent/frontend
python3 -m http.server 8080
```

### 9. Access the Application

Open your browser and go to: http://localhost:8080

### 9. Connect to Voice Assistant

1. Click "Generate Token" to create a LiveKit token
2. Click "Connect" to join the voice assistant
3. Allow microphone access when prompted
4. Start talking to your AI assistant!

## 📊 Database Persistence

The Personal Agent now supports PostgreSQL database persistence for reliable data storage. This ensures your MCP server configurations and tool information are preserved across deployments.

### Key Benefits:
- **Data Persistence**: Server configurations survive container restarts
- **Reliable Storage**: ACID compliance ensures data integrity  
- **Backup Support**: Compatible with your deployment platform's backup systems
- **Production Ready**: Battle-tested for production deployments

### Quick Database Setup:
```bash
# Automated setup with migration
./setup_database.sh

# Manual setup
docker-compose up -d postgres
cd backend
python migrate_to_db.py create-defaults
```

For detailed database setup instructions, see [DATABASE_SETUP.md](DATABASE_SETUP.md).

**💡 Pro Tips for Best Performance:**
- Speak clearly and at normal pace
- Wait for a brief pause before the agent responds (turn detection)
- You can interrupt the agent if needed - it will stop and listen
- Keep questions concise for fastest responses

## 🎯 Features

### Current Implementation

- **Voice Agent Backend**: Python-based agent using LiveKit framework
- **Speech-to-Text**: Deepgram integration for real-time transcription
- **Text-to-Speech**: OpenAI TTS with "ash" voice
- **LLM Integration**: OpenAI GPT for conversational responses
- **Turn Detection**: Multilingual turn detection for natural conversation flow
- **Simple Web UI**: Clean, responsive interface with connection controls
- **Token Generation**: Automatic JWT token generation for LiveKit
- **🆕 MCP Server Support**: Configurable external tool integration
- **🆕 MCP Management UI**: Web interface for managing MCP servers
- **🆕 Multiple Authentication Methods**: Bearer tokens, API keys, Basic auth, custom headers

### Frontend Features

- **Connection Management**: Connect/disconnect to LiveKit server
- **Microphone Control**: Mute/unmute functionality
- **Visual Feedback**: Status indicators and microphone activity
- **Responsive Design**: Works on desktop and mobile devices
- **Automatic Token Generation**: One-click token generation
- **🆕 MCP Server Management**: Configure and manage external tool servers

### 🆕 MCP (Model Context Protocol) Features

#### Supported Server Types
- **SSE (Server-Sent Events)**: Real-time streaming MCP servers
- **HTTP (Streamable)**: Standard HTTP-based MCP servers
- **OpenAI Tools Format**: Servers that use OpenAI-compatible tool formats
- **STDIO**: Local command-line MCP servers

#### Authentication Methods
- **None**: No authentication required
- **Bearer Token**: Authorization header with bearer token
- **API Key**: Custom API key header
- **Basic Auth**: Username and password authentication
- **Custom Header**: Any custom header-based authentication

#### Management Features
- **Web UI**: Easy-to-use interface for server configuration
- **Live Status**: Real-time monitoring of server status
- **Tool Discovery**: Automatic detection of available tools
- **Hot Reload**: Start/stop/restart servers without restarting the agent

## 🏗️ Architecture

```
personal_agent/
├── backend/
│   ├── simple_agent.py         # Main agent implementation with MCP integration
│   ├── token_server.py         # JWT token generation server
│   ├── generate_token.py       # Standalone token generator
│   ├── mcp_config.py          # 🆕 MCP server configuration management
│   ├── mcp_api.py             # 🆕 FastAPI server for MCP management
│   ├── start_mcp_api.py       # 🆕 MCP API startup script
│   ├── requirements-mcp.txt   # 🆕 MCP-related dependencies
│   └── .env                   # Environment variables
├── frontend/
│   ├── index.html             # Main web interface
│   └── mcp-management.html    # 🆕 MCP server management interface
└── README.md                  # This file
```

### Backend Components

- **SimpleAgent**: Main agent class handling voice interactions with MCP tool integration
- **Deepgram STT**: Real-time speech-to-text conversion
- **OpenAI TTS**: High-quality text-to-speech synthesis
- **Turn Detection**: Multilingual end-of-utterance detection
- **Tool Integration**: Built-in tools plus dynamic MCP tools
- **Token Server**: HTTP server for generating LiveKit JWT tokens
- **🆕 MCP Manager**: Configuration and lifecycle management for MCP servers
- **🆕 MCP API**: RESTful API for managing MCP server configurations

### Frontend Components

- **Connection Interface**: LiveKit URL and token input
- **Audio Controls**: Connect, disconnect, and mute buttons
- **Status Display**: Real-time connection and microphone status
- **Visual Indicators**: Animated microphone activity indicator
- **Token Generation**: Automatic token generation via API
- **🆕 MCP Management**: Web interface for configuring MCP servers

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LIVEKIT_URL` | WebSocket URL for LiveKit server | `ws://127.0.0.1:7880` |
| `LIVEKIT_API_KEY` | LiveKit API key | `devkey` |
| `LIVEKIT_API_SECRET` | LiveKit API secret | `secret` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `DEEPGRAM_API_KEY` | Deepgram API key | `...` |
| `MCP_API_PORT` | Port for MCP management API | `8082` |

### Ports Used

| Service | Port | Description |
|---------|------|-------------|
| LiveKit Server | 7880 | WebSocket server for voice communication |
| Frontend | 8080 | Web interface |
| Token Server | 8081 | JWT token generation API |
| 🆕 MCP API | 8082 | MCP server management API |

### Agent Configuration

The agent can be customized by modifying `simple_agent.py`:

- **System Prompt**: Change the agent's personality and behavior
- **Tools**: Add custom tools for specific functionality
- **Voice Settings**: Modify TTS voice and parameters
- **Turn Detection**: Adjust sensitivity and language settings
- **🆕 MCP Integration**: Configure external tool servers

### 🆕 MCP Server Configuration

MCP servers are configured through the web interface at http://localhost:8080/mcp-management.html or via the API at http://localhost:8082.

Example server configurations are automatically created on first run:

#### SSE MCP Server
```json
{
  "id": "example-sse",
  "name": "Example SSE Server",
  "server_type": "sse",
  "url": "http://localhost:8000/sse",
  "auth": {"type": "none"},
  "enabled": false
}
```

#### OpenAI Tools Server
```json
{
  "id": "example-openai-tools",
  "name": "Example OpenAI Tools Server", 
  "server_type": "openai_tools",
  "url": "http://localhost:9000/api",
  "auth": {
    "type": "bearer",
    "token": "your-api-token-here"
  },
  "enabled": false
}
```

## 🛠️ Development

### Adding New Tools

To add a new tool to the agent:

```python
@function_tool
async def get_weather(location: str) -> str:
    """Get current weather for a location."""
    # Implement weather API call
    return f"Weather in {location}: Sunny, 72°F"
```

### 🆕 Creating MCP Servers

You can create custom MCP servers to extend the assistant's capabilities:

1. **SSE MCP Server**: Use the MCP SDK to create Server-Sent Events based servers
2. **OpenAI Tools Format**: Create REST APIs that follow OpenAI tools specification
3. **Local Tools**: Use STDIO-based servers for local command-line tools

### Customizing the Frontend

The frontend consists of simple HTML files that can be easily modified:

- **Styling**: Update CSS in the `<style>` sections
- **Functionality**: Modify JavaScript in the `<script>` sections
- **MCP Management**: Extend the MCP management interface

### Testing

1. **Backend Testing**: Run `python simple_agent.py dev` and check logs
2. **Frontend Testing**: Open browser console for JavaScript errors
3. **Integration Testing**: Test voice interaction through the web interface
4. **Token Testing**: Test token generation with `curl http://localhost:8081/`
5. **🆕 MCP Testing**: Test MCP API with `curl http://localhost:8082/health`

## 🚀 Performance Optimizations

### Speed Improvements Implemented

The voice assistant has been optimized for **ultra-fast responses** using several key techniques:

#### **1. Preemptive Generation**
- **Enabled**: `preemptive_generation=True`
- **Benefit**: Agent starts generating responses as soon as it receives the final transcript, before the user has finished speaking
- **Result**: Significantly reduced response latency

#### **2. Latest Models for Speed**
- **STT**: Deepgram Nova-3 (latest, fastest model with real-time optimization)
- **LLM**: OpenAI GPT-4o-mini (fastest OpenAI model)
- **TTS**: OpenAI TTS with "ash" voice (optimized for speed and naturalness)

#### **3. Real-time Interruptions**
- **Enabled**: `allow_interruptions=True`
- **Benefit**: More natural conversation flow, user can interrupt the agent
- **Result**: Feels more like human conversation

#### **4. Optimized Instructions**
- **Focus**: Concise, quick responses
- **Instruction**: "Respond quickly and avoid lengthy explanations unless specifically asked"
- **Result**: Shorter response generation time

#### **5. Advanced Turn Detection**
- **Model**: MultilingualModel() - LiveKit's optimized turn detection
- **Benefit**: Faster detection of when user has finished speaking
- **Result**: Quicker response triggering

#### **6. 🆕 MCP Tool Preloading**
- **Feature**: Tools from MCP servers are loaded at startup
- **Benefit**: No delay when accessing external tools
- **Result**: Instant tool availability

### Expected Performance

With these optimizations, you should experience:
- ✅ **Sub-second response times** for simple queries
- ✅ **Natural conversation flow** with interruption support
- ✅ **Immediate response start** after you finish speaking
- ✅ **Reduced end-to-end latency** for voice interactions
- ✅ **🆕 Instant tool access** for MCP-enabled functionality

### Measuring Performance

The agent now logs detailed metrics including:
- End-to-end latency measurements
- Turn detection timing
- Response generation speed
- 🆕 MCP server connection status and tool loading times

Check the backend logs to see performance metrics in real-time.

## 🆕 MCP Server Examples

### Example Weather Server (SSE)

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather Server")

@mcp.tool()
def get_weather(location: str) -> str:
    """Get current weather for a location"""
    # Your weather API integration here
    return f"The weather in {location} is sunny and 72°F"

if __name__ == "__main__":
    mcp.run(transport="sse", port=8000)
```

### Example Tools Server (OpenAI Format)

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/tools")
def list_tools():
    return [
        {
            "name": "calculate",
            "description": "Perform mathematical calculations",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                }
            }
        }
    ]

@app.post("/tools/calculate")
def calculate(expression: str):
    try:
        result = eval(expression)  # In production, use a safe evaluator
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
```

## 🚨 Troubleshooting

### Common Issues

1. **"ModuleNotFoundError: No module named 'livekit'"**
   - Ensure you're in the correct virtual environment
   - Run: `pip install "livekit-agents[deepgram,openai,silero,turn-detector,mcp]"`

2. **"Could not find model livekit/turn-detector"**
   - Run: `python simple_agent.py download-files`

3. **"InvalidUrlClientError"**
   - Check that LiveKit URL includes `ws://` protocol
   - Verify LiveKit server is running

4. **🆕 "MCP API not responding"**
   - Ensure MCP API server is running on port 8082
   - Check that no firewall is blocking the connection
   - Verify the MCP dependencies are installed

5. **🆕 "MCP server failed to start"**
   - Check server URL is accessible
   - Verify authentication credentials are correct
   - Check server logs for specific error messages

6. **Frontend not loading**
   - Check that Python HTTP server is running on port 8080
   - Verify no other service is using the port

7. **"MediaDevices API not available"**
   - Use HTTPS or localhost for microphone access
   - Allow microphone permissions in browser

### Debug Mode

Run the backend with verbose logging:

```bash
python simple_agent.py dev --log-level DEBUG
```

### Manual Token Generation

If the token server fails, you can generate tokens manually:

```bash
cd personal_agent/backend
python generate_token.py
```

### 🆕 MCP Debug Commands

Check MCP API health:
```bash
curl http://localhost:8082/health
```

List configured servers:
```bash
curl http://localhost:8082/servers
```

Get available tools:
```bash
curl http://localhost:8082/tools
```

## 📋 TODO / Future Enhancements

### Planned Features

- [x] **🆕 MCP Server Integration**: Model Context Protocol support
- [x] **🆕 MCP Management UI**: Web interface for server configuration
- [x] **🆕 Multiple Auth Methods**: Bearer, API key, Basic, custom headers
- [ ] **Settings Page**: Configure LLM providers and API keys
- [ ] **Agent Presets**: Create multiple personalized agents
- [ ] **Advanced MCP Features**: Resource management, prompts, sampling
- [ ] **Advanced UI**: React-based interface with routing
- [ ] **Docker Support**: Containerized deployment
- [ ] **Authentication**: User management and security
- [ ] **Analytics**: Usage tracking and performance metrics

### Technical Improvements

- [x] **🆕 MCP Integration**: Real-time tool server management
- [ ] **Real-time LiveKit Integration**: Replace simulated frontend
- [ ] **Error Handling**: Comprehensive error recovery
- [ ] **Testing Suite**: Unit and integration tests for MCP functionality
- [ ] **Documentation**: API documentation and examples
- [ ] **Performance Optimization**: Latency reduction and caching
- [ ] **🆕 MCP Server Templates**: Pre-built server configurations for common services

## 📄 License

This project is part of the LiveKit agents framework. See the main project license for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly (including MCP functionality)
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the troubleshooting section above
- Review LiveKit documentation
- Check MCP documentation at https://github.com/modelcontextprotocol/modelcontextprotocol
- Open an issue in the repository 