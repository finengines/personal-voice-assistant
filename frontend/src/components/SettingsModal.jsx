import React, { useState } from 'react';
import './SettingsModal.css';
import { FiX, FiRefreshCw, FiSave, FiShield } from 'react-icons/fi';
import TOTPSetup from './TOTPSetup';

const SettingsModal = ({ show, onClose, livekitUrl, setLivekitUrl, livekitToken, setLivekitToken, onGenerateToken, visualSettings, setVisualSettings }) => {
  const [showTOTPSetup, setShowTOTPSetup] = useState(false);
  
  if (!show) return null;

  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="settings-overlay" onClick={handleOverlayClick}>
      <div className="settings-modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <h3 className="modal-title">Settings</h3>
          <button className="close-btn" onClick={onClose} title="Close">
            <FiX size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="modal-content">
          <div className="settings-section">
            {/* Visuals */}
            <div className="input-group">
              <label>Visual Style</label>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  className="btn secondary"
                  style={{ opacity: visualSettings?.visualStyle === 'circle' ? 1 : 0.7 }}
                  onClick={() => setVisualSettings({ ...visualSettings, visualStyle: 'circle' })}
                >
                  Classic Circle
                </button>
                <button
                  className="btn secondary"
                  style={{ opacity: visualSettings?.visualStyle === 'particles' ? 1 : 0.7 }}
                  onClick={() => setVisualSettings({ ...visualSettings, visualStyle: 'particles' })}
                >
                  Particle Sphere
                </button>
                <button
                  className="btn secondary"
                  style={{ opacity: visualSettings?.visualStyle === 'flow-field' ? 1 : 0.7 }}
                  onClick={() => setVisualSettings({ ...visualSettings, visualStyle: 'flow-field' })}
                >
                  Flow Field
                </button>
                <button
                  className="btn secondary"
                  style={{ opacity: visualSettings?.visualStyle === 'constellation' ? 1 : 0.7 }}
                  onClick={() => setVisualSettings({ ...visualSettings, visualStyle: 'constellation' })}
                >
                  Constellation
                </button>
                <button
                  className="btn secondary"
                  style={{ opacity: visualSettings?.visualStyle === 'radial-spectrum' ? 1 : 0.7 }}
                  onClick={() => setVisualSettings({ ...visualSettings, visualStyle: 'radial-spectrum' })}
                >
                  Radial Spectrum
                </button>
              </div>

              {visualSettings?.visualStyle === 'particles' && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                    <span style={{ color: '#bbb', fontSize: 13 }}>Density</span>
                    <select
                      value={visualSettings?.particleDensity || 'medium'}
                      onChange={(e) => setVisualSettings({ ...visualSettings, particleDensity: e.target.value })}
                      style={{ background: '#222', color: '#eee', border: '1px solid #444', borderRadius: 8, padding: '6px 10px' }}
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                    <span style={{ color: '#bbb', fontSize: 13, marginLeft: 8 }}>Color</span>
                    <input
                      type="color"
                      value={visualSettings?.particleColor || '#3a3a3a'}
                      onChange={(e) => setVisualSettings({ ...visualSettings, particleColor: e.target.value })}
                      style={{ background: '#222', border: '1px solid #444', borderRadius: 8, padding: 4 }}
                    />
                  </div>
                  <p className="input-hint">Audio‑reactive sphere with subtle motion. Adjust density/color.</p>
                </>
              )}

              {visualSettings?.visualStyle === 'flow-field' && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                    <label style={{ color: '#bbb', fontSize: 13 }}>Particles</label>
                    <input
                      type="number"
                      min={200}
                      max={6000}
                      value={visualSettings?.flowNumParticles ?? 1400}
                      onChange={(e) => setVisualSettings({ ...visualSettings, flowNumParticles: parseInt(e.target.value || '1400', 10) })}
                      style={{ width: 100, background: '#222', color: '#eee', border: '1px solid #444', borderRadius: 8, padding: '6px 10px' }}
                    />
                    <label style={{ color: '#bbb', fontSize: 13 }}>Trail</label>
                    <input
                      type="range"
                      min={0}
                      max={0.3}
                      step={0.01}
                      value={visualSettings?.flowTrailAlpha ?? 0.08}
                      onChange={(e) => setVisualSettings({ ...visualSettings, flowTrailAlpha: parseFloat(e.target.value) })}
                    />
                    <label style={{ color: '#bbb', fontSize: 13 }}>Color</label>
                    <input
                      type="color"
                      value={visualSettings?.flowColor || '#5a5aff'}
                      onChange={(e) => setVisualSettings({ ...visualSettings, flowColor: e.target.value })}
                      style={{ background: '#222', border: '1px solid #444', borderRadius: 8, padding: 4 }}
                    />
                    <label style={{ color: '#bbb', fontSize: 13 }}>Sensitivity</label>
                    <input
                      type="range"
                      min={0.5}
                      max={2.5}
                      step={0.05}
                      value={visualSettings?.flowSensitivity ?? 1.0}
                      onChange={(e) => setVisualSettings({ ...visualSettings, flowSensitivity: parseFloat(e.target.value) })}
                    />
                  </div>
                  <p className="input-hint">Organic flow driven by a procedural field, responsive to bass/mids.</p>
                </>
              )}

              {visualSettings?.visualStyle === 'constellation' && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                    <span style={{ color: '#bbb', fontSize: 13 }}>Density</span>
                    <select
                      value={visualSettings?.constellationDensity || 'medium'}
                      onChange={(e) => setVisualSettings({ ...visualSettings, constellationDensity: e.target.value })}
                      style={{ background: '#222', color: '#eee', border: '1px solid #444', borderRadius: 8, padding: '6px 10px' }}
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                    <label style={{ color: '#bbb', fontSize: 13 }}>Dot</label>
                    <input
                      type="color"
                      value={visualSettings?.constellationColor || '#5fd1ff'}
                      onChange={(e) => setVisualSettings({ ...visualSettings, constellationColor: e.target.value })}
                      style={{ background: '#222', border: '1px solid #444', borderRadius: 8, padding: 4 }}
                    />
                    <label style={{ color: '#bbb', fontSize: 13 }}>Line</label>
                    <input
                      type="color"
                      value={visualSettings?.constellationLineColor || '#5fd1ff'}
                      onChange={(e) => setVisualSettings({ ...visualSettings, constellationLineColor: e.target.value })}
                      style={{ background: '#222', border: '1px solid #444', borderRadius: 8, padding: 4 }}
                    />
                    <label style={{ color: '#bbb', fontSize: 13 }}>Sensitivity</label>
                    <input
                      type="range"
                      min={0.5}
                      max={2.5}
                      step={0.05}
                      value={visualSettings?.constellationSensitivity ?? 1.0}
                      onChange={(e) => setVisualSettings({ ...visualSettings, constellationSensitivity: parseFloat(e.target.value) })}
                    />
                  </div>
                  <p className="input-hint">Orbiting points that connect when near; audio drives radius and pulses.</p>
                </>
              )}

              {visualSettings?.visualStyle === 'radial-spectrum' && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                    <label style={{ color: '#bbb', fontSize: 13 }}>Bars</label>
                    <input
                      type="number"
                      min={32}
                      max={256}
                      value={visualSettings?.radialBarCount ?? 96}
                      onChange={(e) => setVisualSettings({ ...visualSettings, radialBarCount: parseInt(e.target.value || '96', 10) })}
                      style={{ width: 100, background: '#222', color: '#eee', border: '1px solid #444', borderRadius: 8, padding: '6px 10px' }}
                    />
                    <label style={{ color: '#bbb', fontSize: 13 }}>Inner Radius</label>
                    <input
                      type="range"
                      min={0.2}
                      max={0.7}
                      step={0.01}
                      value={visualSettings?.radialInnerRadiusRatio ?? 0.45}
                      onChange={(e) => setVisualSettings({ ...visualSettings, radialInnerRadiusRatio: parseFloat(e.target.value) })}
                    />
                    <label style={{ color: '#bbb', fontSize: 13 }}>Color</label>
                    <input
                      type="color"
                      value={visualSettings?.radialBarColor || '#a6ff7a'}
                      onChange={(e) => setVisualSettings({ ...visualSettings, radialBarColor: e.target.value })}
                      style={{ background: '#222', border: '1px solid #444', borderRadius: 8, padding: 4 }}
                    />
                    <label style={{ color: '#bbb', fontSize: 13 }}>Glow</label>
                    <input
                      type="checkbox"
                      checked={visualSettings?.radialGlow ?? true}
                      onChange={(e) => setVisualSettings({ ...visualSettings, radialGlow: e.target.checked })}
                    />
                  </div>
                  <p className="input-hint">Circular FFT bars; simple and crisp. Driven directly by audio.</p>
                </>
              )}
            </div>

            <div className="input-group">
              <label htmlFor="livekit-url">LiveKit Server URL</label>
              <input 
                id="livekit-url"
                type="text"
                value={livekitUrl} 
                onChange={e => setLivekitUrl(e.target.value)}
                placeholder="ws://localhost:7883"
              />
            </div>

            <div className="input-group">
              <label htmlFor="livekit-token">LiveKit Token</label>
              <textarea 
                id="livekit-token"
                value={livekitToken} 
                onChange={e => setLivekitToken(e.target.value)}
                placeholder="Your LiveKit token will appear here..."
                rows={4}
              />
              <p className="input-hint">
                Token is automatically generated when you connect, or you can generate a new one manually.
              </p>
            </div>
            
            <div className="input-group">
              <label>Security Settings</label>
              <button
                className="settings-button"
                onClick={() => setShowTOTPSetup(true)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px 16px',
                  border: '1px solid #444',
                  borderRadius: '8px',
                  background: '#222',
                  color: '#eee',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <FiShield size={16} />
                Set Up Two-Factor Authentication (TOTP)
              </button>
              <p className="input-hint">
                Add an extra layer of security to your account with time-based one-time passwords.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button className="btn secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" onClick={onGenerateToken}>
            <FiRefreshCw size={16} />
            Generate Token
          </button>
        </div>
      </div>
      
      {/* TOTP Setup Modal */}
      {showTOTPSetup && (
        <div className="settings-overlay" onClick={(e) => {
          if (e.target === e.currentTarget) {
            setShowTOTPSetup(false);
          }
        }}>
          <TOTPSetup
            onSetupComplete={() => {
              setShowTOTPSetup(false);
              onClose(); // Close the main settings modal too
            }}
            onSkip={() => setShowTOTPSetup(false)}
          />
        </div>
      )}
    </div>
  );
};

export default SettingsModal; 