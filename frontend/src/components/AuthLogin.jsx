import React, { useState, useEffect } from 'react';
import { FiEye, FiEyeOff, FiShield, FiKey, FiAlertCircle } from 'react-icons/fi';
import { useAuth } from './AuthContext';
import './AuthLogin.css';

const AuthLogin = ({ onAuthSuccess }) => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [requiresTotp, setRequiresTotp] = useState(false);
  const [useRecoveryCode, setUseRecoveryCode] = useState(false);
  const [totpSetupRequired, setTotpSetupRequired] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const { default: config } = await import('../config.js');
      const loginData = {
        email,
        password,
      };

      // Add TOTP or recovery code if required
      if (requiresTotp) {
        if (useRecoveryCode) {
          loginData.recovery_code = recoveryCode;
        } else {
          loginData.totp_code = totpCode;
        }
      }

      const response = await fetch(`${config.API_BASE_AUTH}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(loginData),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 423) {
          throw new Error('Account temporarily locked due to too many failed attempts. Please try again later.');
        }
        throw new Error(data.detail || 'Login failed');
      }

      // Check if TOTP is required
      if (data.requires_totp && !requiresTotp) {
        setRequiresTotp(true);
        // Store partial token temporarily
        localStorage.setItem('partial_token', data.access_token);
        return;
      }

      // Check if TOTP setup is required
      if (data.totp_setup_required) {
        setTotpSetupRequired(true);
        login({ access_token: data.access_token, refresh_token: data.refresh_token });
        onAuthSuccess({ needsTotpSetup: true });
        return;
      }

      // Successful login
      login({ access_token: data.access_token, refresh_token: data.refresh_token });
      localStorage.removeItem('partial_token');
      
      onAuthSuccess({ needsTotpSetup: false });

    } catch (err) {
      console.error('Login error:', err);
      
      // Check if TOTP is required (simple auth system specific)
      if (err.message === 'TOTP code or recovery code required' && !requiresTotp) {
        console.log('TOTP required, switching to TOTP form');
        setRequiresTotp(true);
        setError(''); // Clear the error since we're showing TOTP form
        return;
      }
      
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setRequiresTotp(false);
    setUseRecoveryCode(false);
    setTotpCode('');
    setRecoveryCode('');
    setError('');
    localStorage.removeItem('partial_token');
  };

  if (totpSetupRequired) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <FiShield className="auth-icon" />
            <h2>Security Setup Required</h2>
          </div>
          <div className="totp-setup-notice">
            <FiAlertCircle className="notice-icon" />
            <p>
              For enhanced security, please set up Two-Factor Authentication (TOTP) 
              to protect your account.
            </p>
          </div>
          <button
            className="auth-button primary"
            onClick={() => onAuthSuccess({ needsTotpSetup: true })}
          >
            Set Up 2FA Now
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <FiShield className="auth-icon" />
          <h2>{requiresTotp ? 'Two-Factor Authentication' : 'Sign In'}</h2>
          <p>
            {requiresTotp 
              ? 'Enter your 6-digit code or use a recovery code'
              : 'Access your Personal Agent'
            }
          </p>
        </div>

        {error && (
          <div className="auth-error">
            <FiAlertCircle />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="auth-form">
          {!requiresTotp ? (
            <>
              <div className="input-group">
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="Enter your email"
                  disabled={isLoading}
                />
              </div>

              <div className="input-group">
                <label htmlFor="password">Password</label>
                <div className="password-input">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="Enter your password"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    disabled={isLoading}
                  >
                    {showPassword ? <FiEyeOff /> : <FiEye />}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="totp-section">
              {!useRecoveryCode ? (
                <div className="input-group">
                  <label htmlFor="totpCode">
                    <FiKey className="inline-icon" />
                    Authentication Code
                  </label>
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
                  />
                  <small>Enter the 6-digit code from your authenticator app</small>
                </div>
              ) : (
                <div className="input-group">
                  <label htmlFor="recoveryCode">
                    <FiKey className="inline-icon" />
                    Recovery Code
                  </label>
                  <input
                    id="recoveryCode"
                    type="text"
                    value={recoveryCode}
                    onChange={(e) => setRecoveryCode(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8))}
                    placeholder="Enter recovery code"
                    maxLength="8"
                    disabled={isLoading}
                    autoFocus
                  />
                  <small>Enter one of your 8-character recovery codes</small>
                </div>
              )}

              <div className="totp-options">
                <button
                  type="button"
                  className="link-button"
                  onClick={() => setUseRecoveryCode(!useRecoveryCode)}
                  disabled={isLoading}
                >
                  {useRecoveryCode ? 'Use authenticator app instead' : 'Use recovery code instead'}
                </button>
              </div>
            </div>
          )}

          <div className="auth-actions">
            <button
              type="submit"
              className="auth-button primary"
              disabled={isLoading || (requiresTotp && !useRecoveryCode && totpCode.length !== 6) || (requiresTotp && useRecoveryCode && recoveryCode.length !== 8)}
            >
              {isLoading ? 'Signing in...' : (requiresTotp ? 'Verify' : 'Sign In')}
            </button>

            {requiresTotp && (
              <button
                type="button"
                className="auth-button secondary"
                onClick={resetForm}
                disabled={isLoading}
              >
                Back to Login
              </button>
            )}
          </div>
        </form>

        {!requiresTotp && (
          <div className="auth-footer">
            <p style={{ color: 'var(--textColorSecondary)', fontSize: '0.9em', textAlign: 'center' }}>
              Personal Agent - Secure Access
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuthLogin;