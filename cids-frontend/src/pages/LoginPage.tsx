import React from 'react';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';

const LoginContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
`;

const LoginCard = styled.div`
  background: white;
  border-radius: 10px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  max-width: 400px;
  width: 100%;
  text-align: center;
`;

const Title = styled.h1`
  color: #333;
  margin-bottom: 30px;
  font-size: 24px;
  font-weight: 500;
`;

const Description = styled.p`
  color: #666;
  margin-bottom: 30px;
  line-height: 1.6;
`;

const LoginButton = styled.button`
  background-color: #1890ff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  width: 100%;
  transition: all 0.3s ease;
  box-shadow: 0 2px 0 rgba(0, 0, 0, 0.015);

  &:hover {
    background-color: #40a9ff;
    box-shadow: 0 2px 0 rgba(0, 0, 0, 0.045);
  }

  &:active {
    background-color: #096dd9;
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
  border-top: 3px solid #1890ff;
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
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 14px;
`;

const InfoBox = styled.div`
  background-color: #f6ffed;
  border: 1px solid #b7eb8f;
  color: #52c41a;
  padding: 16px;
  border-radius: 6px;
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
        <Title>Azure AD Authentication</Title>
        
        <Description>
          Welcome to the Centralized Identity Service (CIDS). Please log in with your Azure AD account to access your profile and manage authentication tokens.
        </Description>

        <InfoBox>
          <strong>What is CIDS?</strong>
          <br />
          CIDS is a centralized authentication service that integrates with Azure Active Directory to provide secure token-based authentication for internal applications.
        </InfoBox>

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
