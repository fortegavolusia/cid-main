import React, { useEffect, useState } from 'react';
import Modal from './Modal';
import PermissionsMatrix from './PermissionsMatrix';
import RuleBuilder from './RuleBuilder';
import adminService from '../services/adminService';
import apiService from '../services/api';
import './PermissionSelector.css';

interface PermissionSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  clientId: string;
  appName: string;
  roleName: string;
  currentPermissions: string[];
  currentResourceScopes: string[];
  onSave: (permissions: string[], deniedPermissions: string[], resourceScopes: string[], savedFilters: Record<string, Array<{ id: string; expression: string; timestamp: string }>>) => void;
}

interface CategoryPermission {
  resource: string;
  action: string;
  category: string;
  permission_id: string;
  available_fields: string[];
}

const PermissionSelector: React.FC<PermissionSelectorProps> = ({ 
  isOpen, 
  onClose, 
  clientId,
  appName,
  roleName,
  currentPermissions,
  currentResourceScopes,
  onSave
}) => {
  const [loading, setLoading] = useState(true);
  const [permissions, setPermissions] = useState<CategoryPermission[]>([]);
  const [selectedPermissions, setSelectedPermissions] = useState<Map<string, Set<string>>>(new Map());
  const [rlsFilters, setRlsFilters] = useState<Record<string, any>>({});
  const [showRlsBuilder, setShowRlsBuilder] = useState(false);
  const [currentRlsResource, setCurrentRlsResource] = useState<string>('');
  const [currentRlsAction, setCurrentRlsAction] = useState<string>('');

  // Fetch available permissions from database
  useEffect(() => {
    if (isOpen) {
      fetchPermissions();
    }
  }, [isOpen, clientId, roleName]);
  
  // Load current role data after permissions are fetched
  useEffect(() => {
    if (isOpen && permissions.length > 0) {
      loadCurrentRoleData();
    }
  }, [isOpen, permissions, currentPermissions]);

  const fetchPermissions = async () => {
    try {
      setLoading(true);
      
      // Fetch permissions from the discovered_permissions table
      const response = await apiService.get(`/discovery/permissions/${clientId}/categories`);
      
      if (response && Array.isArray(response)) {
        setPermissions(response);
      } else {
        console.error('Invalid permissions response:', response);
        setPermissions([]);
      }
    } catch (error) {
      console.error('Failed to fetch permissions:', error);
      // Fallback: try to construct from current data if available
      try {
        const fallbackResponse = await adminService.getAppPermissions(clientId);
        if (fallbackResponse && fallbackResponse.permissions) {
          // Convert old format to new category format
          const converted = convertToCategories(fallbackResponse.permissions);
          setPermissions(converted);
        }
      } catch (fallbackError) {
        console.error('Fallback also failed:', fallbackError);
        setPermissions([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadCurrentRoleData = async () => {
    try {
      console.log('Loading current role data for:', roleName);
      console.log('Current permissions passed from parent:', currentPermissions);
      
      // Convert current permissions (resource.action.category format) to selected categories
      const selected = new Map<string, Set<string>>();
      
      if (currentPermissions && Array.isArray(currentPermissions)) {
        currentPermissions.forEach((perm: string) => {
          // Parse the permission string: resource.action.category
          const parts = perm.split('.');
          if (parts.length === 3) {
            const [resource, action, category] = parts;
            const key = `${resource}.${action}`;
            
            if (!selected.has(key)) {
              selected.set(key, new Set());
            }
            selected.get(key)!.add(category);
            console.log(`Loaded permission: ${resource}.${action} -> ${category}`);
          }
        });
      }
      
      console.log('Loaded selected permissions:', selected);
      setSelectedPermissions(selected);
      
      // Load RLS filters from backend if available
      try {
        const roleData = await adminService.getAppRolesWithMetadata(clientId);
        if (roleData && roleData[roleName]) {
          const roleInfo = roleData[roleName];
          if (roleInfo.metadata && roleInfo.metadata.rls_filters) {
            setRlsFilters(roleInfo.metadata.rls_filters);
            console.log('Loaded RLS filters:', roleInfo.metadata.rls_filters);
          }
        }
      } catch (error) {
        console.error('Failed to load RLS filters:', error);
      }
    } catch (error) {
      console.error('Failed to load role data:', error);
    }
  };

  const convertToCategories = (oldPermissions: any): CategoryPermission[] => {
    const categories: CategoryPermission[] = [];
    
    // This is a fallback converter - ideally we should always get category data from backend
    Object.entries(oldPermissions).forEach(([resource, data]: [string, any]) => {
      if (data.actions) {
        Object.entries(data.actions).forEach(([action, actionData]: [string, any]) => {
          // Create base permission
          categories.push({
            resource,
            action,
            category: 'base',
            permission_id: `${resource}.${action}.base`,
            available_fields: actionData.fields ? Object.keys(actionData.fields).filter(f => !actionData.fields[f].sensitive) : []
          });
          
          // Create wildcard permission
          categories.push({
            resource,
            action,
            category: 'wildcard',
            permission_id: `${resource}.${action}.wildcard`,
            available_fields: actionData.fields ? Object.keys(actionData.fields) : []
          });
        });
      }
    });
    
    return categories;
  };

  const handlePermissionChange = (resource: string, action: string, categories: Set<string>) => {
    const newSelected = new Map(selectedPermissions);
    const key = `${resource}.${action}`;
    
    if (categories.size === 0) {
      newSelected.delete(key);
    } else {
      newSelected.set(key, categories);
    }
    
    setSelectedPermissions(newSelected);
  };

  const handleRLSClick = (resource: string, action: string) => {
    setCurrentRlsResource(resource);
    setCurrentRlsAction(action);
    setShowRlsBuilder(true);
  };

  const handleSaveRls = (filters: any) => {
    const key = currentRlsAction === 'all' ? currentRlsResource : `${currentRlsResource}.${currentRlsAction}`;
    setRlsFilters({
      ...rlsFilters,
      [key]: filters
    });
    setShowRlsBuilder(false);
  };

  const handleSave = async () => {
    try {
      console.log('=== STARTING SAVE PERMISSIONS ===');
      console.log('Selected permissions Map:', selectedPermissions);
      
      // Convert selected permissions to the format backend expects: resource.action.category
      const selectedPermIds: string[] = [];
      const deniedPermIds: string[] = [];
      
      selectedPermissions.forEach((categories, key) => {
        console.log(`Processing key: ${key}, categories:`, categories);
        const [resource, action] = key.split('.');
        
        // For each selected category, create permission in format: resource.action.category
        categories.forEach(category => {
          // Backend expects format: resource.action.category (e.g., "employees.read.pii")
          const permissionString = `${resource}.${action}.${category}`;
          selectedPermIds.push(permissionString);
          
          console.log(`  Adding permission: ${permissionString}`);
        });
      });
      
      console.log('=== PERMISSIONS TO SAVE ===');
      console.log('Permissions array:', selectedPermIds);
      console.log('RLS Filters:', rlsFilters);
      console.log('Calling onSave with:', {
        permissions: selectedPermIds,
        denied_permissions: deniedPermIds,
        resource_scopes: [],
        rls_filters: rlsFilters
      });
      
      // Save with RLS filters
      await onSave(selectedPermIds, deniedPermIds, [], rlsFilters);
      console.log('=== SAVE COMPLETED SUCCESSFULLY ===');
      onClose();
    } catch (error) {
      console.error('=== SAVE FAILED ===');
      console.error('Error details:', error);
      alert('Failed to save permissions. Please try again.');
    }
  };

  if (!isOpen) return null;

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      title={`Configure Permissions for Role: ${roleName}`}
      subtitle={`Application: ${appName} | Select permission categories for each resource and action`}
    >
      <div className="permission-selector" style={{ width: '100%', maxWidth: '1200px' }}>
        <div className="permission-content" style={{ maxHeight: '550px', overflowY: 'auto', padding: '20px' }}>
          {loading ? (
            <div className="loading-container">
              <div className="spinner"></div>
              <p>Loading permissions...</p>
            </div>
          ) : (
            <>
              <PermissionsMatrix
                permissions={permissions}
                selectedPermissions={selectedPermissions}
                onPermissionChange={handlePermissionChange}
                onRLSClick={handleRLSClick}
              />
              
              <div className="permission-summary" style={{ marginTop: '16px' }}>
                <div className="summary-stats" style={{ 
                  display: 'flex', 
                  gap: '24px',
                  fontSize: '12px',
                  color: '#6b7280'
                }}>
                  <div className="stat">
                    <span className="stat-label" style={{ textTransform: 'capitalize' }}>Total resources:</span>
                    <span className="stat-value" style={{ fontWeight: '600', marginLeft: '4px' }}>
                      {new Set(permissions.map(p => p.resource)).size}
                    </span>
                  </div>
                  <div className="stat">
                    <span className="stat-label" style={{ textTransform: 'capitalize' }}>Permissions selected:</span>
                    <span className="stat-value" style={{ fontWeight: '600', marginLeft: '4px' }}>{selectedPermissions.size}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label" style={{ textTransform: 'capitalize' }}>RLS filters:</span>
                    <span className="stat-value" style={{ fontWeight: '600', marginLeft: '4px' }}>{Object.keys(rlsFilters).length}</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="permission-actions" style={{ 
          display: 'flex', 
          justifyContent: 'flex-end', 
          gap: '12px', 
          padding: '20px',
          borderTop: '1px solid #e5e7eb'
        }}>
          <button 
            onClick={onClose}
            style={{
              padding: '10px 20px',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              background: 'white',
              color: '#374151',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#f9fafb'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
          >
            Cancel
          </button>
          <button 
            onClick={handleSave} 
            disabled={loading}
            style={{
              padding: '10px 20px',
              border: 'none',
              borderRadius: '6px',
              background: loading ? '#9ca3af' : '#1e40af',
              color: 'white',
              fontSize: '14px',
              fontWeight: '500',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => !loading && (e.currentTarget.style.background = '#1e3a8a')}
            onMouseLeave={(e) => !loading && (e.currentTarget.style.background = '#1e40af')}
          >
            Save Permissions
          </button>
        </div>
      </div>

      {showRlsBuilder && (
        <RuleBuilder
          isOpen={showRlsBuilder}
          onClose={() => setShowRlsBuilder(false)}
          onSave={handleSaveRls}
          resource={currentRlsResource}
          action={currentRlsAction}
          existingFilters={rlsFilters[currentRlsAction === 'all' ? currentRlsResource : `${currentRlsResource}.${currentRlsAction}`]}
        />
      )}
    </Modal>
  );
};

export default PermissionSelector;