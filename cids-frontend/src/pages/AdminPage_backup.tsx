import { useState, useEffect } from 'react';
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


// Component to display structured endpoints data
const EndpointsDisplay: React.FC<{ data: string }> = ({ data }) => {
  // If it's an error message, show it simply
  if (data.includes('No discovered endpoints') || data.includes('Error fetching')) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
        <div style={{ fontSize: '16px', marginBottom: '8px' }}>📭</div>
        <div>{data}</div>
      </div>
    );
  }

  try {
    // Parse the structured data
    const lines = data.split('\n').filter(line => line.trim());
    const resources: { [key: string]: { actions: { [key: string]: { fields: any[], sensitiveCount: number, hasWildcard: boolean } } } } = {};

    let currentResource = '';
    let currentAction = '';

    for (const line of lines) {
      if (line.startsWith('Discovered Resources for')) continue;

      if (!line.startsWith('  ') && !line.startsWith('    ')) {
        // This is a resource name
        currentResource = line.trim();
        if (!resources[currentResource]) {
          resources[currentResource] = { actions: {} };
        }
      } else if (line.startsWith('  ') && !line.startsWith('    ')) {
        // This is an action
        const actionLine = line.trim();
        const match = actionLine.match(/^(\w+)(?:\s+\((\d+)\s+sensitive fields\))?(?:\s+\(has wildcard \*\))?/);
        if (match && currentResource) {
          currentAction = match[1];
          const sensitiveCount = match[2] ? parseInt(match[2]) : 0;
          const hasWildcard = actionLine.includes('has wildcard');

          if (!resources[currentResource]) {
            resources[currentResource] = { actions: {} };
          }
          if (!resources[currentResource].actions[currentAction]) {
            resources[currentResource].actions[currentAction] = {
              fields: [],
              sensitiveCount,
              hasWildcard
            };
          }
        }
      } else if (line.startsWith('    ') && currentResource && currentAction) {
        // This is a field
        const fieldLine = line.trim();
        if (!fieldLine.startsWith('  ')) { // Skip description lines
          const isSensitive = fieldLine.includes('SENSITIVE');
          const fieldName = fieldLine.replace(' SENSITIVE', '');

          if (resources[currentResource] && resources[currentResource].actions[currentAction]) {
            resources[currentResource].actions[currentAction].fields.push({
              name: fieldName,
              sensitive: isSensitive
            });
          }
        }
      }
    }

    return (
      <div style={{ padding: '0' }}>
        {Object.entries(resources).map(([resourceName, resource]) => (
          <div key={resourceName} style={{ marginBottom: '24px' }}>
            <div style={{
              backgroundColor: '#f8f9fa',
              padding: '12px 20px',
              borderLeft: '4px solid #007bff',
              marginBottom: '12px',
              fontWeight: '600',
              fontSize: '16px',
              color: '#333'
            }}>
              {resourceName || '/ (Root)'}
            </div>

            {Object.entries(resource.actions).map(([actionName, action]) => (
              <div key={actionName} style={{ marginBottom: '16px', marginLeft: '20px' }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  marginBottom: '8px',
                  padding: '8px 12px',
                  backgroundColor: '#e3f2fd',
                  borderRadius: '4px',
                  border: '1px solid #bbdefb'
                }}>
                  <span style={{
                    fontWeight: '500',
                    color: '#1976d2',
                    textTransform: 'uppercase',
                    fontSize: '14px',
                    letterSpacing: '0.5px'
                  }}>
                    {actionName}
                  </span>

                  {action.sensitiveCount > 0 && (
                    <span style={{
                      backgroundColor: '#fff3cd',
                      color: '#856404',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: '500',
                      border: '1px solid #ffeaa7'
                    }}>
                      {action.sensitiveCount} sensitive field{action.sensitiveCount !== 1 ? 's' : ''}
                    </span>
                  )}

                  {action.hasWildcard && (
                    <span style={{
                      backgroundColor: '#d1ecf1',
                      color: '#0c5460',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: '500',
                      border: '1px solid #bee5eb'
                    }}>
                      has wildcard *
                    </span>
                  )}
                </div>

                {action.fields.length > 0 && (
                  <div style={{ marginLeft: '12px' }}>
                    {action.fields.map((field, idx) => (
                      <div key={idx} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '6px 12px',
                        marginBottom: '4px',
                        backgroundColor: field.sensitive ? '#fff5f5' : '#f9f9f9',
                        borderRadius: '3px',
                        border: field.sensitive ? '1px solid #fed7d7' : '1px solid #e2e8f0',
                        fontSize: '14px'
                      }}>
                        <code style={{
                          fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                          fontSize: '13px',
                          color: '#2d3748',
                          backgroundColor: 'transparent'
                        }}>
                          {field.name}
                        </code>

                        {field.sensitive && (
                          <span style={{
                            backgroundColor: '#fed7d7',
                            color: '#c53030',
                            padding: '1px 6px',
                            borderRadius: '8px',
                            fontSize: '11px',
                            fontWeight: '600',
                            textTransform: 'uppercase',
                            letterSpacing: '0.3px'
                          }}>
                            SENSITIVE
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  } catch (error) {
    console.error('Error parsing endpoints data:', error);
    // Fallback to simple text display
    return (
      <div style={{ padding: '20px' }}>
        <div style={{ marginBottom: '16px', color: '#666', fontSize: '14px' }}>
          ⚠️ Could not parse structured data. Showing raw output:
        </div>
        <pre style={{
          margin: 0,
          fontFamily: 'Monaco, Consolas, "Courier New", monospace',
          fontSize: '13px',
          lineHeight: '1.4',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          backgroundColor: '#f8f9fa',
          padding: '16px',
          borderRadius: '4px',
          border: '1px solid #e0e0e0'
        }}>
          {data}
        </pre>
      </div>
    );
  }
};

const AdminPage: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Apps state
  const [registrationOpen, setRegistrationOpen] = useState(false);
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

  // Discovery status tracking
  const [discoveryStatus, setDiscoveryStatus] = useState<Record<string, 'running' | 'success' | 'error' | 'unknown'>>({});

  const [editModal, setEditModal] = useState({
    isOpen: false,
    app: null as AppInfo | null
  });

  const [endpointsModal, setEndpointsModal] = useState<{isOpen: boolean, clientId: string, appName: string, data: string}>({
    isOpen: false,
    clientId: '',
    appName: '',
    data: ''
  });

  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    redirect_uris: [''],
    allow_discovery: false,
    discovery_endpoint: ''
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

  // Load apps when component mounts
  useEffect(() => {
    loadApps();
  }, []);

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



  const handleDeleteApp = async (clientId: string) => {
    if (!confirm('Delete (deactivate) this app?')) return;
    try {
      await adminService.deleteApp(clientId);
      await loadApps();
    } catch (e: any) {
      alert(e.message || 'Failed to delete app');
    }
  };

  const handleEditApp = (app: AppInfo) => {
    setEditForm({
      name: app.name,
      description: app.description || '',
      redirect_uris: app.redirect_uris && app.redirect_uris.length > 0 ? app.redirect_uris : [''],
      allow_discovery: app.allow_discovery || false,
      discovery_endpoint: app.discovery_endpoint || ''
    });
    setEditModal({ isOpen: true, app });
  };

  const handleUpdateApp = async (e: any) => {
    e.preventDefault();
    if (!editModal.app) return;

    try {
      const payload = {
        name: editForm.name,
        description: editForm.description,
        redirect_uris: editForm.redirect_uris.filter(u => u && u.trim().length > 0),
        allow_discovery: editForm.allow_discovery,
        discovery_endpoint: editForm.discovery_endpoint || null
      };

      await adminService.updateApp(editModal.app.client_id, payload);
      alert('App updated successfully!');
      setEditModal({ isOpen: false, app: null });
      await loadApps();
    } catch (e: any) {
      alert(e.message || 'Failed to update app');
    }
  };

  const handleEditRedirectChange = (index: number, value: string) => {
    const newUris = [...editForm.redirect_uris];
    newUris[index] = value;
    setEditForm({ ...editForm, redirect_uris: newUris });
  };

  const handleAddEditRedirect = () => {
    setEditForm({ ...editForm, redirect_uris: [...editForm.redirect_uris, ''] });
  };

  const handleRemoveEditRedirect = (index: number) => {
    if (editForm.redirect_uris.length > 1) {
      const newUris = editForm.redirect_uris.filter((_, i) => i !== index);
      setEditForm({ ...editForm, redirect_uris: newUris });
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

      {/* Registered Apps Section */}
      <InfoSection>
        <SectionHeader style={{ cursor: 'default', borderBottom: '1px solid var(--border-color)' }}>
          <h2 style={{ margin: 0 }}>Registered Applications</h2>
        </SectionHeader>
        <SectionContent>
          {appLoading && <p>Loading apps...</p>}
          {!appLoading && apps && apps.length === 0 && <p>No apps registered yet.</p>}
          {!appLoading && apps && apps.length > 0 && (
            <div style={{ display: 'grid', gap: 16 }}>
              {apps.map(app => (
                <div key={app.client_id} style={{ 
                  border: '1px solid var(--border-color)', 
                  borderRadius: 6, 
                  padding: 16, 
                  background: '#fafafa',
                  display: 'flex',
                  gap: '16px'
                }}>
                  {/* Content Area - Left Side */}
                  <div style={{ flex: 1 }}>
                    <h4 style={{ marginTop: 0, marginBottom: 16, textAlign: 'left' }}>{app.name}</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: '150px 1fr', gap: 8, alignItems: 'start' }}>
                      <div style={{ textAlign: 'left', fontWeight: '500' }}>Client ID:</div>
                      <div style={{ wordBreak: 'break-all', textAlign: 'left' }}>{app.client_id}</div>
                      
                      <div style={{ textAlign: 'left', fontWeight: '500' }}>Description:</div>
                      <div style={{ textAlign: 'left' }}>{app.description || '—'}</div>
                      
                      <div style={{ textAlign: 'left', fontWeight: '500' }}>Owner:</div>
                      <div style={{ textAlign: 'left' }}>{app.owner_email || '—'}</div>
                      
                      <div style={{ textAlign: 'left', fontWeight: '500' }}>Status:</div>
                      <div style={{ textAlign: 'left' }}>{app.is_active ? 'Active' : 'Inactive'}</div>
                      
                      <div style={{ textAlign: 'left', fontWeight: '500' }}>Redirect URIs:</div>
                      <div style={{ textAlign: 'left' }}>{(app.redirect_uris || []).join(', ') || '—'}</div>
                      
                      <div style={{ textAlign: 'left', fontWeight: '500' }}>Created:</div>
                      <div style={{ textAlign: 'left' }}>{formatDate(app.created_at)}</div>
                      
                      {app.allow_discovery && (
                        <>
                          <div style={{ textAlign: 'left', fontWeight: '500' }}>Discovery:</div>
                          <div style={{ textAlign: 'left' }}>Enabled {app.discovery_endpoint ? `(Endpoint: ${app.discovery_endpoint})` : ''}</div>
                          {app.last_discovery_at && (
                            <>
                              <div style={{ textAlign: 'left', fontWeight: '500' }}>Last Discovery:</div>
                              <div style={{ textAlign: 'left' }}>{formatDate(app.last_discovery_at)}{app.discovery_status ? ` (${app.discovery_status})` : ''}</div>
                            </>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                  
                  {/* Action Buttons - Right Side */}
                  <div style={{ 
                    display: 'flex', 
                    flexDirection: 'column', 
                    gap: 8, 
                    minWidth: '160px',
                    alignItems: 'stretch'
                  }}>
                    <button className="button secondary" style={{ fontSize: '12px', padding: '6px 12px' }} onClick={async()=>{
                      const data = await adminService.getRoleMappings(app.client_id);
                      if (!data.mappings.length) alert('No role mappings configured for this app.');
                      else alert(`Role Mappings for ${data.app_name}:\n\n${data.mappings.map(m=>`AD Group: ${m.ad_group}  Role: ${m.app_role}`).join('\n')}`);
                    }}>Role Mappings</button>
                    {app.allow_discovery && (
                      <>
                        <button className="button secondary" style={{ fontSize: '12px', padding: '6px 12px' }} onClick={async()=>{
                          try {
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
                                  const hasWildcard = fields.some((f: any) => f.field_path === '*');

                                  output += `  ${action}`;
                                  if (hasWildcard) output += ' (has wildcard *)';
                                  if (sensitiveFields.length > 0) output += ` (${sensitiveFields.length} sensitive fields)`;
                                  output += '\n';

                                  // Show fields with details
                                  for (const field of fields) {
                                    if (field.field_path !== '*') {
                                      output += `    ${field.field_path}`;
                                      if (field.sensitive || field.pii || field.phi) {
                                        output += ' SENSITIVE';
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
                              setEndpointsModal({
                                isOpen: true,
                                clientId: app.client_id,
                                appName: app.name,
                                data: output
                              });
                            } else {
                              setEndpointsModal({
                                isOpen: true,
                                clientId: app.client_id,
                                appName: app.name,
                                data: 'No discovered endpoints found for this app. Run discovery first.'
                              });
                            }
                          } catch (error) {
                            console.error('Error fetching permission tree:', error);
                            setEndpointsModal({
                              isOpen: true,
                              clientId: app.client_id,
                              appName: app.name,
                              data: 'Error fetching discovered endpoints. Run discovery first.'
                            });
                          }
                        }}>View Endpoints</button>
                        <button className="button secondary" onClick={() => {
                          setApiKeyModal({
                            isOpen: true,
                            clientId: app.client_id,
                            appName: app.name
                          });
                        }}>A2A Roles & Permissions</button>
                        <button className="button secondary" onClick={() => {
                          setRolesModal({
                            isOpen: true,
                            clientId: app.client_id,
                            appName: app.name
                          });
                        }}>User Roles & Permissions</button>

                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          <button className="button secondary" onClick={async()=>{
                            try {
                              setDiscoveryStatus(prev => ({ ...prev, [app.client_id]: 'running' }));
                              const res = await adminService.triggerDiscovery(app.client_id, true);
                              console.log('Discovery response:', res);

                              if (res && res.status === 'success') {
                                setDiscoveryStatus(prev => ({ ...prev, [app.client_id]: 'success' }));
                                alert(`✅ Discovery completed successfully!\n\n` +
                                      `📊 Results:\n` +
                                      `• Endpoints discovered: ${res.endpoints_discovered}\n` +
                                      `• Endpoints stored: ${res.endpoints_stored}\n` +
                                      `• Permissions generated: ${res.permissions_generated || 0}\n` +
                                      `• Response time: ${res.response_time_ms || 0}ms\n` +
                                      `• Discovery version: ${res.discovery_version || 'N/A'}`);

                              } else if (res && res.status === 'error') {
                                setDiscoveryStatus(prev => ({ ...prev, [app.client_id]: 'error' }));
                                const errorType = res.error_type ? ` (${res.error_type})` : '';
                                const responseTime = res.response_time_ms ? `\nResponse time: ${res.response_time_ms}ms` : '';
                                alert(`❌ Discovery failed${errorType}\n\nError: ${res.error}${responseTime}`);
                              } else {
                                setDiscoveryStatus(prev => ({ ...prev, [app.client_id]: 'unknown' }));
                                alert(`❓ Unexpected response: ${JSON.stringify(res)}`);
                              }
                              await loadApps();
                            } catch (error) {
                              console.error('Discovery error:', error);
                              setDiscoveryStatus(prev => ({ ...prev, [app.client_id]: 'error' }));
                              alert(`❌ Discovery failed: ${error.message || 'unknown error'}`);
                            }
                          }} disabled={discoveryStatus[app.client_id] === 'running'}>
                            {discoveryStatus[app.client_id] === 'running' ? 'Running...' : 'Run Discovery'}
                          </button>






                        </div>
                      </>
                    )}
                    <button className="button secondary" onClick={()=>handleEditApp(app)}>Edit</button>
                    <button className="button danger" onClick={()=>handleDeleteApp(app.client_id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionContent>
      </InfoSection>



      {/* App Registration Section */}
      <InfoSection>
        <SectionHeader onClick={() => setRegistrationOpen(!registrationOpen)}>
          <h2 style={{ margin: 0 }}>App Registration</h2>
          <span style={{ transform: registrationOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease', color: 'var(--text-secondary)' }}>▼</span>
        </SectionHeader>
        {registrationOpen && (
          <SectionContent>
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
          </SectionContent>
        )}
      </InfoSection>

      {/* Edit App Modal */}
      {editModal.isOpen && editModal.app && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: 8,
            padding: 24,
            maxWidth: 600,
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <h3 style={{ marginTop: 0 }}>Edit App: {editModal.app.name}</h3>
            <form onSubmit={handleUpdateApp}>
              <div style={{ display: 'grid', gap: 16 }}>
                <div>
                  <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Name</label>
                  <input
                    required
                    value={editForm.name}
                    onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                    style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Description</label>
                  <textarea
                    required
                    value={editForm.description}
                    onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                    style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4, minHeight: 80 }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Redirect URIs</label>
                  {editForm.redirect_uris.map((uri, idx) => (
                    <div key={idx} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                      <input
                        type="url"
                        required
                        value={uri}
                        onChange={e => handleEditRedirectChange(idx, e.target.value)}
                        style={{ flex: 1, padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                      />
                      {editForm.redirect_uris.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveEditRedirect(idx)}
                          style={{ padding: '8px 12px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: 4 }}
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={handleAddEditRedirect}
                    style={{ padding: '8px 16px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: 4 }}
                  >
                    Add URI
                  </button>
                </div>

                <div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input
                      type="checkbox"
                      checked={editForm.allow_discovery}
                      onChange={e => setEditForm({ ...editForm, allow_discovery: e.target.checked })}
                    />
                    Enable Discovery
                  </label>
                </div>

                {editForm.allow_discovery && (
                  <div>
                    <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>Discovery Endpoint</label>
                    <input
                      type="url"
                      value={editForm.discovery_endpoint}
                      onChange={e => setEditForm({ ...editForm, discovery_endpoint: e.target.value })}
                      style={{ width: '100%', padding: 8, border: '1px solid #ddd', borderRadius: 4 }}
                      placeholder="http://localhost:5001/discovery/endpoints"
                    />
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: 12, marginTop: 24, justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => setEditModal({ isOpen: false, app: null })}
                  style={{ padding: '8px 16px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: 4 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ padding: '8px 16px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: 4 }}
                >
                  Update App
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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

      {/* Endpoints Modal */}
      {endpointsModal.isOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '24px',
            maxWidth: '900px',
            maxHeight: '85vh',
            width: '95%',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '20px',
              borderBottom: '2px solid #e0e0e0',
              paddingBottom: '16px'
            }}>
              <h2 style={{ margin: 0, color: '#333', fontSize: '20px', fontWeight: '600' }}>
                Discovered Endpoints - {endpointsModal.appName}
              </h2>
              <button
                onClick={() => setEndpointsModal({ isOpen: false, clientId: '', appName: '', data: '' })}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '24px',
                  cursor: 'pointer',
                  color: '#666',
                  padding: '4px',
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: '4px'
                }}
                onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f0f0f0'}
                onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
              >
                ×
              </button>
            </div>
            <div style={{
              flex: 1,
              overflow: 'auto',
              backgroundColor: '#fafafa',
              borderRadius: '6px',
              border: '1px solid #e0e0e0'
            }}>
              <EndpointsDisplay data={endpointsModal.data} />
            </div>
            <div style={{
              marginTop: '20px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '12px'
            }}>
              <button
                className="button secondary"
                onClick={async () => {
                  try {
                    // Get the raw permission tree data from the API
                    const permTree = await adminService.getAppPermissionTree(endpointsModal.clientId);

                    // Create the JSON export
                    const exportData = {
                      app_id: endpointsModal.clientId,
                      app_name: endpointsModal.appName,
                      exported_at: new Date().toISOString(),
                      permission_tree: permTree?.permission_tree || {},
                      raw_permissions: permTree || {}
                    };

                    // Create and download the file
                    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
                      type: 'application/json'
                    });
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = `${endpointsModal.appName}_endpoints_${new Date().toISOString().split('T')[0]}.json`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                  } catch (error) {
                    console.error('Export error:', error);
                    alert('Failed to export endpoints data');
                  }
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                📥 Export to JSON
              </button>

              <button
                className="button secondary"
                onClick={() => setEndpointsModal({ isOpen: false, clientId: '', appName: '', data: '' })}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </Container>
  );
};

export default AdminPage;