import React, { useState, useEffect } from 'react';
import TokenBuilder from '../components/TokenBuilder';
import TokenTemplates from '../components/TokenTemplates';
import TokenDetailsModal from '../components/TokenDetailsModal';
import adminService from '../services/adminService';
import type { TokenListResponse, TokenInfo } from '../types/admin';
import './TokenAdministrationPage.css';

const TokenAdministrationPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('builder');
  const [templateToLoad, setTemplateToLoad] = useState<any>(null);
  
  // Logs state
  const [internalTokens, setInternalTokens] = useState<TokenListResponse | null>(null);
  const [azureTokens, setAzureTokens] = useState<TokenListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterText, setFilterText] = useState('');
  const [sortKey, setSortKey] = useState<'issued_desc' | 'issued_asc' | 'expires_soon' | 'expires_late'>('issued_desc');
  
  // Modal state
  const [selectedToken, setSelectedToken] = useState<TokenInfo | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);

  const handleLoadTemplate = (template: any) => {
    setTemplateToLoad(template);
    setActiveTab('builder');
  };

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchTokens();
    }
  }, [activeTab]);

  const fetchTokens = async () => {
    try {
      setLoading(true);
      setError(null);

      const [internalResponse, azureResponse] = await Promise.all([
        adminService.getInternalTokens(),
        adminService.getAzureTokens()
      ]);

      setInternalTokens(internalResponse);
      setAzureTokens(azureResponse);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch tokens');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString?: string) => {
    try {
      if (!dateString) return '—';
      const d = new Date(dateString);
      return isNaN(d.getTime()) ? '—' : d.toLocaleString();
    } catch {
      return '—';
    }
  };

  const shorten = (val?: string, max: number = 20) => {
    if (!val) return '—';
    return val.length > max ? `${val.substring(0, max)}...` : val;
  };

  const renderTokenTable = (tokens: TokenInfo[]) => (
    <table className="token-table">
      <thead>
        <tr>
          <th>User</th>
          <th>Email</th>
          <th>Type</th>
          <th>Issued</th>
          <th>Expires</th>
          <th>Subject</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {tokens.map((token, idx) => (
          <tr key={token.id || `${token.user?.email || 'unknown'}-${token.issued_at || idx}`}>
            <td>{token.user?.name || '—'}</td>
            <td>{token.user?.email || '—'}</td>
            <td>
              <span className={`token-status ${token.type?.toLowerCase()}`}>
                {token.type || 'Unknown'}
              </span>
            </td>
            <td>{formatDate(token.issued_at)}</td>
            <td>{formatDate(token.expires_at)}</td>
            <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
              {shorten(token.subject, 20)}
            </td>
            <td>
              <div className="token-actions">
                <button className="button small" onClick={() => {
                  setSelectedToken(token);
                  setIsDetailsModalOpen(true);
                }}>Details</button>
                <button className="button small" onClick={async () => {
                  try {
                    const service = token.type === 'Azure' ? adminService.getAzureTokenActivity(token.id) : adminService.getTokenActivity(token.id);
                    const data = await service;
                    alert(JSON.stringify(data, null, 2));
                  } catch (e: any) {
                    alert(e.message || 'Failed to load logs');
                  }
                }}>Activity</button>
                <button className="button small danger" onClick={async () => {
                  if (!confirm('Revoke this token?')) return;
                  try {
                    if (token.type === 'Azure') await adminService.removeAzureToken(token.id);
                    else await adminService.removeToken(token.id);
                    fetchTokens();
                  } catch(e:any){ alert(e.message || 'Failed to revoke'); }
                }}>Revoke</button>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  return (
    <div className="token-admin-page">
      <div className="page-header">
        <h1>Token Administration</h1>
        <p className="page-subtitle">Manage JWT token structures and templates</p>
      </div>

      <div className="tab-navigation">
        <button 
          className={`tab-button ${activeTab === 'builder' ? 'active' : ''}`}
          onClick={() => setActiveTab('builder')}
        >
          Token Builder
        </button>
        <button 
          className={`tab-button ${activeTab === 'templates' ? 'active' : ''}`}
          onClick={() => setActiveTab('templates')}
        >
          Templates
        </button>
        <button 
          className={`tab-button ${activeTab === 'testing' ? 'active' : ''}`}
          onClick={() => setActiveTab('testing')}
        >
          Testing
        </button>
        <button 
          className={`tab-button ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          Settings
        </button>
        <button 
          className={`tab-button ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          Logs
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'builder' && <TokenBuilder templateToLoad={templateToLoad} />}
        {activeTab === 'templates' && <TokenTemplates onLoadTemplate={handleLoadTemplate} />}
        {activeTab === 'testing' && (
          <div className="coming-soon">
            <h3>Token Testing</h3>
            <p>Test token generation with sample data</p>
            <span className="placeholder">Coming Soon</span>
          </div>
        )}
        {activeTab === 'settings' && (
          <div className="coming-soon">
            <h3>Token Settings</h3>
            <p>Configure expiration, algorithms, and defaults</p>
            <span className="placeholder">Coming Soon</span>
          </div>
        )}
        {activeTab === 'logs' && (
          <div className="logs-content">
            <div className="logs-header">
              <h3>Token Logs</h3>
              <div className="logs-controls">
                <input 
                  placeholder="Filter by user, email, subject" 
                  value={filterText} 
                  onChange={e=>setFilterText(e.target.value)} 
                  className="filter-input"
                />
                <select value={sortKey} onChange={e=>setSortKey(e.target.value as any)} className="sort-select">
                  <option value="issued_desc">Newest issued</option>
                  <option value="issued_asc">Oldest issued</option>
                  <option value="expires_soon">Expires soon</option>
                  <option value="expires_late">Expires latest</option>
                </select>
                <button className="button" onClick={fetchTokens}>Refresh</button>
              </div>
            </div>
            
            {loading && <div className="loading">Loading token logs...</div>}
            {error && <div className="error-message">{error}</div>}
            
            {!loading && !error && (
              <div className="logs-table-container">
                <h4>Active Tokens ({(internalTokens?.total || 0) + (azureTokens?.total || 0)})</h4>
                {(() => {
                  const internal = (internalTokens?.tokens || []).map(t => ({ ...t, type: (t.type || 'Internal') as any }));
                  const azure = (azureTokens?.tokens || []).map(t => ({ ...t, type: (t.type || 'Azure') as any }));
                  const combined = [...internal, ...azure]
                    .filter(t => {
                      const q = filterText.toLowerCase();
                      return !q || [t.user?.name, t.user?.email, t.subject, t.type].some(v => (v||'').toLowerCase().includes(q));
                    })
                    .sort((a,b) => {
                      const ia = new Date(a.issued_at||'').getTime();
                      const ib = new Date(b.issued_at||'').getTime();
                      const ea = new Date(a.expires_at||'').getTime();
                      const eb = new Date(b.expires_at||'').getTime();
                      switch (sortKey) {
                        case 'issued_asc': return ia - ib;
                        case 'expires_soon': return ea - eb;
                        case 'expires_late': return eb - ea;
                        default: return ib - ia;
                      }
                    });
                  return combined.length ? renderTokenTable(combined) : <p>No tokens found.</p>;
                })()}
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Token Details Modal */}
      <TokenDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={() => {
          setIsDetailsModalOpen(false);
          setSelectedToken(null);
        }}
        token={selectedToken}
      />
    </div>
  );
};

export default TokenAdministrationPage;