import React, { useState } from 'react';
import './SettingsModal.css';
import { FiX, FiRefreshCw, FiSave, FiShield } from 'react-icons/fi';
import TOTPSetup from './TOTPSetup';

const SettingsModal = ({ show, onClose, livekitUrl, setLivekitUrl, livekitToken, setLivekitToken, onGenerateToken }) => {
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