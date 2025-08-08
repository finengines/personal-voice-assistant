import React, { useState, useEffect } from 'react';
import './MinimalVoiceAgent.css';
import { FiSettings, FiChevronDown, FiVolume2, FiVolumeX } from 'react-icons/fi';
import MemoryIndicator from './MemoryIndicator';
import ParticleIndicator from './ParticleIndicator';
import AudioParticleSphere from './AudioParticleSphere';

const MinimalVoiceAgent = ({
  isConnected,
  isConnecting,
  connectionStep,
  isMuted,
  status,
  onConnect,
  onDisconnect,
  onToggleMute,
  onOpenSettings,
  memoryIndicator = { isVisible: false, type: '', message: '' },
  memoryFallback = false,
  connectionState = {},
  agentReady = false,
  audioPlaying = false,
  toolIndicator = { isVisible: false, label: '' },
  presets = [],
  selectedPreset,
  onPresetChange,
  // visual
  visualSettings = { particleSphere: true, particleDensity: 'medium' },
  audioAnalyser = null,
}) => {
  const [showPresets, setShowPresets] = useState(false);
  const [localSelectedPreset, setLocalSelectedPreset] = useState(selectedPreset);

  useEffect(() => {
    setLocalSelectedPreset(selectedPreset);
  }, [selectedPreset]);

  const getStatusColor = () => {
    if (status.type === 'connected') return 'var(--color-success)';
    if (status.type === 'error') return 'var(--color-error)';
    if (status.type === 'connecting') return 'var(--color-warning)';
    return 'var(--color-text-secondary)';
  };

  const getConnectionIcon = () => {
    if (isConnecting) {
      return <div className="connection-spinner"></div>;
    }
    return null;
  };

  const getButtonText = () => {
    if (isConnecting) return 'Connecting...';
    if (isConnected) return 'Disconnect';
    return 'Connect';
  };

  const handlePresetSelect = (preset) => {
    setLocalSelectedPreset(preset);
    onPresetChange(preset);
    setShowPresets(false);
  };

  return (
    <div className="minimal-agent">
      <header className="agent-header">
        <div className="status-indicator">
          <div
            className={`status-dot ${status.type} ${isConnecting ? 'pulsing' : ''}`}
            style={{ backgroundColor: getStatusColor() }}
          />
          <div className="agent-selector" onClick={() => setShowPresets(!showPresets)}>
            <span className="agent-name">{localSelectedPreset ? localSelectedPreset.name : 'Personal Agent'}</span>
            <FiChevronDown size={16} />
            {showPresets && (
              <div className="presets-dropdown">
                {presets.map(preset => (
                  <div key={preset.id} className="preset-item" onClick={() => handlePresetSelect(preset)}>
                    {preset.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        <button className="settings-btn" onClick={onOpenSettings} title="Settings">
          <FiSettings size={20} />
        </button>
      </header>

      <div className="main-interaction">
        <div className="voice-visualizer">
          <div className="connection-container">
            {/* Particle sphere background */}
            {visualSettings.visualStyle === 'particles' && (
              <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 1 }}>
                <AudioParticleSphere
                  enabled
                  analyser={audioAnalyser}
                  density={visualSettings.particleDensity}
                  color={visualSettings.particleColor || '#3a3a3a'}
                  size={320}
                  reactToAudioOnly
                />
              </div>
            )}
            <button
              className={`primary-btn ${isConnected ? 'connected' : ''} ${isConnecting ? 'connecting' : ''} ${visualSettings.visualStyle === 'particles' ? 'outline' : ''}`}
              onClick={() => isConnected ? onDisconnect() : onConnect(localSelectedPreset?.id)}
              disabled={isConnecting}
              title={getButtonText()}
            >
              {!isConnecting && isConnected && agentReady && <div className="connection-pulse"></div>}
              {!isConnecting && !isConnected && getConnectionIcon()}
            </button>

            {/* Tool call particle effect overlay */}
            <ParticleIndicator isVisible={toolIndicator.isVisible} label={toolIndicator.label} />
          </div>

          {isConnecting && (
            <div className="status-display">
              <p className="status-message connecting-text">Connecting...</p>
              {connectionStep && <p className="status-detail">{connectionStep}</p>}
            </div>
          )}
        </div>

        <div className="controls-section">
          {isConnected && agentReady && (
            <div className="voice-controls">
              <button
                className={`mute-btn ${isMuted ? 'muted' : ''}`}
                onClick={onToggleMute}
                title={isMuted ? 'Unmute' : 'Mute'}
              >
                {isMuted ? <FiVolumeX size={24} /> : <FiVolume2 size={24} />}
              </button>
            </div>
          )}

          {status.type === 'error' && (
            <div className="error-actions">
              <button className="retry-btn" onClick={onConnect}>
                Try Again
              </button>
            </div>
          )}
        </div>

        <MemoryIndicator
          isVisible={memoryIndicator.isVisible}
          type={memoryIndicator.type}
          message={memoryIndicator.message}
          fallback={memoryFallback}
        />
      </div>
    </div>
  );
};

export default MinimalVoiceAgent; 