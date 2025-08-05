import React, { useState, useEffect } from 'react';
import { FiShield, FiKey, FiAlertCircle, FiCopy, FiCheck, FiDownload } from 'react-icons/fi';
import './AuthLogin.css'; // Reuse the same styles

const TOTPSetup = ({ onSetupComplete, onSkip }) => {
  const [step, setStep] = useState(1); // 1: Password, 2: QR Code, 3: Verify, 4: Recovery Codes
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [qrCodeUrl, setQrCodeUrl] = useState('');
  const [secret, setSecret] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedCodes, setCopiedCodes] = useState(false);

  useEffect(() => {
    initializeTOTP();
  }, []);

  const initializeTOTP = async () => {
    try {
      // For simple auth, we need to call setup first with password
      // For now, we'll skip initialization and let user start the setup process
      console.log('TOTP component initialized - waiting for user to start setup');
    } catch (err) {
      console.error('TOTP initialization error:', err);
      setError(err.message);
    }
  };

  const setupTOTP = async () => {
    setIsLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No access token found');
      }

      const { default: config } = await import('../config.js');
      const response = await fetch(`${config.API_BASE_AUTH}/totp/setup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          password: password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'TOTP setup failed');
      }

      if (data.success) {
        // Extract QR code and recovery codes
        setQrCodeUrl(data.qr_code);
        setRecoveryCodes(data.recovery_codes);
        setStep(2); // Move to QR code step
      } else {
        throw new Error(data.message || 'TOTP setup failed');
      }

    } catch (err) {
      console.error('TOTP setup error:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const verifyTOTP = async () => {
    setIsLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('No access token found');
      }

      const { default: config } = await import('../config.js');
      const response = await fetch(`${config.API_BASE_AUTH}/totp/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          totp_code: totpCode,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'TOTP verification failed');
      }

      if (data.success) {
        setStep(4); // Move to recovery codes step
      } else {
        throw new Error(data.message || 'TOTP verification failed');
      }

    } catch (err) {
      console.error('TOTP verification error:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = async (text, setCopiedState) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedState(true);
      setTimeout(() => setCopiedState(false), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const downloadRecoveryCodes = () => {
    const codesText = `Personal Agent Recovery Codes
Generated: ${new Date().toLocaleString()}

Save these codes in a secure location. Each code can only be used once.

${recoveryCodes.map((code, index) => `${index + 1}. ${code}`).join('\n')}

Important:
- These codes can be used to access your account if you lose your authenticator device
- Each code can only be used once
- Keep them secure and don't share them with anyone
- Consider printing this file and storing it in a safe place`;

    const blob = new Blob([codesText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'personal-agent-recovery-codes.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleComplete = () => {
    // Clean up QR code URL (only if it's a blob URL, not a data URL)
    if (qrCodeUrl && qrCodeUrl.startsWith('blob:')) {
      URL.revokeObjectURL(qrCodeUrl);
    }
    onSetupComplete();
  };

  if (step === 1) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <FiShield className="auth-icon" />
            <h2>Set Up Two-Factor Authentication</h2>
            <p>Enter your password to begin TOTP setup</p>
          </div>

          {error && (
            <div className="auth-error">
              <FiAlertCircle />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={(e) => { e.preventDefault(); setupTOTP(); }} className="auth-form">
            <div className="input-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your account password"
                disabled={isLoading}
                autoFocus
              />
              <small>We need to verify your identity before setting up TOTP</small>
            </div>

            <div className="auth-actions">
              <button
                type="submit"
                className="auth-button primary"
                disabled={isLoading || !password.trim()}
              >
                {isLoading ? 'Setting up...' : 'Generate QR Code'}
              </button>
              
              <button
                type="button"
                className="auth-button secondary"
                onClick={onSkip}
                disabled={isLoading}
              >
                Skip for Now
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  if (step === 2) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <FiShield className="auth-icon" />
            <h2>Scan QR Code</h2>
            <p>Scan the QR code with your authenticator app</p>
          </div>

          {error && (
            <div className="auth-error">
              <FiAlertCircle />
              <span>{error}</span>
            </div>
          )}

          <div className="qr-section">
            {qrCodeUrl ? (
              <div className="qr-code-container">
                <img src={qrCodeUrl} alt="TOTP QR Code" />
              </div>
            ) : (
              <div className="qr-code-container">
                <div style={{ padding: '60px', color: '#666' }}>Loading QR Code...</div>
              </div>
            )}

            <p style={{ color: 'var(--textColorSecondary)', fontSize: '14px', margin: '16px 0' }}>
              Scan this QR code with an authenticator app like Google Authenticator, 
              Microsoft Authenticator, or Authy.
            </p>
          </div>

          <div className="auth-actions">
            <button
              className="auth-button primary"
              onClick={() => setStep(3)}
              disabled={!qrCodeUrl}
            >
              I've Scanned the QR Code
            </button>
            
            <button
              className="auth-button secondary"
              onClick={() => setStep(1)}
            >
              Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (step === 3) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <FiKey className="auth-icon" />
            <h2>Verify Your Setup</h2>
            <p>Enter the 6-digit code from your authenticator app</p>
          </div>

          {error && (
            <div className="auth-error">
              <FiAlertCircle />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={(e) => { e.preventDefault(); verifyTOTP(); }} className="auth-form">
            <div className="input-group">
              <label htmlFor="totpCode">Authentication Code</label>
              <input
                id="totpCode"
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="Enter 6-digit code"
                maxLength="6"
                pattern="\d{6}"
                disabled={isLoading}
                autoFocus
                style={{ textAlign: 'center', fontSize: '18px', letterSpacing: '2px' }}
              />
              <small>This code changes every 30 seconds</small>
            </div>

            <div className="auth-actions">
              <button
                type="submit"
                className="auth-button primary"
                disabled={isLoading || totpCode.length !== 6}
              >
                {isLoading ? 'Verifying...' : 'Verify & Continue'}
              </button>
              
              <button
                type="button"
                className="auth-button secondary"
                onClick={() => setStep(2)}
                disabled={isLoading}
              >
                Back
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  if (step === 4) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <FiCheck className="auth-icon" style={{ color: '#86efac' }} />
            <h2>TOTP Setup Complete!</h2>
            <p>Save your recovery codes in a secure location</p>
          </div>

          <div className="recovery-codes">
            <h4>Recovery Codes</h4>
            <p style={{ color: 'var(--textColorSecondary)', fontSize: '14px', margin: '0 0 16px 0' }}>
              These codes can be used to access your account if you lose your authenticator device. 
              Each code can only be used once.
            </p>

            <div className="codes-grid">
              {recoveryCodes.map((code, index) => (
                <div key={index} className="recovery-code">
                  {code}
                </div>
              ))}
            </div>

            <div className="recovery-warning">
              <FiAlertCircle style={{ marginRight: '8px' }} />
              Save these codes now! You won't be able to see them again after leaving this page.
            </div>

            <div className="auth-actions">
              <button
                className="auth-button secondary"
                onClick={() => copyToClipboard(recoveryCodes.join('\n'), setCopiedCodes)}
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                {copiedCodes ? <FiCheck /> : <FiCopy />}
                {copiedCodes ? 'Copied!' : 'Copy Codes'}
              </button>

              <button
                className="auth-button secondary"
                onClick={downloadRecoveryCodes}
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <FiDownload />
                Download Codes
              </button>

              <button
                className="auth-button primary"
                onClick={handleComplete}
              >
                Complete Setup
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default TOTPSetup;