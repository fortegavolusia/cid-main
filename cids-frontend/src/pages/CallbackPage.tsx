import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import authService from '../services/authService';

const CallbackContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--bg-color);
  padding: 24px;
`;

const CallbackCard = styled.div`
  background: white;
  border-radius: var(--border-radius);
  padding: 32px;
  box-shadow: var(--card-shadow);
  border: 1px solid var(--border-color);
  max-width: 420px;
  width: 100%;
  text-align: center;
`;

const LoadingSpinner = styled.div`
  display: inline-block;
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const IconContainer = styled.div`
  font-size: 48px;
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  
  svg {
    animation: ${props => props.$animate ? 'pulse 1.5s ease-in-out infinite' : 'none'};
  }
  
  @keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.1); opacity: 0.8; }
  }
`;

const Message = styled.div`
  font-size: 16px;
  color: var(--text-secondary);
  margin-bottom: 20px;
`;

const ErrorMessage = styled.div`
  background-color: #fff2f0;
  border: 1px solid var(--error-color);
  color: var(--error-color);
  padding: 12px;
  border-radius: var(--border-radius);
  margin-bottom: 20px;
  font-size: 14px;
  text-align: left;
`;

const RetryButton = styled.button`
  background-color: var(--primary-color);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.2s ease;
  box-shadow: 0 2px 0 rgba(0, 0, 0, 0.015);

  &:hover {
    filter: brightness(1.05);
  }

  &:active {
    filter: brightness(0.95);
  }
`;

const CallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { checkAuth } = useAuth();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    handleCallback();
  }, []);

  const handleCallback = async () => {
    try {
      setStatus('processing');
      setError(null);

      // Check for error parameters from OAuth
      const errorParam = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      if (errorParam) {
        throw new Error(errorDescription || `OAuth error: ${errorParam}`);
      }

      // Check for authorization code from Azure AD
      const code = searchParams.get('code');
      const state = searchParams.get('state');

      if (code) {
        console.log('Found authorization code in URL');
        
        // Verify state parameter
        const storedState = localStorage.getItem('oauth_state');
        if (!state || state !== storedState) {
          throw new Error('Invalid state parameter - possible CSRF attack');
        }
        
        // Clear state from storage
        localStorage.removeItem('oauth_state');
        
        // Exchange code for token
        const tokenResponse = await authService.exchangeCodeForToken(code);
        
        if (tokenResponse.access_token) {
          console.log('Successfully exchanged code for token');
          authService.setAuthToken(tokenResponse.access_token);
          
          // Store refresh token if provided
          if (tokenResponse.refresh_token) {
            localStorage.setItem('refresh_token', tokenResponse.refresh_token);
          }
          
          // Initialize token manager for automatic refresh
          const { tokenManager } = await import('../services/tokenManager');
          tokenManager.initialize(tokenResponse.access_token, tokenResponse.refresh_token);
          
          // Clear the URL parameters for security
          window.history.replaceState({}, document.title, window.location.pathname);
          
          // Check authentication status with the new token
          await checkAuth();
          
          setStatus('success');
          
          // Redirect to dashboard after a brief delay
          setTimeout(() => {
            navigate('/', { replace: true });
          }, 1500);
          
          return;
        } else {
          throw new Error('No access token received from token exchange');
        }
      }

      // Check for token in URL fragment (legacy support)
      const fragment = window.location.hash.substring(1);
      const params = new URLSearchParams(fragment);
      const accessToken = params.get('access_token');

      if (accessToken) {
        console.log('Found access token in URL fragment');
        authService.setAuthToken(accessToken);

        // Clear the fragment from URL for security
        window.history.replaceState({}, document.title, window.location.pathname);

        // Check authentication status with the new token
        await checkAuth();

        setStatus('success');

        // Redirect to home page after a brief delay
        setTimeout(() => {
          navigate('/', { replace: true });
        }, 1500);

        return;
      }

      // If we get here, no token or code was found
      throw new Error('No authentication code or token received');

    } catch (err: any) {
      console.error('Callback handling error:', err);
      setError(err.message || 'Authentication failed');
      setStatus('error');
    }
  };

  const handleRetry = () => {
    navigate('/login', { replace: true });
  };

  return (
    <CallbackContainer>
      <CallbackCard>
        {status === 'processing' && (
          <>
            <IconContainer $animate={true}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20Z" fill="#1976d2"/>
                <path d="M12 6V12L16.25 14.15L17 12.92L13.5 11.25V6H12Z" fill="#1976d2"/>
                <circle cx="12" cy="12" r="10" stroke="#1976d2" strokeWidth="2" strokeLinecap="round" strokeDasharray="5 5">
                  <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="2s" repeatCount="indefinite"/>
                </circle>
              </svg>
            </IconContainer>
            <Message>Processing authentication...</Message>
            <div style={{ fontSize: '12px', color: '#666', marginTop: '10px' }}>
              Verifying your credentials with Azure AD
            </div>
          </>
        )}

        {status === 'success' && (
          <>
            <IconContainer>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" fill="#4caf50"/>
                <path d="M9 12L11 14L15 10" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </IconContainer>
            <Message style={{ color: '#4caf50', fontWeight: 600 }}>Authentication Successful!</Message>
            <div style={{ fontSize: '14px', color: '#666', marginTop: '10px' }}>
              Redirecting to dashboard...
            </div>
          </>
        )}

        {status === 'error' && (
          <>
            <IconContainer>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" fill="#f44336"/>
                <path d="M15 9L9 15M9 9L15 15" stroke="white" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </IconContainer>
            <Message style={{ color: '#f44336', fontWeight: 600 }}>Authentication Failed</Message>
            {error && <ErrorMessage>{error}</ErrorMessage>}
            <RetryButton onClick={handleRetry}>
              Try Again
            </RetryButton>
          </>
        )}
      </CallbackCard>
    </CallbackContainer>
  );
};

export default CallbackPage;
