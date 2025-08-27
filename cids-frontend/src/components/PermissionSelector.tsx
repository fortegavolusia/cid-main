import React, { useEffect, useState } from 'react';
import Modal from './Modal';
import RuleBuilder from './RuleBuilder';
import adminService from '../services/adminService';
import './PermissionSelector.css';

interface PermissionSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  clientId: string;
  appName: string;
  roleName: string;
  currentPermissions: string[];
  currentResourceScopes: string[];
  onSave: (permissions: string[], resourceScopes: string[], savedFilters: Record<string, Array<{ id: string; expression: string; timestamp: string }>>) => void;
}

interface FieldInfo {
  path?: string;  // The actual field name is stored in the 'path' property
  field_name?: string;  // Legacy property - may not be present
  permission_key?: string;  // Full permission key
  field_type?: string;
  description?: string;
  sensitive?: boolean;
  pii?: boolean;
  phi?: boolean;
  required?: boolean;
}

interface ActionDetails {
  fields: FieldInfo[];
  endpoint?: string;
  method?: string;
}

interface PermissionTree {
  [resource: string]: {
    [action: string]: ActionDetails;
  };
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
  const [loading, setLoading] = useState(false);
  const [permissionTree, setPermissionTree] = useState<PermissionTree | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedResources, setExpandedResources] = useState<Set<string>>(new Set());
  const [ruleBuilderOpen, setRuleBuilderOpen] = useState(false);
  const [ruleBuilderContext, setRuleBuilderContext] = useState<any>(null);
  
  // Track allow/deny states for resources and actions
  const [resourcePermissions, setResourcePermissions] = useState<Record<string, 'allow' | 'deny' | 'unset'>>(() => {
    // Try to load from unified storage first
    const unifiedKey = `cids_unified_role_${clientId}_${roleName}`;
    const saved = localStorage.getItem(unifiedKey);
    
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Extract resource permissions from action permissions
        const resourcePerms: Record<string, 'allow' | 'deny' | 'unset'> = {};
        if (parsed.actionPermissions) {
          Object.entries(parsed.actionPermissions).forEach(([key, value]) => {
            const resource = (key as string).split('.')[0];
            if (!resourcePerms[resource] || resourcePerms[resource] === 'unset') {
              resourcePerms[resource] = value as 'allow' | 'deny' | 'unset';
            }
          });
        }
        return resourcePerms;
      } catch (e) {
        console.error('Error loading saved permissions:', e);
      }
    }
    
    // Fallback to current resource scopes
    const initial: Record<string, 'allow' | 'deny' | 'unset'> = {};
    currentResourceScopes.forEach(scope => {
      initial[scope] = 'allow';
    });
    return initial;
  }); 
  
  const [actionPermissions, setActionPermissions] = useState<Record<string, 'allow' | 'deny' | 'unset'>>(() => {
    // Try to load from unified storage first
    const unifiedKey = `cids_unified_role_${clientId}_${roleName}`;
    const saved = localStorage.getItem(unifiedKey);
    
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.actionPermissions) {
          return parsed.actionPermissions;
        }
      } catch (e) {
        console.error('Error loading saved permissions:', e);
      }
    }
    
    // Fallback to current permissions
    const initial: Record<string, 'allow' | 'deny' | 'unset'> = {};
    currentPermissions.forEach(perm => {
      initial[perm] = 'allow';
    });
    return initial;
  });
  
  // Track saved filters - now as arrays of filters per key
  const [savedFilters, setSavedFilters] = useState<Record<string, Array<{ id: string; expression: string; timestamp: string }>>>(() => {
    // Load filters from localStorage on component mount - specific to this app and role
    const storageKey = `cids_filters_${clientId}_${roleName}`;
    const stored = localStorage.getItem(storageKey);
    if (!stored) return {};
    
    try {
      const parsed = JSON.parse(stored);
      // Migrate old format to new format if needed
      const migrated: Record<string, Array<{ id: string; expression: string; timestamp: string }>> = {};
      
      Object.entries(parsed).forEach(([key, value]: [string, any]) => {
        if (Array.isArray(value)) {
          // Already in correct format
          migrated[key] = value;
        } else if (value && typeof value === 'object' && value.expression) {
          // Old single-filter format - convert to array
          migrated[key] = [{
            id: Date.now().toString(),
            expression: value.expression,
            timestamp: value.timestamp || new Date().toISOString()
          }];
        }
      });
      
      return migrated;
    } catch (e) {
      console.error('Error parsing saved filters:', e);
      return {};
    }
  });
  const [viewFiltersModal, setViewFiltersModal] = useState(false);
  const [viewFiltersContext, setViewFiltersContext] = useState<any>(null);
  const [editingFilterId, setEditingFilterId] = useState<string | null>(null);
  
  // Save filters to localStorage whenever they change - specific to this app and role
  useEffect(() => {
    const storageKey = `cids_filters_${clientId}_${roleName}`;
    localStorage.setItem(storageKey, JSON.stringify(savedFilters));
  }, [savedFilters, clientId, roleName]);

  useEffect(() => {
    if (isOpen && clientId) {
      fetchPermissions();
      // Migrate any old filters with field-N format to use actual field names
      migrateOldFilters();
    }
  }, [isOpen, clientId]);
  
  const migrateOldFilters = () => {
    const storageKey = `cids_filters_${clientId}_${roleName}`;
    const stored = localStorage.getItem(storageKey);
    if (!stored) return;
    
    try {
      const filters = JSON.parse(stored);
      let needsUpdate = false;
      const migrated: Record<string, any[]> = {};
      
      Object.entries(filters).forEach(([key, filterArray]: [string, any]) => {
        // Check if key contains field-N pattern
        if (key.includes(':field-')) {
          console.log('Found old filter format, attempting to migrate:', key);
          needsUpdate = true;
          // Skip migration for now - would need the actual field data
          migrated[key] = filterArray;
        } else {
          migrated[key] = filterArray;
        }
      });
      
      if (needsUpdate) {
        console.warn('Old filter format detected. Please recreate filters to use proper field names.');
        // Clear old filters with field-N format
        const cleaned: Record<string, any[]> = {};
        Object.entries(migrated).forEach(([key, filterArray]) => {
          if (!key.includes(':field-')) {
            cleaned[key] = filterArray;
          }
        });
        setSavedFilters(cleaned);
        localStorage.setItem(storageKey, JSON.stringify(cleaned));
      }
    } catch (e) {
      console.error('Error migrating filters:', e);
    }
  };

  const fetchPermissions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await adminService.getAppPermissionTree(clientId);
      if (response && response.permission_tree) {
        console.log('Permission tree loaded:', response.permission_tree);
        
        // Check for any fields with undefined field_name and log field structure
        Object.entries(response.permission_tree).forEach(([resource, actions]: [string, any]) => {
          Object.entries(actions).forEach(([action, details]: [string, any]) => {
            if (details.fields) {
              console.log(`Fields for ${resource}.${action}:`, details.fields);
              details.fields.forEach((field: any, index: number) => {
                const extractedName = field.path || field.field_name || field.name || field.column_name || field.id;
                if (!extractedName) {
                  console.warn(`Field at ${resource}.${action}[${index}] - could not extract name from:`, field);
                  console.log('Available properties:', Object.keys(field));
                  console.log('Full field object:', JSON.stringify(field, null, 2));
                } else if (field.path) {
                  console.log(`Field ${resource}.${action}.${field.path} extracted from 'path' property`);
                }
              });
            }
          });
        });
        
        setPermissionTree(response.permission_tree);
        // Auto-expand all resources
        setExpandedResources(new Set(Object.keys(response.permission_tree)));
      } else {
        setError('No permissions found for this application.');
      }
    } catch (err) {
      console.error('Error fetching permissions:', err);
      setError('Failed to load permissions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toggleResource = (resource: string) => {
    const newExpanded = new Set(expandedResources);
    if (newExpanded.has(resource)) {
      newExpanded.delete(resource);
    } else {
      newExpanded.add(resource);
    }
    setExpandedResources(newExpanded);
  };

  const openRuleBuilder = (type: 'resource' | 'action' | 'field', data: any, filterId?: string) => {
    // Generate filter key for looking up existing filter - unique per resource/action/field
    let filterKey = '';
    if (type === 'resource') {
      filterKey = `resource:${data.resource}`;
    } else if (type === 'action') {
      filterKey = `action:${data.resource}.${data.action}`;
    } else if (type === 'field') {
      filterKey = `field:${data.resource}.${data.action}.${data.field}`;
    }
    
    // If editing a specific filter, find its expression
    let existingExpression = '';
    if (filterId && savedFilters[filterKey]) {
      const filter = savedFilters[filterKey].find(f => f.id === filterId);
      existingExpression = filter?.expression || '';
    }
    
    setEditingFilterId(filterId || null);
    setRuleBuilderContext({
      type,
      clientId,
      appName,
      filterKey,
      existingFilter: existingExpression,
      ...data
    });
    setRuleBuilderOpen(true);
  };
  
  const handleFilterSave = (filterKey: string, expression: string) => {
    if (expression.trim()) {
      setSavedFilters(prev => {
        const newFilters = { ...prev };
        
        if (editingFilterId && newFilters[filterKey] && Array.isArray(newFilters[filterKey])) {
          // Update existing filter
          newFilters[filterKey] = newFilters[filterKey].map(f => 
            f.id === editingFilterId 
              ? { ...f, expression, timestamp: new Date().toISOString() }
              : f
          );
        } else {
          // Add new filter - ensure it's an array
          if (!newFilters[filterKey] || !Array.isArray(newFilters[filterKey])) {
            newFilters[filterKey] = [];
          }
          newFilters[filterKey] = [
            ...newFilters[filterKey],
            {
              id: Date.now().toString(),
              expression,
              timestamp: new Date().toISOString()
            }
          ];
        }
        
        return newFilters;
      });
    } else if (editingFilterId) {
      // Remove specific filter if expression is empty and we're editing
      handleFilterDelete(filterKey, editingFilterId);
    }
    setEditingFilterId(null);
  };
  
  const handleFilterDelete = (filterKey: string, filterId: string) => {
    setSavedFilters(prev => {
      const newFilters = { ...prev };
      if (newFilters[filterKey]) {
        newFilters[filterKey] = newFilters[filterKey].filter(f => f.id !== filterId);
        if (newFilters[filterKey].length === 0) {
          delete newFilters[filterKey];
        }
      }
      return newFilters;
    });
  };
  
  const getResourceFilterCount = (resource: string) => {
    let count = 0;
    Object.entries(savedFilters).forEach(([key, filters]) => {
      // Count all filters that belong to this resource
      if (key.startsWith(`resource:${resource}`) || 
          key.includes(`:${resource}.`)) {
        // Ensure filters is an array before accessing length
        count += Array.isArray(filters) ? filters.length : 0;
      }
    });
    return count;
  };
  
  const getActionFilterCount = (resource: string, action: string) => {
    const actionKey = `${resource}.${action}`;
    let count = 0;
    Object.entries(savedFilters).forEach(([key, filters]) => {
      if (key.startsWith(`action:${actionKey}`) || 
          key.startsWith(`field:${actionKey}.`)) {
        // Ensure filters is an array before accessing length
        count += Array.isArray(filters) ? filters.length : 0;
      }
    });
    return count;
  };
  
  const openViewFilters = (resource?: string, action?: string) => {
    const allFilters: any[] = [];
    
    Object.entries(savedFilters).forEach(([key, filterArray]) => {
      let include = false;
      
      if (action) {
        include = key.includes(`${resource}.${action}`);
      } else if (resource) {
        include = key.startsWith(`resource:${resource}`) || 
                 key.includes(`:${resource}.`);
      } else {
        include = true;
      }
      
      if (include && Array.isArray(filterArray)) {
        const parts = key.split(':');
        filterArray.forEach(filter => {
          allFilters.push({
            ...filter,
            filterKey: key,
            type: parts[0],
            path: parts[1]
          });
        });
      }
    });
    
    setViewFiltersContext({
      resource,
      action,
      filters: allFilters
    });
    setViewFiltersModal(true);
  };

  const handleResourcePermission = (resource: string, permission: 'allow' | 'deny' | 'unset') => {
    setResourcePermissions(prev => ({
      ...prev,
      [resource]: permission
    }));
    
    // If setting resource level, update all its actions
    if (permissionTree && permissionTree[resource] && permission !== 'unset') {
      const newActionPerms: Record<string, 'allow' | 'deny' | 'unset'> = {};
      Object.keys(permissionTree[resource]).forEach(action => {
        newActionPerms[`${resource}.${action}`] = permission;
      });
      setActionPermissions(prev => ({
        ...prev,
        ...newActionPerms
      }));
    }
  };

  const handleActionPermission = (resource: string, action: string, permission: 'allow' | 'deny' | 'unset') => {
    const key = `${resource}.${action}`;
    setActionPermissions(prev => ({
      ...prev,
      [key]: permission
    }));
    
    // Check if all actions in resource have same permission
    if (permissionTree && permissionTree[resource]) {
      const allActions = Object.keys(permissionTree[resource]);
      const allSame = allActions.every(a => {
        const actionKey = `${resource}.${a}`;
        const currentPerm = actionKey === key ? permission : actionPermissions[actionKey];
        return currentPerm === permission;
      });
      
      if (allSame && permission !== 'unset') {
        setResourcePermissions(prev => ({
          ...prev,
          [resource]: permission
        }));
      } else {
        setResourcePermissions(prev => ({
          ...prev,
          [resource]: 'unset'
        }));
      }
    }
  };

  const renderField = (resource: string, action: string, field: FieldInfo, index: number) => {
    const isSensitive = field.sensitive || field.pii || field.phi;
    // Extract field name - the actual field name is in the 'path' property
    const fieldName = field.path || field.field_name || field.name || field.column_name || field.id || `field-${index}`;
    const fieldKey = `${resource}-${action}-${fieldName}`;
    
    return (
      <div 
        key={fieldKey} 
        className="field-item clickable"
        onClick={() => openRuleBuilder('field', { resource, action, field: fieldName, fieldMetadata: field })}
      >
        <div className="field-header">
          <span className="field-name">
            {fieldName === '*' ? '* (all fields)' : fieldName}
          </span>
          {isSensitive && (
            <span className="field-badge sensitive">SENSITIVE</span>
          )}
          {field.required && (
            <span className="field-badge required">REQUIRED</span>
          )}
          {field.pii && (
            <span className="field-badge pii">PII</span>
          )}
          {field.phi && (
            <span className="field-badge phi">PHI</span>
          )}
        </div>
        {field.description && (
          <div className="field-description">{field.description}</div>
        )}
        {field.field_type && field.field_type !== 'string' && (
          <div className="field-type">Type: {field.field_type}</div>
        )}
      </div>
    );
  };

  const renderAction = (resource: string, action: string, details: ActionDetails) => {
    const sensitiveCount = details.fields.filter(f => 
      f.sensitive || f.pii || f.phi
    ).length;
    const hasWildcard = details.fields.some(f => f.field_name === '*');
    const actionKey = `${resource}.${action}`;
    const currentPermission = actionPermissions[actionKey] || 'unset';
    const filterCount = getActionFilterCount(resource, action);

    // Determine endpoint info based on action and resource
    let endpointInfo = '';
    if (details.endpoint && details.method) {
      endpointInfo = `${details.method} ${details.endpoint}`;
    } else {
      // Infer from action type
      if (action === 'read') {
        endpointInfo = `GET /api/${resource} or GET /api/${resource}/{id}`;
      } else if (action === 'write' || action === 'update') {
        endpointInfo = `PUT /api/${resource}/{id}`;
      } else if (action === 'create') {
        endpointInfo = `POST /api/${resource}`;
      } else if (action === 'delete') {
        endpointInfo = `DELETE /api/${resource}/{id}`;
      }
    }

    return (
      <div 
        key={`${resource}-${action}`} 
        className={`action-section ${currentPermission !== 'unset' ? `permission-${currentPermission}` : ''}`}
      >
        <div className="action-header">
          <span 
            className="permission-name clickable"
            onClick={() => openRuleBuilder('action', { resource, action })}
          >
            {resource}.{action}
          </span>
          
          <div className="permission-selector">
            <button 
              className={`permission-btn allow ${currentPermission === 'allow' ? 'active' : ''}`}
              onClick={() => handleActionPermission(resource, action, currentPermission === 'allow' ? 'unset' : 'allow')}
              title="Allow this action"
            >
              ✓ Allow
            </button>
            <button 
              className={`permission-btn deny ${currentPermission === 'deny' ? 'active' : ''}`}
              onClick={() => handleActionPermission(resource, action, currentPermission === 'deny' ? 'unset' : 'deny')}
              title="Deny this action"
            >
              ✗ Deny
            </button>
          </div>
          
          {hasWildcard && (
            <span className="action-badge wildcard">HAS WILDCARD</span>
          )}
          {sensitiveCount > 0 && (
            <span className="action-badge sensitive-count">
              {sensitiveCount} sensitive {sensitiveCount === 1 ? 'field' : 'fields'}
            </span>
          )}
          {filterCount > 0 && (
            <button 
              className="filter-count-badge"
              onClick={(e) => {
                e.stopPropagation();
                openViewFilters(resource, action);
              }}
              title="View filters"
            >
              {filterCount} {filterCount === 1 ? 'filter' : 'filters'}
            </button>
          )}
        </div>
        {endpointInfo && (
          <div className="endpoint-info">
            Endpoint: {endpointInfo}
          </div>
        )}
        <div className="fields-label">Fields accessible:</div>
        <div className="fields-list">
          {details.fields.map((field, index) => renderField(resource, action, field, index))}
        </div>
      </div>
    );
  };

  const renderResource = (resource: string, actions: any) => {
    const isExpanded = expandedResources.has(resource);
    const actionCount = Object.keys(actions).length;
    const currentPermission = resourcePermissions[resource] || 'unset';
    const filterCount = getResourceFilterCount(resource);
    
    return (
      <div 
        key={resource} 
        className={`resource-section ${currentPermission !== 'unset' ? `permission-${currentPermission}` : ''}`}
      >
        <div 
          className="resource-header"
          onClick={() => toggleResource(resource)}
        >
          <span className="expand-icon">
            {isExpanded ? '▼' : '▶'}
          </span>
          <span 
            className="resource-name clickable"
            onClick={(e) => {
              e.stopPropagation();
              openRuleBuilder('resource', { resource });
            }}
          >
            {resource}
          </span>
          
          <div className="permission-selector" onClick={(e) => e.stopPropagation()}>
            <button 
              className={`permission-btn allow ${currentPermission === 'allow' ? 'active' : ''}`}
              onClick={() => handleResourcePermission(resource, currentPermission === 'allow' ? 'unset' : 'allow')}
              title="Allow all actions on this resource"
            >
              ✓ Allow All
            </button>
            <button 
              className={`permission-btn deny ${currentPermission === 'deny' ? 'active' : ''}`}
              onClick={() => handleResourcePermission(resource, currentPermission === 'deny' ? 'unset' : 'deny')}
              title="Deny all actions on this resource"
            >
              ✗ Deny All
            </button>
          </div>
          
          <span className="resource-count">
            {actionCount} {actionCount === 1 ? 'action' : 'actions'}
          </span>
          {filterCount > 0 && (
            <button 
              className="filter-count-badge"
              onClick={(e) => {
                e.stopPropagation();
                openViewFilters(resource);
              }}
              title="View filters for this resource"
            >
              {filterCount} {filterCount === 1 ? 'filter' : 'filters'}
            </button>
          )}
        </div>
        {isExpanded && (
          <div className="resource-content">
            {Object.entries(actions).map(([action, details]) => 
              renderAction(resource, action, details as ActionDetails)
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title={`Edit Permissions - ${appName} / Role: ${roleName}`}
        width="90%"
        maxHeight="85vh"
      >
        <div className="permissions-modal-content">
          {loading && (
            <div className="loading-message">Loading permissions...</div>
          )}
          
          {error && (
            <div className="error-message">{error}</div>
          )}
          
          {!loading && !error && permissionTree && (
            <div className="permissions-tree">
              {Object.keys(permissionTree).length === 0 ? (
                <div className="no-permissions">
                  No permissions have been discovered for this application.
                  Try running discovery first.
                </div>
              ) : (
                Object.entries(permissionTree).map(([resource, actions]) => 
                  renderResource(resource, actions)
                )
              )}
            </div>
          )}
        </div>
        
        <div className="permissions-footer">
          <button 
            className="save-permissions-btn"
            onClick={() => {
              // Collect all allowed permissions (endpoints/actions)
              const permissions: string[] = [];
              
              // Add action-level permissions (Allow/Deny on endpoints)
              Object.entries(actionPermissions).forEach(([actionKey, permission]) => {
                if (permission === 'allow') {
                  permissions.push(actionKey);
                }
              });
              
              // Collect RLS filters as resource scopes
              const resourceScopes: string[] = [];
              Object.entries(savedFilters).forEach(([filterKey, filterArray]) => {
                if (Array.isArray(filterArray) && filterArray.length > 0) {
                  // Each filter represents a resource scope
                  filterArray.forEach(filter => {
                    resourceScopes.push(`${filterKey}:${filter.expression}`);
                  });
                }
              });
              
              // Save complete role configuration for persistence
              const roleConfig = {
                clientId,
                roleName,
                permissions,  // Allowed endpoints
                resourceScopes,  // RLS filters
                actionPermissions,  // Full allow/deny state for actions
                savedFilters,  // Raw filter data
                timestamp: new Date().toISOString()
              };
              
              // Store unified role configuration
              const unifiedKey = `cids_unified_role_${clientId}_${roleName}`;
              localStorage.setItem(unifiedKey, JSON.stringify(roleConfig));
              
              console.log('Saved role configuration:', roleConfig);
              
              // Call the onSave callback with collected permissions and filters
              onSave(permissions, resourceScopes, savedFilters);
              alert(`Permissions saved successfully!\nPermissions: ${permissions.length}\nResource Scopes (RLS Filters): ${resourceScopes.length}`);
            }}
          >
            Save Permissions
          </button>
        </div>
      </Modal>
      
      <RuleBuilder
        isOpen={ruleBuilderOpen}
        onClose={() => {
          setRuleBuilderOpen(false);
          setRuleBuilderContext(null);
          setEditingFilterId(null);
        }}
        context={ruleBuilderContext}
        onSave={handleFilterSave}
      />
      
      {viewFiltersModal && (
        <Modal
          isOpen={viewFiltersModal}
          onClose={() => {
            setViewFiltersModal(false);
            setViewFiltersContext(null);
          }}
          title={`Saved Filters${viewFiltersContext?.resource ? ` for ${viewFiltersContext.resource}` : ''}`}
          width="800px"
        >
          <div className="filters-view">
            {viewFiltersContext?.filters?.length > 0 ? (
              <>
                <div className="filters-summary">
                  Total filters: {viewFiltersContext.filters.length}
                </div>
                <div className="filters-list">
                  {viewFiltersContext.filters.map((filter: any) => (
                    <div key={filter.id} className="filter-item">
                      <div className="filter-header">
                        <span className="filter-type">{filter.type.toUpperCase()}</span>
                        <span className="filter-path">{filter.path}</span>
                        <div className="filter-actions">
                          <button
                            className="filter-edit-btn"
                            onClick={() => {
                              const type = filter.type;
                              const path = filter.path;
                              const parts = path.split('.');
                              let data: any = {};
                              
                              if (type === 'resource') {
                                data = { resource: parts[0] };
                              } else if (type === 'action') {
                                data = { resource: parts[0], action: parts[1] };
                              } else if (type === 'field') {
                                data = { resource: parts[0], action: parts[1], field: parts[2] };
                              }
                              
                              setViewFiltersModal(false);
                              openRuleBuilder(type as any, data, filter.id);
                            }}
                          >
                            Edit
                          </button>
                          <button
                            className="filter-delete-btn"
                            onClick={() => {
                              if (confirm('Delete this filter?')) {
                                handleFilterDelete(filter.filterKey, filter.id);
                                // Refresh the view
                                openViewFilters(viewFiltersContext.resource, viewFiltersContext.action);
                              }
                            }}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                      <div className="filter-expression">
                        <code>{filter.expression}</code>
                      </div>
                      <div className="filter-timestamp">
                        Created: {new Date(filter.timestamp).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="no-filters">No filters configured</div>
            )}
          </div>
        </Modal>
      )}
    </>
  );
};

export default PermissionSelector;