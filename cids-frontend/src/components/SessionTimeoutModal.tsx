import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { inactivityMonitor } from '../services/inactivityMonitor';
import { authService } from '../services/authService';

const ModalOverlay = styled.div<{ $isVisible: boolean }>`
  display: ${props => props.$isVisible ? 'flex' : 'none'};
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  justify-content: center;
  align-items: center;
  z-index: 10000;
  animation: ${props => props.$isVisible ? 'fadeIn 0.3s ease-in-out' : 'none'};

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 12px;
  padding: 32px;
  max-width: 450px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;

  @keyframes slideUp {
    from {
      transform: translateY(20px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }
`;

const ModalHeader = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: 24px;
`;

const WarningIcon = styled.div`
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #ff9800 0%, #ff5722 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  font-size: 24px;
  color: white;
`;

const Title = styled.h2`
  margin: 0;
  font-size: 24px;
  color: #333;
  font-weight: 600;
`;

const Message = styled.p`
  font-size: 16px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 24px;
`;

const CountdownContainer = styled.div`
  background: #f5f5f5;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
  text-align: center;
`;

const CountdownText = styled.div`
  font-size: 14px;
  color: #999;
  margin-bottom: 8px;
`;

const CountdownTimer = styled.div`
  font-size: 32px;
  font-weight: bold;
  color: #ff5722;
  font-variant-numeric: tabular-nums;
`;

const ButtonContainer = styled.div`
  display: flex;
  gap: 12px;
  justify-content: flex-end;
`;

const Button = styled.button<{ $variant?: 'primary' | 'secondary' }>`
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;

  ${props => props.$variant === 'primary' ? `
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
  ` : `
    background: #f5f5f5;
    color: #666;
    
    &:hover {
      background: #e0e0e0;
    }
  `}

  &:active {
    transform: translateY(0);
  }
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 4px;
  background: #e0e0e0;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 24px;
`;

const ProgressFill = styled.div<{ $progress: number }>`
  height: 100%;
  background: linear-gradient(90deg, #ff5722, #ff9800);
  width: ${props => props.$progress}%;
  transition: width 1s linear;
`;

interface SessionTimeoutModalProps {
  onExtend?: () => void;
  onLogout?: () => void;
}

const SessionTimeoutModal: React.FC<SessionTimeoutModalProps> = ({ 
  onExtend, 
  onLogout 
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [countdown, setCountdown] = useState(120); // 2 minutes default
  const [totalTime, setTotalTime] = useState(120);

  useEffect(() => {
    // Start inactivity monitor with callbacks
    inactivityMonitor.start({
      onWarning: () => {
        setIsVisible(true);
        setTotalTime(120); // Reset to full countdown
        setCountdown(120);
      },
      onCountdown: (secondsLeft) => {
        setCountdown(secondsLeft);
        if (secondsLeft <= 0) {
          handleLogout();
        }
      },
      onLogout: () => {
        handleLogout();
      }
    });

    // Listen for token expiration
    const handleTokenExpired = () => {
      setIsVisible(true);
      setTotalTime(30); // Shorter countdown for expired tokens
      setCountdown(30);
    };

    window.addEventListener('token-expired', handleTokenExpired);

    return () => {
      inactivityMonitor.stop();
      window.removeEventListener('token-expired', handleTokenExpired);
    };
  }, []);

  const handleExtendSession = () => {
    setIsVisible(false);
    inactivityMonitor.extendSession();
    if (onExtend) {
      onExtend();
    }
  };

  const handleLogout = async () => {
    setIsVisible(false);
    if (onLogout) {
      onLogout();
    }
    try {
      await authService.logout();
    } catch (error) {
      console.error('Logout error:', error);
      window.location.href = '/login';
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const progress = ((totalTime - countdown) / totalTime) * 100;

  return (
    <ModalOverlay $isVisible={isVisible}>
      <ModalContent>
        <ModalHeader>
          <WarningIcon>⚠️</WarningIcon>
          <Title>Session Timeout Warning</Title>
        </ModalHeader>
        
        <Message>
          Your session is about to expire due to inactivity. 
          Would you like to stay logged in?
        </Message>

        <ProgressBar>
          <ProgressFill $progress={progress} />
        </ProgressBar>

        <CountdownContainer>
          <CountdownText>Time remaining</CountdownText>
          <CountdownTimer>{formatTime(countdown)}</CountdownTimer>
        </CountdownContainer>

        <ButtonContainer>
          <Button $variant="secondary" onClick={handleLogout}>
            Log Out
          </Button>
          <Button $variant="primary" onClick={handleExtendSession}>
            Stay Logged In
          </Button>
        </ButtonContainer>
      </ModalContent>
    </ModalOverlay>
  );
};

export default SessionTimeoutModal;