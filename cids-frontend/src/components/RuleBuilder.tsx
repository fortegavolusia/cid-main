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

// Define fields based on security context
const securityFields: Config['fields'] = {
  permission: {
    label: 'Permission',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'select_tables', title: 'Select tables' },
        { value: 'view_data', title: 'View data' },
        { value: 'edit_data', title: 'Edit data' },
        { value: 'delete_data', title: 'Delete data' },
        { value: 'create_tables', title: 'Create tables' },
        { value: 'drop_tables', title: 'Drop tables' },
        { value: 'execute_queries', title: 'Execute queries' },
        { value: 'export_data', title: 'Export data' },
      ],
    },
  },
  user: {
    label: 'User',
    type: 'text',
    valueSources: ['value'],
  },
  role: {
    label: 'Role',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'admin', title: 'Admin' },
        { value: 'editor', title: 'Editor' },
        { value: 'viewer', title: 'Viewer' },
        { value: 'analyst', title: 'Analyst' },
        { value: 'developer', title: 'Developer' },
      ],
    },
  },
  department: {
    label: 'Department',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'engineering', title: 'Engineering' },
        { value: 'sales', title: 'Sales' },
        { value: 'marketing', title: 'Marketing' },
        { value: 'hr', title: 'Human Resources' },
        { value: 'finance', title: 'Finance' },
        { value: 'operations', title: 'Operations' },
      ],
    },
  },
  location: {
    label: 'Location',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'headquarters', title: 'Headquarters' },
        { value: 'remote', title: 'Remote' },
        { value: 'branch_office', title: 'Branch Office' },
        { value: 'home', title: 'Home' },
      ],
    },
  },
  ip_address: {
    label: 'IP Address',
    type: 'text',
    valueSources: ['value'],
  },
  time_range: {
    label: 'Time Range',
    type: 'select',
    valueSources: ['value'],
    fieldSettings: {
      listValues: [
        { value: 'business_hours', title: 'Business Hours' },
        { value: 'after_hours', title: 'After Hours' },
        { value: 'weekends', title: 'Weekends' },
        { value: 'always', title: 'Always' },
      ],
    },
  },
};

// Configure the query builder
const queryBuilderConfig: Config = {
  ...BasicConfig,
  fields: securityFields,
  operators: {
    ...BasicConfig.operators,
    equal: {
      ...BasicConfig.operators.equal,
      label: 'is',
    },
    not_equal: {
      ...BasicConfig.operators.not_equal,
      label: 'is not',
    },
    select_equals: {
      ...BasicConfig.operators.select_equals,
      label: 'is',
    },
    select_not_equals: {
      ...BasicConfig.operators.select_not_equals,
      label: 'is not',
    },
    like: {
      ...BasicConfig.operators.like,
      label: 'contains',
    },
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
    renderSize: 'small',
    renderField: (props: any) => props.value,
    renderOperator: (props: any) => props.value,
    addRuleLabel: '+ Add',
    deleteLabel: 'Delete',
    addGroupLabel: '+ Add Group',
    delGroupLabel: 'Delete',
  },
};

const emptyTree = {
  id: QbUtils.uuid(),
  type: 'group' as const,
};

const RuleBuilder: React.FC<RuleBuilderProps> = ({ isOpen, onClose, context }) => {
  const [tree, setTree] = useState<ImmutableTree>(
    QbUtils.checkTree(QbUtils.loadTree(emptyTree), queryBuilderConfig)
  );
  const [saveLabel, setSaveLabel] = useState('Save');

  useEffect(() => {
    if (isOpen) {
      setTree(QbUtils.checkTree(QbUtils.loadTree(emptyTree), queryBuilderConfig));
      setSaveLabel('Save');
    }
  }, [isOpen]);

  const onChange = useCallback((immutableTree: ImmutableTree, config: Config) => {
    setTree(immutableTree);
  }, []);

  const renderBuilder = useCallback((props: BuilderProps) => (
    <div className="query-builder-simple">
      <Builder {...props} />
    </div>
  ), []);

  const handleSave = () => {
    const jsonTree = QbUtils.getTree(tree);
    console.log('Saving rules:', jsonTree);
    
    // Show feedback
    setSaveLabel('Saved!');
    setTimeout(() => {
      onClose();
    }, 1000);
  };

  const handleCancel = () => {
    onClose();
  };

  const handleClear = () => {
    setTree(QbUtils.checkTree(QbUtils.loadTree(emptyTree), queryBuilderConfig));
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Manage security rules"
      width="700px"
      maxHeight="500px"
    >
      <div className="rule-builder-simple">
        <div className="rule-builder-description">
          Define conditions for data access and permissions
        </div>
        
        <div className="rules-section">
          <div className="rules-header">
            <span className="rules-label">Rules</span>
            <div className="header-actions">
              <button 
                className="link-button"
                onClick={handleClear}
              >
                Clear
              </button>
            </div>
          </div>
          
          <div className="query-wrapper">
            <Query
              {...queryBuilderConfig}
              value={tree}
              onChange={onChange}
              renderBuilder={renderBuilder}
            />
          </div>
        </div>

        <div className="modal-footer">
          <button 
            className="btn-text"
            onClick={handleCancel}
          >
            Cancel
          </button>
          <button 
            className="btn-primary"
            onClick={handleSave}
          >
            {saveLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default RuleBuilder;