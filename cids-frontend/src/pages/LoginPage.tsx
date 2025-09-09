import React from 'react';
import styled, { createGlobalStyle } from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import logo from '../assets/volusia-logo.png';
import { materialTheme } from '../styles/materialTheme';

// Material Design Global Styles
const MaterialGlobalStyle = createGlobalStyle`
  body {
    background: ${materialTheme.colors.background};
    font-family: ${materialTheme.typography.fontFamily};
    margin: 0;
    padding: 0;
  }
`;

const LoginContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: ${materialTheme.colors.surfaceVariant};
  padding: ${materialTheme.spacing.lg};
`;

const LoginCard = styled.div`
  background: #ffffff;
  background-color: rgb(255, 255, 255);
  border-radius: ${materialTheme.borderRadius.lg};
  padding: ${materialTheme.spacing.xl};
  box-shadow: ${materialTheme.elevation[2]};
  border: 1px solid rgba(0, 0, 0, 0.05);
  max-width: 420px;
  width: 100%;
  text-align: center;
  position: relative;
  overflow: hidden;
`;

const Title = styled.h1`
  color: ${materialTheme.colors.onSurface};
  margin: 12px 0 24px 0;
  font-size: ${materialTheme.typography.headlineSmall.fontSize};
  font-weight: ${materialTheme.typography.headlineSmall.fontWeight};
  line-height: ${materialTheme.typography.headlineSmall.lineHeight};
  letter-spacing: ${materialTheme.typography.headlineSmall.letterSpacing};
`;

const Logo = styled.img`
  width: 140px;
  height: auto;
  max-height: 100px;
  object-fit: contain;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
`;

const LoginButton = styled.button`
  background: ${materialTheme.colors.primary};
  color: ${materialTheme.colors.onPrimary};
  border: none;
  padding: 14px 24px;
  border-radius: ${materialTheme.borderRadius.md};
  cursor: pointer;
  font-size: ${materialTheme.typography.labelLarge.fontSize};
  font-weight: ${materialTheme.typography.labelLarge.fontWeight};
  letter-spacing: ${materialTheme.typography.labelLarge.letterSpacing};
  text-transform: uppercase;
  width: 100%;
  transition: ${materialTheme.transitions.standard};
  box-shadow: ${materialTheme.elevation[2]};
  position: relative;
  overflow: hidden;
  z-index: 1;

  /* Material Design ripple effect */
  &::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.5);
    transform: translate(-50%, -50%);
    transition: width 0.6s, height 0.6s;
  }

  &:hover {
    background: ${materialTheme.colors.primaryDark};
    box-shadow: ${materialTheme.elevation[4]};
    transform: translateY(-1px);
  }

  &:active {
    box-shadow: ${materialTheme.elevation[1]};
    transform: translateY(0);
    
    &::after {
      width: 300px;
      height: 300px;
    }
  }

  &:disabled {
    background: ${materialTheme.colors.surfaceVariant};
    color: ${materialTheme.colors.onSurfaceVariant};
    cursor: not-allowed;
    box-shadow: none;
  }
`;

const LoadingSpinner = styled.div`
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top: 3px solid ${materialTheme.colors.onPrimary};
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-right: 8px;
  vertical-align: middle;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const ErrorMessage = styled.div`
  background-color: ${materialTheme.colors.errorContainer};
  border-left: 4px solid ${materialTheme.colors.error};
  color: ${materialTheme.colors.onErrorContainer};
  padding: ${materialTheme.spacing.md};
  border-radius: ${materialTheme.borderRadius.sm};
  margin-bottom: ${materialTheme.spacing.lg};
  font-size: ${materialTheme.typography.bodyMedium.fontSize};
  text-align: left;
  box-shadow: ${materialTheme.elevation[1]};
  position: relative;
  z-index: 1;
`;

// Subtitle for Material Design
const Subtitle = styled.p`
  color: ${materialTheme.colors.onSurfaceVariant};
  font-size: ${materialTheme.typography.bodyMedium.fontSize};
  margin: 0 0 ${materialTheme.spacing.xl} 0;
  line-height: ${materialTheme.typography.bodyMedium.lineHeight};
  position: relative;
  z-index: 1;
`;

// Version badge
const VersionBadge = styled.div`
  position: absolute;
  top: ${materialTheme.spacing.md};
  right: ${materialTheme.spacing.md};
  background: transparent;
  color: #b0b0b0;
  padding: 4px 12px;
  border-radius: ${materialTheme.borderRadius.full};
  font-size: ${materialTheme.typography.labelSmall.fontSize};
  font-weight: ${materialTheme.typography.labelSmall.fontWeight};
  letter-spacing: ${materialTheme.typography.labelSmall.letterSpacing};
  z-index: 1;
`;

const LoginPage: React.FC = () => {
  const { login, loading, error, clearError } = useAuth();

  const handleLogin = () => {
    clearError();
    login();
  };

  return (
    <>
      <MaterialGlobalStyle />
      <LoginContainer>
        <LoginCard>
          <VersionBadge>v1.0.0</VersionBadge>
          <Logo src={logo} alt="Volusia County Logo" />
          <Title>Volusia County Services</Title>
          <Subtitle>Centralized Identity Discovery Service</Subtitle>

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
    </>
  );
};

export default LoginPage;