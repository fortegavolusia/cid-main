import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import './RuleBuilder.css';

interface RuleBuilderProps {
  isOpen: boolean;
  onClose: () => void;
  context: {
    type: 'resource' | 'action' | 'field';
    resource?: string;
    action?: string;
    field?: string;
    fieldMetadata?: any;
    clientId: string;
    appName: string;
  };
}

interface Rule {
  id: string;
  name: string;
  description: string;
  effect: 'allow' | 'deny';
  principals: string[];
  resources: string[];
  actions: string[];
  conditions?: {
    field?: string;
    operator?: 'equals' | 'not_equals' | 'contains' | 'exists';
    value?: string;
  }[];
}

const RuleBuilder: React.FC<RuleBuilderProps> = ({ isOpen, onClose, context }) => {
  const [rule, setRule] = useState<Rule>({
    id: '',
    name: '',
    description: '',
    effect: 'allow',
    principals: [],
    resources: [],
    actions: [],
    conditions: []
  });

  const [principalInput, setPrincipalInput] = useState('');
  const [resourceInput, setResourceInput] = useState('');
  const [actionInput, setActionInput] = useState('');

  useEffect(() => {
    if (isOpen && context) {
      // Pre-populate based on context
      const newRule: Rule = {
        id: `rule_${Date.now()}`,
        name: '',
        description: '',
        effect: 'allow',
        principals: [],
        resources: context.resource ? [`${context.resource}/*`] : [],
        actions: context.action ? [`${context.resource}:${context.action}`] : [],
        conditions: []
      };

      // If field context, add field condition
      if (context.type === 'field' && context.field) {
        newRule.conditions = [{
          field: context.field,
          operator: 'exists',
          value: ''
        }];
      }

      setRule(newRule);
      
      // Set inputs
      if (context.resource) setResourceInput(context.resource);
      if (context.action) setActionInput(`${context.resource}:${context.action}`);
    }
  }, [isOpen, context]);

  const addPrincipal = () => {
    if (principalInput.trim()) {
      setRule({
        ...rule,
        principals: [...rule.principals, principalInput.trim()]
      });
      setPrincipalInput('');
    }
  };

  const removePrincipal = (index: number) => {
    setRule({
      ...rule,
      principals: rule.principals.filter((_, i) => i !== index)
    });
  };

  const addResource = () => {
    if (resourceInput.trim()) {
      setRule({
        ...rule,
        resources: [...rule.resources, resourceInput.trim()]
      });
      setResourceInput('');
    }
  };

  const removeResource = (index: number) => {
    setRule({
      ...rule,
      resources: rule.resources.filter((_, i) => i !== index)
    });
  };

  const addAction = () => {
    if (actionInput.trim()) {
      setRule({
        ...rule,
        actions: [...rule.actions, actionInput.trim()]
      });
      setActionInput('');
    }
  };

  const removeAction = (index: number) => {
    setRule({
      ...rule,
      actions: rule.actions.filter((_, i) => i !== index)
    });
  };

  const addCondition = () => {
    setRule({
      ...rule,
      conditions: [
        ...(rule.conditions || []),
        { field: '', operator: 'equals', value: '' }
      ]
    });
  };

  const updateCondition = (index: number, updates: Partial<Rule['conditions'][0]>) => {
    const newConditions = [...(rule.conditions || [])];
    newConditions[index] = { ...newConditions[index], ...updates };
    setRule({ ...rule, conditions: newConditions });
  };

  const removeCondition = (index: number) => {
    setRule({
      ...rule,
      conditions: rule.conditions?.filter((_, i) => i !== index)
    });
  };

  const generatePolicyPreview = () => {
    return JSON.stringify({
      version: '1.0',
      statement: {
        id: rule.id,
        effect: rule.effect,
        principals: rule.principals,
        resources: rule.resources,
        actions: rule.actions,
        conditions: rule.conditions
      }
    }, null, 2);
  };

  const handleSave = () => {
    // TODO: Implement save to backend
    console.log('Saving rule:', rule);
    alert('Rule saved successfully! (Implementation pending)');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Rule Builder"
      width="85%"
      maxHeight="90vh"
    >
      <div className="rule-builder">
        {context && (
          <div className="rule-context-info">
            <h3>Building rule for:</h3>
            <div className="context-details">
              {context.resource && <div><strong>Resource:</strong> {context.resource}</div>}
              {context.action && <div><strong>Action:</strong> {context.action}</div>}
              {context.field && <div><strong>Field:</strong> {context.field}</div>}
            </div>
          </div>
        )}

        <div className="rule-form">
          <div className="form-section">
            <h3>Basic Information</h3>
            <div className="form-group">
              <label>Rule Name</label>
              <input
                type="text"
                value={rule.name}
                onChange={(e) => setRule({ ...rule, name: e.target.value })}
                placeholder="e.g., Allow admins to read all products"
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                value={rule.description}
                onChange={(e) => setRule({ ...rule, description: e.target.value })}
                placeholder="Describe what this rule does..."
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Effect</label>
              <select
                value={rule.effect}
                onChange={(e) => setRule({ ...rule, effect: e.target.value as 'allow' | 'deny' })}
              >
                <option value="allow">Allow</option>
                <option value="deny">Deny</option>
              </select>
            </div>
          </div>

          <div className="form-section">
            <h3>Principals (Who)</h3>
            <div className="list-input">
              <input
                type="text"
                value={principalInput}
                onChange={(e) => setPrincipalInput(e.target.value)}
                placeholder="e.g., user:john@example.com, role:admin, group:developers"
                onKeyPress={(e) => e.key === 'Enter' && addPrincipal()}
              />
              <button onClick={addPrincipal} className="button secondary">Add</button>
            </div>
            <div className="item-list">
              {rule.principals.map((principal, index) => (
                <div key={index} className="list-item">
                  <span>{principal}</span>
                  <button onClick={() => removePrincipal(index)}>×</button>
                </div>
              ))}
            </div>
          </div>

          <div className="form-section">
            <h3>Resources (What)</h3>
            <div className="list-input">
              <input
                type="text"
                value={resourceInput}
                onChange={(e) => setResourceInput(e.target.value)}
                placeholder="e.g., products/*, products/123, products/sensitive/*"
                onKeyPress={(e) => e.key === 'Enter' && addResource()}
              />
              <button onClick={addResource} className="button secondary">Add</button>
            </div>
            <div className="item-list">
              {rule.resources.map((resource, index) => (
                <div key={index} className="list-item">
                  <span>{resource}</span>
                  <button onClick={() => removeResource(index)}>×</button>
                </div>
              ))}
            </div>
          </div>

          <div className="form-section">
            <h3>Actions (What can they do)</h3>
            <div className="list-input">
              <input
                type="text"
                value={actionInput}
                onChange={(e) => setActionInput(e.target.value)}
                placeholder="e.g., products:read, products:write, products:delete"
                onKeyPress={(e) => e.key === 'Enter' && addAction()}
              />
              <button onClick={addAction} className="button secondary">Add</button>
            </div>
            <div className="item-list">
              {rule.actions.map((action, index) => (
                <div key={index} className="list-item">
                  <span>{action}</span>
                  <button onClick={() => removeAction(index)}>×</button>
                </div>
              ))}
            </div>
          </div>

          <div className="form-section">
            <h3>Conditions (Optional)</h3>
            <button onClick={addCondition} className="button secondary">Add Condition</button>
            {rule.conditions?.map((condition, index) => (
              <div key={index} className="condition-row">
                <input
                  type="text"
                  value={condition.field || ''}
                  onChange={(e) => updateCondition(index, { field: e.target.value })}
                  placeholder="Field name"
                />
                <select
                  value={condition.operator || 'equals'}
                  onChange={(e) => updateCondition(index, { operator: e.target.value as any })}
                >
                  <option value="equals">Equals</option>
                  <option value="not_equals">Not Equals</option>
                  <option value="contains">Contains</option>
                  <option value="exists">Exists</option>
                </select>
                <input
                  type="text"
                  value={condition.value || ''}
                  onChange={(e) => updateCondition(index, { value: e.target.value })}
                  placeholder="Value"
                  disabled={condition.operator === 'exists'}
                />
                <button onClick={() => removeCondition(index)} className="button danger">×</button>
              </div>
            ))}
          </div>

          <div className="form-section">
            <h3>Policy Preview</h3>
            <pre className="policy-preview">{generatePolicyPreview()}</pre>
          </div>

          <div className="form-actions">
            <button onClick={handleSave} className="button primary">Save Rule</button>
            <button onClick={onClose} className="button secondary">Cancel</button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default RuleBuilder;