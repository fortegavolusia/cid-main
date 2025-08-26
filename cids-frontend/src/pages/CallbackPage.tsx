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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
`;

const CallbackCard = styled.div`
  background: white;
  border-radius: 10px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 400px;
  width: 100%;
  text-align: center;
`;

const LoadingSpinner = styled.div`
  display: inline-block;
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const Message = styled.div`
  font-size: 16px;
  color: #666;
  margin-bottom: 20px;
`;

const ErrorMessage = styled.div`
  background-color: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 14px;
`;

const RetryButton = styled.button`
  background-color: #1890ff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.3s ease;

  &:hover {
    background-color: #40a9ff;
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
          
          // Redirect to admin page after a brief delay
          setTimeout(() => {
            navigate('/admin', { replace: true });
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
            <LoadingSpinner />
            <Message>Processing authentication...</Message>
          </>
        )}

        {status === 'success' && (
          <>
            <div style={{ fontSize: '48px', marginBottom: '20px' }}>✓</div>
            <Message>Authentication successful! Redirecting...</Message>
          </>
        )}

        {status === 'error' && (
          <>
            <div style={{ fontSize: '48px', marginBottom: '20px', color: '#ff4d4f' }}>✗</div>
            <Message>Authentication failed</Message>
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
