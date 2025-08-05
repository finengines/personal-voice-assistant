# MCP Server Troubleshooting Guide

## Issue: 403 Forbidden Errors for SSE MCP Servers

### Problem
Gmail and Calendar MCP servers were returning `403 Forbidden` errors when the voice agent tried to connect via Server-Sent Events (SSE).

### Root Cause
The bearer tokens stored in the database were corrupted or incorrect, ending with "Null" instead of valid token values.

### Solution
1. **Access MCP Management UI**: Navigate to the MCP servers configuration in the web interface
2. **Update Bearer Tokens**: Enter the correct bearer tokens for Gmail and Calendar services
3. **Verify Update**: Check that tokens are properly saved to database via API endpoint
4. **Test Connection**: Restart voice agent session to verify MCP servers connect successfully

### API Endpoints for Debugging
- `GET /servers` - List all MCP server configurations
- `GET /servers/{server_id}` - Get specific server configuration and status
- `PUT /servers/{server_id}` - Update server configuration (including auth tokens)

### Log Monitoring
Monitor backend logs for MCP-related errors:
```bash
docker logs personal_agent_backend --follow | grep -E "(MCP|403|Forbidden)"
```

### Verification
- **Graphiti MCP**: Should connect to `https://your-graphiti-instance.com/sse` without auth
- **Gmail MCP**: Requires valid bearer token for `https://your-n8n-instance.com/mcp/gmail-enhanced/sse`
- **Calendar MCP**: Requires valid bearer token for `https://your-n8n-instance.com/mcp/my-calendar/sse`
- **Web Search MCPs**: EXA and Bright Data work with HTTP transport (not SSE)

### Resolution Date
August 3, 2025 - Bearer tokens updated successfully via UI interface.