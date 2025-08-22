import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import './RuleBuilder.css';

// React Awesome Query Builder imports
import {
  Query,
  Builder,
  BasicConfig,
  Utils as QbUtils,
  JsonGroup,
  Config,
  ImmutableTree,
  BuilderProps
} from '@react-awesome-query-builder/ui';
import '@react-awesome-query-builder/ui/css/styles.css';

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

// User-friendly field configuration
const tokenFields: Config['fields'] = {
  'user.email': {
    label: 'User Email',
    type: 'text',
    valueSources: ['value'],
    preferWidgets: ['text'],
  },
  'user.name': {
    label: 'User Name',
    type: 'text',
    valueSources: ['value'],
    preferWidgets: ['text'],
  },
  'user.department': {
    label: 'User Department',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'IT', title: 'IT' },
        { value: 'HR', title: 'Human Resources' },
        { value: 'Finance', title: 'Finance' },
        { value: 'Sales', title: 'Sales' },
        { value: 'Marketing', title: 'Marketing' },
        { value: 'Engineering', title: 'Engineering' },
        { value: 'Operations', title: 'Operations' },
      ]
    }
  },
  'user.role': {
    label: 'User Role',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'admin', title: 'Administrator' },
        { value: 'manager', title: 'Manager' },
        { value: 'user', title: 'Regular User' },
        { value: 'viewer', title: 'Viewer Only' },
        { value: 'editor', title: 'Editor' },
      ]
    }
  },
  'user.groups': {
    label: 'User Groups',
    type: 'multiselect',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'AllEmployees', title: 'All Employees' },
        { value: 'Managers', title: 'Managers' },
        { value: 'Executives', title: 'Executives' },
        { value: 'Contractors', title: 'Contractors' },
        { value: 'RemoteWorkers', title: 'Remote Workers' },
      ]
    }
  },
  'user.location': {
    label: 'User Location',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'US', title: 'United States' },
        { value: 'EU', title: 'Europe' },
        { value: 'Asia', title: 'Asia' },
        { value: 'Remote', title: 'Remote' },
      ]
    }
  },
  'request.time_of_day': {
    label: 'Time of Day',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'business_hours', title: 'Business Hours (9AM-5PM)' },
        { value: 'after_hours', title: 'After Hours' },
        { value: 'weekend', title: 'Weekend' },
      ]
    }
  },
  'request.ip_location': {
    label: 'Request Location',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'internal', title: 'Internal Network' },
        { value: 'vpn', title: 'VPN' },
        { value: 'external', title: 'External/Public' },
      ]
    }
  },
  'resource.sensitivity': {
    label: 'Data Sensitivity',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'public', title: 'Public' },
        { value: 'internal', title: 'Internal Use' },
        { value: 'confidential', title: 'Confidential' },
        { value: 'restricted', title: 'Highly Restricted' },
      ]
    }
  },
  'resource.owner': {
    label: 'Resource Owner',
    type: 'text',
    valueSources: ['value'],
    preferWidgets: ['text'],
  }
};

// Simplified, user-friendly config
const InitialConfig: Config = {
  ...BasicConfig,
  fields: tokenFields,
  operators: {
    ...BasicConfig.operators,
    equal: {
      ...BasicConfig.operators.equal,
      label: 'is'
    },
    not_equal: {
      ...BasicConfig.operators.not_equal,
      label: 'is not'
    },
    less: {
      ...BasicConfig.operators.less,
      label: 'less than'
    },
    greater: {
      ...BasicConfig.operators.greater,
      label: 'greater than'
    },
    select_equals: {
      ...BasicConfig.operators.select_equals,
      label: 'is'
    },
    select_not_equals: {
      ...BasicConfig.operators.select_not_equals,
      label: 'is not'
    },
    multiselect_contains: {
      ...BasicConfig.operators.multiselect_contains,
      label: 'includes'
    },
    multiselect_not_contains: {
      ...BasicConfig.operators.multiselect_not_contains,
      label: 'does not include'
    },
  },
  widgets: {
    ...BasicConfig.widgets,
  },
  settings: {
    ...BasicConfig.settings,
    showNot: false, // Hide the NOT checkbox
    showLock: false,
    canReorder: false, // Simplify by removing drag handles
    canRegroup: false, // Simplify by removing regroup
    showLabels: true,
    maxNesting: 3,
    addRuleLabel: '+ Add Condition',
    addGroupLabel: '+ Add Group',
    delGroupLabel: 'Delete Group',
    delRuleLabel: 'Delete',
    valueLabel: 'Value',
    fieldLabel: 'When',
    operatorLabel: 'Is',
    conjunctionLabel: 'Match',
    renderConjsAsRadios: false, // Keep as buttons
    renderField: (props: any) => props.value,
    renderOperator: (props: any) => props.value,
    renderConjs: (props: any, {renderProps}: any) => {
      return (
        <div className="conjunction-wrapper">
          <span className="conjunction-label">Match:</span>
          <div className="conjunction-buttons">
            {renderProps({
              ...props,
              conjunctionOptions: {
                AND: { label: 'ALL conditions', className: 'conj-and' },
                OR: { label: 'ANY condition', className: 'conj-or' }
              }
            })}
          </div>
        </div>
      );
    },
  },
};

const RuleBuilder: React.FC<RuleBuilderProps> = ({ isOpen, onClose, context }) => {
  const [config, setConfig] = useState<Config>(InitialConfig);
  const [tree, setTree] = useState<ImmutableTree>(
    QbUtils.checkTree(QbUtils.loadTree({ 
      id: QbUtils.uuid(), 
      type: 'group',
      properties: {
        conjunction: 'AND'
      }
    }), config)
  );
  const [selectedOutput, setSelectedOutput] = useState<'simple' | 'technical'>('simple');

  useEffect(() => {
    // Reset tree when modal opens
    if (isOpen) {
      const emptyTree = QbUtils.checkTree(QbUtils.loadTree({ 
        id: QbUtils.uuid(), 
        type: 'group',
        properties: {
          conjunction: 'AND'
        }
      }), config);
      setTree(emptyTree);
    }
  }, [isOpen]);

  const onChange = (immutableTree: ImmutableTree, config: Config) => {
    setTree(immutableTree);
    setConfig(config);
  };

  const renderBuilder = (props: BuilderProps) => (
    <div className="query-builder-container user-friendly">
      <Builder {...props} />
    </div>
  );

  const getContextDescription = () => {
    if (!context) return 'Access Rule';
    
    if (context.type === 'resource') {
      return `Who can access ${context.resource}?`;
    } else if (context.type === 'action') {
      return `Who can ${context.action} ${context.resource}?`;
    } else if (context.type === 'field') {
      return `Who can see ${context.field} in ${context.resource}?`;
    }
    return 'Access Rule';
  };

  const getSimpleDescription = () => {
    const jsonTree = QbUtils.getTree(tree);
    if (!jsonTree || !jsonTree.children1 || jsonTree.children1.length === 0) {
      return 'No conditions set - Access will be denied by default';
    }
    
    const conjunction = jsonTree.properties?.conjunction === 'OR' ? 'ANY' : 'ALL';
    const ruleCount = jsonTree.children1.length;
    
    return `Access granted when ${conjunction} of the ${ruleCount} condition${ruleCount > 1 ? 's' : ''} below ${ruleCount > 1 ? 'are' : 'is'} met:`;
  };

  const handleSave = () => {
    const jsonTree = QbUtils.getTree(tree);
    const sqlString = QbUtils.sqlFormat(tree, config);
    
    const rule = {
      context: context,
      sql: sqlString,
      json: jsonTree,
      description: getSimpleDescription(),
    };
    
    console.log('Saving rule:', rule);
    
    // In production, this would save to backend
    alert(`Rule saved!\n\n${getSimpleDescription()}`);
    onClose();
  };

  const getTechnicalOutput = () => {
    const sqlString = QbUtils.sqlFormat(tree, config) || 'TRUE';
    const jsonTree = QbUtils.getTree(tree);
    
    return {
      sql: sqlString,
      json: JSON.stringify(jsonTree, null, 2)
    };
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={getContextDescription()}
      width="85%"
      maxHeight="90vh"
    >
      <div className="rule-builder-content">
        <div className="rule-builder-header">
          <h3 className="rule-title">Define Access Conditions</h3>
          <p className="rule-description">
            Set up conditions that must be met for users to access this resource. 
            You can combine multiple conditions using "ALL" (every condition must be true) 
            or "ANY" (at least one condition must be true).
          </p>
        </div>

        <div className="rule-summary">
          <div className="summary-icon">ℹ️</div>
          <div className="summary-text">{getSimpleDescription()}</div>
        </div>

        <div className="query-builder-wrapper user-friendly">
          <Query
            {...config}
            value={tree}
            onChange={onChange}
            renderBuilder={renderBuilder}
          />
        </div>

        <div className="rule-output-section">
          <div className="output-tabs">
            <button 
              className={`output-tab ${selectedOutput === 'simple' ? 'active' : ''}`}
              onClick={() => setSelectedOutput('simple')}
            >
              Simple View
            </button>
            <button 
              className={`output-tab ${selectedOutput === 'technical' ? 'active' : ''}`}
              onClick={() => setSelectedOutput('technical')}
            >
              Technical Details
            </button>
          </div>
          
          <div className="output-content">
            {selectedOutput === 'simple' ? (
              <div className="output-simple">
                <h4>Rule Summary:</h4>
                <p>{getSimpleDescription()}</p>
                {QbUtils.getTree(tree)?.children1?.map((child: any, index: number) => {
                  if (child.type === 'rule') {
                    const field = tokenFields[child.properties.field];
                    const fieldLabel = field?.label || child.properties.field;
                    const operator = child.properties.operator;
                    const value = child.properties.value?.[0];
                    
                    let operatorText = 'equals';
                    if (operator === 'not_equal' || operator === 'select_not_equals') operatorText = 'is not';
                    if (operator === 'less') operatorText = 'is less than';
                    if (operator === 'greater') operatorText = 'is greater than';
                    if (operator === 'multiselect_contains') operatorText = 'includes';
                    if (operator === 'multiselect_not_contains') operatorText = 'does not include';
                    
                    return (
                      <div key={index} className="condition-item">
                        • {fieldLabel} {operatorText} "{value}"
                      </div>
                    );
                  }
                  return null;
                })}
              </div>
            ) : (
              <div className="output-technical">
                <div className="technical-section">
                  <h5>SQL Query:</h5>
                  <pre className="output-code sql">{getTechnicalOutput().sql}</pre>
                </div>
                <div className="technical-section">
                  <h5>JSON Structure:</h5>
                  <pre className="output-code json">{getTechnicalOutput().json}</pre>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="rule-builder-actions">
          <button className="button primary" onClick={handleSave}>
            Save Rule
          </button>
          <button className="button secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default RuleBuilder;