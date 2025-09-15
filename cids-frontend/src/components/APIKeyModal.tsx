import { useState, useEffect } from 'react';
import styled from 'styled-components';
import adminService from '../services/adminService';
import type { APIKey, APIKeyCreationResponse } from '../types/admin';
import apiService from '../services/api';


const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 8px;
  padding: 24px;
  max-width: 900px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
`;

const ModalHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e8e8e8;
`;

const ModalTitle = styled.h2`
  margin: 0;
  color: #333;
  font-size: 20px;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    color: #333;
  }
`;

const Section = styled.div`
  margin-bottom: 24px;
`;

const SectionTitle = styled.h3`
  margin: 0 0 16px 0;
  color: #333;
  font-size: 16px;
`;

const FormSection = styled.div`
  background: #f8f9fa;
  padding: 20px;
  border-radius: 6px;
  margin-bottom: 20px;
`;

const FormGroup = styled.div`
  margin-bottom: 16px;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #333;
  font-size: 14px;
`;

const Input = styled.input`
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;

  &:focus {
    outline: none;
    border-color: #40a9ff;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
  }
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  min-height: 60px;
  resize: vertical;

  &:focus {
    outline: none;
    border-color: #40a9ff;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
  }
`;

const Select = styled.select`
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  background: white;

  &:focus {
    outline: none;
    border-color: #40a9ff;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
  }
`;

const Button = styled.button`
  padding: 8px 16px;
  border-radius: 4px;
  border: none;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const PrimaryButton = styled(Button)`
  background: #52c41a;
  color: white;

  &:hover:not(:disabled) {
    background: #73d13d;
  }
`;

const DangerButton = styled(Button)`
  background: #ff4d4f;
  color: white;
  margin-left: 8px;

  &:hover:not(:disabled) {
    background: #ff7875;
  }
`;

const SecondaryButton = styled(Button)`
  background: #ffc107;
  color: #333;
  margin-left: 8px;

  &:hover:not(:disabled) {
    background: #ffca28;
  }
`;

const KeyDisplay = styled.div`
  background: #d4edda;
  border: 1px solid #c3e6cb;
  padding: 16px;
  border-radius: 6px;
  margin-bottom: 20px;
`;

const KeyValue = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
`;

const KeyCode = styled.code`
  flex: 1;
  padding: 8px 12px;
  background: white;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  word-break: break-all;
`;

const CopyButton = styled(Button)`
  background: #1890ff;
  color: white;

  &:hover:not(:disabled) {
    background: #40a9ff;
  }
`;
// Inline editor for A2A mappings
const Row = styled.div`
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
  flex-wrap: wrap;
`;

const SmallButton = styled(Button)`
  background: #1890ff;
  color: white;
  &:hover:not(:disabled) { background: #40a9ff; }
`;

interface MappingRow { appId: string; role: string; }

const A2AMappingsEditor: React.FC<{ callerId: string }>=({ callerId })=>{
  const [apps, setApps] = useState<{ client_id: string; name: string }[]>([]);
  const [rows, setRows] = useState<MappingRow[]>([]);
  const [rolesByApp, setRolesByApp] = useState<Record<string, string[]>>({});
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(()=>{
    (async()=>{
      try {
        setLoading(true);
        const allApps = await adminService.getApps();
        setApps(allApps.map(a=>({ client_id: a.client_id, name: a.name })));
        const mapping = await adminService.getA2ARoleMappings(callerId);
        // Flatten mapping to rows (one role per row)
        const flat: MappingRow[] = [];
        for (const [appId, roleList] of Object.entries(mapping)){
          for (const r of roleList){ flat.push({ appId, role: r }); }
        }
        setRows(flat.length ? flat : [{ appId: '', role: '' }]);
        // Preload roles for any apps present so the role dropdown shows existing selections
        const uniqueAppIds = Array.from(new Set(flat.map(r => r.appId).filter(a => !!a)));
        await Promise.all(uniqueAppIds.map(async (aid) => {
          try {
            const roles = await adminService.getAppRoles(aid);
            setRolesByApp(prev => ({ ...prev, [aid]: roles }));
          } catch (e:any) {
            console.error('Failed to preload roles for app', aid, e);
          }
        }));
      } catch(e:any) {
        console.error('Failed to load A2A mappings', e);
        setRows([{ appId: '', role: '' }]);
      } finally { setLoading(false); }
    })();
  }, [callerId]);

  const ensureRolesLoaded = async (appId: string)=>{
    if (!appId || rolesByApp[appId]) return;
    try {
      const roles = await adminService.getAppRoles(appId);
      setRolesByApp(prev=>({ ...prev, [appId]: roles }));
    } catch(e:any){
      console.error('Failed to load roles for app', appId, e);
      setRolesByApp(prev=>({ ...prev, [appId]: [] }));
    }
  };

  const updateRowApp = async (idx: number, appId: string)=>{
    const copy = [...rows];
    copy[idx] = { appId, role: '' };
    setRows(copy);
    await ensureRolesLoaded(appId);
  };

  const updateRowRole = (idx: number, role: string)=>{
    const copy = [...rows];
    copy[idx] = { ...copy[idx], role };
    setRows(copy);
  };

  const addRow = ()=> setRows(prev=>[...prev, { appId: '', role: '' }]);
  const removeRow = (i:number)=> setRows(prev=> prev.filter((_,idx)=> idx!==i));

  const save = async ()=>{
    try {
      setSaving(true);
      // Build mapping: appId -> list of roles (dedup)
      const mapping: Record<string, string[]> = {};
      for (const r of rows){
        if (!r.appId || !r.role) continue;
        mapping[r.appId] = mapping[r.appId] || [];
        if (!mapping[r.appId].includes(r.role)) mapping[r.appId].push(r.role);
      }
      await adminService.putA2ARoleMappings(callerId, mapping);
      alert('A2A mappings saved');
    } catch(e:any){
      alert('Failed to save A2A mappings: ' + (e.message || 'Unknown error'));
    } finally { setSaving(false); }
  };

  return (
    <div>
      {loading ? <p>Loading…</p> : (
        <>
          {rows.map((row, idx)=> (
            <Row key={idx}>
              <Select
                value={row.appId}
                onChange={async (e)=> updateRowApp(idx, e.target.value)}
              >
                <option value="">Select Registered Application…</option>
                {apps.map(a=> (
                  <option key={a.client_id} value={a.client_id}>{a.name}</option>
                ))}
              </Select>
              <Select
                value={row.role}
                onChange={(e)=> updateRowRole(idx, e.target.value)}
                disabled={!row.appId}
              >
                <option value="">Select Role…</option>
                {(rolesByApp[row.appId] || []).map(role=> (
                  <option key={role} value={role}>{role}</option>
                ))}
              </Select>
              <SmallButton onClick={()=> addRow()}>+ Add</SmallButton>
              {rows.length>1 && (
                <SmallButton onClick={()=> removeRow(idx)} style={{ background: '#ff4d4f' }}>Remove</SmallButton>
              )}
            </Row>
          ))}
          <div style={{ marginTop: 8 }}>
            <PrimaryButton onClick={save} disabled={saving}>Save Defaults</PrimaryButton>
          </div>
        </>
      )}
    </div>
  );
};


const KeyCard = styled.div`
  background: white;
  border: 1px solid #e8e8e8;
  padding: 16px;
  border-radius: 6px;
  margin-bottom: 12px;
`;

const KeyHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
`;

const KeyName = styled.h4`
  margin: 0;
  color: #333;
  font-size: 15px;
`;

const KeyInfo = styled.div`
  font-size: 13px;
  color: #666;
  margin-bottom: 8px;

  strong {
    color: #333;
    margin-right: 4px;
  }
`;

const ClaimsPanel = styled.div`
  margin-top: 8px;
  background: #f9f9f9;
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 10px;
  text-align: left;
`;

const ClaimsPre = styled.pre`
  margin: 0;
  white-space: pre;
  word-break: normal;
  overflow: auto;
  max-height: 320px;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace;
`;


const StatusBadge = styled.span<{ $status: 'active' | 'expired' | 'revoked' }>`
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  background: ${props =>
    props.$status === 'active' ? '#d4edda' :
    props.$status === 'expired' ? '#fff3cd' :
    '#f8d7da'
  };
  color: ${props =>
    props.$status === 'active' ? '#155724' :
    props.$status === 'expired' ? '#856404' :
    '#721c24'
  };
`;

const KeyActions = styled.div`
  display: flex;
  gap: 8px;
`;

const NoKeys = styled.p`
  color: #999;
  font-style: italic;
  text-align: center;
  padding: 20px;
`;

interface APIKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  clientId: string;
  appName: string;
}

const APIKeyModal: React.FC<APIKeyModalProps> = ({ isOpen, onClose, clientId, appName }) => {
  const [loading, setLoading] = useState(false);
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    allow_admin: false,
    ttl_days: 90
  });

  useEffect(() => {
    if (isOpen && clientId) {
      loadAPIKeys();
    }
  }, [isOpen, clientId]);

  const loadAPIKeys = async () => {
    try {
      setLoading(true);
      const response = await adminService.getAppAPIKeys(clientId);
      setApiKeys(response.api_keys || []);
    } catch (error: any) {
      console.error('Failed to load API keys:', error);
      alert('Failed to load API keys: ' + (error.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateKey = async () => {
    if (!formData.name.trim()) {
      alert('Please provide a name for the API key');
      return;
    }

    try {
      setLoading(true);
      const permissions = formData.allow_admin ? ['admin'] : [];

      const response: APIKeyCreationResponse = await adminService.createAPIKey(clientId, {
        name: formData.name,
        permissions,
        ttl_days: formData.ttl_days === 0 ? undefined : formData.ttl_days
      });

      setGeneratedKey(response.api_key);
      setFormData({ name: '', allow_admin: false, ttl_days: 90 });
      await loadAPIKeys();
    } catch (error: any) {
      alert('Failed to generate API key: ' + (error.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const handleRotateKey = async (keyId: string, keyName: string) => {
    if (!confirm(`Are you sure you want to rotate the API key "${keyName}"? The old key will have a 24-hour grace period before being deactivated.`)) {
      return;
    }

    try {
      setLoading(true);
      const response = await adminService.rotateAPIKey(clientId, keyId, 24);
      setGeneratedKey(response.api_key);
      alert(`API key "${keyName}" has been rotated. The new key is displayed above. The old key will remain active for 24 hours.`);
      await loadAPIKeys();
    } catch (error: any) {
      alert('Failed to rotate API key: ' + (error.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeKey = async (keyId: string, keyName: string) => {
    if (!confirm(`Are you sure you want to revoke the API key "${keyName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setLoading(true);
      await adminService.revokeAPIKey(clientId, keyId);
      alert(`API key "${keyName}" has been revoked successfully.`);
      await loadAPIKeys();
    } catch (error: any) {
      alert('Failed to revoke API key: ' + (error.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('API key copied to clipboard');
    }).catch(() => {
      alert('Failed to copy to clipboard');
    });
  };

  const getKeyStatus = (key: APIKey): 'active' | 'expired' | 'revoked' => {
    if (!key.is_active) return 'revoked';
    if (key.expires_at && new Date(key.expires_at) < new Date()) return 'expired';
    return 'active';
  };

  if (!isOpen) return null;

  return (
    <ModalOverlay onClick={(e) => e.target === e.currentTarget && onClose()}>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>API Keys for {appName}</ModalTitle>
          <CloseButton onClick={onClose}>×</CloseButton>
        </ModalHeader>

        {generatedKey && (
          <KeyDisplay>
            <h4 style={{ margin: '0 0 8px 0', color: '#155724' }}>API Key Generated Successfully!</h4>
            <p style={{ margin: '0 0 12px 0', fontSize: '14px' }}>
              This is the only time you'll see this key. Please copy it now:
            </p>
            <KeyValue>
              <KeyCode>{generatedKey}</KeyCode>
              <CopyButton onClick={() => copyToClipboard(generatedKey)}>
                Copy
              </CopyButton>
            </KeyValue>
          </KeyDisplay>
        )}

        <Section>
          <SectionTitle>Generate New API Key</SectionTitle>
          <FormSection>
            <FormGroup>
              <Label>Key Name *</Label>
              <Input
                type="text"
                placeholder="e.g., Mobile App, Admin Dashboard"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                disabled={loading}
              />
            </FormGroup>
            <FormGroup>
              <Label>Allow this key to call CID Admin APIs</Label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="checkbox"
                  checked={formData.allow_admin}
                  onChange={(e) => setFormData({ ...formData, allow_admin: e.target.checked })}
                  disabled={loading}
                />
                <span style={{ color: '#666', fontSize: 13 }}>
                  When enabled, the key will include the 'admin' permission to access CID admin endpoints.
                </span>
              </div>
            </FormGroup>
            <FormGroup>
              <Label>Expiration</Label>
              <Select
                value={formData.ttl_days}
                onChange={(e) => setFormData({ ...formData, ttl_days: parseInt(e.target.value) })}
                disabled={loading}
              >
                <option value="1">1 Day</option>
                <option value="7">1 Week</option>
                <option value="30">30 Days</option>
                <option value="90">90 Days (Default)</option>
                <option value="365">1 Year</option>
                <option value="1825">5 Years</option>
                <option value="3650">10 Years</option>
                <option value="0">Never Expires</option>
              </Select>
            </FormGroup>
            <PrimaryButton onClick={handleGenerateKey} disabled={loading || !formData.name.trim()}>
              Generate API Key
            </PrimaryButton>
          </FormSection>
        </Section>
        <Section>
          <SectionTitle>A2A Roles & Permissions (Defaults)</SectionTitle>
          <FormSection>
            <A2AMappingsEditor callerId={clientId} />
          </FormSection>
        </Section>


        <Section>
          <SectionTitle>Existing API Keys</SectionTitle>
          {loading && <p>Loading API keys...</p>}
          {!loading && apiKeys.length === 0 && (
            <NoKeys>No API keys have been generated yet.</NoKeys>
          )}
          {!loading && apiKeys.length > 0 && (
            <div>
              {apiKeys.map((key) => {
                const status = getKeyStatus(key);
                return (
                  <KeyCard key={key.key_id}>
                    <KeyHeader>
                      <div>
                        <KeyName>{key.name || 'Unnamed Key'}</KeyName>
                        <StatusBadge $status={status}>
                          {status.toUpperCase()}
                        </StatusBadge>
                      </div>
                      <KeyActions>
                        {status === 'active' && (
                          <>
                            <SecondaryButton onClick={() => handleRotateKey(key.key_id, key.name)}>
                              Rotate
                            </SecondaryButton>
                            <DangerButton onClick={() => handleRevokeKey(key.key_id, key.name)}>
                              Revoke
                            </DangerButton>
                          </>
                        )}
                      </KeyActions>
                    </KeyHeader>
                    <KeyInfo>
                      <strong>Key ID:</strong> <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: '3px' }}>{key.key_id}</code>
                    </KeyInfo>
                    <KeyInfo>
                      <strong>Prefix:</strong> {key.key_prefix}...
                    </KeyInfo>
                    <KeyInfo>
                      <strong>Permissions:</strong> {key.permissions && key.permissions.length > 0 ? key.permissions.join(', ') : 'No specific permissions'}
                    </KeyInfo>
                    <KeyInfo>
                      <strong>Created:</strong> {new Date(key.created_at).toLocaleString()}
                    </KeyInfo>
                    <KeyInfo>
                      <strong>Expires:</strong> {key.expires_at ? new Date(key.expires_at).toLocaleString() : 'Never'}
                    </KeyInfo>
                    <KeyInfo>
                      <strong>Created By:</strong> {key.created_by}
                    </KeyInfo>
                    {key.last_used_at && (
                      <KeyInfo>
                        {status === 'active' && (
                          <div style={{ marginTop: 8 }}>
                            <SecondaryButton onClick={async () => {
                              const pasted = prompt('Paste the full API key (starts with cids_ak_) to mint an app token:');
                              if (!pasted) return;
                              try {
                                const resp = await adminService.mintA2AToken(pasted);
                                const claims = await apiService.post('/auth/validate', { token: resp.access_token });
                                (window as any)[`claims_${key.key_id}`] = claims; // store for preview rendering
                                alert('A2A token minted and validated. A claims preview will be shown below.');
                                // Force re-render by setting state (append a no-op)
                                setApiKeys(prev => [...prev]);
                              } catch (e: any) {
                                alert('Failed to mint token: ' + (e.message || 'Unknown error'));
                              }
                            }}>Mint App Token</SecondaryButton>
                            {(window as any)[`claims_${key.key_id}`] && (
                              <ClaimsPanel>
                                <div style={{ fontWeight: 600, marginBottom: 6 }}>Token Claims (preview)</div>
                                <ClaimsPre>
{JSON.stringify((window as any)[`claims_${key.key_id}`], null, 2)}
                                </ClaimsPre>
                              </ClaimsPanel>
                            )}
                          </div>
                        )}

                        <strong>Last Used:</strong> {new Date(key.last_used_at).toLocaleString()} ({key.usage_count} times)
                      </KeyInfo>
                    )}
                  </KeyCard>
                );
              })}
            </div>
          )}
        </Section>
      </ModalContent>
    </ModalOverlay>
  );
};

export default APIKeyModal;