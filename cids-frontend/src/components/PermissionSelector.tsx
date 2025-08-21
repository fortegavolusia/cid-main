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
  onSave: (permissions: string[], resourceScopes: string[]) => void;
}

interface FieldInfo {
  field_name: string;
  field_type: string;
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
  const [resourcePermissions, setResourcePermissions] = useState<Record<string, 'allow' | 'deny' | 'unset'>>({}); 
  const [actionPermissions, setActionPermissions] = useState<Record<string, 'allow' | 'deny' | 'unset'>>({});

  useEffect(() => {
    if (isOpen && clientId) {
      fetchPermissions();
    }
  }, [isOpen, clientId]);

  const fetchPermissions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await adminService.getAppPermissionTree(clientId);
      if (response && response.permission_tree) {
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

  const openRuleBuilder = (type: 'resource' | 'action' | 'field', data: any) => {
    setRuleBuilderContext({
      type,
      clientId,
      appName,
      ...data
    });
    setRuleBuilderOpen(true);
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

  const renderField = (resource: string, action: string, field: FieldInfo) => {
    const isSensitive = field.sensitive || field.pii || field.phi;
    
    return (
      <div 
        key={field.field_name} 
        className="field-item clickable"
        onClick={() => openRuleBuilder('field', { resource, action, field: field.field_name, fieldMetadata: field })}
      >
        <div className="field-header">
          <span className="field-name">
            {field.field_name === '*' ? '* (all fields)' : field.field_name}
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
        </div>
        {endpointInfo && (
          <div className="endpoint-info">
            Endpoint: {endpointInfo}
          </div>
        )}
        <div className="fields-label">Fields accessible:</div>
        <div className="fields-list">
          {details.fields.map(field => renderField(resource, action, field))}
        </div>
      </div>
    );
  };

  const renderResource = (resource: string, actions: any) => {
    const isExpanded = expandedResources.has(resource);
    const actionCount = Object.keys(actions).length;
    const currentPermission = resourcePermissions[resource] || 'unset';
    
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
        title={`Edit Permissions for Role: ${roleName} - ${appName}`}
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
      </Modal>
      
      <RuleBuilder
        isOpen={ruleBuilderOpen}
        onClose={() => {
          setRuleBuilderOpen(false);
          setRuleBuilderContext(null);
        }}
        context={ruleBuilderContext}
      />
    </>
  );
};

export default PermissionSelector;