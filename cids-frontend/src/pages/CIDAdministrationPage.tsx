import React, { useEffect, useState } from 'react';
import './TokenAdministrationPage.css';
import adminService from '../services/adminService';
import PublicKeyModal from '../components/PublicKeyModal';
import A2AConfigModal from '../components/A2AConfigModal';

const CIDAdministrationPage: React.FC = () => {
  // Security section states
  const [showPublicKeyModal, setShowPublicKeyModal] = useState(false);
  const [a2aPermissions, setA2aPermissions] = useState<any[]>([]);
  const [showA2aModal, setShowA2aModal] = useState(false);
  const [loadingA2a, setLoadingA2a] = useState(false);

  // Load A2A permissions
  const loadA2aPermissions = async () => {
    console.log('🔄 [CIDAdmin] Loading A2A permissions from page...');
    try {
      setLoadingA2a(true);
      const response = await adminService.getA2aPermissions();
      console.log('📦 [CIDAdmin] A2A permissions response:', response);
      setA2aPermissions(response);
    } catch (error) {
      console.error('❌ [CIDAdmin] Failed to load A2A permissions:', error);
    } finally {
      setLoadingA2a(false);
    }
  };

  useEffect(() => {
    // Load A2A permissions on mount
    loadA2aPermissions();
  }, []);

  return (
    <div className="token-admin-page">
      <div className="page-header" style={{
        background: '#0b3b63',
        color: 'white',
        padding: '24px 32px',
        marginBottom: '24px',
        borderRadius: '0',
        textAlign: 'left'
      }}>
        <h1 style={{ margin: '0 0 8px 0', fontSize: '28px', fontWeight: '600', color: 'white' }}>CID Administration</h1>
        <p style={{ margin: 0, fontSize: '16px', color: 'white' }}>Security Configuration</p>
      </div>

      <div className="tab-content">
        <div>
          {/* Two column card layout */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>

            {/* Public Key Card */}
            <div style={{
              background: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <span style={{ fontSize: '24px' }}>🔑</span>
                <h3 style={{ margin: 0, color: '#1f2937' }}>Public Key Management</h3>
              </div>
              <p style={{ color: '#6b7280', marginBottom: '20px' }}>
                View and manage the public key used by applications to verify JWT tokens issued by CID.
              </p>
              <div style={{
                background: '#f9fafb',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '16px',
                fontFamily: 'monospace',
                fontSize: '13px'
              }}>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Algorithm:</strong> RS256
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Key Size:</strong> 2048 bits
                </div>
                <div>
                  <strong>JWKS Endpoint:</strong> /.well-known/jwks.json
                </div>
              </div>
              <button
                className="button"
                onClick={() => setShowPublicKeyModal(true)}
                style={{
                  background: '#0b3b63',
                  color: 'white',
                  padding: '10px 20px',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}
              >
                View Public Key
              </button>
            </div>

            {/* A2A Configuration Card */}
            <div style={{
              background: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <span style={{ fontSize: '24px' }}>🔄</span>
                <h3 style={{ margin: 0, color: '#1f2937' }}>A2A Configuration</h3>
              </div>
              <p style={{ color: '#6b7280', marginBottom: '20px' }}>
                Manage Application-to-Application permissions for secure service communication.
              </p>
              <div style={{
                background: '#f0f9ff',
                border: '1px solid #bae6fd',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '16px',
                fontSize: '13px'
              }}>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Active Permissions:</strong> {a2aPermissions.length}
                </div>
                <div style={{ marginBottom: '8px' }}>
                  <strong>Token Duration:</strong> 5-10 minutes
                </div>
                <div>
                  <strong>Authentication:</strong> API Key based
                </div>
              </div>
              <button
                className="button"
                onClick={() => {
                  setShowA2aModal(true);
                  loadA2aPermissions();
                }}
                style={{
                  background: '#0ea5e9',
                  color: 'white',
                  padding: '10px 20px',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}
              >
                Configure A2A Permissions
              </button>
            </div>
          </div>

          {/* Important Security Recommendations */}
          <div style={{
            background: '#fbbf24',
            border: '2px solid #f59e0b',
            borderRadius: '12px',
            padding: '24px',
            marginTop: '32px',
            color: 'black'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', justifyContent: 'center' }}>
              <span style={{ fontSize: '24px' }}>⚠️</span>
              <h3 style={{ margin: 0, color: 'black', fontWeight: '600' }}>Important Security Recommendations</h3>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <div>
                <h4 style={{ marginTop: 0, marginBottom: '12px', color: 'black', fontWeight: '600' }}>🔑 Public Key Management</h4>
                <ul style={{ margin: 0, paddingLeft: '20px', lineHeight: '1.8' }}>
                  <li><strong>Never share the private key</strong> - Only the public key should be distributed</li>
                  <li><strong>Use JWKS endpoint</strong> - Applications should fetch keys from /.well-known/jwks.json</li>
                  <li><strong>Implement key rotation</strong> - Plan for periodic key rotation (quarterly recommended)</li>
                  <li><strong>Cache public keys</strong> - Applications should cache keys for 24 hours</li>
                </ul>
              </div>

              <div>
                <h4 style={{ marginTop: 0, marginBottom: '12px', color: 'black', fontWeight: '600' }}>🔄 A2A Security Best Practices</h4>
                <ul style={{ margin: 0, paddingLeft: '20px', lineHeight: '1.8' }}>
                  <li><strong>Limit token duration</strong> - Keep A2A tokens short-lived (5-10 minutes max)</li>
                  <li><strong>Use least privilege</strong> - Only grant necessary scopes for each service</li>
                  <li><strong>Rotate API keys regularly</strong> - Implement automatic key rotation policies</li>
                  <li><strong>Monitor A2A activity</strong> - Review audit logs for unusual patterns</li>
                </ul>
              </div>
            </div>

            <div style={{
              marginTop: '20px',
              padding: '12px',
              background: 'rgba(0,0,0,0.1)',
              borderRadius: '8px',
              borderLeft: '4px solid #dc2626'
            }}>
              <strong style={{ color: 'black' }}>🚨 Security Alert:</strong>
              <span style={{ marginLeft: '8px', color: 'black' }}>
                Always validate JWT signatures using the public key. Never trust unverified tokens.
                Implement proper error handling for invalid or expired tokens.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      <PublicKeyModal
        isOpen={showPublicKeyModal}
        onClose={() => setShowPublicKeyModal(false)}
      />

      <A2AConfigModal
        isOpen={showA2aModal}
        onClose={() => setShowA2aModal(false)}
        onRefresh={loadA2aPermissions}
      />
    </div>
  );
};

export default CIDAdministrationPage;