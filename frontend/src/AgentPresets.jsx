import React, { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import './AgentPresets.css';

const AgentPresets = () => {
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    description: '',
    system_prompt: '',
    voice_config: {
      provider: 'openai',
      voice: 'ash',
      speed: 1.0
    },
    mcp_server_ids: [],
    llm_config: {
      provider: 'openai',
      model: 'gpt-4o-mini',
      temperature: 0.7,
      parallel_tool_calls: true
    },
    stt_config: {
      provider: 'deepgram',
      model: 'nova-3',
      language: 'multi'
    },
    agent_config: {
      allow_interruptions: true,
      preemptive_generation: false,
      max_tool_steps: 10,
      speed_config: {
        preemptive_generation: false,
        fast_preresponse: false,
        advanced_turn_detection: false,
        audio_speedup: 1.0,
        min_interruption_duration: 0.3,
        min_endpointing_delay: 0.4,
        max_endpointing_delay: 3.0
      }
    },
    enabled: true,
    is_default: false
  });
  const [voiceOptions, setVoiceOptions] = useState({});
  const [modelOptions, setModelOptions] = useState([]);
  const [mcpServers, setMcpServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const presetsRef = useRef(null);
  const modalRef = useRef(null);

  useEffect(() => {
    if (presetsRef.current && presetsRef.current.children.length) {
      // Clear any existing animations first
      gsap.killTweensOf(Array.from(presetsRef.current.children));
      
      // Set initial state to ensure cards are visible
      gsap.set(Array.from(presetsRef.current.children), { opacity: 1, y: 0 });
      
      // Only animate on initial load, not on every preset change
      if (presets.length > 0) {
        gsap.fromTo(Array.from(presetsRef.current.children), 
          { opacity: 0, y: 30 },
          {
            opacity: 1,
            y: 0,
            stagger: 0.1,
            duration: 0.6,
            ease: "power2.out"
          }
        );
      }
    }
  }, [presets.length]); // Only trigger on length change, not content change

  useEffect(() => {
    if (showForm) {
      gsap.from(modalRef.current, { 
        opacity: 0, 
        scale: 0.95, 
        duration: 0.3,
        ease: "power2.out"
      });
      
      // Add escape key handler
      const handleEscape = (e) => {
        if (e.key === 'Escape') {
          setShowForm(false);
        }
      };
      
      document.addEventListener('keydown', handleEscape);
      
      // Cleanup
      return () => {
        document.removeEventListener('keydown', handleEscape);
      };
    }
  }, [showForm]);

  // Dynamic API base URL configuration
  const getApiBase = async () => {
    const { default: config } = await import('./config.js');
    return config.API_BASE_PRESET;
  };

  // Dynamic MCP API base URL configuration
  const getMcpApiBase = async () => {
    const { default: config } = await import('./config.js');
    return config.API_BASE_MCP;
  };

  useEffect(() => {
    loadData();
  }, []);

  // Load model options when LLM provider changes
  useEffect(() => {
    const provider = formData.llm_config.provider;
    if (!provider) return;
    (async () => {
      try {
        const API_BASE = await getApiBase();
        const res = await fetch(`${API_BASE}/models/${provider}`);
        const result = await res.json();
        if (result.success) {
          setModelOptions(result.data || []);
        } else {
          setModelOptions([]);
        }
      } catch (err) {
        console.warn('Failed to load models:', err);
        setModelOptions([]);
      }
    })();
  }, [formData.llm_config.provider]);

  // Load voice options when voice provider changes
  useEffect(() => {
    const provider = formData.voice_config.provider;
    if (!provider) return;
    (async () => {
      try {
        const API_BASE = await getApiBase();
        const res = await fetch(`${API_BASE}/voices/${provider}`);
        const result = await res.json();
        if (result.success) {
          setVoiceOptions({
            ...voiceOptions,
            [provider]: result.data
          });
        } else {
          console.warn(`Failed to load voices for ${provider}:`, result.message);
        }
      } catch (err) {
        console.warn('Failed to load voices:', err);
      }
    })();
  }, [formData.voice_config.provider]);

  const loadData = async () => {
    try {
      setLoading(true);
      await Promise.all([
        loadPresets(),
        loadVoiceOptions(),
        loadMcpServers()
      ]);
    } catch (err) {
      setError('Failed to load data');
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadPresets = async () => {
    try {
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/presets`);
      const result = await response.json();
      if (result.success && Array.isArray(result.data)) {
        setPresets(result.data);
      } else {
        console.error('Invalid presets data:', result);
        setPresets([]);
      }
    } catch (err) {
      console.error('Failed to load presets:', err);
      setPresets([]);
    }
  };

  const loadVoiceOptions = async () => {
    try {
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/voice-options`);
      const result = await response.json();
      if (result.success) {
        setVoiceOptions(result.data || {});
      }
    } catch (err) {
      console.error('Failed to load voice options:', err);
    }
  };

  const loadMcpServers = async () => {
    try {
      const MCP_API_BASE = await getMcpApiBase();
      const response = await fetch(`${MCP_API_BASE}/servers`);
      const result = await response.json();
      if (result.success) {
        setMcpServers(result.data || []);
      }
    } catch (err) {
      console.warn('Could not load MCP servers:', err);
      setMcpServers([]);
    }
  };

  const handleSave = async () => {
    try {
      const API_BASE = await getApiBase();
      const url = selectedPreset 
        ? `${API_BASE}/presets/${selectedPreset.id}`
        : `${API_BASE}/presets`;
      
      const method = selectedPreset ? 'PUT' : 'POST';
      
      // Filter formData to only include fields expected by the API
      const cleanedData = {
        id: formData.id,
        name: formData.name,
        description: formData.description,
        system_prompt: formData.system_prompt,
        voice_config: {
          provider: formData.voice_config.provider,
          voice: formData.voice_config.voice,
          speed: formData.voice_config.speed
        },
        mcp_server_ids: formData.mcp_server_ids,
        llm_config: {
          provider: formData.llm_config.provider,
          model: formData.llm_config.model,
          temperature: formData.llm_config.temperature,
          parallel_tool_calls: formData.llm_config.parallel_tool_calls
        },
        stt_config: {
          provider: formData.stt_config.provider,
          model: formData.stt_config.model,
          language: formData.stt_config.language
        },
        agent_config: {
          allow_interruptions: formData.agent_config.allow_interruptions,
          preemptive_generation: formData.agent_config.preemptive_generation,
          max_tool_steps: formData.agent_config.max_tool_steps,
          user_away_timeout: formData.agent_config.user_away_timeout || null,
          speed_config: formData.agent_config.speed_config || {
            preemptive_generation: false,
            fast_preresponse: false,
            advanced_turn_detection: false,
            audio_speedup: 1.0,
            audio_speed_factor: 1.0,
            min_interruption_duration: 0.3,
            min_endpointing_delay: 0.4,
            max_endpointing_delay: 3.0
          }
        },
        enabled: formData.enabled,
        is_default: formData.is_default
      };
      
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cleanedData)
      });
      
      const result = await response.json();
      
      if (result.success) {
        await loadPresets();
        setShowForm(false);
        setSelectedPreset(null);
        resetForm();
      } else {
        setError(result.message || 'Failed to save preset');
      }
    } catch (err) {
      setError('Failed to save preset');
      console.error('Save error:', err);
    }
  };

  const handleDelete = async (presetId) => {
    if (!confirm('Are you sure you want to delete this preset?')) return;
    
    try {
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/presets/${presetId}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      
      if (result.success) {
        await loadPresets();
      } else {
        setError(result.message || 'Failed to delete preset');
      }
    } catch (err) {
      setError('Failed to delete preset');
      console.error('Delete error:', err);
    }
  };

  const handleSetDefault = async (presetId) => {
    try {
      const API_BASE = await getApiBase();
      const response = await fetch(`${API_BASE}/presets/${presetId}/set-default`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (result.success) {
        await loadPresets();
      } else {
        setError(result.message || 'Failed to set default');
      }
    } catch (err) {
      setError('Failed to set default');
      console.error('Set default error:', err);
    }
  };

  const handleEdit = (preset) => {
    setSelectedPreset(preset);
    setFormData({ 
      ...preset,
      mcp_server_ids: preset.mcp_server_ids || [],
      agent_config: {
        ...preset.agent_config,
        speed_config: preset.agent_config?.speed_config || {
          preemptive_generation: false,
          fast_preresponse: false,
          advanced_turn_detection: false,
          audio_speedup: 1.0,
          audio_speed_factor: 1.0,
          min_interruption_duration: 0.3,
          min_endpointing_delay: 0.4,
          max_endpointing_delay: 3.0
        }
      }
    });
    setShowForm(true);
  };

  const resetForm = () => {
    setFormData({
      id: '',
      name: '',
      description: '',
      system_prompt: '',
      voice_config: {
        provider: 'openai',
        voice: 'ash',
        speed: 1.0
      },
      mcp_server_ids: [],
      llm_config: {
        provider: 'openai',
        model: 'gpt-4o-mini',
        temperature: 0.7,
        parallel_tool_calls: true
      },
      stt_config: {
        provider: 'deepgram',
        model: 'nova-3',
        language: 'multi'
      },
      agent_config: {
        allow_interruptions: true,
        preemptive_generation: false,
        max_tool_steps: 10
      },
      enabled: true,
      is_default: false
    });
  };

  const handleFormChange = (path, value) => {
    setFormData(prev => {
      const keys = path.split('.');
      const newData = { ...prev };
      let current = newData;
      
      for (let i = 0; i < keys.length - 1; i++) {
        current[keys[i]] = { ...current[keys[i]] };
        current = current[keys[i]];
      }
      
      current[keys[keys.length - 1]] = value;
      return newData;
    });
  };

  if (loading) {
    return (
      <div className="agent-presets">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading agent presets...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="agent-presets">
      {/* Header Section */}
      <div className="page-header">
        <div className="header-content">
          <h1>🤖 Agent Presets</h1>
          <p>Create and manage customizable agent personalities with different voices, behaviors, and capabilities.</p>
        </div>
        
        {error && (
          <div className="alert alert-error">
            <span>❌ {error}</span>
            <button onClick={() => setError(null)} className="alert-close">×</button>
          </div>
        )}
      </div>

      {/* Action Bar */}
      <div className="action-bar">
        <button 
          className="btn btn-primary"
          onClick={() => {
            setSelectedPreset(null);
            resetForm();
            setShowForm(true);
          }}
        >
          <span className="btn-icon">➕</span>
          Create New Preset
        </button>
        
        <button className="btn btn-secondary" onClick={loadData}>
          <span className="btn-icon">🔄</span>
          Refresh
        </button>
      </div>

      {/* Presets Grid */}
      <div className="presets-container">
        {!presets || presets.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🤖</div>
            <h3>No Agent Presets</h3>
            <p>Create your first agent preset to get started</p>
            <button 
              className="btn btn-primary"
              onClick={() => {
                setSelectedPreset(null);
                resetForm();
                setShowForm(true);
              }}
            >
              Create First Preset
            </button>
          </div>
        ) : (
          <div className="presets-grid" ref={presetsRef}>
            {(presets || []).map(preset => (
              <div 
                key={preset.id} 
                className={`preset-card ${preset.is_default ? 'is-default' : ''} ${!preset.enabled ? 'is-disabled' : ''}`}
              >
                {/* Card Header */}
                <div className="card-header">
                  <div className="card-title-section">
                    <h3 className="card-title">{preset.name}</h3>
                    <div className="card-badges">
                      {preset.is_default && (
                        <span className="badge badge-default">
                          <span className="badge-icon">⭐</span>
                          Default
                        </span>
                      )}
                      <span className={`badge badge-status ${preset.enabled ? 'badge-enabled' : 'badge-disabled'}`}>
                        <span className="status-dot"></span>
                        {preset.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Content */}
                <div className="card-content">
                  <p className="card-description">{preset.description}</p>
                  
                  <div className="card-details">
                    <div className="detail-row">
                      <span className="detail-label">Voice</span>
                      <span className="detail-value">
                        {preset.voice_config.provider} / {preset.voice_config.voice}
                      </span>
                    </div>
                    <div className="detail-row">
                      <span className="detail-label">LLM</span>
                      <span className="detail-value">
                        {preset.llm_config.provider} / {preset.llm_config.model}
                      </span>
                    </div>
                    <div className="detail-row">
                      <span className="detail-label">Tools</span>
                      <span className="detail-value">
                        {preset.mcp_server_ids.length} MCP server{preset.mcp_server_ids.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Actions */}
                <div className="card-actions">
                  <button 
                    className="action-btn action-btn-edit"
                    onClick={() => handleEdit(preset)}
                    title="Edit preset"
                  >
                    <span className="action-icon">✏️</span>
                    Edit
                  </button>
                  
                  {!preset.is_default && (
                    <button 
                      className="action-btn action-btn-default"
                      onClick={() => handleSetDefault(preset.id)}
                      title="Set as default"
                    >
                      <span className="action-icon">⭐</span>
                      Set Default
                    </button>
                  )}
                  
                  {!preset.is_default && (
                    <button 
                      className="action-btn action-btn-delete"
                      onClick={() => handleDelete(preset.id)}
                      title="Delete preset"
                    >
                      <span className="action-icon">🗑️</span>
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showForm && (
        <div 
          className="modal-overlay" 
          onClick={(e) => {
            // Only close if clicking directly on the overlay, not on any child elements
            if (e.target === e.currentTarget) {
              setShowForm(false);
            }
          }}
        >
          <div 
            className="modal-container" 
            onClick={e => e.stopPropagation()} 
            ref={modalRef}
            onMouseDown={e => e.stopPropagation()}
            onTouchStart={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="modal-header">
              <h2>{selectedPreset ? 'Edit' : 'Create'} Agent Preset</h2>
              <button className="modal-close" onClick={() => setShowForm(false)}>×</button>
            </div>
            
            {/* Modal Body */}
            <div className="modal-body">
              {/* Basic Information */}
              <div className="form-section">
                <h3 className="section-title">Basic Information</h3>
                <div className="form-grid">
                  <div className="form-group">
                    <label htmlFor="preset-id">Preset ID</label>
                    <input
                      id="preset-id"
                      type="text"
                      value={formData.id}
                      onChange={e => handleFormChange('id', e.target.value)}
                      placeholder="my-custom-agent"
                      pattern="[a-z0-9\-]+"
                      disabled={!!selectedPreset}
                      className={!!selectedPreset ? 'input-disabled' : ''}
                    />
                    <small className="form-help">Lowercase letters, numbers, and hyphens only</small>
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="preset-name">Display Name</label>
                    <input
                      id="preset-name"
                      type="text"
                      value={formData.name}
                      onChange={e => handleFormChange('name', e.target.value)}
                      placeholder="My Custom Agent"
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label htmlFor="preset-description">Description</label>
                  <textarea
                    id="preset-description"
                    value={formData.description}
                    onChange={e => handleFormChange('description', e.target.value)}
                    placeholder="Describe what makes this agent unique..."
                    rows={3}
                  />
                </div>
                
                <div className="form-group">
                  <label htmlFor="preset-prompt">System Prompt</label>
                  <textarea
                    id="preset-prompt"
                    value={formData.system_prompt}
                    onChange={e => handleFormChange('system_prompt', e.target.value)}
                    placeholder="You are a helpful assistant that..."
                    rows={6}
                  />
                  <small className="form-help">This defines the agent's personality and behavior</small>
                </div>
              </div>

              {/* Voice Configuration */}
              <div className="form-section">
                <h3 className="section-title">Voice Configuration</h3>
                <div className="form-grid form-grid-3">
                  <div className="form-group">
                    <label htmlFor="voice-provider">Provider</label>
                    <select
                      id="voice-provider"
                      value={formData.voice_config.provider}
                      onChange={e => handleFormChange('voice_config.provider', e.target.value)}
                    >
                      <option value="openai">OpenAI</option>
                      <option value="cartesia">Cartesia</option>
                      <option value="elevenlabs">ElevenLabs</option>
                      <option value="deepgram">Deepgram</option>
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="voice-voice">Voice</label>
                    <select
                      id="voice-voice"
                      value={formData.voice_config.voice}
                      onChange={e => handleFormChange('voice_config.voice', e.target.value)}
                    >
                      {Object.entries(voiceOptions[formData.voice_config.provider] || {}).map(([id, desc]) => (
                        <option key={id} value={id}>{desc}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="voice-speed">Speed: {formData.voice_config.speed}</label>
                    <input
                      id="voice-speed"
                      type="range"
                      min="0.5"
                      max="2.0"
                      step="0.1"
                      value={formData.voice_config.speed}
                      onChange={e => handleFormChange('voice_config.speed', parseFloat(e.target.value))}
                      className="range-input"
                    />
                  </div>
                </div>
              </div>

              {/* LLM Configuration */}
              <div className="form-section">
                <h3 className="section-title">LLM Configuration</h3>
                <div className="form-grid form-grid-3">
                  <div className="form-group">
                    <label htmlFor="llm-provider">Provider</label>
                    <select
                      id="llm-provider"
                      value={formData.llm_config.provider}
                      onChange={e => handleFormChange('llm_config.provider', e.target.value)}
                    >
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="groq">Groq</option>
                      <option value="google">Google</option>
                      <option value="openrouter">OpenRouter</option>
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="llm-model">Model</label>
                    <select
                      id="llm-model"
                      value={formData.llm_config.model}
                      onChange={e => handleFormChange('llm_config.model', e.target.value)}
                    >
                      {!modelOptions || modelOptions.length === 0 ? (
                        <option value={formData.llm_config.model}>{formData.llm_config.model}</option>
                      ) : (
                        (modelOptions || []).map(model => (
                          <option key={model} value={model}>{model}</option>
                        ))
                      )}
                    </select>
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="llm-temperature">Temperature: {formData.llm_config.temperature}</label>
                    <input
                      id="llm-temperature"
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={formData.llm_config.temperature}
                      onChange={e => handleFormChange('llm_config.temperature', parseFloat(e.target.value))}
                      className="range-input"
                    />
                  </div>
                </div>
              </div>

              {/* MCP Servers */}
              <div className="form-section">
                <h3 className="section-title">MCP Servers</h3>
                <div className="mcp-servers-grid">
                  {!mcpServers || mcpServers.length === 0 ? (
                    <div className="no-servers">
                      <p>No MCP servers available</p>
                    </div>
                  ) : (
                    (mcpServers || []).map(server => (
                      <label key={server.server_id} className="mcp-server-item">
                        <input
                          type="checkbox"
                          checked={(formData.mcp_server_ids || []).includes(server.server_id)}
                          onChange={e => {
                            const ids = formData.mcp_server_ids || [];
                            if (e.target.checked) {
                              handleFormChange('mcp_server_ids', [...ids, server.server_id]);
                            } else {
                              handleFormChange('mcp_server_ids', ids.filter(id => id !== server.server_id));
                            }
                          }}
                          className="mcp-checkbox"
                        />
                        <div className="mcp-server-info">
                          <span className="mcp-name">{server.name}</span>
                          <span className="mcp-description">{server.description}</span>
                        </div>
                      </label>
                    ))
                  )}
                </div>
              </div>

              {/* Agent Behavior */}
              <div className="form-section">
                <h3 className="section-title">Agent Behavior</h3>
                <div className="form-grid form-grid-2">
                  <div className="form-group">
                    <label htmlFor="max-steps">Max Tool Steps</label>
                    <input
                      id="max-steps"
                      type="number"
                      min="1"
                      max="20"
                      value={formData.agent_config.max_tool_steps}
                      onChange={e => handleFormChange('agent_config.max_tool_steps', parseInt(e.target.value))}
                    />
                  </div>
                </div>
                
                <div className="checkbox-group">
                  <label className="checkbox-item">
                    <input
                      type="checkbox"
                      checked={formData.agent_config.allow_interruptions}
                      onChange={e => handleFormChange('agent_config.allow_interruptions', e.target.checked)}
                      className="checkbox-input"
                    />
                    <span className="checkbox-label">Allow Interruptions</span>
                    <small className="checkbox-help">Allow users to interrupt the agent while speaking</small>
                  </label>
                  
                  <label className="checkbox-item">
                    <input
                      type="checkbox"
                      checked={formData.agent_config.preemptive_generation}
                      onChange={e => handleFormChange('agent_config.preemptive_generation', e.target.checked)}
                      className="checkbox-input"
                    />
                    <span className="checkbox-label">Preemptive Generation</span>
                    <small className="checkbox-help">Start generating responses before user finishes speaking</small>
                  </label>
                </div>
              </div>

              {/* Speed Optimization Configuration */}
              <div className="form-section">
                <h3 className="section-title">Speed Optimizations</h3>
                
                <div className="checkbox-group">
                  <label className="checkbox-item">
                    <input
                      type="checkbox"
                      checked={formData.agent_config.speed_config.fast_preresponse}
                      onChange={e => handleFormChange('agent_config.speed_config.fast_preresponse', e.target.checked)}
                      className="checkbox-input"
                    />
                    <span className="checkbox-label">Fast Pre-Response</span>
                    <small className="checkbox-help">Quick acknowledgment responses while processing (e.g., "let me think about that")</small>
                  </label>
                  
                  <label className="checkbox-item">
                    <input
                      type="checkbox"
                      checked={formData.agent_config.speed_config.advanced_turn_detection}
                      onChange={e => handleFormChange('agent_config.speed_config.advanced_turn_detection', e.target.checked)}
                      className="checkbox-input"
                    />
                    <span className="checkbox-label">Advanced Turn Detection</span>
                    <small className="checkbox-help">Use LiveKit's multilingual turn detection model (may require additional resources)</small>
                  </label>
                </div>
                
                <div className="form-grid form-grid-2">
                  <div className="form-group">
                    <label htmlFor="audio-speedup">Audio Speedup: {formData.agent_config.speed_config.audio_speedup}x</label>
                    <input
                      id="audio-speedup"
                      type="range"
                      min="1.0"
                      max="2.0"
                      step="0.1"
                      value={formData.agent_config.speed_config.audio_speedup}
                      onChange={e => handleFormChange('agent_config.speed_config.audio_speedup', parseFloat(e.target.value))}
                      className="range-input"
                    />
                    <small className="form-help">Speed up audio output without changing pitch (requires librosa)</small>
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="min-interruption">Min Interruption Duration: {formData.agent_config.speed_config.min_interruption_duration}s</label>
                    <input
                      id="min-interruption"
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.1"
                      value={formData.agent_config.speed_config.min_interruption_duration}
                      onChange={e => handleFormChange('agent_config.speed_config.min_interruption_duration', parseFloat(e.target.value))}
                      className="range-input"
                    />
                    <small className="form-help">Minimum speech duration before allowing interruption</small>
                  </div>
                </div>
                
                <div className="form-grid form-grid-2">
                  <div className="form-group">
                    <label htmlFor="min-endpointing">Min Endpointing Delay: {formData.agent_config.speed_config.min_endpointing_delay}s</label>
                    <input
                      id="min-endpointing"
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.1"
                      value={formData.agent_config.speed_config.min_endpointing_delay}
                      onChange={e => handleFormChange('agent_config.speed_config.min_endpointing_delay', parseFloat(e.target.value))}
                      className="range-input"
                    />
                    <small className="form-help">Faster response timing (lower = more responsive)</small>
                  </div>
                  
                  <div className="form-group">
                    <label htmlFor="max-endpointing">Max Endpointing Delay: {formData.agent_config.speed_config.max_endpointing_delay}s</label>
                    <input
                      id="max-endpointing"
                      type="range"
                      min="1.0"
                      max="5.0"
                      step="0.5"
                      value={formData.agent_config.speed_config.max_endpointing_delay}
                      onChange={e => handleFormChange('agent_config.speed_config.max_endpointing_delay', parseFloat(e.target.value))}
                      className="range-input"
                    />
                    <small className="form-help">Allow longer pauses for complex thoughts</small>
                  </div>
                </div>
              </div>

              {/* MCP Server Selection */}
              <div className="form-section">
                <h3 className="section-title">MCP Server Selection</h3>
                <div className="checkbox-group">
                  {(mcpServers || []).map(server => (
                    <label key={server.server_id} className="checkbox-item">
                      <input
                        type="checkbox"
                        checked={(formData.mcp_server_ids || []).includes(server.server_id)}
                        onChange={e => {
                                                      const currentIds = formData.mcp_server_ids || [];
                            const newIds = e.target.checked
                              ? [...currentIds, server.server_id]
                              : currentIds.filter(id => id !== server.server_id);
                          handleFormChange('mcp_server_ids', newIds);
                        }}
                        className="checkbox-input"
                      />
                      <span className="checkbox-label">{server.name}</span>
                      <small className="checkbox-help">{server.description}</small>
                    </label>
                  ))}
                </div>
              </div>

              {/* Preset Settings */}
              <div className="form-section">
                <h3 className="section-title">Preset Settings</h3>
                <div className="checkbox-group">
                  <label className="checkbox-item">
                    <input
                      type="checkbox"
                      checked={formData.enabled}
                      onChange={e => handleFormChange('enabled', e.target.checked)}
                      className="checkbox-input"
                    />
                    <span className="checkbox-label">Enabled</span>
                    <small className="checkbox-help">Make this preset available for use</small>
                  </label>
                  
                  <label className="checkbox-item">
                    <input
                      type="checkbox"
                      checked={formData.is_default}
                      onChange={e => handleFormChange('is_default', e.target.checked)}
                      className="checkbox-input"
                    />
                    <span className="checkbox-label">Set as Default</span>
                    <small className="checkbox-help">Use this preset as the default for new sessions</small>
                  </label>
                </div>
              </div>
            </div>
            
            {/* Modal Footer */}
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleSave}>
                {selectedPreset ? 'Update' : 'Create'} Preset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentPresets; 