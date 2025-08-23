import React, { useState } from 'react';
import TokenBuilder from '../components/TokenBuilder';
import TokenTemplates from '../components/TokenTemplates';
import './TokenAdministrationPage.css';

const TokenAdministrationPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('builder');
  const [templateToLoad, setTemplateToLoad] = useState<any>(null);

  const handleLoadTemplate = (template: any) => {
    setTemplateToLoad(template);
    setActiveTab('builder');
  };

  return (
    <div className="token-admin-page">
      <div className="page-header">
        <h1>Token Administration</h1>
        <p className="page-subtitle">Manage JWT token structures and templates</p>
      </div>

      <div className="tab-navigation">
        <button 
          className={`tab-button ${activeTab === 'builder' ? 'active' : ''}`}
          onClick={() => setActiveTab('builder')}
        >
          Token Builder
        </button>
        <button 
          className={`tab-button ${activeTab === 'templates' ? 'active' : ''}`}
          onClick={() => setActiveTab('templates')}
        >
          Templates
        </button>
        <button 
          className={`tab-button ${activeTab === 'testing' ? 'active' : ''}`}
          onClick={() => setActiveTab('testing')}
        >
          Testing
        </button>
        <button 
          className={`tab-button ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          Settings
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'builder' && <TokenBuilder templateToLoad={templateToLoad} />}
        {activeTab === 'templates' && <TokenTemplates onLoadTemplate={handleLoadTemplate} />}
        {activeTab === 'testing' && (
          <div className="coming-soon">
            <h3>Token Testing</h3>
            <p>Test token generation with sample data</p>
            <span className="placeholder">Coming Soon</span>
          </div>
        )}
        {activeTab === 'settings' && (
          <div className="coming-soon">
            <h3>Token Settings</h3>
            <p>Configure expiration, algorithms, and defaults</p>
            <span className="placeholder">Coming Soon</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default TokenAdministrationPage;