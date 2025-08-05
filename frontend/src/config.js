/**
 * Configuration for API endpoints
 * Handles both development (localhost) and production (container) environments
 */

// Determine if we're running in development or production container environment
const isLocalhost = window.location.hostname === 'localhost' || 
                   window.location.hostname === '127.0.0.1' || 
                   window.location.hostname === '0.0.0.0';

// Base configuration
const config = {
  // API endpoints - automatically adjust for container environment
  API_BASE_MCP: isLocalhost 
    ? 'http://localhost:8082' 
    : '/api/mcp',  // Use relative path for internal container access
    
  API_BASE_PRESET: isLocalhost 
    ? 'http://localhost:8083' 
    : '/api/presets',  // Use relative path for internal container access
    
  API_BASE_GLOBAL_SETTINGS: isLocalhost 
    ? 'http://localhost:8084' 
    : '/api/settings',  // Use relative path for internal container access
    
  TOKEN_SERVER_URL: isLocalhost 
    ? 'http://localhost:8081/' 
    : '/api/token/',  // Use relative path for internal container access
    
  API_BASE_AUTH: isLocalhost 
    ? 'http://localhost:8001' 
    : window.location.origin + '/api/auth',  // Use full URL for production routing
    
  // Environment information
  IS_DEVELOPMENT: isLocalhost,
  IS_PRODUCTION: !isLocalhost,
};

export default config; 