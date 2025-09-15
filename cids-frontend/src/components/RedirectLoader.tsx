import React from 'react';
import styled, { keyframes } from 'styled-components';

const fadeIn = keyframes`
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
`;

const spin = keyframes`
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
`;

const LoaderOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #0b3b63 0%, #084172 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  animation: ${fadeIn} 0.3s ease-in;
`;

const LoaderContent = styled.div`
  background: white;
  border-radius: 20px;
  padding: 60px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  text-align: center;
  max-width: 500px;
  animation: ${fadeIn} 0.5s ease-in;
`;

const Spinner = styled.div`
  width: 60px;
  height: 60px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #0b3b63;
  border-radius: 50%;
  margin: 0 auto 30px;
  animation: ${spin} 1s linear infinite;
`;

const Title = styled.h2`
  color: #333;
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 15px 0;
`;

const Message = styled.p`
  color: #666;
  font-size: 16px;
  margin: 0 0 25px 0;
  line-height: 1.5;
`;

const AppName = styled.div`
  background: linear-gradient(135deg, #0b3b63 0%, #084172 100%);
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 18px;
  display: inline-block;
`;

const SecureNote = styled.p`
  color: #999;
  font-size: 12px;
  margin-top: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  i {
    color: #10b981;
  }
`;

interface RedirectLoaderProps {
  appName?: string;
}

const RedirectLoader: React.FC<RedirectLoaderProps> = ({ appName = 'the application' }) => {
  return (
    <LoaderOverlay>
      <LoaderContent>
        <Spinner />
        <Title>Redirecting</Title>
        <Message>
          You are being securely redirected to:
        </Message>
        <AppName>{appName}</AppName>
        <SecureNote>
          <i className="fas fa-shield-alt"></i>
          Secure connection via CID SSO
        </SecureNote>
      </LoaderContent>
    </LoaderOverlay>
  );
};

export default RedirectLoader;