import React, { useState, useEffect } from 'react';
import './GlobalSettings.css';

const GlobalSettings = () => {
  const [settings, setSettings] = useState({
    global_system_prompt: '',
    enabled: true
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [previewAgentPrompt, setPreviewAgentPrompt] = useState('');
  const [previewResult, setPreviewResult] = useState(null);

  // Dynamic API base URL configuration
  const getApiBase = async () => {
    const { default: config } = await import('../config.js');
    return config.API_BASE_GLOBAL_SETTINGS;
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/settings`);
      const data = await response.json();
      
      if (data.success) {
        setSettings(data.data);
      } else {
        setError(data.message || 'Failed to load settings');
      }
    } catch (err) {
      setError(`Failed to load settings: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSuccess('Settings saved successfully!');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.message || 'Failed to save settings');
      }
    } catch (err) {
      setError(`Failed to save settings: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const toggleEnabled = async () => {
    try {
      setSaving(true);
      setError(null);
      
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/settings/prompt/enable?enabled=${!settings.enabled}`, {
        method: 'POST',
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSettings(prev => ({ ...prev, enabled: !prev.enabled }));
        setSuccess(`Global prompt ${!settings.enabled ? 'enabled' : 'disabled'} successfully!`);
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.message || 'Failed to toggle global prompt');
      }
    } catch (err) {
      setError(`Failed to toggle global prompt: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const previewCombinedPrompt = async () => {
    if (!previewAgentPrompt.trim()) {
      setError('Please enter a sample agent prompt to preview');
      return;
    }

    try {
      setError(null);
      
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/settings/preview?agent_prompt=${encodeURIComponent(previewAgentPrompt)}`);
      const data = await response.json();
      
      if (data.success) {
        setPreviewResult(data.data);
      } else {
        setError(data.message || 'Failed to generate preview');
      }
    } catch (err) {
      setError(`Failed to generate preview: ${err.message}`);
    }
  };

  const handleInputChange = (field, value) => {
    setSettings(prev => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <div className="global-settings">
        <div className="loading">Loading global settings...</div>
      </div>
    );
  }

  return (
    <div className="global-settings">
      <div className="settings-header">
        <h2>Global System Prompt</h2>
        <p className="settings-description">
          This prompt will be applied to all agents regardless of which agent is selected. 
          It will be combined with each agent's individual system prompt.
        </p>
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)} className="close-error">×</button>
        </div>
      )}

      {success && (
        <div className="success-message">
          {success}
          <button onClick={() => setSuccess(null)} className="close-success">×</button>
        </div>
      )}

      <div className="settings-section">
        <div className="setting-group">
          <label className="setting-label">
            <input
              type="checkbox"
              checked={settings.enabled}
              onChange={toggleEnabled}
              disabled={saving}
            />
            Enable Global System Prompt
          </label>
          <p className="setting-help">
            When enabled, this prompt will be applied to all agents
          </p>
        </div>

        <div className="setting-group">
          <label className="setting-label">Global System Prompt</label>
          <textarea
            value={settings.global_system_prompt || ''}
            onChange={(e) => handleInputChange('global_system_prompt', e.target.value)}
            placeholder="Enter a global system prompt that will be applied to all agents..."
            rows={8}
            disabled={!settings.enabled || saving}
            className="prompt-textarea"
          />
          <p className="setting-help">
            This prompt will be combined with each agent's individual system prompt
          </p>
        </div>

        <div className="settings-actions">
          <button
            onClick={saveSettings}
            disabled={saving}
            className="save-button"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>

      <div className="preview-section">
        <h3>Prompt Preview</h3>
        <p className="preview-description">
          Test how your global prompt will be combined with an agent prompt
        </p>

        <div className="preview-input">
          <label className="setting-label">Sample Agent Prompt</label>
          <textarea
            value={previewAgentPrompt}
            onChange={(e) => setPreviewAgentPrompt(e.target.value)}
            placeholder="Enter a sample agent prompt to see how it combines with the global prompt..."
            rows={4}
            className="preview-textarea"
          />
          <button
            onClick={previewCombinedPrompt}
            disabled={!previewAgentPrompt.trim()}
            className="preview-button"
          >
            Generate Preview
          </button>
        </div>

        {previewResult && (
          <div className="preview-result">
            <div className="preview-section">
              <h4>Global Prompt</h4>
              <div className="preview-content">
                {previewResult.global_prompt || 'No global prompt set'}
              </div>
            </div>

            <div className="preview-section">
              <h4>Agent Prompt</h4>
              <div className="preview-content">
                {previewResult.agent_prompt}
              </div>
            </div>

            <div className="preview-section">
              <h4>Combined Result</h4>
              <div className="preview-content combined">
                {previewResult.combined_prompt}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GlobalSettings; 