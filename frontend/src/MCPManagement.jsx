import React, { useState, useEffect, useRef } from 'react';
import './MCPManagement.css';

const MCPManagement = () => {
  const [servers, setServers] = useState([]);
  const [newServer, setNewServer] = useState({
    id: '',
    name: '',
    description: '',
    server_type: 'sse',
    url: '',
    command: '',
    args: '',
    env: '',
    auth: {
      type: 'none',
      token: '',
      username: '',
      password: '',
      header_name: '',
      header_value: ''
    },
    enabled: true,
    timeout: 5.0,
    sse_read_timeout: 300.0
  });
  const [editingServer, setEditingServer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Dynamic API base URL configuration
  const getApiBase = async () => {
    const { default: config } = await import('./config.js');
    return config.API_BASE_MCP;
  };

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/servers`);
      const result = await response.json();
      
      if (result.success) {
        setServers(result.data || []);
      } else {
        setError(result.message || 'Failed to load servers');
      }
    } catch (err) {
      setError('Failed to connect to MCP server');
      console.error('Error loading servers:', err);
    } finally {
      setLoading(false);
    }
  };

  const createServer = async () => {
    try {
      setError(null);
      
      const serverData = {
        ...newServer,
        args: newServer.args ? newServer.args.split(',').map(arg => arg.trim()) : [],
        env: newServer.env ? Object.fromEntries(
          newServer.env.split(',').map(env => {
            const [key, value] = env.split('=').map(s => s.trim());
            return [key, value];
          })
        ) : {},
        // Only include auth if it's not 'none'
        auth: newServer.auth.type !== 'none' ? newServer.auth : null
      };

      // Remove empty fields based on server type
      if (serverData.server_type !== 'stdio') {
        delete serverData.command;
        if (!serverData.args.length) delete serverData.args;
        if (Object.keys(serverData.env).length === 0) delete serverData.env;
      } else {
        delete serverData.url;
      }

      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/servers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(serverData)
      });

      const result = await response.json();
      
      if (result.success) {
        setSuccess('Server created successfully');
        setNewServer({
          id: '',
          name: '',
          description: '',
          server_type: 'sse',
          url: '',
          command: '',
          args: '',
          env: '',
          auth: {
            type: 'none',
            token: '',
            username: '',
            password: '',
            header_name: '',
            header_value: ''
          },
          enabled: true,
          timeout: 5.0,
          sse_read_timeout: 300.0
        });
        loadServers();
      } else {
        setError(result.message || 'Failed to create server');
      }
    } catch (err) {
      setError('Failed to create server');
      console.error('Error creating server:', err);
    }
  };

  const updateServer = async (serverId, data) => {
    try {
      setError(null);
      
      const serverData = {
        ...data,
        args: data.args ? (Array.isArray(data.args) ? data.args : data.args.split(',').map(arg => arg.trim())) : [],
        env: data.env ? (typeof data.env === 'string' ? Object.fromEntries(
          data.env.split(',').map(env => {
            const [key, value] = env.split('=').map(s => s.trim());
            return [key, value];
          })
        ) : data.env) : {},
        // Only include auth if it's not 'none'
        auth: data.auth && data.auth.type !== 'none' ? data.auth : null
      };

      // Remove empty fields based on server type
      if (serverData.server_type !== 'stdio') {
        delete serverData.command;
        if (!serverData.args.length) delete serverData.args;
        if (Object.keys(serverData.env).length === 0) delete serverData.env;
      } else {
        delete serverData.url;
      }

      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/servers/${serverId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(serverData)
      });

      const result = await response.json();
      
      if (result.success) {
        setSuccess('Server updated successfully');
        setEditingServer(null);
        loadServers();
      } else {
        setError(result.message || 'Failed to update server');
      }
    } catch (err) {
      setError('Failed to update server');
      console.error('Error updating server:', err);
    }
  };

  const deleteServer = async (serverId) => {
    if (!confirm('Are you sure you want to delete this server?')) return;
    
    try {
      setError(null);
      
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/servers/${serverId}`, {
        method: 'DELETE'
      });

      const result = await response.json();
      
      if (result.success) {
        setSuccess('Server deleted successfully');
        loadServers();
      } else {
        setError(result.message || 'Failed to delete server');
      }
    } catch (err) {
      setError('Failed to delete server');
      console.error('Error deleting server:', err);
    }
  };

  const toggleServer = async (serverId, enabled) => {
    try {
      setError(null);
      
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/servers/${serverId}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      });

      const result = await response.json();
      
      if (result.success) {
        setSuccess(`Server ${enabled ? 'enabled' : 'disabled'} successfully`);
        loadServers();
      } else {
        setError(result.message || 'Failed to toggle server');
      }
    } catch (err) {
      setError('Failed to toggle server');
      console.error('Error toggling server:', err);
    }
  };

  const startEdit = async (server) => {
    try {
      setError(null);
      
      // Fetch the full server configuration
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/servers/${server.server_id}`);
      const result = await response.json();
      
      if (result.success) {
        const fullConfig = result.data.config;
        setEditingServer({
          ...fullConfig,
          server_id: fullConfig.id, // Ensure we have server_id for consistency
          args: Array.isArray(fullConfig.args) ? fullConfig.args.join(', ') : fullConfig.args || '',
          env: typeof fullConfig.env === 'object' ? Object.entries(fullConfig.env || {}).map(([k, v]) => `${k}=${v}`).join(', ') : fullConfig.env || '',
          auth: fullConfig.auth || {
            type: 'none',
            token: '',
            username: '',
            password: '',
            header_name: '',
            header_value: ''
          }
        });
      } else {
        setError('Failed to load server details for editing');
      }
    } catch (err) {
      setError('Failed to load server details');
      console.error('Error loading server details:', err);
    }
  };

  const cancelEdit = () => {
    setEditingServer(null);
  };

  const saveEdit = () => {
    if (editingServer) {
      updateServer(editingServer.server_id, editingServer);
    }
  };

  const updateNewServerField = (field, value) => {
    if (field.startsWith('auth.')) {
      const authField = field.split('.')[1];
      setNewServer(prev => ({
        ...prev,
        auth: {
          ...prev.auth,
          [authField]: value
        }
      }));
    } else {
      setNewServer(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  const updateEditingServerField = (field, value) => {
    if (field.startsWith('auth.')) {
      const authField = field.split('.')[1];
      setEditingServer(prev => ({
        ...prev,
        auth: {
          ...prev.auth,
          [authField]: value
        }
      }));
    } else {
      setEditingServer(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  const renderAuthFields = (authConfig, updateFunction) => {
    const authType = authConfig.type;
    
    return (
      <>
        <div className="form-group">
          <label>Authentication Type</label>
          <select
            value={authType}
            onChange={e => updateFunction('auth.type', e.target.value)}
          >
            <option value="none">None</option>
            <option value="bearer">Bearer Token</option>
            <option value="api_key">API Key</option>
            <option value="basic">Basic Auth</option>
            <option value="custom_header">Custom Header</option>
          </select>
        </div>
        
        {authType === 'bearer' && (
          <div className="form-group">
            <label>Bearer Token</label>
            <input
              type="password"
              value={authConfig.token || ''}
              onChange={e => updateFunction('auth.token', e.target.value)}
              placeholder="your-bearer-token"
            />
          </div>
        )}
        
        {authType === 'api_key' && (
          <div className="form-group">
            <label>API Key</label>
            <input
              type="password"
              value={authConfig.token || ''}
              onChange={e => updateFunction('auth.token', e.target.value)}
              placeholder="your-api-key"
            />
          </div>
        )}
        
        {authType === 'basic' && (
          <>
            <div className="form-group">
              <label>Username</label>
              <input
                type="text"
                value={authConfig.username || ''}
                onChange={e => updateFunction('auth.username', e.target.value)}
                placeholder="username"
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                value={authConfig.password || ''}
                onChange={e => updateFunction('auth.password', e.target.value)}
                placeholder="password"
              />
            </div>
          </>
        )}
        
        {authType === 'custom_header' && (
          <>
            <div className="form-group">
              <label>Header Name</label>
              <input
                type="text"
                value={authConfig.header_name || ''}
                onChange={e => updateFunction('auth.header_name', e.target.value)}
                placeholder="X-Custom-Auth"
              />
            </div>
            <div className="form-group">
              <label>Header Value</label>
              <input
                type="password"
                value={authConfig.header_value || ''}
                onChange={e => updateFunction('auth.header_value', e.target.value)}
                placeholder="header-value"
              />
            </div>
          </>
        )}
      </>
    );
  };

  if (loading) {
    return (
      <div className="mcp-management">
        <div className="container">
          <div className="loading">Loading MCP servers...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="mcp-management section">
      <h2>MCP Server Management</h2>
      <p>Manage Model Context Protocol servers for enhanced agent capabilities.</p>

      {error && (
        <div className="alert alert-error">
          ❌ {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {success && (
        <div className="alert alert-success">
          ✅ {success}
          <button onClick={() => setSuccess(null)}>×</button>
        </div>
      )}

      <div className="toolbar">
        <button className="btn btn-primary" onClick={loadServers}>
          🔄 Refresh
        </button>
      </div>

      {/* Add New Server */}
      <div className="card">
        <div className="card-header">
          <h2>➕ Add New Server</h2>
        </div>
        <div className="card-body">
          <div className="form-grid">
            <div className="form-group">
              <label>Server ID *</label>
              <input
                type="text"
                value={newServer.id}
                onChange={e => updateNewServerField('id', e.target.value)}
                placeholder="my-server"
              />
            </div>
            
            <div className="form-group">
              <label>Name *</label>
              <input
                type="text"
                value={newServer.name}
                onChange={e => updateNewServerField('name', e.target.value)}
                placeholder="My MCP Server"
              />
            </div>
            
            <div className="form-group span-2">
              <label>Description</label>
              <input
                type="text"
                value={newServer.description}
                onChange={e => updateNewServerField('description', e.target.value)}
                placeholder="Brief description of what this server does"
              />
            </div>
            
            <div className="form-group">
              <label>Server Type *</label>
              <select
                value={newServer.server_type}
                onChange={e => updateNewServerField('server_type', e.target.value)}
              >
                <option value="sse">SSE (Server-Sent Events)</option>
                <option value="http">HTTP (Streamable)</option>
                <option value="openai_tools">OpenAI Tools Format</option>
                <option value="stdio">STDIO (Local)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Enabled</label>
              <select
                value={newServer.enabled}
                onChange={e => updateNewServerField('enabled', e.target.value === 'true')}
              >
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
            
            {/* URL fields for non-stdio servers */}
            {newServer.server_type !== 'stdio' && (
              <div className="form-group span-2">
                <label>Server URL *</label>
                <input
                  type="url"
                  value={newServer.url}
                  onChange={e => updateNewServerField('url', e.target.value)}
                  placeholder="https://example.com/mcp/sse"
                />
              </div>
            )}
            
            {/* Command fields for stdio servers */}
            {newServer.server_type === 'stdio' && (
              <>
                <div className="form-group span-2">
                  <label>Command *</label>
                  <input
                    type="text"
                    value={newServer.command}
                    onChange={e => updateNewServerField('command', e.target.value)}
                    placeholder="python -m my_mcp_server"
                  />
                </div>
                
                <div className="form-group">
                  <label>Arguments</label>
                  <input
                    type="text"
                    value={newServer.args}
                    onChange={e => updateNewServerField('args', e.target.value)}
                    placeholder="arg1, arg2, arg3"
                  />
                </div>
                
                <div className="form-group">
                  <label>Environment Variables</label>
                  <input
                    type="text"
                    value={newServer.env}
                    onChange={e => updateNewServerField('env', e.target.value)}
                    placeholder="KEY1=value1, KEY2=value2"
                  />
                </div>
              </>
            )}

            {/* Authentication fields for URL-based servers */}
            {newServer.server_type !== 'stdio' && renderAuthFields(newServer.auth, updateNewServerField)}

            {/* Advanced settings */}
            <div className="form-group">
              <label>Timeout (seconds)</label>
              <input
                type="number"
                value={newServer.timeout}
                onChange={e => updateNewServerField('timeout', parseFloat(e.target.value))}
                min="1"
                max="60"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label>SSE Read Timeout (seconds)</label>
              <input
                type="number"
                value={newServer.sse_read_timeout}
                onChange={e => updateNewServerField('sse_read_timeout', parseFloat(e.target.value))}
                min="10"
                max="3600"
                step="1"
              />
            </div>
          </div>
          
          <div className="form-actions">
            <button 
              className="btn btn-primary"
              onClick={createServer}
              disabled={!newServer.id || !newServer.name || 
                (newServer.server_type === 'stdio' ? !newServer.command : !newServer.url)}
            >
              ➕ Create Server
            </button>
          </div>
        </div>
      </div>

      {/* Server List */}
      <div className="servers-grid">
        {servers.map(server => (
          <div key={server.server_id} className={`server-card ${!server.enabled ? 'disabled' : ''}`}>
            {editingServer && editingServer.server_id === server.server_id ? (
              // Edit Mode
              <div className="edit-form">
                <div className="form-group">
                  <label>Name</label>
                  <input
                    type="text"
                    value={editingServer.name}
                    onChange={e => updateEditingServerField('name', e.target.value)}
                  />
                </div>
                
                <div className="form-group">
                  <label>Description</label>
                  <input
                    type="text"
                    value={editingServer.description}
                    onChange={e => updateEditingServerField('description', e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Server Type</label>
                  <select
                    value={editingServer.server_type}
                    onChange={e => updateEditingServerField('server_type', e.target.value)}
                  >
                    <option value="sse">SSE (Server-Sent Events)</option>
                    <option value="http">HTTP (Streamable)</option>
                    <option value="openai_tools">OpenAI Tools Format</option>
                    <option value="stdio">STDIO (Local)</option>
                  </select>
                </div>

                {editingServer.server_type !== 'stdio' ? (
                  <div className="form-group">
                    <label>Server URL</label>
                    <input
                      type="url"
                      value={editingServer.url || ''}
                      onChange={e => updateEditingServerField('url', e.target.value)}
                    />
                  </div>
                ) : (
                  <>
                    <div className="form-group">
                      <label>Command</label>
                      <input
                        type="text"
                        value={editingServer.command}
                        onChange={e => updateEditingServerField('command', e.target.value)}
                      />
                    </div>
                    
                    <div className="form-group">
                      <label>Arguments</label>
                      <input
                        type="text"
                        value={editingServer.args}
                        onChange={e => updateEditingServerField('args', e.target.value)}
                      />
                    </div>
                    
                    <div className="form-group">
                      <label>Environment</label>
                      <input
                        type="text"
                        value={editingServer.env}
                        onChange={e => updateEditingServerField('env', e.target.value)}
                      />
                    </div>
                  </>
                )}

                {/* Authentication fields for URL-based servers in edit mode */}
                {editingServer.server_type !== 'stdio' && renderAuthFields(editingServer.auth, updateEditingServerField)}
                
                <div className="form-actions">
                  <button className="btn btn-primary" onClick={saveEdit}>
                    💾 Save
                  </button>
                  <button className="btn btn-secondary" onClick={cancelEdit}>
                    ❌ Cancel
                  </button>
                </div>
              </div>
            ) : (
              // View Mode
              <>
                <div className="server-header">
                  <h3>{server.name}</h3>
                  <div className="server-status">
                    <span className={`status-indicator ${server.enabled ? 'enabled' : 'disabled'}`}>
                      {server.enabled ? '🟢' : '🔴'}
                    </span>
                    <span>{server.enabled ? 'Enabled' : 'Disabled'}</span>
                  </div>
                </div>
                
                <div className="server-details">
                  <p><strong>ID:</strong> {server.server_id}</p>
                  <p><strong>Type:</strong> {server.server_type}</p>
                  {server.description && <p><strong>Description:</strong> {server.description}</p>}
                  
                  {server.server_type === 'stdio' ? (
                    <>
                      <p><strong>Command:</strong> <code>{server.command}</code></p>
                      {server.args && server.args.length > 0 && (
                        <p><strong>Args:</strong> <code>{Array.isArray(server.args) ? server.args.join(', ') : server.args}</code></p>
                      )}
                      {server.env && Object.keys(server.env).length > 0 && (
                        <p><strong>Env:</strong> <code>{typeof server.env === 'object' ? Object.entries(server.env).map(([k, v]) => `${k}=${v}`).join(', ') : server.env}</code></p>
                      )}
                    </>
                  ) : (
                    <>
                      <p><strong>URL:</strong> <code>{server.url}</code></p>
                      {server.auth && server.auth.type !== 'none' && (
                        <p><strong>Auth:</strong> {server.auth.type}</p>
                      )}
                    </>
                  )}
                </div>
                
                <div className="server-actions">
                  <button 
                    className={`btn btn-sm ${server.enabled ? 'btn-warning' : 'btn-success'}`}
                    onClick={() => toggleServer(server.server_id, !server.enabled)}
                  >
                    {server.enabled ? '⏸️ Disable' : '▶️ Enable'}
                  </button>
                  
                  <button 
                    className="btn btn-sm btn-secondary"
                    onClick={() => startEdit(server)}
                  >
                    ✏️ Edit
                  </button>
                  
                  <button 
                    className="btn btn-sm btn-danger"
                    onClick={() => deleteServer(server.server_id)}
                  >
                    🗑️ Delete
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {servers.length === 0 && (
        <div className="empty-state">
          <h3>No MCP servers configured</h3>
          <p>Add your first MCP server using the form above.</p>
        </div>
      )}

      <div className="info-section">
        <h3>📖 What are MCP Servers?</h3>
        <p>Model Context Protocol (MCP) servers extend your agent's capabilities by providing:</p>
        <ul>
          <li><strong>Tools & Functions:</strong> Custom actions the agent can perform</li>
          <li><strong>Resources:</strong> Access to external data sources and APIs</li>
          <li><strong>Context:</strong> Additional information to enhance responses</li>
        </ul>
        
        <h4>Server Types:</h4>
        <ul>
          <li><strong>SSE:</strong> Server-Sent Events for real-time streaming (URLs ending in /sse)</li>
          <li><strong>HTTP:</strong> Streamable HTTP transport (URLs ending in /mcp)</li>
          <li><strong>OpenAI Tools:</strong> OpenAI-compatible tool server</li>
          <li><strong>STDIO:</strong> Local command-line MCP servers</li>
        </ul>

        <h4>Authentication Types:</h4>
        <ul>
          <li><strong>Bearer Token:</strong> Authorization: Bearer your-token</li>
          <li><strong>API Key:</strong> X-API-Key: your-key</li>
          <li><strong>Basic Auth:</strong> Username and password</li>
          <li><strong>Custom Header:</strong> Custom header name and value</li>
        </ul>
      </div>
    </div>
  );
};

export default MCPManagement; 