import React, { useState, useEffect, useCallback } from 'react';
import Modal from './Modal';
import './RuleBuilder.css';

import {
  Query,
  Builder,
  BasicConfig,
  Utils as QbUtils,
  Config,
  ImmutableTree,
  BuilderProps,
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

// Initialize config
const InitialConfig: Config = {
  ...BasicConfig,
  fields: {
    user_email: {
      label: 'User Email',
      type: 'text',
      valueSources: ['value'],
    },
    user_name: {
      label: 'User Name',
      type: 'text',
      valueSources: ['value'],
    },
    user_department: {
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
        ],
      },
    },
    user_role: {
      label: 'User Role',
      type: 'select',
      valueSources: ['value'],
      fieldSettings: {
        listValues: [
          { value: 'admin', title: 'Administrator' },
          { value: 'manager', title: 'Manager' },
          { value: 'user', title: 'Regular User' },
          { value: 'viewer', title: 'Viewer' },
          { value: 'editor', title: 'Editor' },
        ],
      },
    },
    user_location: {
      label: 'User Location',
      type: 'select',
      valueSources: ['value'],
      fieldSettings: {
        listValues: [
          { value: 'US', title: 'United States' },
          { value: 'EU', title: 'Europe' },
          { value: 'Asia', title: 'Asia' },
          { value: 'Remote', title: 'Remote' },
        ],
      },
    },
    request_time: {
      label: 'Request Time',
      type: 'select',
      valueSources: ['value'],
      fieldSettings: {
        listValues: [
          { value: 'business_hours', title: 'Business Hours (9-5)' },
          { value: 'after_hours', title: 'After Hours' },
          { value: 'weekend', title: 'Weekend' },
        ],
      },
    },
    data_sensitivity: {
      label: 'Data Sensitivity',
      type: 'select',
      valueSources: ['value'],
      fieldSettings: {
        listValues: [
          { value: 'public', title: 'Public' },
          { value: 'internal', title: 'Internal' },
          { value: 'confidential', title: 'Confidential' },
          { value: 'restricted', title: 'Restricted' },
        ],
      },
    },
  },
  operators: {
    ...BasicConfig.operators,
  },
  widgets: {
    ...BasicConfig.widgets,
  },
  settings: {
    ...BasicConfig.settings,
    showNot: false,
    showLock: false,
    canReorder: false,
    canRegroup: false,
    maxNesting: 1,
    showLabels: false,
  },
  conjunctions: {
    AND: {
      label: 'ALL',
      formatConj: (children: any, conj: string, isForDisplay?: boolean) => {
        return isForDisplay ? 'ALL conditions must be true' : 'AND';
      },
    },
    OR: {
      label: 'ANY',
      formatConj: (children: any, conj: string, isForDisplay?: boolean) => {
        return isForDisplay ? 'ANY condition can be true' : 'OR';
      },
    },
  },
};

// Create empty tree
const queryValue = {
  id: QbUtils.uuid(),
  type: 'group',
  properties: {
    conjunction: 'AND',
  },
};

const RuleBuilder: React.FC<RuleBuilderProps> = ({ isOpen, onClose, context }) => {
  const [tree, setTree] = useState<ImmutableTree>(
    QbUtils.checkTree(QbUtils.loadTree(queryValue), InitialConfig)
  );
  const [config] = useState(InitialConfig);

  useEffect(() => {
    if (isOpen) {
      // Reset tree when modal opens
      setTree(QbUtils.checkTree(QbUtils.loadTree(queryValue), config));
    }
  }, [isOpen, config]);

  const onChange = useCallback((immutableTree: ImmutableTree, config: Config) => {
    setTree(immutableTree);
  }, []);

  const renderBuilder = useCallback((props: BuilderProps) => (
    <div className="query-builder-container">
      <Builder {...props} />
    </div>
  ), []);

  const getContextTitle = () => {
    if (!context) return 'Define Access Rule';
    
    switch (context.type) {
      case 'resource':
        return `Access Rules for ${context.resource}`;
      case 'action':
        return `Rules for ${context.action} on ${context.resource}`;
      case 'field':
        return `Field Access: ${context.field}`;
      default:
        return 'Define Access Rule';
    }
  };

  const getSqlOutput = () => {
    try {
      return QbUtils.sqlFormat(tree, config) || '';
    } catch (error) {
      return '';
    }
  };

  const getJsonOutput = () => {
    try {
      return JSON.stringify(QbUtils.getTree(tree), null, 2);
    } catch (error) {
      return '{}';
    }
  };

  const getPlainEnglish = () => {
    const treeData = QbUtils.getTree(tree);
    if (!treeData || !treeData.children1 || treeData.children1.length === 0) {
      return 'No conditions defined. Click "+ Add rule" to start.';
    }

    const conjunction = treeData.properties?.conjunction || 'AND';
    const conjText = conjunction === 'OR' ? 'ANY' : 'ALL';
    
    let result = `Grant access when ${conjText} of these conditions are met:\n\n`;
    
    treeData.children1.forEach((child: any, index: number) => {
      if (child.type === 'rule' && child.properties) {
        const field = config.fields[child.properties.field];
        const fieldLabel = field?.label || child.properties.field;
        const value = child.properties.value?.[0] || '';
        const operator = child.properties.operator;
        
        let opText = 'equals';
        if (operator === 'not_equal') opText = 'is not';
        if (operator === 'less') opText = 'is less than';
        if (operator === 'greater') opText = 'is greater than';
        
        result += `${index + 1}. ${fieldLabel} ${opText} "${value}"\n`;
      }
    });
    
    return result;
  };

  const handleSave = () => {
    const output = {
      sql: getSqlOutput(),
      json: getJsonOutput(),
      plain: getPlainEnglish(),
      context: context,
    };
    
    console.log('Saving rule:', output);
    alert('Rule saved successfully!');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={getContextTitle()}
      width="80%"
      maxHeight="85vh"
    >
      <div className="rule-builder-content">
        <div className="rule-intro">
          <h3>Build Your Access Rules</h3>
          <p>
            Define who can access this resource by setting conditions. 
            Choose whether ALL conditions must be met (AND) or if ANY single condition is enough (OR).
          </p>
        </div>

        <div className="builder-section">
          <div className="builder-label">Conditions:</div>
          <Query
            {...config}
            value={tree}
            onChange={onChange}
            renderBuilder={renderBuilder}
          />
        </div>

        <div className="preview-section">
          <h4>Rule Preview</h4>
          <div className="preview-tabs">
            <div className="preview-tab active">Plain English</div>
            <div className="preview-tab">SQL</div>
            <div className="preview-tab">JSON</div>
          </div>
          <div className="preview-content">
            <pre>{getPlainEnglish()}</pre>
          </div>
        </div>

        <div className="builder-actions">
          <button className="btn-save" onClick={handleSave}>
            Save Rule
          </button>
          <button className="btn-cancel" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default RuleBuilder;