import React from 'react';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import logo from '../assets/logo.png';

const LoginContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--bg-color);
  padding: 24px;
`;

const LoginCard = styled.div`
  background: white;
  border-radius: var(--border-radius);
  padding: 32px;
  box-shadow: var(--card-shadow);
  border: 1px solid var(--border-color);
  max-width: 420px;
  width: 100%;
  text-align: center;
`;

const Title = styled.h1`
  color: var(--text-primary);
  margin: 12px 0 24px 0;
  font-size: 24px;
  font-weight: 500;
`;

const Logo = styled.img`
  width: 96px;
  height: 96px;
  object-fit: contain;
  margin-bottom: 12px;
`;

const LoginButton = styled.button`
  background-color: var(--primary-color);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  width: 100%;
  transition: all 0.2s ease;
  box-shadow: 0 2px 0 rgba(0, 0, 0, 0.015);

  &:hover {
    filter: brightness(1.05);
    box-shadow: 0 2px 0 rgba(0, 0, 0, 0.045);
  }

  &:active {
    filter: brightness(0.95);
  }

  &:disabled {
    background-color: #f5f5f5;
    color: #bfbfbf;
    cursor: not-allowed;
  }
`;

const LoadingSpinner = styled.div`
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 8px;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
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


const LoginPage: React.FC = () => {
  const { login, loading, error, clearError } = useAuth();

  const handleLogin = () => {
    clearError();
    login();
  };

  return (
    <LoginContainer>
      <LoginCard>
        <Logo src={logo} alt="Logo" />
        <Title>Azure AD Authentication</Title>


        {error && (
          <ErrorMessage>
            {error}
          </ErrorMessage>
        )}

        <LoginButton onClick={handleLogin} disabled={loading}>
          {loading && <LoadingSpinner />}
          {loading ? 'Redirecting...' : 'Sign in with Azure AD'}
        </LoginButton>
      </LoginCard>
    </LoginContainer>
  );
};

export default LoginPage;
