import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import './Modal.css';

interface PublicKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 800px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
`;

const ModalHeader = styled.div`
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;

  h2 {
    margin: 0;
    font-size: 24px;
    color: #1f2937;
  }
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  font-size: 28px;
  color: #6b7280;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;

  &:hover {
    background: #f3f4f6;
    color: #1f2937;
  }
`;

const ModalBody = styled.div`
  padding: 24px;
  overflow-y: auto;
  flex: 1;
`;

const InfoSection = styled.div`
  margin-bottom: 24px;

  h3 {
    font-size: 18px;
    color: #1f2937;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  p {
    color: #6b7280;
    line-height: 1.6;
    margin-bottom: 16px;
  }
`;

const EndpointBox = styled.div`
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  font-family: 'Monaco', 'Courier New', monospace;
  display: flex;
  justify-content: space-between;
  align-items: center;

  .endpoint {
    color: #0b3b63;
    font-size: 14px;
  }
`;

const KeyDisplay = styled.div`
  background: #1f2937;
  color: #10b981;
  padding: 16px;
  border-radius: 8px;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
  position: relative;
`;

const CopyButton = styled.button`
  background: #0b3b63;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;

  &:hover {
    background: #084172;
  }

  &:active {
    transform: scale(0.98);
  }
`;

const TabContainer = styled.div`
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  border-bottom: 2px solid #e5e7eb;
`;

const Tab = styled.button<{ active: boolean }>`
  background: none;
  border: none;
  padding: 12px 16px;
  cursor: pointer;
  font-size: 16px;
  color: ${props => props.active ? '#0b3b63' : '#6b7280'};
  border-bottom: 2px solid ${props => props.active ? '#0b3b63' : 'transparent'};
  margin-bottom: -2px;
  transition: all 0.2s;

  &:hover {
    color: #0b3b63;
  }
`;

const LoadingState = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: #6b7280;
`;

const ErrorState = styled.div`
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
`;

const PublicKeyModal: React.FC<PublicKeyModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'jwks' | 'pem'>('jwks');
  const [jwksData, setJwksData] = useState<any>(null);
  const [pemKey, setPemKey] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchPublicKey();
    }
  }, [isOpen]);

  const fetchPublicKey = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/.well-known/jwks.json');
      if (!response.ok) throw new Error('Failed to fetch public key');
      const data = await response.json();
      setJwksData(data);
      
      // Convert JWKS to PEM format (simplified)
      if (data.keys && data.keys[0]) {
        const key = data.keys[0];
        // This is a simplified PEM representation
        const pemFormat = `-----BEGIN PUBLIC KEY-----\n${key.n || 'Key data not available'}\n-----END PUBLIC KEY-----`;
        setPemKey(pemFormat);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load public key');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!isOpen) return null;

  const jwksEndpoint = `${window.location.origin}/.well-known/jwks.json`;

  return (
    <ModalOverlay onClick={onClose}>
      <ModalContent onClick={(e) => e.stopPropagation()}>
        <ModalHeader>
          <h2>🔑 Public Key Information</h2>
          <CloseButton onClick={onClose}>×</CloseButton>
        </ModalHeader>
        <ModalBody>
          <InfoSection>
            <h3>About CID Public Keys</h3>
            <p>
              The public key is used to verify JWT tokens issued by CID. Applications can use this key
              to validate tokens independently without making API calls to CID, providing resilience
              in case CID is temporarily unavailable.
            </p>
          </InfoSection>

          <InfoSection>
            <h3>JWKS Endpoint</h3>
            <p>Applications should fetch the public key from this endpoint:</p>
            <EndpointBox>
              <span className="endpoint">{jwksEndpoint}</span>
              <CopyButton onClick={() => copyToClipboard(jwksEndpoint)}>
                {copied ? '✓ Copied' : '📋 Copy'}
              </CopyButton>
            </EndpointBox>
          </InfoSection>

          <InfoSection>
            <h3>Public Key Data</h3>
            <TabContainer>
              <Tab active={activeTab === 'jwks'} onClick={() => setActiveTab('jwks')}>
                JWKS Format
              </Tab>
              <Tab active={activeTab === 'pem'} onClick={() => setActiveTab('pem')}>
                PEM Format
              </Tab>
            </TabContainer>

            {loading && <LoadingState>Loading public key...</LoadingState>}
            {error && <ErrorState>Error: {error}</ErrorState>}
            
            {!loading && !error && (
              <>
                {activeTab === 'jwks' && jwksData && (
                  <>
                    <KeyDisplay>
                      {JSON.stringify(jwksData, null, 2)}
                    </KeyDisplay>
                    <div style={{ marginTop: '12px' }}>
                      <CopyButton onClick={() => copyToClipboard(JSON.stringify(jwksData, null, 2))}>
                        {copied ? '✓ Copied' : '📋 Copy JWKS'}
                      </CopyButton>
                    </div>
                  </>
                )}
                
                {activeTab === 'pem' && pemKey && (
                  <>
                    <KeyDisplay>
                      {pemKey}
                    </KeyDisplay>
                    <div style={{ marginTop: '12px' }}>
                      <CopyButton onClick={() => copyToClipboard(pemKey)}>
                        {copied ? '✓ Copied' : '📋 Copy PEM'}
                      </CopyButton>
                    </div>
                  </>
                )}
              </>
            )}
          </InfoSection>

          <InfoSection>
            <h3>Usage Example</h3>
            <KeyDisplay>
{`// Fetch and cache the public key
const jwks = await fetch('${jwksEndpoint}').then(r => r.json());

// Use the key to verify JWT tokens
const verified = await verifyJWT(token, jwks.keys[0]);`}
            </KeyDisplay>
          </InfoSection>
        </ModalBody>
      </ModalContent>
    </ModalOverlay>
  );
};

export default PublicKeyModal;