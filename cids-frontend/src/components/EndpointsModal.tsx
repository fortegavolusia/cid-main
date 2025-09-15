import React from 'react';
import './Modal.css';

interface Endpoint {
  path: string;
  method: string;
  resource: string;
  action: string;
  description?: string;
  permissions?: string[];
}

interface EndpointsModalProps {
  isOpen: boolean;
  onClose: () => void;
  appName: string;
  endpoints: {
    endpoints?: Endpoint[];
    total?: number;
    last_discovered?: string;
    last_discovery_at?: string;
    permissions_generated?: string[];
  } | null;
}

const EndpointsModal: React.FC<EndpointsModalProps> = ({
  isOpen,
  onClose,
  appName,
  endpoints
}) => {
  if (!isOpen) return null;

  const getMethodColor = (method: string) => {
    const colors: Record<string, string> = {
      GET: '#10b981',
      POST: '#3b82f6',
      PUT: '#f59e0b',
      PATCH: '#8b5cf6',
      DELETE: '#ef4444',
      OPTIONS: '#6b7280',
      HEAD: '#06b6d4'
    };
    return colors[method] || '#6b7280';
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-container"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: '900px',
          maxHeight: '80vh',
          background: 'white',
          borderRadius: '12px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
        }}
      >
        <div className="modal-header">
          <h2>Discovered Endpoints - {appName}</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body" style={{ overflowY: 'auto', maxHeight: '60vh' }}>
          {endpoints && endpoints.endpoints && endpoints.endpoints.length > 0 ? (
            <>
              <div style={{
                background: '#f9fafb',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '20px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <strong>Total Endpoints:</strong> {endpoints.total || endpoints.endpoints.length}
                </div>
                <div>
                  <strong>Last Discovered:</strong> {formatDate(endpoints.last_discovery_at || endpoints.last_discovered)}
                </div>
              </div>

              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '12px', fontWeight: '600' }}>Method</th>
                    <th style={{ textAlign: 'left', padding: '12px', fontWeight: '600' }}>Path</th>
                    <th style={{ textAlign: 'left', padding: '12px', fontWeight: '600' }}>Resource</th>
                    <th style={{ textAlign: 'left', padding: '12px', fontWeight: '600' }}>Action</th>
                    <th style={{ textAlign: 'left', padding: '12px', fontWeight: '600' }}>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {endpoints.endpoints.map((endpoint, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #e5e7eb' }}>
                      <td style={{ padding: '12px' }}>
                        <span style={{
                          background: getMethodColor(endpoint.method),
                          color: 'white',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: '600',
                          display: 'inline-block',
                          minWidth: '60px',
                          textAlign: 'center'
                        }}>
                          {endpoint.method}
                        </span>
                      </td>
                      <td style={{
                        padding: '12px',
                        fontFamily: 'monospace',
                        fontSize: '13px',
                        wordBreak: 'break-all'
                      }}>
                        {endpoint.path}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span style={{
                          background: '#e0e7ff',
                          color: '#3730a3',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '12px'
                        }}>
                          {endpoint.resource || '—'}
                        </span>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span style={{
                          background: '#fef3c7',
                          color: '#92400e',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '12px'
                        }}>
                          {endpoint.action || '—'}
                        </span>
                      </td>
                      <td style={{ padding: '12px', color: '#6b7280', fontSize: '13px' }}>
                        {endpoint.description || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {endpoints.permissions_generated && endpoints.permissions_generated.length > 0 && (
                <div style={{
                  marginTop: '20px',
                  padding: '16px',
                  background: '#f0fdf4',
                  border: '1px solid #86efac',
                  borderRadius: '8px'
                }}>
                  <h4 style={{ margin: '0 0 12px 0', color: '#166534' }}>
                    Generated Permissions ({endpoints.permissions_generated.length})
                  </h4>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {endpoints.permissions_generated.slice(0, 15).map((perm, idx) => (
                      <span key={idx} style={{
                        background: '#10b981',
                        color: 'white',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontFamily: 'monospace'
                      }}>
                        {perm}
                      </span>
                    ))}
                    {endpoints.permissions_generated.length > 15 && (
                      <span style={{
                        color: '#6b7280',
                        padding: '4px 8px',
                        fontSize: '12px'
                      }}>
                        +{endpoints.permissions_generated.length - 15} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div style={{
              textAlign: 'center',
              padding: '40px',
              color: '#6b7280'
            }}>
              <p style={{ fontSize: '18px', marginBottom: '8px' }}>No endpoints discovered</p>
              <p style={{ fontSize: '14px' }}>Run discovery to detect available endpoints</p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="button secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default EndpointsModal;