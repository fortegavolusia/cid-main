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
  const [newRoleA2AOnly, setNewRoleA2AOnly] = useState(false);

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

      // Convert to roles format and load saved permissions
      const rolesData = Array.from(roleMap.entries()).map(([roleName, adGroups], index) => {
        const unifiedKey = `cids_unified_role_${clientId}_${roleName}`;
        const saved = localStorage.getItem(unifiedKey);
        let permissions: string[] = [];
        let resourceScopes: string[] = [];
        if (saved) {
          try {
            const parsed = JSON.parse(saved);
            permissions = parsed.permissions || [];
            resourceScopes = parsed.resourceScopes || [];
          } catch (e) { console.error('Error loading saved permissions for role:', roleName, e); }
        }
        return {
          id: `role_${index}`,
          name: roleName,
          ad_groups: adGroups,
          permissions,
          resource_scopes: resourceScopes,
          metadata: {} as any
        } as any;
      });

      // Merge in roles from permission registry (to include A2A-only roles)
      try {
        const rolesMap = await adminService.getAppRolesWithMetadata(clientId);
        const hideA2A = localStorage.getItem(`hide_a2a_only_${clientId}`) === 'true';
        for (const [roleName, info] of Object.entries(rolesMap)) {
          if (hideA2A && info.metadata?.a2a_only) continue;
          if (!rolesData.find(r => r.name === roleName)) {
            rolesData.push({ id: `meta_${roleName}`, name: roleName, ad_groups: [], permissions: info.permissions || [], resource_scopes: [], metadata: info.metadata as any } as any);
          } else {
            const idx = rolesData.findIndex(r => r.name === roleName);
            (rolesData[idx] as any).metadata = info.metadata;
          }
        }
      } catch {}

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
    if (!newRole.name) {
      alert('Please provide a role name');
      return;
    }
    if (!newRoleA2AOnly && newRole.ad_groups.length === 0) {
      alert('Please add at least one AD group or mark the role as A2A only');
      return;
    }

    try {
      // Create mappings object - backend expects Dict[str, Union[str, List[str]]]
      const mappingsDict: Record<string, string | string[]> = {};

      // Add existing roles to mappings
      roles.forEach(role => {
        role.ad_groups.forEach(group => {
          if (mappingsDict[group]) {
            // If group already has a role, make it an array
            if (typeof mappingsDict[group] === 'string') {
              mappingsDict[group] = [mappingsDict[group] as string, role.name];
            } else {
              (mappingsDict[group] as string[]).push(role.name);
            }
          } else {
            mappingsDict[group] = role.name;
          }
        });
      });

      // Add new role mappings
      newRole.ad_groups.forEach(group => {
        if (mappingsDict[group]) {
          // If group already has a role, make it an array
          if (typeof mappingsDict[group] === 'string') {
            mappingsDict[group] = [mappingsDict[group] as string, newRole.name];
          } else {
            (mappingsDict[group] as string[]).push(newRole.name);
          }
        } else {
          mappingsDict[group] = newRole.name;
        }
      });

      await adminService.setRoleMappings(clientId, mappingsDict);

      // Create the role in the backend permission registry with empty permissions
      // This ensures the role exists in the backend for later permission updates
      try {
        const token = localStorage.getItem('access_token');
        if (token) {
          await adminService.createRolePermissions(clientId, {
            role_name: newRole.name,
            permissions: [],  // Start with empty permissions
            denied_permissions: [],  // Start with empty denied permissions
            description: newRole.description || `Role for ${newRole.ad_groups.join(', ')}`,
            a2a_only: newRoleA2AOnly
          });
          console.log(`Role ${newRole.name} created in backend permission registry`);
        }
      } catch (error) {
        console.error('Error creating role in permission registry:', error);
        // Don't fail the whole operation if this fails
      }

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

      // Update all mappings - convert to dictionary format
      const mappingsDict: Record<string, string | string[]> = {};
      roles.forEach(r => {
        const groupList = r.id === role.id ? updatedRole.ad_groups : r.ad_groups;
        groupList.forEach(group => {
          if (mappingsDict[group]) {
            // If group already exists, make it an array
            if (Array.isArray(mappingsDict[group])) {
              (mappingsDict[group] as string[]).push(r.name);
            } else {
              mappingsDict[group] = [mappingsDict[group] as string, r.name];
            }
          } else {
            mappingsDict[group] = r.name;
          }
        });
      });

      await adminService.setRoleMappings(clientId, mappingsDict);
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

      // Update all mappings - convert to dictionary format
      const mappingsDict: Record<string, string | string[]> = {};
      roles.forEach(r => {
        const groupList = r.id === role.id ? updatedRole.ad_groups : r.ad_groups;
        groupList.forEach(group => {
          if (mappingsDict[group]) {
            // If group already exists, make it an array
            if (Array.isArray(mappingsDict[group])) {
              (mappingsDict[group] as string[]).push(r.name);
            } else {
              mappingsDict[group] = [mappingsDict[group] as string, r.name];
            }
          } else {
            mappingsDict[group] = r.name;
          }
        });
      });

      await adminService.setRoleMappings(clientId, mappingsDict);
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
      // First, delete the role's permissions from the backend
      try {
        await adminService.deleteRolePermissions(clientId, role.name);
        console.log(`Deleted permissions for role: ${role.name}`);
      } catch (err) {
        console.error('Error deleting role permissions:', err);
        // Continue with role deletion even if permission deletion fails
      }

      // Remove this role from mappings - convert to dictionary format
      const mappingsDict: Record<string, string | string[]> = {};
      roles
        .filter(r => r.id !== role.id)
        .forEach(r => {
          r.ad_groups.forEach(group => {
            if (mappingsDict[group]) {
              // If group already exists, make it an array
              if (Array.isArray(mappingsDict[group])) {
                (mappingsDict[group] as string[]).push(r.name);
              } else {
                mappingsDict[group] = [mappingsDict[group] as string, r.name];
              }
            } else {
              mappingsDict[group] = r.name;
            }
          });
        });

      await adminService.setRoleMappings(clientId, mappingsDict);

      // Also remove from localStorage
      const unifiedKey = `cids_unified_role_${clientId}_${role.name}`;
      localStorage.removeItem(unifiedKey);

      await fetchRoles();
      alert(`Role "${role.name}" has been deleted successfully`);
    } catch (err) {
      console.error('Error deleting role:', err);
      alert('Failed to delete role');
    }
  };

  const handlePermissionsUpdate = async (permissions: string[], deniedPermissions: string[], resourceScopes: string[], savedFilters: Record<string, Array<{ id: string; expression: string; timestamp: string }>>) => {
    if (selectedRole) {
      // Update the role's permissions
      const updatedRole = {
        ...selectedRole,
        permissions,
        resource_scopes: resourceScopes
      };

      try {
        // Save permissions to backend
        const token = localStorage.getItem('access_token');
        if (!token) {
          throw new Error('No access token found');
        }

        // Format permissions for backend API - add app prefix
        const formattedPermissions = permissions.map(perm => {
          // If permission doesn't already have the app prefix, add it
          if (!perm.startsWith(clientId)) {
            return `${clientId}.${perm}`;
          }
          return perm;
        });

        // Format denied permissions for backend API - add app prefix
        const formattedDeniedPermissions = deniedPermissions.map(perm => {
          // If permission doesn't already have the app prefix, add it
          if (!perm.startsWith(clientId)) {
            return `${clientId}.${perm}`;
          }
          return perm;
        });

        // Also add field-level permissions for fields that have RLS filters
        // Parse resource scopes to extract field permissions
        const fieldPermissions = new Set(formattedPermissions);
        resourceScopes.forEach(scope => {
          // Format: "field:resource.action.field:expression" or "resource.action.field:expression"
          // Find the last colon to get the expression separator
          const lastColonIndex = scope.lastIndexOf(':');
          if (lastColonIndex > -1) {
            let fieldPath = scope.substring(0, lastColonIndex);
            // Remove "field:" prefix if present
            if (fieldPath.startsWith('field:')) {
              fieldPath = fieldPath.substring(6);
            }
            // Add the field permission with app prefix
            const fieldPerm = fieldPath.startsWith(clientId) ? fieldPath : `${clientId}.${fieldPath}`;
            fieldPermissions.add(fieldPerm);
          }
        });

        const allPermissions = Array.from(fieldPermissions);

        // Use adminService to save permissions to backend with RLS filters
        console.log('Sending to backend:', {
          permissions: allPermissions,
          denied_permissions: formattedDeniedPermissions,
          description: selectedRole.description || `Role with ${permissions.length} allowed, ${deniedPermissions.length} denied permissions and ${resourceScopes.length} RLS filters`,
          rls_filters: savedFilters
        });

        const result = await adminService.updateRolePermissions(clientId, selectedRole.name, {
          permissions: allPermissions,
          denied_permissions: formattedDeniedPermissions,
          description: selectedRole.description || `Role with ${permissions.length} allowed, ${deniedPermissions.length} denied permissions and ${resourceScopes.length} RLS filters`,
          rls_filters: savedFilters
        });

        console.log('Permissions saved to backend:', result);

        // Update local state
        setRoles(roles.map(r => r.id === selectedRole.id ? updatedRole : r));

        alert(`Permissions saved successfully! ${result.valid_count || result.valid_permissions || 0} allowed and ${result.denied_count || 0} denied permissions were saved to the backend.`);
      } catch (error) {
        console.error('Error saving permissions to backend:', error);
        alert(`Failed to save permissions to backend: ${error.message}\n\nThe permissions have been saved locally but may not be reflected in your token until saved to the backend.`);

        // Still update local state even if backend save fails
        setRoles(roles.map(r => r.id === selectedRole.id ? updatedRole : r));
      }
    }
  };

  const handleExportRole = (role: any) => {
    // Load the full configuration from localStorage
    const unifiedKey = `cids_unified_role_${clientId}_${role.name}`;
    const saved = localStorage.getItem(unifiedKey);

    let exportData: any = {
      app_id: clientId,
      app_name: appName,
      role_name: role.name,
      ad_groups: role.ad_groups,
      permissions: [],
      rls_filters: [],
      exported_at: new Date().toISOString()
    };

    if (saved) {
      try {
        const parsed = JSON.parse(saved);

        // Format permissions for database
        exportData.permissions = parsed.permissions?.map((perm: string) => {
          const [resource, action] = perm.split('.');
          return {
            endpoint: perm,
            resource: resource,
            action: action,
            allowed: true
          };
        }) || [];

        // Format RLS filters for database
        if (parsed.savedFilters) {
          exportData.rls_filters = Object.entries(parsed.savedFilters).flatMap(([key, filters]: [string, any]) => {
            if (Array.isArray(filters)) {
              return filters.map((filter: any) => {
                const [type, path] = key.split(':');
                return {
                  filter_type: type,
                  filter_path: path,
                  expression: filter.expression,
                  created_at: filter.timestamp
                };
              });
            }
            return [];
          });
        }

        // Add summary statistics
        exportData.summary = {
          total_permissions: exportData.permissions.length,
          total_rls_filters: exportData.rls_filters.length,
          resources: [...new Set(exportData.permissions.map((p: any) => p.resource))],
          actions: [...new Set(exportData.permissions.map((p: any) => p.action))]
        };
      } catch (e) {
        console.error('Error parsing saved role data:', e);
      }
    } else {
      // Use basic data if no saved config exists
      exportData.permissions = role.permissions?.map((perm: string) => {
        const [resource, action] = perm.split('.');
        return {
          endpoint: perm,
          resource: resource || perm,
          action: action || '',
          allowed: true
        };
      }) || [];

      exportData.summary = {
        total_permissions: role.permissions?.length || 0,
        total_rls_filters: role.resource_scopes?.length || 0
      };
    }

    // Create and download the JSON file
    const jsonStr = JSON.stringify(exportData, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${clientId}_${role.name}_permissions_${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    console.log('Exported role configuration:', exportData);
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
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    className="button secondary"
                    onClick={() => {
                      // Export all roles
                      const allRolesExport = {
                        app_id: clientId,
                        app_name: appName,
                        roles: roles.map(role => {
                          const unifiedKey = `cids_unified_role_${clientId}_${role.name}`;
                          const saved = localStorage.getItem(unifiedKey);
                          let roleData: any = {
                            role_name: role.name,
                            ad_groups: role.ad_groups,
                            permissions: role.permissions,
                            resource_scopes: role.resource_scopes
                          };

                          if (saved) {
                            try {
                              const parsed = JSON.parse(saved);
                              roleData.rls_filters = parsed.savedFilters || {};
                              roleData.action_permissions = parsed.actionPermissions || {};
                            } catch (e) {
                              console.error('Error parsing role data:', e);
                            }
                          }

                          return roleData;
                        }),
                        exported_at: new Date().toISOString()
                      };

                      const jsonStr = JSON.stringify(allRolesExport, null, 2);
                      const blob = new Blob([jsonStr], { type: 'application/json' });
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = `${clientId}_all_roles_${Date.now()}.json`;
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                      URL.revokeObjectURL(url);
                    }}
                    title="Export all roles configuration"
                  >
                    Export All Roles
                  </button>
                  <button
                    className="button primary"
                    onClick={handleCreateRole}
                  >
                    Create New Role
                  </button>
                </div>
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
                  <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input
                      type="checkbox"
                      checked={newRoleA2AOnly}
                      onChange={(e)=> setNewRoleA2AOnly(e.target.checked)}
                    />
                    <label>Use this role for A2A only (no AD group mapping required)</label>
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
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <input
                  type="checkbox"
                  id="hideA2AOnly"
                  checked={localStorage.getItem(`hide_a2a_only_${clientId}`) === 'true'}
                  onChange={(e)=>{
                    if (e.target.checked) localStorage.setItem(`hide_a2a_only_${clientId}`, 'true');
                    else localStorage.removeItem(`hide_a2a_only_${clientId}`);
                    fetchRoles();
                  }}
                />
                <label htmlFor="hideA2AOnly">Hide A2A-only roles</label>
              </div>


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
                          className="button secondary"
                          onClick={() => handleExportRole(role)}
                          title="Export role configuration as JSON"
                        >
                          Export
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