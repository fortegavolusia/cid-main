import React, { useState, useEffect } from 'react';
import { adminService } from '../services/adminService';
import './TokenTemplates.css';

interface TokenClaim {
  id: string;
  key: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object' | 'date';
  value?: any;
  description?: string;
  required?: boolean;
  children?: TokenClaim[];
}

interface TokenTemplate {
  name: string;
  claims: TokenClaim[];
  savedAt: string;
  description?: string;
  adGroups?: string[];
  priority?: number;
  enabled?: boolean;
  isDefault?: boolean;
}

interface TokenTemplatesProps {
  onLoadTemplate?: (template: TokenTemplate) => void;
}

const TokenTemplates: React.FC<TokenTemplatesProps> = ({ onLoadTemplate }) => {
  const [templates, setTemplates] = useState<TokenTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<TokenTemplate | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [importJson, setImportJson] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [editingGroups, setEditingGroups] = useState<string | null>(null);
  const [groupInput, setGroupInput] = useState('');
  const [selectedGroups, setSelectedGroups] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [azureGroups, setAzureGroups] = useState<Array<{ id: string; displayName: string; description?: string }>>([]);
  const [activeSuggestionIndex, setActiveSuggestionIndex] = useState(0);
  const [loadingGroups, setLoadingGroups] = useState(false);
  const [searchTimeout, setSearchTimeout] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleGroupInputChange = (value: string) => {
    setGroupInput(value);
    
    // Clear existing timeout
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }
    
    // Get the last part after comma for autocomplete
    const parts = value.split(',');
    const currentInput = parts[parts.length - 1].trim();
    
    if (currentInput && currentInput.length >= 2) {
      setLoadingGroups(true);
      
      // Debounce the search to avoid too many API calls
      const timeout = setTimeout(async () => {
        try {
          const response = await adminService.searchAzureGroups(currentInput, 10);
          const groups = response.groups || [];
          
          // Filter out already selected groups
          const alreadySelected = parts.slice(0, -1).map(g => g.trim()).filter(g => g);
          const filteredGroups = groups.filter(g => 
            !alreadySelected.includes(g.displayName)
          );
          
          setAzureGroups(filteredGroups);
          setShowSuggestions(filteredGroups.length > 0);
          setActiveSuggestionIndex(0);
        } catch (error) {
          console.error('Failed to search Azure groups:', error);
          setAzureGroups([]);
          setShowSuggestions(false);
        } finally {
          setLoadingGroups(false);
        }
      }, 300); // 300ms debounce
      
      setSearchTimeout(timeout);
    } else {
      setShowSuggestions(false);
      setAzureGroups([]);
      setLoadingGroups(false);
    }
  };

  const handleSuggestionClick = (groupName: string) => {
    const parts = groupInput.split(',');
    parts[parts.length - 1] = groupName;
    const newGroups = parts.map(g => g.trim()).filter(g => g);
    setSelectedGroups(newGroups);
    setGroupInput(newGroups.join(', ') + ', ');
    setShowSuggestions(false);
    setAzureGroups([]);
  };

  const handleGroupInputKeyDown = (e: React.KeyboardEvent, templateName: string) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveSuggestionIndex((prev) => 
        prev < azureGroups.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveSuggestionIndex((prev) => prev > 0 ? prev - 1 : 0);
    } else if (e.key === 'Tab' || (e.key === 'Enter' && showSuggestions)) {
      e.preventDefault();
      if (azureGroups[activeSuggestionIndex]) {
        handleSuggestionClick(azureGroups[activeSuggestionIndex].displayName);
      }
    } else if (e.key === 'Enter' && !showSuggestions) {
      const groups = groupInput.split(',').map(g => g.trim()).filter(g => g);
      updateTemplateGroups(templateName, groups);
      setEditingGroups(null);
      setGroupInput('');
      setSelectedGroups([]);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  const startEditingGroups = (templateName: string, currentGroups: string[] | undefined) => {
    setEditingGroups(templateName);
    const groups = currentGroups || [];
    setSelectedGroups(groups);
    setGroupInput(groups.join(', '));
    setShowSuggestions(false);
  };

  const loadTemplates = async () => {
    try {
      // Try to load from backend first
      const response = await adminService.getTokenTemplates();
      if (response && response.templates) {
        // Convert backend format to frontend format if needed
        const backendTemplates = response.templates.map((t: any) => ({
          name: t.name,
          description: t.description,
          claims: t.claims || [],
          savedAt: t.savedAt || new Date().toISOString(),
          adGroups: t.adGroups || [],
          priority: t.priority || 0,
          enabled: t.enabled !== false,
          isDefault: t.isDefault || false
        }));
        setTemplates(backendTemplates);
        // Also save to localStorage as cache
        localStorage.setItem('cids_token_templates', JSON.stringify(backendTemplates));
      } else {
        // Fallback to localStorage if backend fails
        const saved = localStorage.getItem('cids_token_templates');
        if (saved) {
          try {
            const parsed = JSON.parse(saved);
            setTemplates(parsed);
            // Try to sync localStorage templates to backend
            syncTemplatesToBackend(parsed);
          } catch (e) {
            console.error('Failed to load templates from localStorage', e);
            setTemplates([]);
          }
        } else {
          setTemplates([]);
        }
      }
    } catch (error) {
      console.error('Failed to load templates from backend:', error);
      // Fallback to localStorage
      const saved = localStorage.getItem('cids_token_templates');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setTemplates(parsed);
        } catch (e) {
          console.error('Failed to load templates', e);
          setTemplates([]);
        }
      } else {
        setTemplates([]);
      }
    }
  };

  const syncTemplatesToBackend = async (templates: TokenTemplate[]) => {
    try {
      // Import all templates to backend
      await adminService.importTokenTemplates(templates);
      console.log('Templates synced to backend');
    } catch (error) {
      console.error('Failed to sync templates to backend:', error);
    }
  };

  const updateTemplateGroups = async (templateName: string, groups: string[]) => {
    const template = templates.find(t => t.name === templateName);
    if (!template) return;

    const updatedTemplate = { ...template, adGroups: groups };
    
    try {
      // Save to backend
      await adminService.saveTokenTemplate(updatedTemplate);
      
      // Update local state
      const updated = templates.map(t => 
        t.name === templateName ? updatedTemplate : t
      );
      setTemplates(updated);
      localStorage.setItem('cids_token_templates', JSON.stringify(updated));
      
      if (selectedTemplate?.name === templateName) {
        setSelectedTemplate(updatedTemplate);
      }
    } catch (error) {
      console.error('Failed to update template groups:', error);
      alert('Failed to save template groups to backend');
    }
  };

  const updateTemplatePriority = async (templateName: string, priority: number) => {
    const template = templates.find(t => t.name === templateName);
    if (!template) return;

    const updatedTemplate = { ...template, priority };
    
    try {
      // Save to backend
      await adminService.saveTokenTemplate(updatedTemplate);
      
      // Update local state
      const updated = templates.map(t => 
        t.name === templateName ? updatedTemplate : t
      );
      setTemplates(updated);
      localStorage.setItem('cids_token_templates', JSON.stringify(updated));
      
      if (selectedTemplate?.name === templateName) {
        setSelectedTemplate(updatedTemplate);
      }
    } catch (error) {
      console.error('Failed to update template priority:', error);
      alert('Failed to save template priority to backend');
    }
  };

  const toggleTemplateEnabled = async (templateName: string) => {
    const template = templates.find(t => t.name === templateName);
    if (!template) return;
    
    const updatedTemplate = { ...template, enabled: !template.enabled };
    
    try {
      // Save to backend
      await adminService.saveTokenTemplate(updatedTemplate);
      
      // Update local state
      const updated = templates.map(t => 
        t.name === templateName ? updatedTemplate : t
      );
      setTemplates(updated);
      localStorage.setItem('cids_token_templates', JSON.stringify(updated));
      
      if (selectedTemplate?.name === templateName) {
        setSelectedTemplate(updatedTemplate);
      }
    } catch (error) {
      console.error('Failed to update template enabled status:', error);
      alert('Failed to save template enabled status to backend');
    }
  };

  const setDefaultTemplate = (templateName: string) => {
    const template = templates.find(t => t.name === templateName);
    if (!template) return;
    
    // If already default, remove default status
    if (template.isDefault) {
      const updated = templates.map(t => 
        t.name === templateName ? { ...t, isDefault: false } : t
      );
      setTemplates(updated);
      localStorage.setItem('cids_token_templates', JSON.stringify(updated));
      
      if (selectedTemplate?.name === templateName) {
        setSelectedTemplate({ ...selectedTemplate, isDefault: false });
      }
    } else {
      // Remove default from all other templates and set this one as default
      const updated = templates.map(t => ({
        ...t,
        isDefault: t.name === templateName
      }));
      setTemplates(updated);
      localStorage.setItem('cids_token_templates', JSON.stringify(updated));
      
      if (selectedTemplate) {
        setSelectedTemplate({ 
          ...selectedTemplate, 
          isDefault: selectedTemplate.name === templateName 
        });
      }
    }
  };

  const deleteTemplate = async (templateName: string) => {
    if (confirm(`Are you sure you want to delete the template "${templateName}"?`)) {
      try {
        // Delete from backend
        await adminService.deleteTokenTemplate(templateName);
        
        // Update local state
        const updated = templates.filter(t => t.name !== templateName);
        setTemplates(updated);
        localStorage.setItem('cids_token_templates', JSON.stringify(updated));
        if (selectedTemplate?.name === templateName) {
          setSelectedTemplate(null);
        }
      } catch (error) {
        console.error('Failed to delete template:', error);
        alert('Failed to delete template from backend');
      }
    }
  };

  const exportTemplate = (template: TokenTemplate) => {
    const dataStr = JSON.stringify(template, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `token-template-${template.name.toLowerCase().replace(/\s+/g, '-')}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const exportAllTemplates = () => {
    const dataStr = JSON.stringify(templates, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `all-token-templates-${new Date().toISOString().split('T')[0]}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const importTemplate = () => {
    try {
      const parsed = JSON.parse(importJson);
      
      // Check if it's a single template or array of templates
      const templatesToImport = Array.isArray(parsed) ? parsed : [parsed];
      
      // Validate structure
      for (const template of templatesToImport) {
        if (!template.name || !template.claims) {
          throw new Error('Invalid template structure');
        }
      }
      
      // Add to existing templates
      const existingNames = new Set(templates.map(t => t.name));
      const newTemplates = templatesToImport.filter(t => !existingNames.has(t.name));
      const duplicates = templatesToImport.filter(t => existingNames.has(t.name));
      
      if (duplicates.length > 0) {
        const overwrite = confirm(`Templates with these names already exist: ${duplicates.map(t => t.name).join(', ')}. Overwrite?`);
        if (overwrite) {
          const updated = templates.filter(t => !duplicates.some(d => d.name === t.name));
          const allTemplates = [...updated, ...templatesToImport];
          setTemplates(allTemplates);
          localStorage.setItem('cids_token_templates', JSON.stringify(allTemplates));
        } else {
          const allTemplates = [...templates, ...newTemplates];
          setTemplates(allTemplates);
          localStorage.setItem('cids_token_templates', JSON.stringify(allTemplates));
        }
      } else {
        const allTemplates = [...templates, ...newTemplates];
        setTemplates(allTemplates);
        localStorage.setItem('cids_token_templates', JSON.stringify(allTemplates));
      }
      
      setShowImport(false);
      setImportJson('');
      alert(`Successfully imported ${templatesToImport.length} template(s)`);
    } catch (e) {
      alert('Failed to import template. Please check the JSON format.');
    }
  };

  const loadTemplateInBuilder = (template: TokenTemplate) => {
    if (onLoadTemplate) {
      onLoadTemplate(template);
    } else {
      // Save to current template for the TokenBuilder to pick up
      localStorage.setItem('cids_token_template_current', JSON.stringify(template));
      alert(`Template "${template.name}" loaded. Switch to Token Builder tab to edit.`);
    }
  };

  const filteredTemplates = templates.filter(t => 
    t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    t.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const generateTokenStructure = (claims: TokenClaim[]) => {
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

  return (
    <div className="token-templates">
      <div className="templates-header">
        <div className="header-left">
          <h3>Saved Token Templates</h3>
          <span className="template-count">{templates.length} templates</span>
        </div>
        <div className="header-actions">
          <input
            type="text"
            className="search-input"
            placeholder="Search templates..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button className="btn-import" onClick={() => setShowImport(true)}>
            Import
          </button>
          <button className="btn-export-all" onClick={exportAllTemplates}>
            Export All
          </button>
        </div>
      </div>

      {showImport && (
        <div className="import-section">
          <h4>Import Template(s)</h4>
          <textarea
            className="import-textarea"
            placeholder="Paste JSON template here..."
            value={importJson}
            onChange={(e) => setImportJson(e.target.value)}
            rows={10}
          />
          <div className="import-actions">
            <button className="btn-confirm-import" onClick={importTemplate}>
              Import
            </button>
            <button className="btn-cancel" onClick={() => {
              setShowImport(false);
              setImportJson('');
            }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="templates-content">
        <div className="templates-list">
          {filteredTemplates.length === 0 ? (
            <div className="no-templates">
              {searchTerm ? 'No templates match your search' : 'No saved templates yet'}
            </div>
          ) : (
            filteredTemplates.map(template => (
              <div
                key={template.name}
                className={`template-card ${selectedTemplate?.name === template.name ? 'selected' : ''}`}
                onClick={() => setSelectedTemplate(template)}
              >
                <div className="template-header">
                  <h4>{template.name}</h4>
                  <div className="template-badges">
                    <span className="claim-count">{template.claims.length} claims</span>
                    {template.isDefault && (
                      <span className="default-badge">DEFAULT</span>
                    )}
                    {template.enabled !== false && (
                      <span className="enabled-badge">Active</span>
                    )}
                    {template.priority && (
                      <span className="priority-badge">Priority: {template.priority}</span>
                    )}
                  </div>
                </div>
                {template.description && (
                  <p className="template-description">{template.description}</p>
                )}
                
                {/* AD Groups Section */}
                <div className="ad-groups-section">
                  <div className="groups-header">
                    <span className="groups-label">AD Groups:</span>
                    {editingGroups === template.name ? (
                      <div className="groups-edit-container">
                        <div className="groups-edit">
                          <input
                            type="text"
                            className="groups-input"
                            placeholder="Start typing AD group names..."
                            value={groupInput}
                            onChange={(e) => handleGroupInputChange(e.target.value)}
                            onKeyDown={(e) => handleGroupInputKeyDown(e, template.name)}
                            onBlur={() => {
                              // Delay to allow click on suggestion
                              setTimeout(() => setShowSuggestions(false), 200);
                            }}
                            onFocus={() => {
                              if (groupInput && azureGroups.length > 0) {
                                setShowSuggestions(true);
                              }
                            }}
                          />
                          <button
                            className="btn-save-groups"
                            onClick={() => {
                              const groups = groupInput.split(',').map(g => g.trim()).filter(g => g);
                              updateTemplateGroups(template.name, groups);
                              setEditingGroups(null);
                              setGroupInput('');
                              setSelectedGroups([]);
                              setShowSuggestions(false);
                            }}
                          >
                            Save
                          </button>
                          <button
                            className="btn-cancel-groups"
                            onClick={() => {
                              setEditingGroups(null);
                              setGroupInput('');
                              setSelectedGroups([]);
                              setShowSuggestions(false);
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                        {showSuggestions && editingGroups === template.name && (
                          <div className="groups-suggestions">
                            {loadingGroups ? (
                              <div className="suggestion-loading">Searching Azure AD...</div>
                            ) : azureGroups.length === 0 ? (
                              <div className="suggestion-no-results">No groups found. Type at least 2 characters to search.</div>
                            ) : (
                              azureGroups.map((group, index) => (
                                <div
                                  key={group.id}
                                  className={`suggestion-item ${index === activeSuggestionIndex ? 'active' : ''}`}
                                  onClick={() => handleSuggestionClick(group.displayName)}
                                  onMouseEnter={() => setActiveSuggestionIndex(index)}
                                >
                                  <div className="suggestion-name">{group.displayName}</div>
                                  {group.description && (
                                    <div className="suggestion-description">{group.description}</div>
                                  )}
                                </div>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="groups-display">
                        {template.adGroups && template.adGroups.length > 0 ? (
                          template.adGroups.map(group => (
                            <span key={group} className="group-tag">{group}</span>
                          ))
                        ) : (
                          <span className="no-groups">No groups assigned</span>
                        )}
                        <button
                          className="btn-edit-groups"
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditingGroups(template.name, template.adGroups);
                          }}
                        >
                          Edit
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="template-meta">
                  <span className="saved-date">
                    Saved: {new Date(template.savedAt).toLocaleDateString()}
                  </span>
                </div>
                <div className="template-actions" onClick={(e) => e.stopPropagation()}>
                  <button 
                    className="btn-load"
                    onClick={() => loadTemplateInBuilder(template)}
                    title="Load in Token Builder"
                  >
                    Load
                  </button>
                  <button 
                    className="btn-export"
                    onClick={() => exportTemplate(template)}
                    title="Export template"
                  >
                    Export
                  </button>
                  <button 
                    className="btn-delete"
                    onClick={() => deleteTemplate(template.name)}
                    title="Delete template"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {selectedTemplate && (
          <div className="template-preview">
            <h3>Template Preview: {selectedTemplate.name}</h3>
            {selectedTemplate.description && (
              <p className="preview-description">{selectedTemplate.description}</p>
            )}
            
            <div className="template-settings">
              <div className="setting-row">
                <label>Default Template:</label>
                <button
                  className={`toggle-btn ${selectedTemplate.isDefault ? 'default-active' : 'default-inactive'}`}
                  onClick={() => setDefaultTemplate(selectedTemplate.name)}
                >
                  {selectedTemplate.isDefault ? 'Default Template' : 'Set as Default'}
                </button>
                {selectedTemplate.isDefault && (
                  <span className="default-hint">Applied to all authenticated users</span>
                )}
              </div>

              <div className="setting-row">
                <label>Status:</label>
                <button
                  className={`toggle-btn ${selectedTemplate.enabled !== false ? 'enabled' : 'disabled'}`}
                  onClick={() => toggleTemplateEnabled(selectedTemplate.name)}
                >
                  {selectedTemplate.enabled !== false ? 'Active' : 'Inactive'}
                </button>
              </div>
              
              <div className="setting-row">
                <label>Priority:</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={selectedTemplate.priority || 0}
                  onChange={(e) => updateTemplatePriority(selectedTemplate.name, parseInt(e.target.value) || 0)}
                  className="priority-input"
                />
                <span className="priority-hint">Higher priority templates override lower priority ones</span>
              </div>
              
              <div className="setting-row">
                <label>AD Groups:</label>
                <div className="preview-groups">
                  {selectedTemplate.adGroups && selectedTemplate.adGroups.length > 0 ? (
                    selectedTemplate.adGroups.map(group => (
                      <span key={group} className="group-tag-preview">{group}</span>
                    ))
                  ) : (
                    <span className="no-groups-preview">{selectedTemplate.isDefault ? 'Default for all users' : 'No groups assigned'}</span>
                  )}
                </div>
              </div>
            </div>
            
            <div className="claims-preview">
              <h4>Claims ({selectedTemplate.claims.length})</h4>
              <div className="claims-list-preview">
                {selectedTemplate.claims.map(claim => (
                  <div key={claim.id} className="claim-preview-item">
                    <span className="claim-key">{claim.key}</span>
                    <span className={`claim-type ${claim.type}`}>{claim.type}</span>
                    {claim.required && <span className="required-badge">Required</span>}
                    {claim.description && (
                      <span className="claim-description">{claim.description}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="json-structure-preview">
              <h4>JSON Structure</h4>
              <pre>{JSON.stringify(generateTokenStructure(selectedTemplate.claims), null, 2)}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TokenTemplates;
