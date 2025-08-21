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

// Common JWT token fields that might be available
const tokenFields: Config['fields'] = {
  'token.sub': {
    label: 'Subject (User ID)',
    type: 'text',
    valueSources: ['value'],
  },
  'token.name': {
    label: 'User Name',
    type: 'text',
    valueSources: ['value'],
  },
  'token.email': {
    label: 'Email',
    type: 'text',
    valueSources: ['value'],
  },
  'token.roles': {
    label: 'Roles',
    type: 'multiselect',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'admin', title: 'Admin' },
        { value: 'user', title: 'User' },
        { value: 'viewer', title: 'Viewer' },
        { value: 'editor', title: 'Editor' },
      ]
    }
  },
  'token.groups': {
    label: 'AD Groups',
    type: 'multiselect',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [] // Will be populated dynamically
    }
  },
  'token.department': {
    label: 'Department',
    type: 'text',
    valueSources: ['value'],
  },
  'token.aud': {
    label: 'Audience',
    type: 'text',
    valueSources: ['value'],
  },
  'token.iss': {
    label: 'Issuer',
    type: 'text',
    valueSources: ['value'],
  },
  'token.exp': {
    label: 'Expiration Time',
    type: 'datetime',
    valueSources: ['value'],
  },
  'token.iat': {
    label: 'Issued At',
    type: 'datetime',
    valueSources: ['value'],
  },
  'token.scope': {
    label: 'Scopes',
    type: 'multiselect',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [] // Will be populated based on app
    }
  },
  'token.tenant_id': {
    label: 'Tenant ID',
    type: 'text',
    valueSources: ['value'],
  },
  'token.app_id': {
    label: 'Application ID',
    type: 'text',
    valueSources: ['value'],
  },
  'request.ip': {
    label: 'Request IP Address',
    type: 'text',
    valueSources: ['value'],
  },
  'request.method': {
    label: 'HTTP Method',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'GET', title: 'GET' },
        { value: 'POST', title: 'POST' },
        { value: 'PUT', title: 'PUT' },
        { value: 'DELETE', title: 'DELETE' },
        { value: 'PATCH', title: 'PATCH' },
      ]
    }
  },
  'request.path': {
    label: 'Request Path',
    type: 'text',
    valueSources: ['value'],
  },
  'request.time': {
    label: 'Request Time',
    type: 'datetime',
    valueSources: ['value'],
  },
  'resource.owner': {
    label: 'Resource Owner',
    type: 'text',
    valueSources: ['value', 'field'],
  },
  'resource.created_by': {
    label: 'Created By',
    type: 'text',
    valueSources: ['value', 'field'],
  },
  'resource.department': {
    label: 'Resource Department',
    type: 'text',
    valueSources: ['value', 'field'],
  },
  'resource.sensitivity': {
    label: 'Data Sensitivity',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'public', title: 'Public' },
        { value: 'internal', title: 'Internal' },
        { value: 'confidential', title: 'Confidential' },
        { value: 'restricted', title: 'Restricted' },
      ]
    }
  }
};

// Initial query builder config
const InitialConfig: Config = {
  ...BasicConfig,
  fields: tokenFields,
  operators: {
    ...BasicConfig.operators,
  },
  widgets: {
    ...BasicConfig.widgets,
  },
  settings: {
    ...BasicConfig.settings,
    showNot: true,
    canReorder: true,
    canRegroup: true,
    showLabels: true,
    maxNesting: 5,
    renderField: (props: any) => props.value,
  },
};

const RuleBuilder: React.FC<RuleBuilderProps> = ({ isOpen, onClose, context }) => {
  const [config, setConfig] = useState<Config>(InitialConfig);
  const [tree, setTree] = useState<ImmutableTree>(QbUtils.checkTree(QbUtils.loadTree({ id: QbUtils.uuid(), type: 'group' }), config));
  const [sqlOutput, setSqlOutput] = useState<string>('');
  const [jsonOutput, setJsonOutput] = useState<string>('');
  const [selectedOutput, setSelectedOutput] = useState<'sql' | 'json' | 'human'>('sql');

  useEffect(() => {
    // Reset tree when modal opens
    if (isOpen) {
      const emptyTree = QbUtils.checkTree(QbUtils.loadTree({ id: QbUtils.uuid(), type: 'group' }), config);
      setTree(emptyTree);
      setSqlOutput('');
      setJsonOutput('');
    }
  }, [isOpen]);

  useEffect(() => {
    // Update outputs when tree changes
    if (tree) {
      const sqlString = QbUtils.sqlFormat(tree, config) || '';
      setSqlOutput(sqlString);
      
      const jsonTree = QbUtils.getTree(tree);
      setJsonOutput(JSON.stringify(jsonTree, null, 2));
    }
  }, [tree, config]);

  const onChange = (immutableTree: ImmutableTree, config: Config) => {
    setTree(immutableTree);
    setConfig(config);
  };

  const renderBuilder = (props: BuilderProps) => (
    <div className="query-builder-container">
      <Builder {...props} />
    </div>
  );

  const getContextDescription = () => {
    if (!context) return 'General Rule';
    
    if (context.type === 'resource') {
      return `Resource: ${context.resource}`;
    } else if (context.type === 'action') {
      return `Action: ${context.resource}.${context.action}`;
    } else if (context.type === 'field') {
      return `Field: ${context.resource}.${context.action}.${context.field}`;
    }
    return 'General Rule';
  };

  const handleSave = () => {
    const rule = {
      context: context,
      sql: sqlOutput,
      json: jsonOutput,
      tree: QbUtils.getTree(tree),
    };
    
    console.log('Saving rule:', rule);
    
    // In production, this would save to backend
    alert(`Rule saved!\n\nSQL: ${sqlOutput}`);
    onClose();
  };

  const getHumanReadable = () => {
    if (!sqlOutput) return 'No conditions defined';
    
    // Convert SQL to human-readable format
    let readable = sqlOutput;
    readable = readable.replace(/token\./g, 'Token ');
    readable = readable.replace(/request\./g, 'Request ');
    readable = readable.replace(/resource\./g, 'Resource ');
    readable = readable.replace(/AND/g, 'AND');
    readable = readable.replace(/OR/g, 'OR');
    readable = readable.replace(/=/g, 'equals');
    readable = readable.replace(/!=/g, 'not equals');
    readable = readable.replace(/>/g, 'greater than');
    readable = readable.replace(/</g, 'less than');
    readable = readable.replace(/IN/g, 'is one of');
    readable = readable.replace(/NOT IN/g, 'is not one of');
    
    return readable;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Rule Builder - ${getContextDescription()}`}
      width="90%"
      maxHeight="90vh"
    >
      <div className="rule-builder-content">
        <div className="rule-builder-header">
          <p className="rule-description">
            Define access rules based on JWT token claims and request context. 
            These rules will be evaluated at runtime to determine access permissions.
          </p>
        </div>

        <div className="query-builder-wrapper">
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
              className={`output-tab ${selectedOutput === 'sql' ? 'active' : ''}`}
              onClick={() => setSelectedOutput('sql')}
            >
              SQL Output
            </button>
            <button 
              className={`output-tab ${selectedOutput === 'json' ? 'active' : ''}`}
              onClick={() => setSelectedOutput('json')}
            >
              JSON Output
            </button>
            <button 
              className={`output-tab ${selectedOutput === 'human' ? 'active' : ''}`}
              onClick={() => setSelectedOutput('human')}
            >
              Human Readable
            </button>
          </div>
          
          <div className="output-content">
            {selectedOutput === 'sql' && (
              <pre className="output-code sql">
                {sqlOutput || 'No conditions defined'}
              </pre>
            )}
            {selectedOutput === 'json' && (
              <pre className="output-code json">
                {jsonOutput || '{}'}
              </pre>
            )}
            {selectedOutput === 'human' && (
              <div className="output-human">
                {getHumanReadable()}
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