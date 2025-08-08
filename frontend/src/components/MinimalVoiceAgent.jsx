import React, { useState, useEffect } from 'react';
import './MinimalVoiceAgent.css';
import { FiSettings, FiChevronDown, FiVolume2, FiVolumeX } from 'react-icons/fi';
import MemoryIndicator from './MemoryIndicator';
import ParticleIndicator from './ParticleIndicator';
import AudioParticleSphere from './AudioParticleSphere';
import FlowFieldParticles from './FlowFieldParticles';
import ConstellationParticles from './ConstellationParticles';
import RadialSpectrum from './RadialSpectrum';
import DotFieldCanvas from '../DotFieldCanvas';

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
            {/* Visual backgrounds */}
            {visualSettings.visualStyle === 'circle' && (
              <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 1 }}>
                <DotFieldCanvas active={isConnected && agentReady} />
              </div>
            )}
            {visualSettings.visualStyle === 'particles' && (
              <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 1 }}>
                <AudioParticleSphere
                  enabled
                  analyser={audioAnalyser}
                  density={visualSettings.particleDensity}
                  color={visualSettings.particleColor || '#3a3a3a'}
                  size={320}
                  reactToAudioOnly
                  sensitivity={visualSettings.particleSensitivity ?? 1.2}
                />
              </div>
            )}
            {visualSettings.visualStyle === 'flow-field' && (
              <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 1, overflow: 'hidden', borderRadius: '50%' }}>
                <FlowFieldParticles
                  enabled
                  analyser={audioAnalyser}
                  size={340}
                  numParticles={visualSettings.flowNumParticles ?? 1400}
                  fieldScale={0.008}
                  baseSpeed={0.5}
                  color={visualSettings.flowColor || 'rgba(90, 90, 255, 0.7)'}
                  trailAlpha={visualSettings.flowTrailAlpha ?? 0.08}
                  sensitivity={visualSettings.flowSensitivity ?? 1.0}
                />
              </div>
            )}
            {visualSettings.visualStyle === 'constellation' && (
              <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 1 }}>
                <ConstellationParticles
                  enabled
                  analyser={audioAnalyser}
                  size={320}
                  density={visualSettings.constellationDensity || 'medium'}
                  color={visualSettings.constellationColor || '#5fd1ff'}
                  lineColor={visualSettings.constellationLineColor || 'rgba(95, 209, 255, 0.35)'}
                  sensitivity={visualSettings.constellationSensitivity ?? 1.0}
                />
              </div>
            )}
            {visualSettings.visualStyle === 'radial-spectrum' && (
              <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 1 }}>
                <RadialSpectrum
                  enabled
                  analyser={audioAnalyser}
                  size={320}
                  barCount={visualSettings.radialBarCount ?? 96}
                  innerRadiusRatio={visualSettings.radialInnerRadiusRatio ?? 0.45}
                  barColor={visualSettings.radialBarColor || '#a6ff7a'}
                  glow={visualSettings.radialGlow ?? true}
                />
              </div>
            )}
            {/* Click visual area to connect/disconnect */}
            <div
              role="button"
              onClick={() => isConnected ? onDisconnect() : onConnect(localSelectedPreset?.id)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { isConnected ? onDisconnect() : onConnect(localSelectedPreset?.id); } }}
              tabIndex={0}
              aria-label={getButtonText()}
              style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', width: 340, height: 340, borderRadius: '50%', zIndex: 2, cursor: isConnecting ? 'not-allowed' : 'pointer', outline: 'none', background: 'transparent' }}
            />

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
          <div className="voice-controls">
            <button
              className={`mute-btn ${isMuted ? 'muted' : ''}`}
              onClick={onToggleMute}
              title={isMuted ? 'Unmute' : 'Mute'}
              disabled={!isConnected}
            >
              {isMuted ? <FiVolumeX size={24} /> : <FiVolume2 size={24} />}
            </button>
            <button
              className={`retry-btn`}
              onClick={() => isConnected ? onDisconnect() : onConnect(localSelectedPreset?.id)}
              disabled={isConnecting}
              style={{ marginLeft: 12 }}
            >
              {isConnecting ? 'Connecting…' : (isConnected ? 'Disconnect' : 'Connect')}
            </button>
          </div>

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