# Global System Prompt

The Global System Prompt feature allows you to define a system prompt that applies to all agents regardless of which agent is selected. This prompt is combined with each agent's individual system prompt to create a unified instruction set.

## Overview

The global system prompt is designed to provide consistent behavior across all agents while still allowing individual agents to have their own specialized prompts. This is useful for:

- Setting company-wide guidelines or policies
- Ensuring consistent tone and behavior across all agents
- Adding security or compliance requirements
- Providing common instructions that apply to all interactions

## How It Works

1. **Combination**: The global prompt is combined with each agent's individual prompt using the format:
   ```
   [Global Prompt]
   
   [Agent-Specific Prompt]
   ```

2. **Application**: When an agent is initialized, the system automatically combines the global prompt with the agent's specific prompt.

3. **Memory Enhancement**: The combined prompt is then enhanced with memory system guidelines before being applied to the agent.

## Configuration

### Database Schema

The global settings are stored in the `global_settings` table:

```sql
CREATE TABLE global_settings (
    id VARCHAR(255) PRIMARY KEY DEFAULT 'main',
    global_system_prompt TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints

The Global Settings API provides the following endpoints:

- `GET /settings` - Get current global settings
- `PUT /settings` - Update global settings
- `GET /settings/prompt` - Get current global system prompt
- `PUT /settings/prompt` - Update global system prompt
- `POST /settings/prompt/enable` - Enable/disable global prompt
- `GET /settings/preview` - Preview combined prompts

### Frontend Interface

Access the global settings through the "Global" tab in the main navigation. The interface provides:

- Enable/disable toggle for the global prompt
- Text area for entering the global system prompt
- Preview functionality to test prompt combinations
- Save functionality to persist changes

## Usage Examples

### Example 1: Company Guidelines

**Global Prompt:**
```
You are an AI assistant for Acme Corporation. Always maintain a professional tone and follow these guidelines:
- Be helpful and courteous
- Protect user privacy and data
- Escalate complex issues to human support
- Follow company policies and procedures
```

**Agent Prompt:**
```
You are a technical support specialist. Help users troubleshoot technical issues and provide step-by-step solutions.
```

**Combined Result:**
```
You are an AI assistant for Acme Corporation. Always maintain a professional tone and follow these guidelines:
- Be helpful and courteous
- Protect user privacy and data
- Escalate complex issues to human support
- Follow company policies and procedures

You are a technical support specialist. Help users troubleshoot technical issues and provide step-by-step solutions.
```

### Example 2: Security Requirements

**Global Prompt:**
```
IMPORTANT SECURITY GUIDELINES:
- Never share sensitive information
- Always verify user identity before providing access
- Log all security-related requests
- Follow data protection regulations
```

**Agent Prompt:**
```
You are a customer service representative. Help customers with their account inquiries and general questions.
```

## Implementation Details

### Backend Components

1. **GlobalSettingsManager** (`core/global_settings_manager.py`)
   - Manages global settings in the database
   - Provides caching for performance
   - Handles CRUD operations

2. **DynamicAgent** (`core/dynamic_agent.py`)
   - Combines global and agent prompts during initialization
   - Applies the combined prompt to the agent
   - Handles fallback scenarios

3. **Global Settings API** (`api/global_settings_api.py`)
   - RESTful API for managing global settings
   - Provides preview functionality
   - Handles validation and error responses

### Frontend Components

1. **GlobalSettings** (`frontend/src/components/GlobalSettings.jsx`)
   - React component for managing global settings
   - Provides real-time preview functionality
   - Handles form validation and error states

2. **Navigation Integration**
   - Added "Global" tab to main navigation
   - Integrated with existing app structure

## Testing

Run the test script to verify functionality:

```bash
cd personal_agent/backend
python test_global_settings.py
```

## Deployment

The Global Settings API runs on port 8084 by default. Update your docker-compose.yml to include:

```yaml
ports:
  - "8084:8084"
environment:
  - GLOBAL_SETTINGS_API_PORT=8084
```

## Troubleshooting

### Common Issues

1. **Global prompt not applying**
   - Check if the global prompt is enabled
   - Verify the API is running on port 8084
   - Check agent logs for initialization errors

2. **Database connection issues**
   - Ensure PostgreSQL is running
   - Verify database schema is created
   - Check connection string configuration

3. **Frontend not loading**
   - Verify the Global Settings API is accessible
   - Check browser console for CORS errors
   - Ensure all required environment variables are set

### Debug Commands

```bash
# Test global settings functionality
python test_global_settings.py

# Check API health
curl http://localhost:8084/health

# Get current settings
curl http://localhost:8084/settings

# Preview prompt combination
curl "http://localhost:8084/settings/preview?agent_prompt=Test%20prompt"
```

## Future Enhancements

Potential improvements for the global system prompt feature:

1. **Version Control**: Track changes to global prompts over time
2. **Environment-Specific Prompts**: Different global prompts for dev/staging/prod
3. **Prompt Templates**: Pre-built templates for common use cases
4. **A/B Testing**: Test different global prompts with subsets of users
5. **Analytics**: Track the effectiveness of global prompts
6. **Conditional Logic**: Apply global prompts based on user context or agent type

## Security Considerations

- Global prompts are stored in the database and should be treated as sensitive configuration
- Consider encrypting global prompts for additional security
- Implement proper access controls for modifying global settings
- Audit logs for changes to global prompts
- Regular backups of global settings configuration 