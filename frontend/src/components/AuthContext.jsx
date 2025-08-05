import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Token refresh utility
  const refreshToken = async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      console.log('Attempting to refresh token...');
      const { default: config } = await import('../config.js');
      const response = await fetch(`${config.API_BASE_AUTH}/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        console.error('Token refresh failed with status:', response.status, 'Error:', errorData);
        throw new Error(`Token refresh failed: ${errorData.detail || 'Unknown error'}`);
      }

      const data = await response.json();
      console.log('Token refresh successful');
      
      // Update stored tokens
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      
      return data.access_token;
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
      throw error;
    }
  };

  // API request with automatic token refresh
  const apiRequest = async (endpoint, options = {}) => {
    let token = localStorage.getItem('access_token');
    
    if (!token) {
      throw new Error('No access token available');
    }

    const makeRequest = async (accessToken) => {
      const { default: config } = await import('../config.js');
      return fetch(`${config.API_BASE_AUTH}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
          ...options.headers,
        },
      });
    };

    let response = await makeRequest(token);

    // If token is expired, try to refresh it
    if (response.status === 401) {
      try {
        token = await refreshToken();
        response = await makeRequest(token);
      } catch (refreshError) {
        throw new Error('Authentication failed');
      }
    }

    return response;
  };

  // Check if user is authenticated
  const checkAuth = async () => {
    try {
      setIsLoading(true);
      
      const response = await apiRequest('/me');
      
      if (response.ok) {
        const data = await response.json();
        setUser(data);
        setIsAuthenticated(true);
      } else {
        logout();
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      logout();
    } finally {
      setIsLoading(false);
    }
  };

  // Login function
  const login = (tokens, userData = null) => {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    
    if (userData) {
      setUser(userData);
    }
    
    setIsAuthenticated(true);
    
    // Check auth to get latest user data
    if (!userData) {
      checkAuth();
    }
  };

  // Logout function
  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('partial_token');
    setUser(null);
    setIsAuthenticated(false);
  };

  // Initialize auth state on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      checkAuth();
    } else {
      setIsLoading(false);
    }
  }, []);

  // Set up token refresh interval
  useEffect(() => {
    if (!isAuthenticated) return;

    // Refresh token every 25 minutes (tokens expire in 30 minutes)
    const refreshInterval = setInterval(() => {
      refreshToken().catch(console.error);
    }, 25 * 60 * 1000);

    return () => clearInterval(refreshInterval);
  }, [isAuthenticated]);

  const value = {
    user,
    isLoading,
    isAuthenticated,
    login,
    logout,
    checkAuth,
    apiRequest,
    refreshToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};