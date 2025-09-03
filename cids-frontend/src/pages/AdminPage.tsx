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
  const [discoveryStatus, setDiscoveryStatus] = useState<Record<string, 'running' | 'success' | 'error' | 'cached' | 'unknown'>>({});

  const [editModal, setEditModal] = useState({
    isOpen: false,
    app: null as AppInfo | null
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
                      else alert(`Role Mappings for ${data.app_name}:\n\n${data.mappings.map(m=>`AD Group: ${m.ad_group}  Role: ${m.app_role}`).join('\n')}`);
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
                          setApiKeyModal({
                            isOpen: true,
                            clientId: app.client_id,
                            appName: app.name
                          });
                        }}>A2A Roles & Permissions</button>
                        <button className="button" onClick={() => {
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
                              const res = await adminService.triggerDiscovery(app.client_id, false);
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
                              } else if (res && res.status === 'cached') {
                                setDiscoveryStatus(prev => ({ ...prev, [app.client_id]: 'cached' }));
                                alert(`📋 Using cached discovery data\n\n${res.message}\n\nCache age: ${res.cache_age_minutes || 0} minutes`);
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
                            {discoveryStatus[app.client_id] === 'running' ? '🔄 Running...' : '🔍 Run Discovery'}
                          </button>

                          <button className="button secondary" onClick={async()=>{
                            try {
                              const res = await adminService.triggerDiscovery(app.client_id, true);
                              console.log('Force discovery response:', res);

                              if (res && res.status === 'success') {
                                alert(`✅ Force discovery completed!\n\n` +
                                      `📊 Results:\n` +
                                      `• Endpoints discovered: ${res.endpoints_discovered}\n` +
                                      `• Permissions generated: ${res.permissions_generated || 0}\n` +
                                      `• Response time: ${res.response_time_ms || 0}ms`);
                              } else if (res && res.status === 'error') {
                                const errorType = res.error_type ? ` (${res.error_type})` : '';
                                alert(`❌ Force discovery failed${errorType}\n\nError: ${res.error}`);
                              }
                              await loadApps();
                            } catch (error) {
                              console.error('Force discovery error:', error);
                              alert(`❌ Force discovery failed: ${error.message || 'unknown error'}`);
                            }
                          }} title="Force discovery (ignore cache)">
                            🔄 Force
                          </button>

                          <button className="button secondary" onClick={async()=>{
                            try {
                              const history = await adminService.getDiscoveryHistory(app.client_id);
                              const recentAttempts = history.recent_attempts || [];
                              const lastSuccess = history.last_successful_discovery ?
                                new Date(history.last_successful_discovery).toLocaleString() : 'Never';

                              let message = `📈 Discovery History for ${history.app_name}\n\n`;
                              message += `📊 Statistics:\n`;
                              message += `• Total attempts: ${history.total_attempts}\n`;
                              message += `• Success rate: ${(history.success_rate * 100).toFixed(1)}%\n`;
                              message += `• Last success: ${lastSuccess}\n\n`;

                              if (recentAttempts.length > 0) {
                                message += `🕒 Recent attempts (last ${Math.min(recentAttempts.length, 5)}):\n`;
                                recentAttempts.slice(-5).reverse().forEach((attempt, i) => {
                                  const timestamp = new Date(attempt.timestamp).toLocaleString();
                                  const status = attempt.success ? '✅' : '❌';
                                  const error = attempt.error_message ? ` - ${attempt.error_message}` : '';
                                  message += `${status} ${timestamp}${error}\n`;
                                });
                              }

                              alert(message);
                            } catch (error) {
                              console.error('History error:', error);
                              alert(`❌ Failed to load history: ${error.message || 'unknown error'}`);
                            }
                          }} title="View discovery history">
                            📈 History
                          </button>

                          {app.discovery_endpoint && (
                            <button className="button secondary" onClick={async()=>{
                              try {
                                const result = await adminService.testDiscoveryEndpoint(app.discovery_endpoint);

                                if (result.status === 'success') {
                                  alert(`✅ Discovery endpoint test passed!\n\n` +
                                        `📊 Results:\n` +
                                        `• App name: ${result.app_name}\n` +
                                        `• Endpoints found: ${result.endpoints_found}\n` +
                                        `• Services found: ${result.services_found}\n` +
                                        `• Discovery version: ${result.discovery_version}\n` +
                                        `• Health check: ${result.health_check?.healthy ? '✅ Healthy' : '❌ Unhealthy'}`);
                                } else {
                                  const stage = result.stage ? ` (${result.stage})` : '';
                                  const errorType = result.error_type ? ` [${result.error_type}]` : '';
                                  alert(`❌ Discovery endpoint test failed${stage}${errorType}\n\nError: ${result.error}`);
                                }
                              } catch (error) {
                                console.error('Test endpoint error:', error);
                                alert(`❌ Endpoint test failed: ${error.message || 'unknown error'}`);
                              }
                            }} title="Test discovery endpoint">
                              🧪 Test
                            </button>
                          )}
                        </div>
                      </>
                    )}
                    <button className="button" onClick={()=>handleEditApp(app)}>Edit</button>
                    <button className="button secondary" onClick={()=>handleRotateSecret(app.client_id)}>Rotate Secret</button>
                    <button className="button danger" onClick={()=>handleDeleteApp(app.client_id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionContent>
      </InfoSection>

      {/* Discovery Statistics Section */}
      <InfoSection>
        <SectionHeader style={{ cursor: 'default', borderBottom: '1px solid var(--border-color)' }}>
          <h2 style={{ margin: 0 }}>🔍 Discovery Statistics</h2>
        </SectionHeader>
        <SectionContent>
          <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
            <button className="button secondary" onClick={async () => {
              try {
                const stats = await adminService.getDiscoveryStatistics();
                const message = `📊 Discovery Statistics\n\n` +
                              `• Total apps: ${stats.total_apps}\n` +
                              `• Total attempts: ${stats.total_attempts}\n` +
                              `• Overall success rate: ${(stats.overall_success_rate * 100).toFixed(1)}%\n` +
                              `• Apps with recent success: ${stats.apps_with_recent_success}\n` +
                              `• Apps with failures: ${stats.apps_with_failures}\n` +
                              `• Average response time: ${stats.average_response_time_ms?.toFixed(0) || 0}ms`;
                alert(message);
              } catch (error) {
                console.error('Stats error:', error);
                alert(`❌ Failed to load statistics: ${error.message || 'unknown error'}`);
              }
            }}>
              📊 View Statistics
            </button>

            <button className="button secondary" onClick={async () => {
              try {
                const active = await adminService.getActiveDiscoveries();
                const discoveries = active.active_discoveries || {};
                const count = Object.keys(discoveries).length;

                if (count === 0) {
                  alert('✅ No active discoveries');
                  return;
                }

                let message = `🔄 Active Discoveries (${count})\n\n`;
                Object.entries(discoveries).forEach(([appId, progress]: [string, any]) => {
                  message += `• ${appId}: ${progress.current_step} (${progress.progress_percentage}%)\n`;
                  if (progress.error_message) {
                    message += `  ❌ Error: ${progress.error_message}\n`;
                  }
                });

                alert(message);
              } catch (error) {
                console.error('Active discoveries error:', error);
                alert(`❌ Failed to load active discoveries: ${error.message || 'unknown error'}`);
              }
            }}>
              🔄 Active Discoveries
            </button>

            <button className="button" onClick={async () => {
              if (!apps) return;

              const appIds = apps.filter(app => app.allow_discovery).map(app => app.client_id);
              if (appIds.length === 0) {
                alert('❌ No apps with discovery enabled');
                return;
              }

              const confirmed = confirm(`🚀 Run batch discovery on ${appIds.length} apps?\n\nThis will discover endpoints for all apps with discovery enabled.`);
              if (!confirmed) return;

              try {
                const result = await adminService.batchDiscovery(appIds, false);
                const summary = result.summary;

                let message = `📊 Batch Discovery Results\n\n`;
                message += `• Total apps: ${summary.total}\n`;
                message += `• Successful: ${summary.successful}\n`;
                message += `• Failed: ${summary.failed}\n`;
                message += `• Cached: ${summary.cached}\n`;
                message += `• Success rate: ${(summary.success_rate * 100).toFixed(1)}%\n\n`;

                if (summary.failed > 0) {
                  message += `❌ Failed apps:\n`;
                  Object.entries(result.batch_results).forEach(([appId, res]: [string, any]) => {
                    if (res.status === 'error') {
                      message += `• ${appId}: ${res.error}\n`;
                    }
                  });
                }

                alert(message);
                await loadApps();
              } catch (error) {
                console.error('Batch discovery error:', error);
                alert(`❌ Batch discovery failed: ${error.message || 'unknown error'}`);
              }
            }}>
              🚀 Batch Discovery
            </button>
          </div>
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
    </Container>
  );
};

export default AdminPage;