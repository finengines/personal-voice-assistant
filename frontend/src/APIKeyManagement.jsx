import React, { useState, useEffect } from 'react';
import './APIKeyManagement.css';

const APIKeyManagement = () => {
  const [providers, setProviders] = useState({});
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    provider: 'openai',
    api_key: '',
    key_name: ''
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [testResults, setTestResults] = useState({});

  // Dynamic API base URL configuration
  const getApiBase = async () => {
    const { default: config } = await import('./config.js');
    return config.API_BASE_MCP;
  };

  const providerInfo = {
    openai: {
      name: 'OpenAI',
      description: 'GPT models and TTS',
      icon: '🤖',
      website: 'https://platform.openai.com/api-keys'
    },
    deepgram: {
      name: 'Deepgram',
      description: 'Speech-to-text transcription',
      icon: '🎙️',
      website: 'https://console.deepgram.com/'
    },
    elevenlabs: {
      name: 'ElevenLabs',
      description: 'Advanced text-to-speech',
      icon: '🗣️',
      website: 'https://elevenlabs.io/app'
    },
    cartesia: {
      name: 'Cartesia',
      description: 'Real-time voice synthesis',
      icon: '🎵',
      website: 'https://cartesia.ai/'
    },
    groq: {
      name: 'Groq',
      description: 'Fast inference models',
      icon: '⚡',
      website: 'https://console.groq.com/keys'
    },
    anthropic: {
      name: 'Anthropic',
      description: 'Claude AI models',
      icon: '🧠',
      website: 'https://console.anthropic.com/'
    },
    google: {
      name: 'Google AI',
      description: 'Gemini and other Google AI services',
      icon: '🔍',
      website: 'https://makersuite.google.com/app/apikey'
    },
    azure: {
      name: 'Azure OpenAI',
      description: 'Microsoft Azure OpenAI Service',
      icon: '☁️',
      website: 'https://portal.azure.com/'
    },
    aws: {
      name: 'AWS Bedrock',
      description: 'Amazon Web Services AI',
      icon: '📦',
      website: 'https://console.aws.amazon.com/'
    }
  };

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/api-keys/`);
      if (response.ok) {
        const data = await response.json();
        setProviders(data.providers || {});
      } else {
        throw new Error('Failed to load providers');
      }
    } catch (err) {
      setError('Failed to load API key providers');
      console.error('Error loading providers:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.api_key.trim()) {
      setError('API key is required');
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api-keys/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('API key stored:', result);
        
        // Reset form and reload providers
        setFormData({ provider: 'openai', api_key: '', key_name: '' });
        setShowAddForm(false);
        await loadProviders();
        
        // Test the new key
        await testApiKey(formData.provider);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to store API key');
      }
    } catch (err) {
      setError(err.message);
      console.error('Error storing API key:', err);
    }
  };

  const testApiKey = async (provider) => {
    try {
      setTestResults(prev => ({ ...prev, [provider]: { testing: true } }));
      
      const response = await fetch(`${API_BASE}/api-keys/${provider}/test`);
      if (response.ok) {
        const data = await response.json();
        setTestResults(prev => ({ 
          ...prev, 
          [provider]: { 
            testing: false, 
            result: data.test_result 
          } 
        }));
      } else {
        throw new Error('Test failed');
      }
    } catch (err) {
      setTestResults(prev => ({ 
        ...prev, 
        [provider]: { 
          testing: false, 
          result: { valid: false, error: err.message } 
        } 
      }));
    }
  };

  const deleteApiKey = async (provider) => {
    if (!confirm(`Are you sure you want to delete the API key for ${providerInfo[provider]?.name || provider}?`)) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api-keys/${provider}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await loadProviders();
        setTestResults(prev => {
          const newResults = { ...prev };
          delete newResults[provider];
          return newResults;
        });
      } else {
        throw new Error('Failed to delete API key');
      }
    } catch (err) {
      setError(err.message);
      console.error('Error deleting API key:', err);
    }
  };

  const renderProviderCard = (provider, data) => {
    const info = providerInfo[provider] || { name: provider, description: '', icon: '🔑' };
    const testResult = testResults[provider];
    
    return (
      <div key={provider} className="provider-card">
        <div className="provider-header">
          <div className="provider-icon">{info.icon}</div>
          <div className="provider-info">
            <h3 className="provider-name">{info.name}</h3>
            <p className="provider-description">{info.description}</p>
          </div>
          <div className="provider-status">
            {data ? (
              <span className="status-badge status-active">
                {data.source === 'database' ? '🔒 Stored' : '📁 Environment'}
              </span>
            ) : (
              <span className="status-badge status-missing">❌ Missing</span>
            )}
          </div>
        </div>

        {data && (
          <div className="provider-details">
            <div className="key-info">
              <div className="key-detail">
                <strong>Name:</strong> {data.key_name || 'Unnamed'}
              </div>
              {data.created_at && (
                <div className="key-detail">
                  <strong>Added:</strong> {new Date(data.created_at).toLocaleDateString()}
                </div>
              )}
            </div>

            <div className="provider-actions">
              <button 
                className="btn btn-test"
                onClick={() => testApiKey(provider)}
                disabled={testResult?.testing}
              >
                {testResult?.testing ? '🔄 Testing...' : '🧪 Test'}
              </button>
              
              {data.source === 'database' && (
                <button 
                  className="btn btn-danger"
                  onClick={() => deleteApiKey(provider)}
                >
                  🗑️ Delete
                </button>
              )}
              
              <a 
                href={info.website} 
                target="_blank" 
                rel="noopener noreferrer"
                className="btn btn-secondary"
              >
                🌐 Get Key
              </a>
            </div>

            {testResult?.result && (
              <div className={`test-result ${testResult.result.valid ? 'test-success' : 'test-error'}`}>
                {testResult.result.valid ? (
                  <span>✅ API key is valid ({testResult.result.key_preview})</span>
                ) : (
                  <span>❌ {testResult.result.error}</span>
                )}
              </div>
            )}
          </div>
        )}

        {!data && (
          <div className="provider-missing">
            <p>No API key configured for this provider.</p>
            <button 
              className="btn btn-primary"
              onClick={() => {
                setFormData(prev => ({ ...prev, provider }));
                setShowAddForm(true);
              }}
            >
              ➕ Add API Key
            </button>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="api-key-management">
        <div className="loading">Loading API key providers...</div>
      </div>
    );
  }

  return (
    <div className="api-key-management">
      <div className="page-header">
        <h1>🔑 API Key Management</h1>
        <p>Securely manage API keys for AI service providers</p>
        <button 
          className="btn btn-primary"
          onClick={() => setShowAddForm(true)}
        >
          ➕ Add API Key
        </button>
      </div>

      {error && (
        <div className="error-message">
          <span>❌ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      <div className="providers-grid">
        {Object.keys(providerInfo).map(provider => 
          renderProviderCard(provider, providers[provider])
        )}
      </div>

      {/* Add API Key Modal */}
      {showAddForm && (
        <div className="modal-overlay" onClick={() => setShowAddForm(false)}>
          <div className="modal-container" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Add API Key</h2>
              <button className="modal-close" onClick={() => setShowAddForm(false)}>×</button>
            </div>
            
            <form onSubmit={handleSubmit} className="modal-body">
              <div className="form-group">
                <label htmlFor="provider">Provider</label>
                <select
                  id="provider"
                  value={formData.provider}
                  onChange={e => setFormData(prev => ({ ...prev, provider: e.target.value }))}
                  required
                >
                  {Object.entries(providerInfo).map(([key, info]) => (
                    <option key={key} value={key}>{info.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="api-key">API Key</label>
                <input
                  id="api-key"
                  type="password"
                  value={formData.api_key}
                  onChange={e => setFormData(prev => ({ ...prev, api_key: e.target.value }))}
                  placeholder="Enter your API key..."
                  required
                />
                <small className="form-help">
                  Your API key will be encrypted and stored securely in the database.
                </small>
              </div>

              <div className="form-group">
                <label htmlFor="key-name">Key Name (Optional)</label>
                <input
                  id="key-name"
                  type="text"
                  value={formData.key_name}
                  onChange={e => setFormData(prev => ({ ...prev, key_name: e.target.value }))}
                  placeholder="e.g., Production Key, Development Key..."
                />
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  🔒 Store Securely
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default APIKeyManagement; 