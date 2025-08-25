import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import './TokenDetailsModal.css';

interface TokenDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  token: any;
}

const TokenDetailsModal: React.FC<TokenDetailsModalProps> = ({ isOpen, onClose, token }) => {
  const [decodedClaims, setDecodedClaims] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'raw' | 'decoded'>('decoded');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token && isOpen) {
      try {
        // Try to decode JWT tokens
        if (token.access_token || token.full_access_token) {
          const tokenToDecode = token.full_access_token || token.access_token;
          const decoded = decodeJWT(tokenToDecode);
          setDecodedClaims(decoded);
          setError(null);
        } else if (token.id_token || token.full_id_token) {
          const tokenToDecode = token.full_id_token || token.id_token;
          const decoded = decodeJWT(tokenToDecode);
          setDecodedClaims(decoded);
          setError(null);
        } else {
          setDecodedClaims(null);
          setError('No JWT token available to decode');
        }
      } catch (err) {
        setError('Failed to decode token');
        setDecodedClaims(null);
      }
    }
  }, [token, isOpen]);

  const decodeJWT = (jwt: string) => {
    try {
      // Remove 'Bearer ' prefix if present
      const cleanToken = jwt.replace(/^Bearer\s+/i, '');
      
      // Split the JWT
      const parts = cleanToken.split('.');
      if (parts.length !== 3) {
        throw new Error('Invalid JWT format');
      }

      // Decode header
      const header = JSON.parse(atob(parts[0]));
      
      // Decode payload
      const payload = JSON.parse(atob(parts[1]));
      
      // Format timestamps if present
      if (payload.exp) {
        payload.exp_formatted = new Date(payload.exp * 1000).toLocaleString();
      }
      if (payload.iat) {
        payload.iat_formatted = new Date(payload.iat * 1000).toLocaleString();
      }
      if (payload.nbf) {
        payload.nbf_formatted = new Date(payload.nbf * 1000).toLocaleString();
      }

      return {
        header,
        payload,
        signature: parts[2]
      };
    } catch (err) {
      console.error('Failed to decode JWT:', err);
      throw err;
    }
  };

  const formatValue = (value: any): string => {
    if (value === null) return 'null';
    if (value === undefined) return 'undefined';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  const renderTokenInfo = () => {
    if (!token) return null;

    return (
      <div className="token-info-section">
        <h3>Token Information</h3>
        <div className="info-grid">
          <div className="info-item">
            <span className="label">Token ID:</span>
            <span className="value mono">{token.id}</span>
          </div>
          <div className="info-item">
            <span className="label">Type:</span>
            <span className={`value token-type ${token.type?.toLowerCase()}`}>
              {token.type || 'Unknown'}
            </span>
          </div>
          <div className="info-item">
            <span className="label">User:</span>
            <span className="value">{token.user?.name || '—'}</span>
          </div>
          <div className="info-item">
            <span className="label">Email:</span>
            <span className="value">{token.user?.email || '—'}</span>
          </div>
          <div className="info-item">
            <span className="label">Issued At:</span>
            <span className="value">{new Date(token.issued_at).toLocaleString()}</span>
          </div>
          <div className="info-item">
            <span className="label">Expires At:</span>
            <span className="value">{new Date(token.expires_at).toLocaleString()}</span>
          </div>
          {token.subject && (
            <div className="info-item">
              <span className="label">Subject:</span>
              <span className="value mono">{token.subject}</span>
            </div>
          )}
          {token.issuer && (
            <div className="info-item">
              <span className="label">Issuer:</span>
              <span className="value">{token.issuer}</span>
            </div>
          )}
          {token.audience && (
            <div className="info-item">
              <span className="label">Audience:</span>
              <span className="value">{token.audience}</span>
            </div>
          )}
          {token.revoked && (
            <div className="info-item full-width">
              <span className="label">Status:</span>
              <span className="value revoked">REVOKED</span>
              {token.revoked_at && (
                <span className="value"> at {new Date(token.revoked_at).toLocaleString()}</span>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderDecodedClaims = () => {
    if (error) {
      return <div className="error-message">{error}</div>;
    }

    if (!decodedClaims) {
      return <div className="no-data">No decoded claims available</div>;
    }

    return (
      <div className="decoded-sections">
        <div className="decoded-section">
          <h4>Header</h4>
          <pre className="json-display">{JSON.stringify(decodedClaims.header, null, 2)}</pre>
        </div>
        
        <div className="decoded-section">
          <h4>Payload (Claims)</h4>
          <pre className="json-display">{JSON.stringify(decodedClaims.payload, null, 2)}</pre>
        </div>

        <div className="decoded-section">
          <h4>Signature</h4>
          <div className="signature-display">{decodedClaims.signature}</div>
        </div>
      </div>
    );
  };

  const renderRawToken = () => {
    const rawToken = token?.full_access_token || token?.access_token || 
                     token?.full_id_token || token?.id_token || '';
    
    if (!rawToken) {
      return <div className="no-data">No raw token available</div>;
    }

    return (
      <div className="raw-token-section">
        <div className="raw-token-header">
          <h4>Raw Token</h4>
          <button 
            className="copy-button"
            onClick={() => {
              navigator.clipboard.writeText(rawToken);
              // You could add a toast notification here
            }}
          >
            Copy to Clipboard
          </button>
        </div>
        <pre className="raw-token-display">{rawToken}</pre>
      </div>
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Token Details" className="token-details-modal">
      <div className="token-details-content">
        {renderTokenInfo()}
        
        <div className="token-tabs">
          <div className="tab-buttons">
            <button 
              className={`tab-button ${activeTab === 'decoded' ? 'active' : ''}`}
              onClick={() => setActiveTab('decoded')}
            >
              Decoded Claims
            </button>
            <button 
              className={`tab-button ${activeTab === 'raw' ? 'active' : ''}`}
              onClick={() => setActiveTab('raw')}
            >
              Raw Token
            </button>
          </div>
          
          <div className="tab-content">
            {activeTab === 'decoded' ? renderDecodedClaims() : renderRawToken()}
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default TokenDetailsModal;