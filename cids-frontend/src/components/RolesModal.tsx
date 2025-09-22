import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import Modal from './Modal';
import PermissionSelector from './PermissionSelector';
import adminService from '../services/adminService';
import apiService from '../services/api';
import './RolesModal.css';

// Styled Components for Role Cards (similar to App Administration)
const RolesGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 20px;
  margin-top: 20px;
`;

const RoleCard = styled.div<{ $isActive?: boolean }>`
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  overflow: hidden;
  transition: all 0.3s ease;
  position: relative;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
  
  &:hover {
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }
`;

const ActiveRibbon = styled.div`
  position: absolute;
  top: 10px;
  right: -25px;
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  padding: 4px 28px;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transform: rotate(45deg);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
  z-index: 10;
`;

const InactiveRibbon = styled.div`
  position: absolute;
  top: 10px;
  right: -25px;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: #7c2d12;
  padding: 4px 28px;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transform: rotate(45deg);
  box-shadow: 0 2px 8px rgba(251, 191, 36, 0.3);
  z-index: 10;
`;

const RoleCardHeader = styled.div<{ $isActive?: boolean }>`
  position: relative;
  padding: 12px 16px;
  background: #0b3b63;
  border-bottom: 1px solid #0a2d4d;
`;

const RoleName = styled.h3`
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const ToggleButton = styled.button<{ $isActive: boolean }>`
  position: absolute;
  bottom: 12px;
  right: 50px;
  width: 48px;
  height: 24px;
  border-radius: 12px;
  background: ${props => props.$isActive ? '#10b981' : '#6b7280'};
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 6px;
  font-size: 9px;
  font-weight: 700;
  color: white;
  z-index: 2;
  
  &:hover {
    opacity: 0.9;
    transform: scale(1.05);
  }
  
  &::before {
    content: ${props => props.$isActive ? "'ON'" : "''"};
    margin-left: 2px;
    opacity: ${props => props.$isActive ? '1' : '0'};
    transition: opacity 0.3s ease;
  }
  
  &::after {
    content: ${props => props.$isActive ? "''" : "'OFF'"};
    position: static;
    margin-right: 2px;
    opacity: ${props => props.$isActive ? '0' : '1'};
    transition: opacity 0.3s ease;
  }
`;

const ToggleSlider = styled.span<{ $isActive: boolean }>`
  position: absolute;
  top: 2px;
  left: ${props => props.$isActive ? '26px' : '2px'};
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  pointer-events: none;
  z-index: 1;
`;

const RoleCardBody = styled.div`
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #fafbfc;
`;

const RoleInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const InfoRow = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #4b5563;
  
  i {
    width: 16px;
    color: #9ca3af;
    margin-top: 2px;
    font-size: 12px;
  }
  
  strong {
    font-weight: 600;
    color: #1f2937;
  }
`;

const CardActions = styled.div`
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
`;

const ActionButton = styled.button`
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #0b3b63;
  background: white;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #0b3b63;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  
  &:hover {
    background: #f0f7ff;
    border-color: #0a3357;
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(11, 59, 99, 0.15);
  }
  
  &.primary {
    background: white;
    color: #0b3b63;
    border-color: #0b3b63;
    
    &:hover {
      background: #f0f7ff;
      border-color: #0a3357;
    }
  }
  
  &.danger {
    background: white;
    color: #ef4444;
    border-color: #ef4444;
    
    &:hover {
      background: #fef2f2;
      border-color: #dc2626;
      color: #dc2626;
    }
  }
  
  i {
    font-size: 10px;
  }
`;

const PermissionBadge = styled.span`
  background: #dbeafe;
  color: #1e40af;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  margin-left: auto;
`;

const CreateRoleButton = styled.button`
  padding: 10px 20px;
  background: #0b3b63;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: #0a3357;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(11, 59, 99, 0.2);
  }
`;

// Styled components for Create Role Modal
const ModalContent = styled.div`
  padding: 0;
`;

const ModalTitle = styled.div`
  background: #0b3b63;
  color: white;
  padding: 16px 24px;
  font-size: 1.25rem;
  font-weight: 600;
  margin: -20px -20px 24px -20px;
  border-radius: 8px 8px 0 0;
`;

const FormGroup = styled.div`
  margin-bottom: 20px;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #374151;
  font-size: 0.9rem;
  
  span {
    color: #ef4444;
    margin-left: 2px;
  }
`;

const Input = styled.input`
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.95rem;
  transition: all 0.2s;
  
  &:focus {
    outline: none;
    border-color: #0b3b63;
    box-shadow: 0 0 0 3px rgba(11, 59, 99, 0.1);
  }
`;

const Textarea = styled.textarea`
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.95rem;
  resize: vertical;
  min-height: 80px;
  transition: all 0.2s;
  
  &:focus {
    outline: none;
    border-color: #0b3b63;
    box-shadow: 0 0 0 3px rgba(11, 59, 99, 0.1);
  }
`;

const ModalActions = styled.div`
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 32px;
  padding: 24px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  margin-left: -20px;
  margin-right: -20px;
  margin-bottom: -20px;
`;

const ModalButton = styled.button`
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 100px;
  
  &.primary {
    background: #0b3b63;
    color: white !important;
    border: none;
    
    &:hover {
      background: #0a3357;
      color: white !important;
    }
  }
  
  &.secondary {
    background: white;
    color: #4a5568;
    border: 1px solid #e2e8f0;
    
    &:hover {
      background: #f7fafc;
      color: #4a5568;
    }
  }
`;

interface Role {
  id?: string;
  name: string;
  description?: string;
  ad_groups: string[];
  permissions: string[];
  resource_scopes?: string[];
  is_active?: boolean;
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
          is_active: true, // Default to active, will be updated from metadata
          metadata: {} as any,
          description: '' // Initialize description
        } as any;
      });

      // Merge in roles from permission registry (to include A2A-only roles)
      // ALWAYS force database read to get real-time data
      try {
        // Force database read by calling the endpoint directly with use_cache=false
        const response = await apiService.get(`/permissions/${clientId}/roles?use_cache=false`);
        const rolesMap = response?.roles || {};
        console.log('Roles metadata from DATABASE:', rolesMap);
        const hideA2A = localStorage.getItem(`hide_a2a_only_${clientId}`) === 'true';
        for (const [roleName, info] of Object.entries(rolesMap)) {
          if (hideA2A && info.metadata?.a2a_only) continue;
          const existingRole = rolesData.find(r => r.name === roleName);
          if (!existingRole) {
            console.log(`Role ${roleName} metadata:`, info.metadata, 'is_active:', info.metadata?.is_active);
            rolesData.push({ 
              id: `meta_${roleName}`, 
              name: roleName, 
              ad_groups: [], 
              permissions: info.permissions || [], 
              resource_scopes: [], 
              is_active: info.metadata?.is_active === true || info.metadata?.is_active === 1,
              metadata: info.metadata as any,
              description: info.metadata?.description || '',
              a2a_only: info.metadata?.a2a_only || false
            } as any);
          } else {
            console.log(`Updating existing role ${roleName} metadata:`, info.metadata, 'is_active:', info.metadata?.is_active, 'type:', typeof info.metadata?.is_active);
            console.log(`Updating existing role ${roleName} permissions:`, info.permissions);
            existingRole.metadata = info.metadata;
            // Handle both boolean true and numeric 1
            existingRole.is_active = info.metadata?.is_active === true || info.metadata?.is_active === 1;
            // Set description from metadata
            existingRole.description = info.metadata?.description || '';
            existingRole.a2a_only = info.metadata?.a2a_only || false;
            // IMPORTANT: Update permissions from database
            existingRole.permissions = info.permissions || [];
          }
        }
      } catch (err) {
        console.error('Error loading roles metadata:', err);
      }

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

  const handleToggleRoleStatus = async (role: Role) => {
    const newStatus = !role.is_active;
    const action = newStatus ? 'activate' : 'deactivate';
    
    if (!confirm(`Are you sure you want to ${action} "${role.name}"?`)) {
      return;
    }
    
    try {
      // Update ONLY the status in backend - don't send permissions
      await adminService.updateRolePermissions(clientId, role.name, {
        is_active: newStatus
      });
      
      // Update local state
      setRoles(roles.map(r => 
        r.id === role.id ? { ...r, is_active: newStatus } : r
      ));
      
      alert(`Role "${role.name}" has been ${newStatus ? 'activated' : 'deactivated'} successfully!`);
    } catch (err) {
      console.error(`Failed to ${action} role:`, err);
      alert(`Failed to ${action} role`);
    }
  };

  const handleEditPermissions = (role: Role) => {
    setSelectedRole(role);
    setPermissionSelectorOpen(true);
  };

  // Función de eliminación comentada - ahora usamos desactivación para mantener integridad referencial
  /*
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
      }

      // Remove this role from mappings
      const mappingsDict: Record<string, string | string[]> = {};
      roles
        .filter(r => r.id !== role.id)
        .forEach(r => {
          r.ad_groups.forEach(group => {
            if (mappingsDict[group]) {
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
  */

  const handlePermissionsUpdate = async (permissions: string[], deniedPermissions: string[], resourceScopes: string[], savedFilters: any) => {
    if (!selectedRole) return;

    console.log('=== RolesModal.handlePermissionsUpdate ===');
    console.log('permissions:', permissions);
    console.log('savedFilters received:', savedFilters);
    console.log('typeof savedFilters:', typeof savedFilters);
    console.log('savedFilters keys:', savedFilters ? Object.keys(savedFilters) : 'null/undefined');

    try {
      // Call backend to update permissions
      await adminService.updateRolePermissions(clientId, selectedRole.name, {
        permissions,
        denied_permissions: deniedPermissions,
        description: selectedRole.description,
        rls_filters: savedFilters,
        a2a_only: selectedRole.a2a_only
      });
      
      console.log('Permissions updated successfully in backend');
      
      // Refresh roles to get updated data
      await fetchRoles();
      setPermissionSelectorOpen(false);
      setSelectedRole(null);
    } catch (err) {
      console.error('Failed to update permissions:', err);
      alert('Failed to update permissions. Please try again.');
    }
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
      // Create mappings object
      const mappingsDict: Record<string, string | string[]> = {};

      // Add existing roles to mappings
      roles.forEach(role => {
        role.ad_groups.forEach(group => {
          if (mappingsDict[group]) {
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
          if (typeof mappingsDict[group] === 'string') {
            mappingsDict[group] = [mappingsDict[group] as string, newRole.name];
          } else {
            (mappingsDict[group] as string[]).push(newRole.name);
          }
        } else {
          mappingsDict[group] = newRole.name;
        }
      });

      // First create the role in the backend permission registry with description
      try {
        console.log('=== SENDING CREATE ROLE REQUEST ===');
        console.log('  role_name:', newRole.name);
        console.log('  description:', newRole.description);
        console.log('  description type:', typeof newRole.description);
        console.log('  a2a_only:', newRoleA2AOnly);
        
        await adminService.createRolePermissions(clientId, {
          role_name: newRole.name,
          permissions: [],
          denied_permissions: [],
          description: newRole.description,
          a2a_only: newRoleA2AOnly
        });
      } catch (error) {
        console.error('Error creating role in permission registry:', error);
        alert('Failed to create role. Please try again.');
        return;
      }

      // Then set the role mappings (if AD groups were assigned)
      if (newRole.ad_groups && newRole.ad_groups.length > 0) {
        await adminService.setRoleMappings(clientId, mappingsDict);
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

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title={`Roles - ${appName}`}
        width="90%"
        maxHeight="90vh"
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
                <CreateRoleButton onClick={handleCreateRole}>
                  Create New Role
                </CreateRoleButton>
              </div>

              <RolesGrid>
                {roles.length === 0 ? (
                  <div className="no-roles">
                    No roles defined for this application.
                    Click "Create New Role" to get started.
                  </div>
                ) : (
                  roles.map(role => (
                    <RoleCard key={role.id} $isActive={role.is_active}>
                      {role.is_active ? (
                        <ActiveRibbon>ACTIVE</ActiveRibbon>
                      ) : (
                        <InactiveRibbon>INACTIVE</InactiveRibbon>
                      )}
                      
                      <RoleCardHeader $isActive={role.is_active}>
                        <ToggleButton 
                          $isActive={role.is_active || false}
                          onClick={() => handleToggleRoleStatus(role)}
                          title={role.is_active ? "Click to deactivate" : "Click to activate"}
                        >
                          <ToggleSlider $isActive={role.is_active || false} />
                        </ToggleButton>
                        <RoleName>
                          <i className="fas fa-user-shield"></i>
                          Role Name: {role.name}
                        </RoleName>
                      </RoleCardHeader>
                      
                      <RoleCardBody>
                        <RoleInfo>
                          {role.description && (
                            <InfoRow>
                              <i className="fas fa-info-circle"></i>
                              <span>
                                <strong>Description:</strong> {role.description}
                              </span>
                            </InfoRow>
                          )}
                          
                          <InfoRow>
                            <i className="fas fa-users"></i>
                            <span>
                              <strong>AD Groups:</strong> {role.ad_groups.length > 0 ? role.ad_groups.join(', ') : 'No groups assigned'}
                            </span>
                          </InfoRow>
                          
                          <InfoRow>
                            <i className="fas fa-key"></i>
                            <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%' }}>
                              <strong style={{ marginBottom: '4px' }}>Permissions:</strong>
                              {role.permissions.length > 0 ? (
                                <div style={{ 
                                  marginLeft: '8px', 
                                  fontSize: '11px', 
                                  color: '#6b7280',
                                  lineHeight: '1.4'
                                }}>
                                  {role.permissions.map((perm, idx) => (
                                    <div key={idx} style={{ marginBottom: '2px' }}>
                                      - {perm}
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <span style={{ fontSize: '11px', color: '#9ca3af', fontStyle: 'italic', marginLeft: '8px' }}>
                                  No permissions assigned
                                </span>
                              )}
                            </span>
                          </InfoRow>
                        </RoleInfo>
                        
                        <CardActions>
                          <ActionButton 
                            className="primary"
                            onClick={() => handleEditPermissions(role)}
                          >
                            <i className="fas fa-edit"></i>
                            <span>Edit Permissions</span>
                          </ActionButton>
                          <ActionButton 
                            className={role.is_active ? "danger" : "primary"}
                            onClick={() => handleToggleRoleStatus(role)}
                          >
                            <i className={role.is_active ? "fas fa-ban" : "fas fa-check-circle"}></i>
                            <span>{role.is_active ? "Deactivate" : "Activate"}</span>
                          </ActionButton>
                        </CardActions>
                      </RoleCardBody>
                    </RoleCard>
                  ))
                )}
              </RolesGrid>
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

      {/* Create Role Modal */}
      <Modal
        isOpen={createMode}
        onClose={() => {
          setCreateMode(false);
          setGroupInput('');
          setShowSuggestions(false);
          setGroupSuggestions([]);
          setNewRoleA2AOnly(false);
        }}
        title="Create New Role"
        width="600px"
      >
        <ModalContent>
          <form onSubmit={(e) => { e.preventDefault(); handleSaveNewRole(); }} style={{ padding: '0 20px' }}>
            <FormGroup>
              <Label>Role Name <span>*</span></Label>
              <Input
                type="text"
                value={newRole.name}
                onChange={(e) => setNewRole({ ...newRole, name: e.target.value })}
                placeholder="Enter role name"
                required
              />
            </FormGroup>
            
            <FormGroup>
              <Label>Description</Label>
              <Textarea
                value={newRole.description}
                onChange={(e) => setNewRole({ ...newRole, description: e.target.value })}
                placeholder="Brief description of the role's purpose (optional)"
              />
            </FormGroup>
            
            <FormGroup>
              <Label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', userSelect: 'none' }}>
                <input
                  type="checkbox"
                  checked={newRoleA2AOnly}
                  onChange={(e) => setNewRoleA2AOnly(e.target.checked)}
                  style={{ 
                    marginRight: '8px',
                    width: '18px',
                    height: '18px',
                    cursor: 'pointer'
                  }}
                />
                <span style={{ fontSize: '14px', color: '#4b5563' }}>
                  A2A Only (Application-to-Application role, no user groups required)
                </span>
              </Label>
            </FormGroup>
            
            {!newRoleA2AOnly && (
              <FormGroup>
                <Label>Azure AD Groups</Label>
                <div className="ad-groups-input-wrapper" style={{ position: 'relative' }}>
                  <div className="ad-groups-input">
                    <Input
                      type="text"
                      value={groupInput}
                      onChange={(e) => {
                        setGroupInput(e.target.value);
                        setShowSuggestions(true);
                        
                        // Clear previous timeout
                        if (searchTimeoutRef.current) {
                          clearTimeout(searchTimeoutRef.current);
                        }
                        
                        // Set new timeout for search
                        if (e.target.value.length >= 2) {
                          setLoadingSuggestions(true);
                          searchTimeoutRef.current = setTimeout(async () => {
                            try {
                              const response = await adminService.searchAzureGroups(e.target.value);
                              setGroupSuggestions(response.groups || []);
                            } catch (err) {
                              console.error('Error searching groups:', err);
                              setGroupSuggestions([]);
                            } finally {
                              setLoadingSuggestions(false);
                            }
                          }, 300);
                        } else {
                          setGroupSuggestions([]);
                          setLoadingSuggestions(false);
                        }
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          if (selectedSuggestionIndex >= 0 && selectedSuggestionIndex < groupSuggestions.length) {
                            const selected = groupSuggestions[selectedSuggestionIndex];
                            if (!newRole.ad_groups.includes(selected.displayName)) {
                              setNewRole({ ...newRole, ad_groups: [...newRole.ad_groups, selected.displayName] });
                            }
                            setGroupInput('');
                            setShowSuggestions(false);
                            setSelectedSuggestionIndex(-1);
                          } else if (groupInput.trim()) {
                            if (!newRole.ad_groups.includes(groupInput.trim())) {
                              setNewRole({ ...newRole, ad_groups: [...newRole.ad_groups, groupInput.trim()] });
                            }
                            setGroupInput('');
                          }
                        } else if (e.key === 'ArrowDown') {
                          e.preventDefault();
                          setSelectedSuggestionIndex(prev => 
                            prev < groupSuggestions.length - 1 ? prev + 1 : prev
                          );
                        } else if (e.key === 'ArrowUp') {
                          e.preventDefault();
                          setSelectedSuggestionIndex(prev => prev > 0 ? prev - 1 : -1);
                        } else if (e.key === 'Escape') {
                          setShowSuggestions(false);
                          setSelectedSuggestionIndex(-1);
                        }
                      }}
                      placeholder="Type to search AD groups..."
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (groupInput.trim() && !newRole.ad_groups.includes(groupInput.trim())) {
                          setNewRole({ ...newRole, ad_groups: [...newRole.ad_groups, groupInput.trim()] });
                          setGroupInput('');
                        }
                      }}
                      style={{
                        padding: '8px 16px',
                        background: '#0b3b63',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '14px'
                      }}
                    >
                      Add
                    </button>
                  </div>
                  
                  {showSuggestions && groupInput.length >= 2 && (
                    <div className="ad-groups-suggestions" ref={suggestionsRef}>
                      {loadingSuggestions ? (
                        <div className="suggestion-loading">Searching AD groups...</div>
                      ) : groupSuggestions.length > 0 ? (
                        groupSuggestions.map((group, index) => (
                          <div
                            key={group.id}
                            className={`suggestion-item ${index === selectedSuggestionIndex ? 'selected' : ''}`}
                            onClick={() => {
                              if (!newRole.ad_groups.includes(group.displayName)) {
                                setNewRole({ ...newRole, ad_groups: [...newRole.ad_groups, group.displayName] });
                              }
                              setGroupInput('');
                              setShowSuggestions(false);
                              setSelectedSuggestionIndex(-1);
                            }}
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
                
                {newRole.ad_groups.length > 0 && (
                  <div className="ad-groups-list" style={{ marginTop: '12px' }}>
                    {newRole.ad_groups.map((group, index) => (
                      <span key={index} className="ad-group-tag editable">
                        <span>{group}</span>
                        <button
                          type="button"
                          onClick={() => {
                            setNewRole({
                              ...newRole,
                              ad_groups: newRole.ad_groups.filter((_, i) => i !== index)
                            });
                          }}
                          style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }}
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </FormGroup>
            )}
            
            <ModalActions>
              <ModalButton
                type="button"
                className="secondary"
                onClick={() => {
                  setCreateMode(false);
                  setGroupInput('');
                  setShowSuggestions(false);
                  setGroupSuggestions([]);
                  setNewRoleA2AOnly(false);
                }}
              >
                Cancel
              </ModalButton>
              <ModalButton type="submit" className="primary">
                Save
              </ModalButton>
            </ModalActions>
          </form>
        </ModalContent>
      </Modal>
    </>
  );
};

export default RolesModal;