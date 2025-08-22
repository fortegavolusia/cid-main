import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import './RuleBuilder.css';

interface RuleBuilderProps {
  isOpen: boolean;
  onClose: () => void;
  context?: {
    type: 'resource' | 'action' | 'field';
    clientId: string;
    appName: string;
    resource?: string;
    action?: string;
    field?: string;
    fieldMetadata?: any;
  };
}

// Common SQL rule templates
const ruleTemplates = [
  {
    name: 'User Email Match',
    rule: 'user_email = @current_user_email',
    description: 'Allow access only to rows where user_email matches logged-in user'
  },
  {
    name: 'Department Match',
    rule: 'department = @current_user_department',
    description: 'Filter data by user\'s department'
  },
  {
    name: 'Role-Based Access',
    rule: 'required_role IN (@current_user_roles)',
    description: 'Check if required role is in user\'s roles'
  },
  {
    name: 'Time-Based Access',
    rule: 'EXTRACT(HOUR FROM CURRENT_TIMESTAMP) BETWEEN 9 AND 17',
    description: 'Allow access only during business hours (9 AM - 5 PM)'
  },
  {
    name: 'Location-Based',
    rule: 'location = \'Headquarters\' OR allow_remote = TRUE',
    description: 'Allow headquarters location or remote-enabled resources'
  },
  {
    name: 'Owner Access',
    rule: 'created_by = @current_user_id OR owner_id = @current_user_id',
    description: 'Allow access to resources owned or created by user'
  },
  {
    name: 'Active Records Only',
    rule: 'status = \'ACTIVE\' AND deleted_at IS NULL',
    description: 'Show only active, non-deleted records'
  },
  {
    name: 'Date Range',
    rule: 'created_date >= CURRENT_DATE - INTERVAL \'30 days\'',
    description: 'Show records from last 30 days'
  }
];

// Common SQL functions and variables for autocomplete
const commonFunctions = [
  '@current_user_email',
  '@current_user_id',
  '@current_user_name',
  '@current_user_department',
  '@current_user_roles',
  '@current_user_groups',
  '@client_ip',
  '@request_time',
  'CURRENT_DATE',
  'CURRENT_TIME',
  'CURRENT_TIMESTAMP',
  'EXTRACT()',
  'DATE_PART()',
  'NOW()',
  'UPPER()',
  'LOWER()',
  'SUBSTRING()',
  'LENGTH()',
  'COALESCE()',
  'CASE WHEN',
  'EXISTS()',
  'NOT EXISTS()',
];

const RuleBuilder: React.FC<RuleBuilderProps> = ({ isOpen, onClose, context }) => {
  const [ruleExpression, setRuleExpression] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [showHelp, setShowHelp] = useState(false);
  const [testResult, setTestResult] = useState<string>('');
  const [isTesting, setIsTesting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      // Reset when modal opens
      setRuleExpression('');
      setSelectedTemplate('');
      setTestResult('');
      setIsTesting(false);
    }
  }, [isOpen]);

  const handleTemplateSelect = (template: typeof ruleTemplates[0]) => {
    setRuleExpression(template.rule);
    setSelectedTemplate(template.name);
  };

  const handleInsertFunction = (func: string) => {
    // Insert function at cursor position or at end
    setRuleExpression(prev => {
      if (prev && !prev.endsWith(' ')) {
        return prev + ' ' + func;
      }
      return prev + func;
    });
  };

  const handleTest = () => {
    setIsTesting(true);
    // Simulate testing the SQL rule
    setTimeout(() => {
      if (!ruleExpression.trim()) {
        setTestResult('✗ Rule cannot be empty');
      } else if (ruleExpression.includes('SELECT') || ruleExpression.includes('DROP') || ruleExpression.includes('DELETE FROM')) {
        setTestResult('✗ Only WHERE clause conditions allowed');
      } else {
        setTestResult('✓ SQL syntax is valid');
      }
      setIsTesting(false);
    }, 500);
  };

  const handleSave = () => {
    const rule = {
      expression: ruleExpression,
      context: context,
      timestamp: new Date().toISOString()
    };
    
    console.log('Saving SQL rule:', rule);
    
    // Show success feedback
    alert('Rule saved successfully!');
    onClose();
  };

  const getContextTitle = () => {
    if (!context) return 'Define SQL Filter';
    
    switch (context.type) {
      case 'resource':
        return `SQL Filter for ${context.resource}`;
      case 'action':
        return `Filter for ${context.action} on ${context.resource}`;
      case 'field':
        return `Field Filter: ${context.field}`;
      default:
        return 'Define SQL Filter';
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={getContextTitle()}
      width="900px"
      maxHeight="700px"
    >
      <div className="rls-rule-builder">
        <div className="rule-builder-layout">
          {/* Left Panel - Templates and Functions */}
          <div className="rule-sidebar">
            <div className="sidebar-section">
              <h4>Common Filters</h4>
              <div className="template-list">
                {ruleTemplates.map((template, index) => (
                  <div
                    key={index}
                    className={`template-item ${selectedTemplate === template.name ? 'selected' : ''}`}
                    onClick={() => handleTemplateSelect(template)}
                  >
                    <div className="template-name">{template.name}</div>
                    <div className="template-desc">{template.description}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="sidebar-section">
              <h4>Variables & Functions</h4>
              <div className="function-list">
                {commonFunctions.map((func, index) => (
                  <button
                    key={index}
                    className="function-btn"
                    onClick={() => handleInsertFunction(func)}
                    title="Click to insert"
                  >
                    {func}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Editor Area */}
          <div className="rule-editor-area">
            <div className="editor-header">
              <label className="editor-label">SQL WHERE clause:</label>
              <button 
                className="help-toggle"
                onClick={() => setShowHelp(!showHelp)}
              >
                {showHelp ? 'Hide Help' : 'Show Help'}
              </button>
            </div>

            {showHelp && (
              <div className="help-panel">
                <p><strong>How to write SQL filter expressions:</strong></p>
                <ul>
                  <li>Use column names directly: <code>department = 'Sales'</code></li>
                  <li>Use @ variables for user context: <code>@current_user_email</code></li>
                  <li>Operators: =, !=, &gt;, &lt;, &gt;=, &lt;=, IN, NOT IN, LIKE, IS NULL</li>
                  <li>Combine conditions: AND, OR, NOT</li>
                  <li>String values need quotes: <code>'value'</code></li>
                  <li>Use parentheses for complex logic: <code>(A OR B) AND C</code></li>
                </ul>
              </div>
            )}

            <div className="editor-container">
              <textarea
                className="rule-editor"
                value={ruleExpression}
                onChange={(e) => setRuleExpression(e.target.value)}
                placeholder="Enter your SQL WHERE clause here...&#10;&#10;Example: department = 'Sales' AND region IN ('North', 'South')&#10;Example: created_by = @current_user_id OR is_public = TRUE"
                spellCheck={false}
                rows={8}
              />
              
              <div className="editor-status">
                <span className="char-count">
                  {ruleExpression.length} characters
                </span>
                {testResult && (
                  <span className={`test-result ${testResult.includes('✓') ? 'valid' : 'invalid'}`}>
                    {testResult}
                  </span>
                )}
              </div>
            </div>

            <div className="example-section">
              <h5>Example SQL Filters:</h5>
              <code className="example-code">
                user_email = @current_user_email
              </code>
              <code className="example-code">
                department = 'Sales' OR is_public = TRUE
              </code>
              <code className="example-code">
                created_by = @current_user_id AND status = 'ACTIVE'
              </code>
              <code className="example-code">
                created_date &gt;= CURRENT_DATE - INTERVAL '7 days'
              </code>
              <code className="example-code">
                role IN (@current_user_roles) AND location = 'HQ'
              </code>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="rule-builder-footer">
          <div className="footer-left">
            <button
              className="btn-test"
              onClick={handleTest}
              disabled={isTesting || !ruleExpression.trim()}
            >
              {isTesting ? 'Testing...' : 'Validate SQL'}
            </button>
          </div>
          <div className="footer-right">
            <button className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button 
              className="btn-save-rule"
              onClick={handleSave}
              disabled={!ruleExpression.trim()}
            >
              Save Filter
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default RuleBuilder;