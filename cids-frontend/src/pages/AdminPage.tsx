import { useState } from 'react';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import adminService from '../services/adminService';
import type { AppInfo } from '../types/admin';
import RolesModal from '../components/RolesModal';
import APIKeyModal from '../components/APIKeyModal';

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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Apps state
  const [appsOpen, setAppsOpen] = useState(true);
  const [apps, setApps] = useState<AppInfo[] | null>(null);
  const [appLoading, setAppLoading] = useState(false);
  const [rolesModal, setRolesModal] = useState<{ isOpen: boolean; clientId: string; appName: string }>({
    isOpen: false,
    clientId: '',
    appName: ''
  });
  const [apiKeyModal, setApiKeyModal] = useState<{ isOpen: boolean; clientId: string; appName: string }>({
    isOpen: false,
    clientId: '',
    appName: ''
  });
  const [registerForm, setRegisterForm] = useState({
    name: '', 
    description: '', 
    owner_email: '', 
    redirect_uris: [''], 
    allow_discovery: false, 
    discovery_endpoint: '',
    create_api_key: false,
    api_key_name: '',
    api_key_permissions: ''
  });


  const formatDate = (dateString?: string) => {
    try {
      if (!dateString) return '—';
      const d = new Date(dateString);
      return isNaN(d.getTime()) ? '—' : d.toLocaleString();
    } catch {
      return '—';
    }
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
        create_api_key: registerForm.create_api_key,
        api_key_name: registerForm.api_key_name || undefined,
        api_key_permissions: registerForm.api_key_permissions ? 
          registerForm.api_key_permissions.split(',').map(p => p.trim()).filter(p => p) : 
          undefined
      };
      const result = await adminService.createApp(payload);
      
      // Build alert message
      let alertMessage = `App registered successfully!\n\nClient ID: ${result.app.client_id}\nClient Secret: ${result.client_secret}`;
      
      if (result.api_key) {
        alertMessage += `\n\n🔑 API Key Created:\n${result.api_key}\n\n⚠️ SAVE BOTH THE CLIENT SECRET AND API KEY NOW!\nThey won't be shown again.`;
      } else {
        alertMessage += `\n\n⚠️ SAVE THE CLIENT SECRET NOW!\nIt won't be shown again.`;
      }
      
      alert(alertMessage);
      setRegisterForm({ 
        name: '', 
        description: '', 
        owner_email: '', 
        redirect_uris: [''], 
        allow_discovery: false, 
        discovery_endpoint: '',
        create_api_key: false,
        api_key_name: '',
        api_key_permissions: ''
      });
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
                
                <div style={{ gridColumn: '1 / -1', marginTop: 16, padding: 16, background: '#e8f4fd', borderRadius: 6, border: '1px solid #b3d9f2' }}>
                  <h4 style={{ marginTop: 0, marginBottom: 12, color: '#0066cc' }}>🔑 Initial API Key (Optional)</h4>
                  <div style={{ marginBottom: 12 }}>
                    <label>
                      <input 
                        type="checkbox" 
                        checked={registerForm.create_api_key} 
                        onChange={e => setRegisterForm({ ...registerForm, create_api_key: e.target.checked })} 
                      /> 
                      Create an API key during registration (eliminates chicken-egg problem!)
                    </label>
                  </div>
                  
                  {registerForm.create_api_key && (
                    <>
                      <div style={{ marginBottom: 12 }}>
                        <label>API Key Name (optional)</label>
                        <input 
                          type="text" 
                          placeholder="e.g., Initial Key, Development Key" 
                          value={registerForm.api_key_name} 
                          onChange={e => setRegisterForm({ ...registerForm, api_key_name: e.target.value })} 
                          style={{ width: '100%' }} 
                        />
                        <small style={{ color: '#666' }}>Leave empty for default name</small>
                      </div>
                      
                      <div>
                        <label>API Key Permissions (comma-separated)</label>
                        <input 
                          type="text" 
                          placeholder="e.g., admin, read:users, write:data" 
                          value={registerForm.api_key_permissions} 
                          onChange={e => setRegisterForm({ ...registerForm, api_key_permissions: e.target.value })} 
                          style={{ width: '100%' }} 
                        />
                        <small style={{ color: '#666' }}>Leave empty for 'admin' permission. Use 'admin' for full access during development.</small>
                      </div>
                    </>
                  )}
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
                        <button className="button" style={{ backgroundColor: '#17a2b8', color: 'white' }} onClick={() => {
                          setApiKeyModal({
                            isOpen: true,
                            clientId: app.client_id,
                            appName: app.name
                          });
                        }}>API Keys</button>
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
      
      <RolesModal
        isOpen={rolesModal.isOpen}
        onClose={() => setRolesModal({ isOpen: false, clientId: '', appName: '' })}
        clientId={rolesModal.clientId}
        appName={rolesModal.appName}
      />
      
      <APIKeyModal
        isOpen={apiKeyModal.isOpen}
        onClose={() => setApiKeyModal({ isOpen: false, clientId: '', appName: '' })}
        clientId={apiKeyModal.clientId}
        appName={apiKeyModal.appName}
      />
    </Container>
  );
};

export default AdminPage;
