import { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import adminService from '../services/adminService';
import type { TokenListResponse, TokenInfo, AppInfo } from '../types/admin';
import RolesModal from '../components/RolesModal';

const Container = styled.div`
  background-color: white;
  border-radius: var(--border-radius);
  box-shadow: var(--card-shadow);
  padding: 24px;
  margin-bottom: 24px;
  overflow-x: auto;
`;

const Title = styled.h1`
  color: rgba(0, 0, 0, 0.85);
  margin: 0 0 24px 0;
  font-size: 24px;
  font-weight: 500;
`;

const InfoSection = styled.div`
  background-color: white;
  border-radius: var(--border-radius);
  padding: 0;
  margin: 24px 0;
  border: 1px solid var(--border-color);
  box-shadow: var(--card-shadow);
`;

const SectionHeader = styled.div`
  padding: 16px 24px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
  transition: all 0.3s ease;
  border-bottom: 1px solid var(--border-color);
`;

const SectionContent = styled.div`
  padding: 24px;
`;

const TokenTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;

  tbody tr:hover {
    background-color: #f5f5f5;
  }
`;

const TableHeader = styled.th`
  text-align: left;
  padding: 12px;
  background-color: #fafafa;
  border-bottom: 1px solid #f0f0f0;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
  white-space: nowrap;
`;

const TableCell = styled.td`
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
  color: rgba(0, 0, 0, 0.65);
  white-space: nowrap;
`;

const TokenStatus = styled.span<{ type: string }>`
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  background-color: ${props => {
    switch (props.type) {
      case 'Internal': return '#e6f7ff';
      case 'Azure': return '#f6ffed';
      default: return '#f0f0f0';
    }
  }};
  color: ${props => {
    switch (props.type) {
      case 'Internal': return '#1890ff';
      case 'Azure': return '#52c41a';
      default: return '#666';
    }
  }};
`;

const LoadingSpinner = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  font-size: 16px;
  color: #666;
`;

const ErrorMessage = styled.div`
  background-color: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
`;


const AdminPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'tokens' | 'apps'>('tokens');
  const [internalTokens, setInternalTokens] = useState<TokenListResponse | null>(null);
  const [azureTokens, setAzureTokens] = useState<TokenListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Token filters/sort
  const [filterText, setFilterText] = useState('');
  const [sortKey, setSortKey] = useState<'issued_desc' | 'issued_asc' | 'expires_soon' | 'expires_late'>('issued_desc');

  // Apps state
  const [appsOpen, setAppsOpen] = useState(true);
  const [apps, setApps] = useState<AppInfo[] | null>(null);
  const [appLoading, setAppLoading] = useState(false);
  const [rolesModal, setRolesModal] = useState<{ isOpen: boolean; clientId: string; appName: string }>({
    isOpen: false,
    clientId: '',
    appName: ''
  });
  const [registerForm, setRegisterForm] = useState({
    name: '', description: '', owner_email: '', redirect_uris: [''], allow_discovery: false, discovery_endpoint: ''
  });

  useEffect(() => {
    fetchTokens();
  }, []);

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

  const loadApps = async () => {
    try {
      setAppLoading(true);
      const list = await adminService.getApps();
      setApps(list);
    } catch (e: any) {
      setError(e.message || 'Failed to load apps');
    } finally {
      setAppLoading(false);
    }
  };

  const handleRegister = async (e: any) => {
    e.preventDefault();
    try {
      const payload: any = {
        name: registerForm.name,
        description: registerForm.description,
        owner_email: registerForm.owner_email,
        redirect_uris: registerForm.redirect_uris.filter(u => u && u.trim().length > 0),
        allow_discovery: registerForm.allow_discovery,
        discovery_endpoint: registerForm.discovery_endpoint || null,
      };
      const result = await adminService.createApp(payload);
      alert(`App registered. Save the Client Secret now!\nClient ID: ${result.app.client_id}\nClient Secret: ${result.client_secret}`);
      setRegisterForm({ name: '', description: '', owner_email: '', redirect_uris: [''], allow_discovery: false, discovery_endpoint: '' });
      loadApps();
    } catch (e: any) {
      alert(e.message || 'Failed to register app');
    }
  };

  const handleRotateSecret = async (clientId: string) => {
    if (!confirm('Rotate client secret? Old secret will stop working immediately.')) return;
    try {
      const res = await adminService.rotateAppSecret(clientId);
      alert(`New secret for ${res.client_id}:\n${res.client_secret}`);
    } catch (e: any) {
      alert(e.message || 'Failed to rotate secret');
    }
  };

  const handleDeleteApp = async (clientId: string) => {
    if (!confirm('Delete (deactivate) this app?')) return;
    try {
      await adminService.deleteApp(clientId);
      await loadApps();
    } catch (e: any) {
      alert(e.message || 'Failed to delete app');
    }
  };

  const handleToggleRedirect = (idx: number, value: string) => {
    const next = [...registerForm.redirect_uris];
    next[idx] = value;
    setRegisterForm({ ...registerForm, redirect_uris: next });
  };

  const addRedirect = () => setRegisterForm({ ...registerForm, redirect_uris: [...registerForm.redirect_uris, ''] });
  const removeRedirect = (idx: number) => setRegisterForm({ ...registerForm, redirect_uris: registerForm.redirect_uris.filter((_, i) => i !== idx) });

  const renderTokenTable = (tokens: TokenInfo[]) => (
    <TokenTable>
      <thead>
        <tr>
          <TableHeader>User</TableHeader>
          <TableHeader>Email</TableHeader>
          <TableHeader>Type</TableHeader>
          <TableHeader>Issued</TableHeader>
          <TableHeader>Expires</TableHeader>
          <TableHeader>Subject</TableHeader>
          <TableHeader>Actions</TableHeader>
        </tr>
      </thead>
      <tbody>
        {tokens.map((token, idx) => (
          <tr key={token.id || `${token.user?.email || 'unknown'}-${token.issued_at || idx}`}>
            <TableCell>{token.user?.name || '—'}</TableCell>
            <TableCell>{token.user?.email || '—'}</TableCell>
            <TableCell>
              <TokenStatus type={token.type || 'Unknown'}>
                {token.type || 'Unknown'}
              </TokenStatus>
            </TableCell>
            <TableCell>{formatDate(token.issued_at)}</TableCell>
            <TableCell>{formatDate(token.expires_at)}</TableCell>
            <TableCell style={{ fontFamily: 'monospace', fontSize: '12px' }}>
              {shorten(token.subject, 20)}
            </TableCell>
            <TableCell>
              <div className="token-actions" style={{ display: 'flex', gap: 8, flexWrap: 'nowrap' }}>
                <button className="button" onClick={() => alert(JSON.stringify(token, null, 2))}>Details</button>
                <button className="button" onClick={async () => {
                  try {
                    const service = token.type === 'Azure' ? adminService.getAzureTokenActivity(token.id) : adminService.getTokenActivity(token.id);
                    const data = await service;
                    alert(JSON.stringify(data, null, 2));
                  } catch (e: any) {
                    alert(e.message || 'Failed to load logs');
                  }
                }}>Logs</button>
                <button className="button danger" onClick={async () => {
                  if (!confirm('Revoke this token?')) return;
                  try {
                    if (token.type === 'Azure') await adminService.removeAzureToken(token.id);
                    else await adminService.removeToken(token.id);
                    fetchTokens();
                  } catch(e:any){ alert(e.message || 'Failed to revoke'); }
                }}>Revoke</button>
              </div>
            </TableCell>
          </tr>
        ))}
      </tbody>
    </TokenTable>
  );

  if (loading) {
    return (
      <Container>
        <LoadingSpinner>Loading admin panel...</LoadingSpinner>
      </Container>
    );
  }

  return (
    <Container>
      <Title>Administration Panel</Title>

      {user && (
        <div style={{ marginBottom: '24px', padding: '12px', backgroundColor: '#f6ffed', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
          <strong>Admin User:</strong> {user.name} ({user.email})
        </div>
      )}

      {error && (
        <ErrorMessage>{error}</ErrorMessage>
      )}

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid var(--border-color)', marginBottom: 16 }}>
        <button
          className="button"
          style={{ width: 'auto', marginRight: 8, backgroundColor: activeTab === 'tokens' ? 'var(--primary-color)' : '#6c757d' }}
          onClick={() => setActiveTab('tokens')}
        >
          Token Management
        </button>
        <button
          className="button"
          style={{ width: 'auto', backgroundColor: activeTab === 'apps' ? 'var(--primary-color)' : '#6c757d' }}
          onClick={() => setActiveTab('apps')}
        >
          App Management
        </button>
      </div>

      {activeTab === 'tokens' && (
        <>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
            <input placeholder="Filter by user, email, subject" value={filterText} onChange={e=>setFilterText(e.target.value)} style={{ flex: 1, padding: 6 }} />
            <select value={sortKey} onChange={e=>setSortKey(e.target.value as any)} style={{ padding: 6 }}>
              <option value="issued_desc">Newest issued</option>
              <option value="issued_asc">Oldest issued</option>
              <option value="expires_soon">Expires soon</option>
              <option value="expires_late">Expires latest</option>
            </select>
            <button className="button" style={{ width: 'auto' }} onClick={fetchTokens}>Refresh</button>
          </div>

          <InfoSection>
            <SectionHeader>
              <h2 style={{ margin: 0 }}>Tokens ({(internalTokens?.total || 0) + (azureTokens?.total || 0)})</h2>
            </SectionHeader>
            <SectionContent>
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
            </SectionContent>
          </InfoSection>
        </>
      )}

      {activeTab === 'apps' && (
      <InfoSection>
        <SectionHeader onClick={() => { setAppsOpen(!appsOpen); if (!apps) loadApps(); }}>
          <h2 style={{ margin: 0 }}>App Management</h2>
          <span style={{ transform: appsOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease', color: 'var(--text-secondary)' }}>▼</span>
        </SectionHeader>
        {appsOpen && (
          <SectionContent>
            <h3 style={{ marginTop: 0 }}>Register New App</h3>
            <form onSubmit={handleRegister} style={{ background: '#f8f9fa', padding: 16, borderRadius: 6, border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'grid', gap: 12, gridTemplateColumns: '1fr 1fr' }}>
                <div>
                  <label>Name</label>
                  <input required value={registerForm.name} onChange={e => setRegisterForm({ ...registerForm, name: e.target.value })} style={{ width: '100%' }} />
                </div>
                <div>
                  <label>Owner Email</label>
                  <input required type="email" value={registerForm.owner_email} onChange={e => setRegisterForm({ ...registerForm, owner_email: e.target.value })} style={{ width: '100%' }} />
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <label>Description</label>
                  <textarea required value={registerForm.description} onChange={e => setRegisterForm({ ...registerForm, description: e.target.value })} style={{ width: '100%' }} />
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <label>Redirect URIs</label>
                  {registerForm.redirect_uris.map((uri, idx) => (
                    <div key={idx} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                      <input type="url" required value={uri} onChange={e => handleToggleRedirect(idx, e.target.value)} style={{ flex: 1 }} />
                      {registerForm.redirect_uris.length > 1 && (
                        <button type="button" className="button secondary" onClick={() => removeRedirect(idx)}>Remove</button>
                      )}
                    </div>
                  ))}
                  <button type="button" className="button secondary" onClick={addRedirect}>Add Redirect URI</button>
                </div>
                <div>
                  <label><input type="checkbox" checked={registerForm.allow_discovery} onChange={e => setRegisterForm({ ...registerForm, allow_discovery: e.target.checked })} /> Allow Endpoint Discovery</label>
                </div>


                <div>
                  <label>Discovery Endpoint (optional)</label>
                  <input type="url" value={registerForm.discovery_endpoint} onChange={e => setRegisterForm({ ...registerForm, discovery_endpoint: e.target.value })} style={{ width: '100%' }} />
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <button type="submit" className="button">Register App</button>
              </div>
            </form>

            <h3>Registered Apps</h3>
            <div>
              {appLoading && <p>Loading apps...</p>}
              {!appLoading && apps && apps.length === 0 && <p>No apps registered yet.</p>}
              {!appLoading && apps && apps.length > 0 && (
                <div style={{ display: 'grid', gap: 16 }}>
                  {apps.map(app => (
                    <div key={app.client_id} style={{ border: '1px solid var(--border-color)', borderRadius: 6, padding: 16, background: '#fafafa' }}>
                      <h4 style={{ marginTop: 0 }}>{app.name}</h4>
                      <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: 8 }}>
                        <div>Client ID:</div><div style={{ wordBreak: 'break-all' }}>{app.client_id}</div>
                        <div>Description:</div><div>{app.description || '—'}</div>
                        <div>Owner:</div><div>{app.owner_email || '—'}</div>
                        <div>Status:</div><div>{app.is_active ? 'Active' : 'Inactive'}</div>
                        <div>Redirect URIs:</div><div>{(app.redirect_uris || []).join(', ') || '—'}</div>
                        <div>Created:</div><div>{formatDate(app.created_at)}</div>
                        {app.allow_discovery && (
                          <>
                            <div>Discovery:</div><div>Enabled {app.discovery_endpoint ? `(Endpoint: ${app.discovery_endpoint})` : ''}</div>
                            {app.last_discovery_at && (
                              <>
                                <div>Last Discovery:</div><div>{formatDate(app.last_discovery_at)}{app.discovery_status ? ` (${app.discovery_status})` : ''}</div>
                              </>
                            )}
                          </>
                        )}
                      </div>
                      <div className="app-actions" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
                        <button className="button" onClick={async()=>{
                          const data = await adminService.getRoleMappings(app.client_id);
                          if (!data.mappings.length) alert('No role mappings configured for this app.');
                          else alert(`Role Mappings for ${data.app_name}:\n\n${data.mappings.map(m=>`AD Group: ${m.ad_group}  Role: ${m.app_role}`).join('\n')}`);
                        }}>Role Mappings</button>
                        {app.allow_discovery && (
                          <>
                            <button className="button" onClick={async()=>{
                              try {
                                // Try to get permission tree first for detailed view
                                const permTree = await adminService.getAppPermissionTree(app.client_id);
                                if (permTree && permTree.permission_tree && Object.keys(permTree.permission_tree).length > 0) {
                                  // Format permission tree for display
                                  let output = `Discovered Resources for ${app.client_id}:\n\n`;
                                  const tree = permTree.permission_tree;
                                  
                                  for (const [resource, actions] of Object.entries(tree as any)) {
                                    output += `${resource}\n`;
                                    for (const [action, details] of Object.entries(actions as any)) {
                                      const fields = details.fields || [];
                                      const sensitiveFields = fields.filter((f: any) => f.sensitive || f.pii || f.phi);
                                      const hasWildcard = fields.some((f: any) => f.field_name === '*');
                                      
                                      output += `  ${action}`;
                                      if (hasWildcard) output += ' (has wildcard *)';
                                      if (sensitiveFields.length > 0) output += ` (${sensitiveFields.length} sensitive fields)`;
                                      output += '\n';
                                      
                                      // Show fields with details
                                      for (const field of fields) {
                                        if (field.field_name !== '*') {
                                          output += `    ${field.field_name}`;
                                          if (field.sensitive || field.pii || field.phi) {
                                            output += 'SENSITIVE';
                                          }
                                          output += '\n';
                                          if (field.description) {
                                            output += `      ${field.description}\n`;
                                          }
                                        }
                                      }
                                    }
                                    output += '\n';
                                  }
                                  alert(output);
                                } else {
                                  // Fallback to basic endpoints
                                  const ep = await adminService.getAppEndpoints(app.client_id);
                                  if (!ep || !ep.endpoints || ep.endpoints.length === 0) {
                                    alert('No endpoints registered for this app.');
                                  } else {
                                    alert(`Endpoints for ${app.client_id}:\n\n${ep.endpoints.map((e:any)=>`${e.method} ${e.path} - ${e.description || ''}${e.discovered ? ' (discovered)' : ''}`).join('\n')}`);
                                  }
                                }
                              } catch (error) {
                                // Fallback to basic endpoints on error
                                try {
                                  const ep = await adminService.getAppEndpoints(app.client_id);
                                  if (!ep || !ep.endpoints || ep.endpoints.length === 0) {
                                    alert('No endpoints registered for this app.');
                                  } else {
                                    alert(`Endpoints for ${app.client_id}:\n\n${ep.endpoints.map((e:any)=>`${e.method} ${e.path} - ${e.description || ''}${e.discovered ? ' (discovered)' : ''}`).join('\n')}`);
                                  }
                                } catch (fallbackError) {
                                  alert('Error fetching endpoint information.');
                                }
                              }
                            }}>View Endpoints</button>
                            <button className="button" onClick={() => {
                              setRolesModal({
                                isOpen: true,
                                clientId: app.client_id,
                                appName: app.name
                              });
                            }}>Roles & Permissions</button>
                            <button className="button secondary" onClick={async()=>{
                              alert('Running discovery...');
                              const res = await adminService.triggerDiscovery(app.client_id);
                              if (res.status === 'success') alert(`Discovery completed! Found ${res.endpoints_discovered} endpoints, stored ${res.endpoints_stored}.`);
                              else if (res.status === 'skipped') alert(res.message);
                              else alert(`Discovery failed: ${res.error || 'unknown error'}`);
                              loadApps();
                            }}>Run Discovery</button>
                          </>
                        )}
                        <button className="button secondary" onClick={()=>handleRotateSecret(app.client_id)}>Rotate Secret</button>
                        <button className="button danger" onClick={()=>handleDeleteApp(app.client_id)}>Delete</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </SectionContent>
        )}
      </InfoSection>
      )}
      
      <RolesModal
        isOpen={rolesModal.isOpen}
        onClose={() => setRolesModal({ isOpen: false, clientId: '', appName: '' })}
        clientId={rolesModal.clientId}
        appName={rolesModal.appName}
      />
    </Container>
  );
};

export default AdminPage;
