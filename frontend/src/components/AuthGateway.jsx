import React, { useState } from 'react';
import { useAuth } from './AuthContext';
import AuthLogin from './AuthLogin';
import TOTPSetup from './TOTPSetup';

const AuthGateway = ({ children }) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const [needsTotpSetup, setNeedsTotpSetup] = useState(false);

  const handleAuthSuccess = ({ needsTotpSetup: requiresSetup }) => {
    if (requiresSetup) {
      setNeedsTotpSetup(true);
    } else {
      // Full authentication completed
      setNeedsTotpSetup(false);
    }
  };

  const handleTotpSetupComplete = () => {
    setNeedsTotpSetup(false);
    // The user is already logged in, just need to refresh the auth state
    window.location.reload(); // Simple refresh to update the app state
  };

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <div style={{ 
              display: 'flex', 
              justifyContent: 'center', 
              alignItems: 'center',
              height: '100px' 
            }}>
              <div style={{
                width: '40px',
                height: '40px',
                border: '3px solid var(--borderColor, #333)',
                borderTop: '3px solid var(--primaryColor, #fff)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }}></div>
            </div>
            <p style={{ color: 'var(--textColorSecondary)', margin: 0 }}>
              Checking authentication...
            </p>
          </div>
        </div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // If authenticated but TOTP setup was specifically requested, show TOTP setup
  if (isAuthenticated && needsTotpSetup) {
    return (
      <TOTPSetup
        onSetupComplete={handleTotpSetupComplete}
        onSkip={() => {
          setNeedsTotpSetup(false);
        }}
      />
    );
  }

  // If fully authenticated with user data, show the main app
  if (isAuthenticated && user) {
    return children;
  }

  // Show login form only (no registration)
  return <AuthLogin onAuthSuccess={handleAuthSuccess} />;
};

export default AuthGateway;