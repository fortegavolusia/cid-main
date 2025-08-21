import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import PermissionSelector from './PermissionSelector';
import adminService from '../services/adminService';
import './RolesModal.css';

interface Role {
  id?: string;
  name: string;
  description?: string;
  ad_groups: string[];  // Changed to array for multiple groups
  permissions: string[];
  resource_scopes?: string[];
  created_at?: string;
  updated_at?: string;
}

interface RolesModalProps {
  isOpen: boolean;
  onClose: () => void;
  clientId: string;
  appName: string;
}

const RolesModal: React.FC<RolesModalProps> = ({ 
  isOpen, 
  onClose, 
  clientId,
  appName 
}) => {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createMode, setCreateMode] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [permissionSelectorOpen, setPermissionSelectorOpen] = useState(false);
  const [editingGroups, setEditingGroups] = useState<string | null>(null);
  const [groupInput, setGroupInput] = useState('');
  const [groupSuggestions, setGroupSuggestions] = useState<Array<{
    id: string;
    displayName: string;
    description?: string;
  }>>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);
  const searchTimeoutRef = React.useRef<NodeJS.Timeout | null>(null);
  const suggestionsRef = React.useRef<HTMLDivElement>(null);
  
  // New role form
  const [newRole, setNewRole] = useState<Role>({
    name: '',
    description: '',
    ad_groups: [],
    permissions: [],
    resource_scopes: []
  });

  useEffect(() => {
    if (isOpen && clientId) {
      fetchRoles();
    }
  }, [isOpen, clientId]);

  // Handle Azure AD group search with debounce
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (groupInput.trim().length > 0) {
      setLoadingSuggestions(true);
      searchTimeoutRef.current = setTimeout(async () => {
        try {
          const response = await adminService.searchAzureGroups(groupInput);
          setGroupSuggestions(response.groups || []);
          setShowSuggestions(true);
          setSelectedSuggestionIndex(-1);
        } catch (error) {
          console.error('Error searching Azure groups:', error);
          setGroupSuggestions([]);
        } finally {
          setLoadingSuggestions(false);
        }
      }, 300); // 300ms debounce
    } else {
      setGroupSuggestions([]);
      setShowSuggestions(false);
      setLoadingSuggestions(false);
    }

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [groupInput]);

  // Handle clicks outside suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const fetchRoles = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch role mappings first
      const mappingsData = await adminService.getRoleMappings(clientId);
      
      // Group mappings by role name to handle multiple AD groups per role
      const roleMap = new Map<string, string[]>();
      mappingsData.mappings.forEach((mapping: any) => {
        if (!roleMap.has(mapping.app_role)) {
          roleMap.set(mapping.app_role, []);
        }
        roleMap.get(mapping.app_role)!.push(mapping.ad_group);
      });
      
      // Convert to roles format
      const rolesData = Array.from(roleMap.entries()).map(([roleName, adGroups], index) => ({
        id: `role_${index}`,
        name: roleName,
        ad_groups: adGroups,
        permissions: [], // Will be fetched separately
        resource_scopes: []
      }));
      
      setRoles(rolesData);
    } catch (err) {
      console.error('Error fetching roles:', err);
      setError('Failed to load roles. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRole = () => {
    setCreateMode(true);
    setNewRole({
      name: '',
      description: '',
      ad_groups: [],
      permissions: [],
      resource_scopes: []
    });
    setGroupInput('');
  };

  const handleSaveNewRole = async () => {
    if (!newRole.name || newRole.ad_groups.length === 0) {
      alert('Please provide both role name and at least one AD group');
      return;
    }

    try {
      // Create mappings for all AD groups for this role
      const existingMappings = roles.flatMap(r => 
        r.ad_groups.map(group => ({
          ad_group: group,
          app_role: r.name
        }))
      );
      
      const newMappings = newRole.ad_groups.map(group => ({
        ad_group: group,
        app_role: newRole.name
      }));
      
      const updatedMappings = [...existingMappings, ...newMappings];
      
      await adminService.setRoleMappings(clientId, updatedMappings);
      
      // Refresh roles
      await fetchRoles();
      setCreateMode(false);
      setNewRole({
        name: '',
        description: '',
        ad_groups: [],
        permissions: [],
        resource_scopes: []
      });
      setGroupInput('');
    } catch (err) {
      console.error('Error creating role:', err);
      alert('Failed to create role');
    }
  };

  const handleEditPermissions = (role: Role) => {
    setSelectedRole(role);
    setPermissionSelectorOpen(true);
  };

  const handleEditGroups = (roleId: string) => {
    setEditingGroups(roleId);
    setGroupInput('');
  };

  const handleSelectSuggestion = (groupName: string, role?: Role) => {
    if (role) {
      // Adding to existing role
      handleAddGroup(role, groupName);
    } else if (createMode) {
      // Adding to new role
      setNewRole({
        ...newRole,
        ad_groups: [...newRole.ad_groups, groupName]
      });
    }
    setGroupInput('');
    setShowSuggestions(false);
    setGroupSuggestions([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent, role?: Role) => {
    if (!showSuggestions || groupSuggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => 
          prev < groupSuggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedSuggestionIndex >= 0 && selectedSuggestionIndex < groupSuggestions.length) {
          handleSelectSuggestion(groupSuggestions[selectedSuggestionIndex].displayName, role);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        break;
    }
  };

  const handleAddGroup = async (role: Role, groupName?: string) => {
    const groupToAdd = groupName || groupInput.trim();
    if (!groupToAdd) return;
    
    try {
      const updatedRole = {
        ...role,
        ad_groups: [...role.ad_groups, groupToAdd]
      };
      
      // Update all mappings
      const allMappings = roles.flatMap(r => {
        if (r.id === role.id) {
          return updatedRole.ad_groups.map(group => ({
            ad_group: group,
            app_role: r.name
          }));
        }
        return r.ad_groups.map(group => ({
          ad_group: group,
          app_role: r.name
        }));
      });
      
      await adminService.setRoleMappings(clientId, allMappings);
      await fetchRoles();
      setGroupInput('');
    } catch (err) {
      console.error('Error adding AD group:', err);
      alert('Failed to add AD group');
    }
  };

  const handleRemoveGroup = async (role: Role, groupToRemove: string) => {
    if (role.ad_groups.length === 1) {
      alert('A role must have at least one AD group');
      return;
    }
    
    try {
      const updatedRole = {
        ...role,
        ad_groups: role.ad_groups.filter(g => g !== groupToRemove)
      };
      
      // Update all mappings
      const allMappings = roles.flatMap(r => {
        if (r.id === role.id) {
          return updatedRole.ad_groups.map(group => ({
            ad_group: group,
            app_role: r.name
          }));
        }
        return r.ad_groups.map(group => ({
          ad_group: group,
          app_role: r.name
        }));
      });
      
      await adminService.setRoleMappings(clientId, allMappings);
      await fetchRoles();
    } catch (err) {
      console.error('Error removing AD group:', err);
      alert('Failed to remove AD group');
    }
  };

  const handleDeleteRole = async (role: Role) => {
    if (!confirm(`Are you sure you want to delete the role "${role.name}"?`)) {
      return;
    }

    try {
      // Remove this role from mappings
      const updatedMappings = roles
        .filter(r => r.id !== role.id)
        .flatMap(r => r.ad_groups.map(group => ({
          ad_group: group,
          app_role: r.name
        })));
      
      await adminService.setRoleMappings(clientId, updatedMappings);
      await fetchRoles();
    } catch (err) {
      console.error('Error deleting role:', err);
      alert('Failed to delete role');
    }
  };

  const handlePermissionsUpdate = (permissions: string[], resourceScopes: string[]) => {
    if (selectedRole) {
      // Update the role's permissions
      const updatedRole = {
        ...selectedRole,
        permissions,
        resource_scopes: resourceScopes
      };
      
      // In production, save to backend
      console.log('Updated role permissions:', updatedRole);
      
      // Update local state
      setRoles(roles.map(r => r.id === selectedRole.id ? updatedRole : r));
    }
  };

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title={`Roles - ${appName}`}
        width="80%"
        maxHeight="80vh"
      >
        <div className="roles-modal-content">
          {loading && (
            <div className="loading-message">Loading roles...</div>
          )}
          
          {error && (
            <div className="error-message">{error}</div>
          )}
          
          {!loading && !error && (
            <>
              <div className="roles-header">
                <h3>Application Roles</h3>
                <button 
                  className="button primary"
                  onClick={handleCreateRole}
                >
                  Create New Role
                </button>
              </div>

              {createMode && (
                <div className="create-role-form">
                  <h4>New Role</h4>
                  <div className="form-group">
                    <label>Role Name</label>
                    <input
                      type="text"
                      value={newRole.name}
                      onChange={(e) => setNewRole({ ...newRole, name: e.target.value })}
                      placeholder="e.g., admin, viewer, editor"
                    />
                  </div>
                  <div className="form-group">
                    <label>Description</label>
                    <textarea
                      value={newRole.description}
                      onChange={(e) => setNewRole({ ...newRole, description: e.target.value })}
                      placeholder="Describe this role's purpose..."
                      rows={2}
                    />
                  </div>
                  <div className="form-group">
                    <label>Azure AD Groups</label>
                    <div className="ad-groups-input-wrapper">
                      <div className="ad-groups-input">
                        <input
                          type="text"
                          value={groupInput}
                          onChange={(e) => setGroupInput(e.target.value)}
                          onKeyDown={(e) => handleKeyDown(e)}
                          onKeyPress={(e) => {
                            if (e.key === 'Enter' && !showSuggestions) {
                              e.preventDefault();
                              if (groupInput.trim()) {
                                setNewRole({
                                  ...newRole,
                                  ad_groups: [...newRole.ad_groups, groupInput.trim()]
                                });
                                setGroupInput('');
                              }
                            }
                          }}
                          placeholder="Start typing to search Azure AD groups..."
                          autoComplete="off"
                        />
                        <button
                          type="button"
                          className="button secondary small"
                          onClick={() => {
                            if (groupInput.trim()) {
                              setNewRole({
                                ...newRole,
                                ad_groups: [...newRole.ad_groups, groupInput.trim()]
                              });
                              setGroupInput('');
                            }
                          }}
                        >
                          Add
                        </button>
                      </div>
                      {showSuggestions && (
                        <div className="ad-groups-suggestions" ref={suggestionsRef}>
                          {loadingSuggestions ? (
                            <div className="suggestion-loading">Searching...</div>
                          ) : groupSuggestions.length > 0 ? (
                            groupSuggestions.map((group, index) => (
                              <div
                                key={group.id}
                                className={`suggestion-item ${index === selectedSuggestionIndex ? 'selected' : ''}`}
                                onClick={() => handleSelectSuggestion(group.displayName)}
                                onMouseEnter={() => setSelectedSuggestionIndex(index)}
                              >
                                <div className="suggestion-name">{group.displayName}</div>
                                {group.description && (
                                  <div className="suggestion-description">{group.description}</div>
                                )}
                              </div>
                            ))
                          ) : (
                            <div className="suggestion-no-results">No groups found</div>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="ad-groups-list">
                      {newRole.ad_groups.map((group, idx) => (
                        <div key={idx} className="ad-group-tag">
                          <span>{group}</span>
                          <button
                            type="button"
                            onClick={() => setNewRole({
                              ...newRole,
                              ad_groups: newRole.ad_groups.filter((_, i) => i !== idx)
                            })}
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="form-actions">
                    <button 
                      className="button primary"
                      onClick={handleSaveNewRole}
                    >
                      Save Role
                    </button>
                    <button 
                      className="button secondary"
                      onClick={() => setCreateMode(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              <div className="roles-list">
                {roles.length === 0 ? (
                  <div className="no-roles">
                    No roles defined for this application.
                    Click "Create New Role" to get started.
                  </div>
                ) : (
                  roles.map(role => (
                    <div key={role.id} className="role-card">
                      <div className="role-header">
                        <div className="role-info">
                          <h4>{role.name}</h4>
                          {role.description && (
                            <p className="role-description">{role.description}</p>
                          )}
                        </div>
                        <div className="role-actions-mini">
                          <button
                            className="button secondary small"
                            onClick={() => handleEditGroups(role.id!)}
                          >
                            Edit AD Groups
                          </button>
                        </div>
                      </div>

                      <div className="ad-groups-section">
                        <div className="ad-groups-header">
                          <span className="ad-label">Azure AD Groups:</span>
                        </div>
                        {editingGroups === role.id ? (
                          <div className="ad-groups-edit">
                            <div className="ad-groups-input-wrapper">
                              <div className="ad-groups-input">
                                <input
                                  type="text"
                                  value={groupInput}
                                  onChange={(e) => setGroupInput(e.target.value)}
                                  onKeyDown={(e) => handleKeyDown(e, role)}
                                  onKeyPress={(e) => {
                                    if (e.key === 'Enter' && !showSuggestions) {
                                      e.preventDefault();
                                      handleAddGroup(role);
                                    }
                                  }}
                                  placeholder="Start typing to search Azure AD groups..."
                                  autoComplete="off"
                                />
                                <button
                                  className="button primary small"
                                  onClick={() => handleAddGroup(role)}
                                >
                                  Add
                                </button>
                                <button
                                  className="button secondary small"
                                  onClick={() => {
                                    setEditingGroups(null);
                                    setGroupInput('');
                                    setShowSuggestions(false);
                                  }}
                                >
                                  Done
                                </button>
                              </div>
                              {showSuggestions && editingGroups === role.id && (
                                <div className="ad-groups-suggestions" ref={suggestionsRef}>
                                  {loadingSuggestions ? (
                                    <div className="suggestion-loading">Searching...</div>
                                  ) : groupSuggestions.length > 0 ? (
                                    groupSuggestions.map((group, index) => (
                                      <div
                                        key={group.id}
                                        className={`suggestion-item ${index === selectedSuggestionIndex ? 'selected' : ''}`}
                                        onClick={() => handleSelectSuggestion(group.displayName, role)}
                                        onMouseEnter={() => setSelectedSuggestionIndex(index)}
                                      >
                                        <div className="suggestion-name">{group.displayName}</div>
                                        {group.description && (
                                          <div className="suggestion-description">{group.description}</div>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <div className="suggestion-no-results">No groups found</div>
                                  )}
                                </div>
                              )}
                            </div>
                            <div className="ad-groups-list">
                              {role.ad_groups.map((group, idx) => (
                                <div key={idx} className="ad-group-tag editable">
                                  <span>{group}</span>
                                  <button
                                    onClick={() => handleRemoveGroup(role, group)}
                                    disabled={role.ad_groups.length === 1}
                                    title={role.ad_groups.length === 1 ? "Cannot remove last group" : "Remove group"}
                                  >
                                    ×
                                  </button>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="ad-groups-list">
                            {role.ad_groups.map((group, idx) => (
                              <div key={idx} className="ad-group-tag">
                                <span>{group}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      <div className="role-stats">
                        <div className="stat">
                          <span className="stat-label">Permissions:</span>
                          <span className="stat-value">{role.permissions.length}</span>
                        </div>
                        <div className="stat">
                          <span className="stat-label">Resource Scopes:</span>
                          <span className="stat-value">{role.resource_scopes?.length || 0}</span>
                        </div>
                      </div>

                      <div className="role-actions">
                        <button 
                          className="button primary"
                          onClick={() => handleEditPermissions(role)}
                        >
                          Edit Permissions
                        </button>
                        <button 
                          className="button danger"
                          onClick={() => handleDeleteRole(role)}
                        >
                          Delete Role
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </Modal>

      {selectedRole && (
        <PermissionSelector
          isOpen={permissionSelectorOpen}
          onClose={() => {
            setPermissionSelectorOpen(false);
            setSelectedRole(null);
          }}
          clientId={clientId}
          appName={appName}
          roleName={selectedRole.name}
          currentPermissions={selectedRole.permissions}
          currentResourceScopes={selectedRole.resource_scopes || []}
          onSave={handlePermissionsUpdate}
        />
      )}
    </>
  );
};

export default RolesModal;