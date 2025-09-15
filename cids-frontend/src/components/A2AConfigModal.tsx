import React, { useState, useEffect } from 'react';
import './Modal.css';
import adminService from '../services/adminService';

interface A2APermission {
  id?: string;
  source_client_id: string;
  source_client_name?: string;
  target_client_id: string;
  target_client_name?: string;
  allowed_scopes: string[];
  max_token_duration: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

interface A2AConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRefresh: () => void;
}

const A2AConfigModal: React.FC<A2AConfigModalProps> = ({ isOpen, onClose, onRefresh }) => {
  const [permissions, setPermissions] = useState<A2APermission[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [registeredApps, setRegisteredApps] = useState<any[]>([]);
  const [availableScopes, setAvailableScopes] = useState<string[]>([]);
  const [loadingScopes, setLoadingScopes] = useState(false);

  // Form state
  const [formData, setFormData] = useState<Partial<A2APermission>>({
    source_client_id: '',
    target_client_id: '',
    allowed_scopes: [],
    max_token_duration: 300,
    is_active: true
  });

  const [scopeInput, setScopeInput] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadPermissions();
      loadRegisteredApps();
    }
  }, [isOpen]);

  const loadPermissions = async () => {
    console.log('🔍 [A2A] Loading A2A permissions...');
    try {
      setLoading(true);
      const data = await adminService.getA2aPermissions();
      console.log('✅ [A2A] Permissions loaded:', data);
      setPermissions(data || []);
    } catch (error) {
      console.error('❌ [A2A] Failed to load A2A permissions:', error);
      setPermissions([]);
    } finally {
      setLoading(false);
    }
  };

  const loadRegisteredApps = async () => {
    try {
      const apps = await adminService.getRegisteredApps();
      console.log('📱 [A2A] Registered apps loaded:', apps);
      setRegisteredApps(apps || []);
    } catch (error) {
      console.error('Failed to load registered apps:', error);
    }
  };

  const loadTargetAppScopes = async (targetClientId: string) => {
    if (!targetClientId) {
      setAvailableScopes([]);
      return;
    }

    console.log('🔍 [A2A] Loading scopes for target app:', targetClientId);
    setLoadingScopes(true);
    try {
      // Get discovered permissions for the target app
      const response = await adminService.getPermissionsByCategory(targetClientId);
      console.log('📦 [A2A] Discovered permissions by category:', response);
      console.log('📊 [A2A] Response type:', typeof response, 'Is Array?', Array.isArray(response));

      // Extract unique resource.action combinations as scopes
      const scopes = new Set<string>();

      // Handle if response is an array of permissions
      if (Array.isArray(response)) {
        response.forEach((item: any) => {
          // Each item might have resource and action properties
          if (item.resource && item.action) {
            scopes.add(`${item.resource}.${item.action}`);
          }
          // Or it might be a string permission
          else if (typeof item === 'string') {
            scopes.add(item);
          }
          // Or it might have a permission property
          else if (item.permission) {
            scopes.add(item.permission);
          }
        });
      }
      // Handle if response is an object with categories
      else if (response && typeof response === 'object') {
        Object.entries(response).forEach(([category, perms]: [string, any]) => {
          if (Array.isArray(perms)) {
            perms.forEach((perm: string) => {
              if (perm) {
                scopes.add(perm);
              }
            });
          }
        });
      }

      const scopesList = Array.from(scopes).sort();
      console.log('✅ [A2A] Available scopes:', scopesList);
      setAvailableScopes(scopesList);
    } catch (error) {
      console.error('❌ [A2A] Failed to load target app scopes:', error);
      // If no discovery data, provide some common scopes as fallback
      const fallbackScopes = [
        'read', 'write', 'delete', 'admin',
        'accounts.read', 'accounts.write',
        'users.read', 'users.write',
        'data.read', 'data.write'
      ];
      setAvailableScopes(fallbackScopes);
    } finally {
      setLoadingScopes(false);
    }
  };

  const handleSave = async () => {
    try {
      if (editingId) {
        await adminService.updateA2aPermission(editingId, formData);
      } else {
        await adminService.createA2aPermission(formData);
      }

      setShowAddForm(false);
      setEditingId(null);
      setFormData({
        source_client_id: '',
        target_client_id: '',
        allowed_scopes: [],
        max_token_duration: 300,
        is_active: true
      });
      setScopeInput('');

      await loadPermissions();
      onRefresh();
    } catch (error) {
      console.error('Failed to save A2A permission:', error);
      alert('Failed to save permission. Please try again.');
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this A2A permission?')) {
      try {
        await adminService.deleteA2aPermission(id);
        await loadPermissions();
        onRefresh();
      } catch (error) {
        console.error('Failed to delete A2A permission:', error);
        alert('Failed to delete permission. Please try again.');
      }
    }
  };

  const handleEdit = (permission: A2APermission) => {
    setEditingId(permission.id || null);
    setFormData(permission);
    setScopeInput(permission.allowed_scopes.join(', '));
    setShowAddForm(true);
  };

  // No longer needed - using checkboxes instead
  // const handleAddScope = () => {
  //   if (scopeInput.trim()) {
  //     const scopes = scopeInput.split(',').map(s => s.trim()).filter(s => s);
  //     setFormData({
  //       ...formData,
  //       allowed_scopes: scopes
  //     });
  //   }
  // };

  const getAppName = (clientId: string) => {
    const app = registeredApps.find(a => a.client_id === clientId);
    return app ? (app.name || app.app_name || app.client_name || clientId) : clientId;
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '900px', maxHeight: '80vh', overflow: 'auto' }}>
        <div className="modal-header">
          <h2>A2A Configuration Management</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {/* Add/Edit Form */}
          {showAddForm && (
            <div style={{
              background: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '20px'
            }}>
              <h3>{editingId ? 'Edit' : 'Add'} A2A Permission</h3>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>
                    Source Application
                  </label>
                  <select
                    value={formData.source_client_id}
                    onChange={(e) => setFormData({ ...formData, source_client_id: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '8px',
                      border: '1px solid #d1d5db',
                      borderRadius: '4px'
                    }}
                  >
                    <option value="">Select source app...</option>
                    {registeredApps.map(app => (
                      <option key={app.client_id} value={app.client_id}>
                        {app.name || app.app_name || app.client_name || 'Unknown'} - {app.client_id}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>
                    Target Application
                  </label>
                  <select
                    value={formData.target_client_id}
                    onChange={(e) => {
                      const targetId = e.target.value;
                      setFormData({ ...formData, target_client_id: targetId });
                      loadTargetAppScopes(targetId);
                    }}
                    style={{
                      width: '100%',
                      padding: '8px',
                      border: '1px solid #d1d5db',
                      borderRadius: '4px'
                    }}
                  >
                    <option value="">Select target app...</option>
                    {registeredApps.map(app => (
                      <option key={app.client_id} value={app.client_id}>
                        {app.name || app.app_name || app.client_name || 'Unknown'} - {app.client_id}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>
                    Allowed Scopes {loadingScopes && '(Loading...)'}
                  </label>
                  {!formData.target_client_id ? (
                    <div style={{ padding: '8px', color: '#6b7280', fontSize: '14px', fontStyle: 'italic' }}>
                      Select a target application first
                    </div>
                  ) : availableScopes.length === 0 && !loadingScopes ? (
                    <div style={{ padding: '8px', color: '#6b7280', fontSize: '14px', fontStyle: 'italic' }}>
                      No scopes discovered for this application
                    </div>
                  ) : (
                    <div style={{
                      border: '1px solid #d1d5db',
                      borderRadius: '4px',
                      maxHeight: '150px',
                      overflowY: 'auto',
                      padding: '8px'
                    }}>
                      {availableScopes.map(scope => (
                        <label key={scope} style={{ display: 'flex', alignItems: 'center', marginBottom: '6px', cursor: 'pointer' }}>
                          <input
                            type="checkbox"
                            checked={formData.allowed_scopes?.includes(scope) || false}
                            onChange={(e) => {
                              const currentScopes = formData.allowed_scopes || [];
                              if (e.target.checked) {
                                setFormData({ ...formData, allowed_scopes: [...currentScopes, scope] });
                              } else {
                                setFormData({ ...formData, allowed_scopes: currentScopes.filter(s => s !== scope) });
                              }
                            }}
                            style={{ marginRight: '8px' }}
                          />
                          <span style={{ fontSize: '14px' }}>{scope}</span>
                        </label>
                      ))}
                    </div>
                  )}
                  {formData.allowed_scopes && formData.allowed_scopes.length > 0 && (
                    <div style={{ marginTop: '8px', fontSize: '12px', color: '#059669' }}>
                      {formData.allowed_scopes.length} scope(s) selected
                    </div>
                  )}
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: '500' }}>
                    Max Token Duration (seconds)
                  </label>
                  <input
                    type="number"
                    value={formData.max_token_duration}
                    onChange={(e) => setFormData({ ...formData, max_token_duration: parseInt(e.target.value) })}
                    min="60"
                    max="600"
                    style={{
                      width: '100%',
                      padding: '8px',
                      border: '1px solid #d1d5db',
                      borderRadius: '4px'
                    }}
                  />
                </div>
              </div>

              <div style={{ marginTop: '16px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  />
                  <span style={{ fontSize: '14px' }}>Active</span>
                </label>
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                <button
                  onClick={handleSave}
                  style={{
                    background: '#10b981',
                    color: 'white',
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  {editingId ? 'Update' : 'Create'} Permission
                </button>
                <button
                  onClick={() => {
                    setShowAddForm(false);
                    setEditingId(null);
                    setFormData({
                      source_client_id: '',
                      target_client_id: '',
                      allowed_scopes: [],
                      max_token_duration: 300,
                      is_active: true
                    });
                    setScopeInput('');
                  }}
                  style={{
                    background: '#6b7280',
                    color: 'white',
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Add Button */}
          {!showAddForm && (
            <button
              onClick={() => setShowAddForm(true)}
              style={{
                background: '#0ea5e9',
                color: 'white',
                padding: '10px 20px',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                marginBottom: '20px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              ➕ Add New A2A Permission
            </button>
          )}

          {/* Permissions Table */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>Source App</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>Target App</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>Allowed Scopes</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>Max Duration</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>Status</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontSize: '14px', fontWeight: '600' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan={6} style={{ padding: '20px', textAlign: 'center', color: '#6b7280' }}>
                      Loading permissions...
                    </td>
                  </tr>
                )}

                {!loading && permissions.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ padding: '20px', textAlign: 'center', color: '#6b7280' }}>
                      No A2A permissions configured yet.
                    </td>
                  </tr>
                )}

                {!loading && permissions.map((perm) => (
                  <tr key={perm.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <td style={{ padding: '12px' }}>
                      <div style={{ fontSize: '14px', fontWeight: '500' }}>
                        {getAppName(perm.source_client_id)}
                      </div>
                      <div style={{ fontSize: '12px', color: '#6b7280' }}>
                        {perm.source_client_id}
                      </div>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ fontSize: '14px', fontWeight: '500' }}>
                        {getAppName(perm.target_client_id)}
                      </div>
                      <div style={{ fontSize: '12px', color: '#6b7280' }}>
                        {perm.target_client_id}
                      </div>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {perm.allowed_scopes.map((scope, idx) => (
                          <span
                            key={idx}
                            style={{
                              background: '#e0f2fe',
                              color: '#0369a1',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '12px'
                            }}
                          >
                            {scope}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td style={{ padding: '12px', fontSize: '14px' }}>
                      {perm.max_token_duration}s
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span
                        style={{
                          background: perm.is_active ? '#d1fae5' : '#fee2e2',
                          color: perm.is_active ? '#065f46' : '#991b1b',
                          padding: '4px 12px',
                          borderRadius: '12px',
                          fontSize: '12px',
                          fontWeight: '500'
                        }}
                      >
                        {perm.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => handleEdit(perm)}
                          style={{
                            background: '#3b82f6',
                            color: 'white',
                            padding: '4px 12px',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '12px'
                          }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(perm.id!)}
                          style={{
                            background: '#ef4444',
                            color: 'white',
                            padding: '4px 12px',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '12px'
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Info Section */}
          <div style={{
            marginTop: '24px',
            padding: '16px',
            background: '#f0f9ff',
            border: '1px solid #bae6fd',
            borderRadius: '8px'
          }}>
            <h4 style={{ margin: '0 0 8px 0', color: '#0369a1' }}>ℹ️ About A2A Permissions</h4>
            <p style={{ margin: '0 0 8px 0', color: '#0c4a6e', fontSize: '14px' }}>
              A2A (Application-to-Application) permissions allow services to communicate securely without user interaction.
            </p>
            <ul style={{ margin: '0', paddingLeft: '20px', color: '#0c4a6e', fontSize: '14px' }}>
              <li>Service tokens are temporary (5-10 minutes max)</li>
              <li>Each token is scoped to specific permissions</li>
              <li>Tokens include audience validation for the target service</li>
              <li>All A2A interactions are logged for audit purposes</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default A2AConfigModal;