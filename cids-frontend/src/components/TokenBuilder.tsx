import React, { useState, useEffect } from 'react';
import { adminService } from '../services/adminService';
import './TokenBuilder.css';

interface TokenClaim {
  id: string;
  key: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object' | 'date';
  value?: any;
  description?: string;
  required?: boolean;
  children?: TokenClaim[];
}

const standardClaims: TokenClaim[] = [
  { id: 'iss', key: 'iss', type: 'string', description: 'Issuer', required: false },
  { id: 'sub', key: 'sub', type: 'string', description: 'Subject', required: false },
  { id: 'aud', key: 'aud', type: 'array', description: 'Audience', required: false },
  { id: 'exp', key: 'exp', type: 'number', description: 'Expiration Time', required: false },
  { id: 'nbf', key: 'nbf', type: 'number', description: 'Not Before', required: false },
  { id: 'iat', key: 'iat', type: 'number', description: 'Issued At', required: false },
  { id: 'jti', key: 'jti', type: 'string', description: 'JWT ID', required: false },
];

const customClaimTemplates: TokenClaim[] = [
  { id: 'email', key: 'email', type: 'string', description: 'User email address' },
  { id: 'name', key: 'name', type: 'string', description: 'User full name' },
  { id: 'roles', key: 'roles', type: 'array', description: 'User roles' },
  { id: 'permissions', key: 'permissions', type: 'array', description: 'User permissions' },
  { id: 'rls_filters', key: 'rls_filters', type: 'object', description: 'Row-level security filters for data access' },
  { id: 'department', key: 'department', type: 'string', description: 'User department' },
  { id: 'groups', key: 'groups', type: 'array', description: 'User groups' },
  { id: 'metadata', key: 'metadata', type: 'object', description: 'Additional metadata' },
];

interface TokenBuilderProps {
  templateToLoad?: any;
}

const TokenBuilder: React.FC<TokenBuilderProps> = ({ templateToLoad }) => {
  const [claims, setClaims] = useState<TokenClaim[]>([]);
  const [selectedClaim, setSelectedClaim] = useState<TokenClaim | null>(null);
  const [showAddClaim, setShowAddClaim] = useState(false);
  const [newClaimKey, setNewClaimKey] = useState('');
  const [newClaimType, setNewClaimType] = useState<TokenClaim['type']>('string');
  const [newClaimDescription, setNewClaimDescription] = useState('');
  const [templateName, setTemplateName] = useState('Current CIDS Token Structure');

  useEffect(() => {
    // Check if a template was passed from the Templates tab
    if (templateToLoad) {
      setClaims(templateToLoad.claims);
      setTemplateName(templateToLoad.name);
      setSelectedClaim(null);
      return;
    }

    // First, load the current token structure from the backend
    // This represents what's actually being used in production
    const currentTokenStructure: TokenClaim[] = [
      // Standard JWT claims currently used
      { id: 'iss_current', key: 'iss', type: 'string', description: 'Issuer (internal-auth-service)', required: true, value: 'internal-auth-service' },
      { id: 'sub_current', key: 'sub', type: 'string', description: 'Subject (User ID)', required: true },
      { id: 'aud_current', key: 'aud', type: 'string', description: 'Audience (internal-services)', required: true, value: 'internal-services' },
      { id: 'exp_current', key: 'exp', type: 'number', description: 'Expiration Time', required: true },
      { id: 'nbf_current', key: 'nbf', type: 'number', description: 'Not Before', required: true },
      { id: 'iat_current', key: 'iat', type: 'number', description: 'Issued At', required: true },
      { id: 'jti_current', key: 'jti', type: 'string', description: 'JWT ID (Unique token identifier)', required: true },
      
      // Custom claims from CIDS
      { id: 'token_type', key: 'token_type', type: 'string', description: 'Type of token (access/refresh/service)', required: true },
      { id: 'token_version', key: 'token_version', type: 'string', description: 'Token version (2.0 or 3.0)', required: true },
      { id: 'email', key: 'email', type: 'string', description: 'User email address', required: false },
      { id: 'name', key: 'name', type: 'string', description: 'User full name', required: false },
      { id: 'groups', key: 'groups', type: 'array', description: 'User AD groups', required: false },
      { id: 'preferred_username', key: 'preferred_username', type: 'string', description: 'Preferred username', required: false },
      { id: 'ver', key: 'ver', type: 'string', description: 'Token schema version', required: false },
      { id: 'tenant_id', key: 'tenant_id', type: 'string', description: 'Azure AD Tenant ID', required: false },
      { id: 'client_id', key: 'client_id', type: 'string', description: 'Application Client ID', required: false },
      { id: 'roles', key: 'roles', type: 'array', description: 'User roles', required: false },
      { id: 'permissions', key: 'permissions', type: 'array', description: 'User permissions', required: false },
      { id: 'rls_filters', key: 'rls_filters', type: 'object', description: 'Row-level security filters for data access', required: false },
    ];

    // Check if there's a saved custom template
    const saved = localStorage.getItem('cids_token_template_current');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // If it's a user-saved template, use it
        if (parsed.name !== 'Current CIDS Token Structure') {
          setClaims(parsed.claims || []);
          setTemplateName(parsed.name || '');
        } else {
          // Otherwise use the current production structure
          setClaims(currentTokenStructure);
        }
      } catch (e) {
        // Fall back to current structure
        setClaims(currentTokenStructure);
      }
    } else {
      // Load current production structure by default
      setClaims(currentTokenStructure);
    }
  }, [templateToLoad]);

  const addStandardClaim = (claim: TokenClaim) => {
    if (!claims.find(c => c.id === claim.id)) {
      const newClaim = { ...claim, id: `${claim.id}_${Date.now()}` };
      setClaims([...claims, newClaim]);
    }
  };

  const addCustomClaim = () => {
    if (newClaimKey) {
      const newClaim: TokenClaim = {
        id: `custom_${Date.now()}`,
        key: newClaimKey,
        type: newClaimType,
        description: newClaimDescription,
        required: false
      };
      setClaims([...claims, newClaim]);
      setNewClaimKey('');
      setNewClaimDescription('');
      setShowAddClaim(false);
    }
  };

  const removeClaim = (id: string) => {
    setClaims(claims.filter(c => c.id !== id));
    if (selectedClaim?.id === id) {
      setSelectedClaim(null);
    }
  };

  const updateClaim = (id: string, updates: Partial<TokenClaim>) => {
    setClaims(claims.map(c => c.id === id ? { ...c, ...updates } : c));
    if (selectedClaim?.id === id) {
      setSelectedClaim({ ...selectedClaim, ...updates });
    }
  };

  const generateTokenStructure = () => {
    const structure: any = {};
    claims.forEach(claim => {
      switch (claim.type) {
        case 'string':
          structure[claim.key] = '<string>';
          break;
        case 'number':
          structure[claim.key] = 0;
          break;
        case 'boolean':
          structure[claim.key] = false;
          break;
        case 'array':
          structure[claim.key] = [];
          break;
        case 'object':
          structure[claim.key] = {};
          break;
        case 'date':
          structure[claim.key] = '<ISO 8601 date>';
          break;
      }
    });
    return structure;
  };

  const saveTemplate = async () => {
    const template = {
      name: templateName || 'Untitled Template',
      claims,
      savedAt: new Date().toISOString(),
      adGroups: [],
      priority: 0,
      enabled: true
    };
    
    try {
      // Save to backend
      await adminService.saveTokenTemplate(template);
      
      // Save to localStorage as well for caching
      localStorage.setItem('cids_token_template_current', JSON.stringify(template));
      
      // Also save to templates list
      const savedTemplates = JSON.parse(localStorage.getItem('cids_token_templates') || '[]');
      const existingIndex = savedTemplates.findIndex((t: any) => t.name === template.name);
      if (existingIndex >= 0) {
        savedTemplates[existingIndex] = template;
      } else {
        savedTemplates.push(template);
      }
      localStorage.setItem('cids_token_templates', JSON.stringify(savedTemplates));
      
      alert('Template saved successfully!');
    } catch (error) {
      console.error('Failed to save template to backend:', error);
      alert('Failed to save template to backend. Template saved locally.');
      
      // Still save locally even if backend fails
      localStorage.setItem('cids_token_template_current', JSON.stringify(template));
      const savedTemplates = JSON.parse(localStorage.getItem('cids_token_templates') || '[]');
      const existingIndex = savedTemplates.findIndex((t: any) => t.name === template.name);
      if (existingIndex >= 0) {
        savedTemplates[existingIndex] = template;
      } else {
        savedTemplates.push(template);
      }
      localStorage.setItem('cids_token_templates', JSON.stringify(savedTemplates));
    }
  };

  const loadCurrentProductionTemplate = () => {
    const currentTokenStructure: TokenClaim[] = [
      // Standard JWT claims currently used
      { id: 'iss_current', key: 'iss', type: 'string', description: 'Issuer (internal-auth-service)', required: true, value: 'internal-auth-service' },
      { id: 'sub_current', key: 'sub', type: 'string', description: 'Subject (User ID)', required: true },
      { id: 'aud_current', key: 'aud', type: 'string', description: 'Audience (internal-services)', required: true, value: 'internal-services' },
      { id: 'exp_current', key: 'exp', type: 'number', description: 'Expiration Time', required: true },
      { id: 'nbf_current', key: 'nbf', type: 'number', description: 'Not Before', required: true },
      { id: 'iat_current', key: 'iat', type: 'number', description: 'Issued At', required: true },
      { id: 'jti_current', key: 'jti', type: 'string', description: 'JWT ID (Unique token identifier)', required: true },
      
      // Custom claims from CIDS
      { id: 'token_type', key: 'token_type', type: 'string', description: 'Type of token (access/refresh/service)', required: true },
      { id: 'token_version', key: 'token_version', type: 'string', description: 'Token version (2.0 or 3.0)', required: true },
      { id: 'email', key: 'email', type: 'string', description: 'User email address', required: false },
      { id: 'name', key: 'name', type: 'string', description: 'User full name', required: false },
      { id: 'groups', key: 'groups', type: 'array', description: 'User AD groups', required: false },
      { id: 'preferred_username', key: 'preferred_username', type: 'string', description: 'Preferred username', required: false },
      { id: 'ver', key: 'ver', type: 'string', description: 'Token schema version', required: false },
      { id: 'tenant_id', key: 'tenant_id', type: 'string', description: 'Azure AD Tenant ID', required: false },
      { id: 'client_id', key: 'client_id', type: 'string', description: 'Application Client ID', required: false },
      { id: 'roles', key: 'roles', type: 'array', description: 'User roles', required: false },
      { id: 'permissions', key: 'permissions', type: 'array', description: 'User permissions', required: false },
      { id: 'rls_filters', key: 'rls_filters', type: 'object', description: 'Row-level security filters for data access', required: false },
    ];
    
    setClaims(currentTokenStructure);
    setTemplateName('Current CIDS Token Structure');
    setSelectedClaim(null);
  };

  const tokenStructure = generateTokenStructure();

  return (
    <div className="token-builder">
      <div className="builder-layout">
        {/* Left Panel - Claim Library */}
        <div className="claims-panel">
          <div className="panel-header">
            <h3>Claim Library</h3>
          </div>
          
          <div className="claims-section">
            <h4>Standard JWT Claims</h4>
            <div className="claims-list">
              {standardClaims.map(claim => (
                <div 
                  key={claim.id} 
                  className="claim-item"
                  onClick={() => addStandardClaim(claim)}
                  title="Click to add to token"
                >
                  <span className="claim-key">{claim.key}</span>
                  <span className="claim-type">{claim.type}</span>
                  <span className="claim-desc">{claim.description}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="claims-section">
            <h4>Common Custom Claims</h4>
            <div className="claims-list">
              {customClaimTemplates.map(claim => (
                <div 
                  key={claim.id} 
                  className="claim-item"
                  onClick={() => addStandardClaim(claim)}
                  title="Click to add to token"
                >
                  <span className="claim-key">{claim.key}</span>
                  <span className="claim-type">{claim.type}</span>
                  <span className="claim-desc">{claim.description}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="add-custom-section">
            <button 
              className="add-custom-btn"
              onClick={() => setShowAddClaim(!showAddClaim)}
            >
              + Add Custom Claim
            </button>
            
            {showAddClaim && (
              <div className="add-custom-form">
                <input
                  type="text"
                  placeholder="Claim key"
                  value={newClaimKey}
                  onChange={(e) => setNewClaimKey(e.target.value)}
                />
                <select 
                  value={newClaimType}
                  onChange={(e) => setNewClaimType(e.target.value as TokenClaim['type'])}
                >
                  <option value="string">String</option>
                  <option value="number">Number</option>
                  <option value="boolean">Boolean</option>
                  <option value="array">Array</option>
                  <option value="object">Object</option>
                  <option value="date">Date</option>
                </select>
                <input
                  type="text"
                  placeholder="Description (optional)"
                  value={newClaimDescription}
                  onChange={(e) => setNewClaimDescription(e.target.value)}
                />
                <button onClick={addCustomClaim}>Add</button>
                <button onClick={() => setShowAddClaim(false)}>Cancel</button>
              </div>
            )}
          </div>
        </div>

        {/* Middle Panel - Token Structure Editor */}
        <div className="editor-panel">
          <div className="panel-header">
            <h3>Token Structure</h3>
            <div className="template-name-input">
              <input
                type="text"
                placeholder="Template Name"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
              />
              <button className="save-template-btn" onClick={saveTemplate}>
                Save Template
              </button>
              <button 
                className="load-current-btn" 
                onClick={loadCurrentProductionTemplate}
                title="Load the current production token structure"
              >
                Load Current
              </button>
            </div>
          </div>

          <div className="claims-editor">
            {claims.length === 0 ? (
              <div className="empty-state">
                <p>No claims added yet</p>
                <p className="hint">Select claims from the library or add custom claims</p>
              </div>
            ) : (
              <div className="active-claims">
                {claims.map(claim => (
                  <div 
                    key={claim.id} 
                    className={`active-claim ${selectedClaim?.id === claim.id ? 'selected' : ''}`}
                    onClick={() => setSelectedClaim(claim)}
                  >
                    <div className="claim-header">
                      <span className="claim-key">{claim.key}</span>
                      <span className="claim-type-badge">{claim.type}</span>
                      {claim.required && <span className="required-badge">Required</span>}
                      <button 
                        className="remove-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeClaim(claim.id);
                        }}
                      >
                        ×
                      </button>
                    </div>
                    {claim.description && (
                      <div className="claim-description">{claim.description}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {selectedClaim && (
            <div className="claim-details">
              <h4>Claim Details</h4>
              <div className="detail-form">
                <label>
                  Key:
                  <input
                    type="text"
                    value={selectedClaim.key}
                    onChange={(e) => updateClaim(selectedClaim.id, { key: e.target.value })}
                  />
                </label>
                <label>
                  Type:
                  <select
                    value={selectedClaim.type}
                    onChange={(e) => updateClaim(selectedClaim.id, { type: e.target.value as TokenClaim['type'] })}
                  >
                    <option value="string">String</option>
                    <option value="number">Number</option>
                    <option value="boolean">Boolean</option>
                    <option value="array">Array</option>
                    <option value="object">Object</option>
                    <option value="date">Date</option>
                  </select>
                </label>
                <label>
                  Description:
                  <input
                    type="text"
                    value={selectedClaim.description || ''}
                    onChange={(e) => updateClaim(selectedClaim.id, { description: e.target.value })}
                  />
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={selectedClaim.required || false}
                    onChange={(e) => updateClaim(selectedClaim.id, { required: e.target.checked })}
                  />
                  Required
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Right Panel - JSON Preview */}
        <div className="preview-panel">
          <div className="panel-header">
            <h3>JSON Structure Preview</h3>
          </div>
          <div className="json-preview">
            <pre>{JSON.stringify(tokenStructure, null, 2)}</pre>
          </div>
          
          <div className="sample-token">
            <h4>Sample Token</h4>
            <div className="token-parts">
              <div className="token-part header">
                <span className="part-label">Header</span>
                <pre>{JSON.stringify({ alg: "HS256", typ: "JWT" }, null, 2)}</pre>
              </div>
              <div className="token-part payload">
                <span className="part-label">Payload</span>
                <pre>{JSON.stringify(tokenStructure, null, 2)}</pre>
              </div>
              <div className="token-part signature">
                <span className="part-label">Signature</span>
                <pre>HMACSHA256(
  base64UrlEncode(header) + "." +
  base64UrlEncode(payload),
  secret
)</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TokenBuilder;