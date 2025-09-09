import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import adminService from '../services/adminService';
import type { AppInfo } from '../types/admin';
import RolesModal from '../components/RolesModal';
import APIKeyModal from '../components/APIKeyModal';

// Main Container
const PageContainer = styled.div`
  padding: 0;
  background: transparent;
`;

const PageHeader = styled.div`
  background: #0b3b63;
  padding: 20px 40px;
  margin: -24px -24px 32px -24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  height: 105px;
  display: flex;
  align-items: center;
`;

const HeaderContent = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
`;

const PageTitle = styled.h1`
  color: white;
  font-size: 28px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 16px;
  
  i {
    font-size: 24px;
    opacity: 0.9;
  }
`;

const PageSubtitle = styled.p`
  color: rgba(255, 255, 255, 0.9);
  margin: 8px 0 0 0;
  font-size: 14px;
`;

const HeaderActions = styled.div`
  display: flex;
  gap: 12px;
`;

const StatsCard = styled.div`
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  padding: 6px 12px;
  color: white;
  min-width: 85px;
  text-align: center;
`;

const StatNumber = styled.div`
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 1px;
`;

const StatLabel = styled.div`
  font-size: 10px;
  opacity: 0.9;
  text-transform: uppercase;
`;

// Search and Filter Bar
const ControlBar = styled.div`
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
`;

const SearchBox = styled.div`
  flex: 1;
  min-width: 300px;
  position: relative;
`;

const SearchInput = styled.input`
  width: 100%;
  padding: 12px 16px 12px 44px;
  border: 2px solid #e1e8ed;
  border-radius: 12px;
  font-size: 14px;
  transition: all 0.3s ease;
  background: white;
  
  &:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }
  
  &::placeholder {
    color: #94a3b8;
  }
`;

const SearchIcon = styled.i`
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
`;

const FilterButton = styled.button`
  padding: 12px 24px;
  background: white;
  border: 2px solid #e1e8ed;
  border-radius: 12px;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  
  &:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
  }
  
  &.active {
    background: #0b3b63;
    color: white;
    border-color: #0b3b63;
  }
`;

const CreateButton = styled.button`
  padding: 12px 24px;
  background: #0b3b63;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 12px rgba(11, 59, 99, 0.3);
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(11, 59, 99, 0.4);
    background: #0a3357;
  }
`;

// Apps Grid
const AppsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
`;

const AppCard = styled.div`
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #e1e8ed;
  overflow: hidden;
  transition: all 0.3s ease;
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  }
`;

const AppCardHeader = styled.div<{ $isActive?: boolean }>`
  padding: 20px 24px;
  background: ${props => props.$isActive === false ? '#e5e7eb' : '#f8fafc'};
  border-bottom: 1px solid #e1e8ed;
`;

const AppName = styled.h3`
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #334155;
`;

const AppStatus = styled.div<{ $isActive: boolean }>`
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
`;

const StatusBadge = styled.span<{ $isActive: boolean }>`
  font-size: 11px;
  padding: 4px 10px;
  background: ${props => props.$isActive ? '#10b981' : '#6b7280'};
  color: white;
  border-radius: 6px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const ToggleButton = styled.button<{ $isActive: boolean }>`
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: ${props => props.$isActive ? '#10b981' : '#6b7280'};
  border: none;
  position: relative;
  cursor: pointer;
  transition: all 0.3s ease;
  
  &:hover {
    opacity: 0.8;
  }
  
  &::after {
    content: '';
    position: absolute;
    top: 2px;
    left: ${props => props.$isActive ? '22px' : '2px'};
    width: 20px;
    height: 20px;
    background: white;
    border-radius: 50%;
    transition: all 0.3s ease;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }
`;

const AppId = styled.div`
  font-size: 12px;
  color: #64748b;
  margin-top: 8px;
  font-family: 'Monaco', 'Courier New', monospace;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const CopyButton = styled.button`
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 2px 4px;
  display: inline-flex;
  align-items: center;
  transition: color 0.2s;
  
  &:hover {
    color: #0b3b63;
  }
  
  &.copied {
    color: #10b981;
  }
`;

const AppCardBody = styled.div`
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  flex: 1;
`;

const AppInfo = styled.div`
  margin-bottom: 16px;
  flex: 1;
`;

const InfoRow = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  color: #64748b;
  font-size: 14px;
  
  i {
    width: 20px;
    text-align: center;
    color: #94a3b8;
  }
  
  strong {
    color: #334155;
    font-weight: 500;
  }
`;

const RedirectUris = styled.div`
  background: #f8fafc;
  border: 1px solid #e1e8ed;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
`;

const UriList = styled.ul`
  margin: 8px 0 0 0;
  padding-left: 20px;
  
  li {
    font-size: 13px;
    color: #64748b;
    margin-bottom: 4px;
    word-break: break-all;
  }
`;

const CardActions = styled.div`
  display: flex;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid #e1e8ed;
  margin-top: auto;
`;

const ActionButton = styled.button`
  flex: 1;
  min-width: 80px;
  height: 70px;
  padding: 12px 8px;
  background: white;
  border: 1px solid #e1e8ed;
  border-radius: 8px;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  
  i {
    font-size: 18px;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  span {
    font-weight: 500;
    line-height: 1.2;
  }
  
  &:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
    color: #334155;
  }
  
  &.primary {
    background: #0b3b63;
    color: white;
    border-color: #0b3b63;
    
    &:hover {
      background: #0a3357;
    }
  }
  
  &.danger {
    color: #ef4444;
    border-color: #fecaca;
    
    &:hover {
      background: #fef2f2;
      border-color: #ef4444;
    }
  }
  
  &.warning {
    background: #fbbf24;
    color: white;
    border-color: #fbbf24;
    
    &:hover {
      background: #f59e0b;
      border-color: #f59e0b;
    }
  }
`;

// Empty State
const EmptyState = styled.div`
  text-align: center;
  padding: 80px 40px;
  background: white;
  border-radius: 16px;
  border: 2px dashed #e1e8ed;
`;

const EmptyIcon = styled.div`
  font-size: 64px;
  color: #cbd5e1;
  margin-bottom: 24px;
`;

const EmptyTitle = styled.h3`
  color: #475569;
  font-size: 20px;
  margin-bottom: 8px;
`;

const EmptyText = styled.p`
  color: #94a3b8;
  font-size: 14px;
  margin-bottom: 24px;
`;

// Modal Styles
const Modal = styled.div<{ $isOpen: boolean }>`
  display: ${props => props.$isOpen ? 'flex' : 'none'};
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  align-items: center;
  justify-content: center;
  z-index: 10000;
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 12px;
  padding: 32px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
`;

const ModalTitle = styled.h2`
  margin: 0 0 24px 0;
  color: #1a202c;
  font-size: 24px;
`;

const FormGroup = styled.div`
  margin-bottom: 20px;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 8px;
  color: #4a5568;
  font-size: 14px;
  font-weight: 500;
`;

const Input = styled.input`
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  
  &:focus {
    outline: none;
    border-color: #0b3b63;
    box-shadow: 0 0 0 3px rgba(11, 59, 99, 0.1);
  }
`;

const Textarea = styled.textarea`
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  min-height: 100px;
  
  &:focus {
    outline: none;
    border-color: #0b3b63;
    box-shadow: 0 0 0 3px rgba(11, 59, 99, 0.1);
  }
`;

const Checkbox = styled.input`
  margin-right: 8px;
`;

const ModalActions = styled.div`
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e2e8f0;
`;

const ModalButton = styled.button`
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  
  &.primary {
    background: #0b3b63;
    color: white;
    border: none;
    
    &:hover {
      background: #0a3357;
    }
  }
  
  &.secondary {
    background: white;
    color: #4a5568;
    border: 1px solid #e2e8f0;
    
    &:hover {
      background: #f7fafc;
    }
  }
`;

const AppAdministration: React.FC = () => {
  const { user } = useAuth();
  const [apps, setApps] = useState<AppInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'inactive'>('all');
  const [selectedApp, setSelectedApp] = useState<AppInfo | null>(null);
  const [showRolesModal, setShowRolesModal] = useState(false);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    owner_email: '',
    redirect_uris: [''],
    allow_discovery: false,
    discovery_endpoint: ''
  });

  useEffect(() => {
    loadApps();
  }, []);

  const loadApps = async () => {
    try {
      setLoading(true);
      const appsData = await adminService.getApps();
      console.log('Apps loaded from API:', appsData); // Debug log
      setApps(appsData);
    } catch (err) {
      setError('Failed to load applications');
      console.error('Failed to load apps:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEditApp = (app: AppInfo) => {
    setSelectedApp(app);
    setFormData({
      name: app.name,
      description: app.description || '',
      owner_email: app.owner_email,
      redirect_uris: app.redirect_uris?.length ? app.redirect_uris : [''],
      allow_discovery: app.allow_discovery || false,
      discovery_endpoint: app.discovery_endpoint || ''
    });
    setShowEditModal(true);
  };
  
  const handleActivateApp = async (app: AppInfo) => {
    if (!confirm(`Are you sure you want to activate "${app.name}"?`)) {
      return;
    }
    
    try {
      // Update app to set is_active to true
      await adminService.updateApp(app.client_id, {
        ...app,
        is_active: true
      });
      await loadApps();
      alert(`Application "${app.name}" has been activated successfully!`);
    } catch (err) {
      console.error('Failed to activate app:', err);
      alert('Failed to activate application');
    }
  };
  
  const handleToggleAppStatus = async (app: AppInfo) => {
    const newStatus = !app.is_active;
    const action = newStatus ? 'activate' : 'deactivate';
    
    if (!confirm(`Are you sure you want to ${action} "${app.name}"?`)) {
      return;
    }
    
    try {
      await adminService.updateApp(app.client_id, {
        ...app,
        is_active: newStatus
      });
      await loadApps();
      alert(`Application "${app.name}" has been ${newStatus ? 'activated' : 'deactivated'} successfully!`);
    } catch (err) {
      console.error(`Failed to ${action} app:`, err);
      alert(`Failed to ${action} application`);
    }
  };
  
  const handleCreateApp = () => {
    setFormData({
      name: '',
      description: '',
      owner_email: '',
      redirect_uris: [''],
      allow_discovery: false,
      discovery_endpoint: ''
    });
    setShowCreateModal(true);
  };
  
  const handleSubmitCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        redirect_uris: formData.redirect_uris.filter(uri => uri.trim())
      };
      const result = await adminService.createApp(payload);
      
      let message = `App registered successfully!\n\nClient ID: ${result.app.client_id}\nClient Secret: ${result.client_secret}`;
      message += `\n\n⚠️ SAVE THE CLIENT SECRET NOW!\nIt won't be shown again.`;
      
      alert(message);
      setShowCreateModal(false);
      await loadApps();
    } catch (err: any) {
      alert(err.message || 'Failed to create app');
    }
  };
  
  const handleSubmitEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedApp) return;
    
    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        redirect_uris: formData.redirect_uris.filter(uri => uri.trim()),
        allow_discovery: formData.allow_discovery,
        discovery_endpoint: formData.discovery_endpoint || null
      };
      
      await adminService.updateApp(selectedApp.client_id, payload);
      alert('App updated successfully!');
      setShowEditModal(false);
      await loadApps();
    } catch (err: any) {
      alert(err.message || 'Failed to update app');
    }
  };
  
  const handleRedirectUriChange = (index: number, value: string) => {
    const newUris = [...formData.redirect_uris];
    newUris[index] = value;
    setFormData({ ...formData, redirect_uris: newUris });
  };
  
  const addRedirectUri = () => {
    setFormData({ ...formData, redirect_uris: [...formData.redirect_uris, ''] });
  };
  
  const removeRedirectUri = (index: number) => {
    const newUris = formData.redirect_uris.filter((_, i) => i !== index);
    setFormData({ ...formData, redirect_uris: newUris.length ? newUris : [''] });
  };
  
  const handleCopyClientId = (clientId: string) => {
    navigator.clipboard.writeText(clientId);
    setCopiedId(clientId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDeleteApp = async (app: AppInfo) => {
    if (!confirm(`Are you sure you want to delete "${app.name}"?`)) {
      return;
    }
    
    try {
      await adminService.deleteApp(app.client_id);
      await loadApps();
    } catch (err) {
      console.error('Failed to delete app:', err);
      alert('Failed to delete application');
    }
  };

  const handleManageRoles = (app: AppInfo) => {
    setSelectedApp(app);
    setShowRolesModal(true);
  };

  const handleManageApiKeys = (app: AppInfo) => {
    setSelectedApp(app);
    setShowApiKeyModal(true);
  };

  const filteredApps = apps.filter(app => {
    const matchesSearch = app.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          app.client_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          app.owner_email.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesFilter = filterStatus === 'all' || 
                          (filterStatus === 'active' && app.is_active) ||
                          (filterStatus === 'inactive' && !app.is_active);
    
    return matchesSearch && matchesFilter;
  });

  const activeCount = apps.filter(app => app.is_active).length;
  const inactiveCount = apps.filter(app => !app.is_active).length;

  if (loading) {
    return (
      <PageContainer>
        <div style={{ textAlign: 'center', padding: '80px 40px' }}>
          <i className="fas fa-spinner fa-spin" style={{ fontSize: '32px', color: '#94a3b8' }}></i>
          <p style={{ marginTop: '16px', color: '#94a3b8' }}>Loading applications...</p>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader>
        <HeaderContent>
          <div>
            <PageTitle>
              <i className="fas fa-cogs"></i>
              App Administration
            </PageTitle>
            <PageSubtitle>Manage registered applications and their configurations</PageSubtitle>
          </div>
          <HeaderActions>
            <StatsCard>
              <StatNumber>{activeCount}</StatNumber>
              <StatLabel>Active</StatLabel>
            </StatsCard>
            <StatsCard>
              <StatNumber>{inactiveCount}</StatNumber>
              <StatLabel>Inactive</StatLabel>
            </StatsCard>
            <StatsCard>
              <StatNumber>{apps.length}</StatNumber>
              <StatLabel>Total</StatLabel>
            </StatsCard>
          </HeaderActions>
        </HeaderContent>
      </PageHeader>

      <ControlBar>
        <SearchBox>
          <SearchIcon className="fas fa-search" />
          <SearchInput
            type="text"
            placeholder="Search by name, ID, or owner email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </SearchBox>
        
        <FilterButton
          className={filterStatus === 'all' ? 'active' : ''}
          onClick={() => setFilterStatus('all')}
        >
          <i className="fas fa-list"></i>
          All Apps
        </FilterButton>
        
        <FilterButton
          className={filterStatus === 'active' ? 'active' : ''}
          onClick={() => setFilterStatus('active')}
        >
          <i className="fas fa-check-circle"></i>
          Active
        </FilterButton>
        
        <FilterButton
          className={filterStatus === 'inactive' ? 'active' : ''}
          onClick={() => setFilterStatus('inactive')}
        >
          <i className="fas fa-times-circle"></i>
          Inactive
        </FilterButton>
        
        <CreateButton onClick={handleCreateApp}>
          <i className="fas fa-plus"></i>
          Register New App
        </CreateButton>
      </ControlBar>

      {filteredApps.length === 0 ? (
        <EmptyState>
          <EmptyIcon>
            <i className="fas fa-inbox"></i>
          </EmptyIcon>
          <EmptyTitle>No applications found</EmptyTitle>
          <EmptyText>
            {searchTerm || filterStatus !== 'all' 
              ? 'Try adjusting your search or filter criteria'
              : 'Get started by registering your first application'}
          </EmptyText>
          {!searchTerm && filterStatus === 'all' && (
            <CreateButton style={{ margin: '0 auto' }} onClick={handleCreateApp}>
              <i className="fas fa-plus"></i>
              Register New App
            </CreateButton>
          )}
        </EmptyState>
      ) : (
        <AppsGrid>
          {filteredApps.map(app => (
            <AppCard key={app.client_id}>
              <AppStatus $isActive={app.is_active}>
                <StatusBadge $isActive={app.is_active}>
                  {app.is_active ? 'Active' : 'Inactive'}
                </StatusBadge>
                {app.is_active && (
                  <ToggleButton 
                    $isActive={app.is_active}
                    onClick={() => handleToggleAppStatus(app)}
                    title="Click to deactivate"
                  />
                )}
              </AppStatus>
              <AppCardHeader $isActive={app.is_active}>
                <AppName>
                  <i className="fas fa-cube"></i>
                  {app.name}
                </AppName>
                <AppId>
                  {app.client_id}
                  <CopyButton 
                    className={copiedId === app.client_id ? 'copied' : ''}
                    onClick={() => handleCopyClientId(app.client_id)}
                    title="Copy Client ID"
                  >
                    <i className={copiedId === app.client_id ? "fas fa-check" : "fas fa-copy"}></i>
                  </CopyButton>
                </AppId>
              </AppCardHeader>
              
              <AppCardBody>
                <div style={{ flex: 1 }}>
                  <AppInfo>
                    <InfoRow>
                      <i className="fas fa-user"></i>
                      <span><strong>Owner:</strong> {app.owner_email}</span>
                    </InfoRow>
                    
                    <InfoRow>
                      <i className="fas fa-calendar"></i>
                      <span><strong>Created:</strong> {new Date(app.created_at).toLocaleDateString()}</span>
                    </InfoRow>
                    
                    {app.discovery_endpoint && (
                      <InfoRow>
                        <i className="fas fa-compass"></i>
                        <span><strong>Discovery:</strong> <span style={{fontSize: '0.9em', wordBreak: 'break-all'}}>{app.discovery_endpoint}</span></span>
                      </InfoRow>
                    )}
                    
                    {app.redirect_uris && app.redirect_uris.length > 0 && (
                      <InfoRow>
                        <i className="fas fa-link"></i>
                        <span><strong>Redirect URIs:</strong> <span style={{fontSize: '0.9em'}}>{app.redirect_uris.join(', ')}</span></span>
                      </InfoRow>
                    )}
                    
                    {app.discovery_endpoint && (
                      <>
                        <InfoRow style={{marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #e2e8f0'}}>
                          <button
                            onClick={async () => {
                              if (confirm('Run auto discovery for ' + app.name + '?')) {
                                try {
                                  const response = await fetch(`${import.meta.env.VITE_API_ORIGIN || ''}/discovery/endpoints/${app.client_id}`, {
                                    method: 'POST',
                                    headers: {
                                      'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                                      'Content-Type': 'application/json'
                                    }
                                  });
                                  if (response.ok) {
                                    alert('Discovery completed successfully!');
                                    loadApps(); // Reload to show updated timestamp
                                  } else {
                                    alert('Discovery failed: ' + (await response.text()));
                                  }
                                } catch (err) {
                                  alert('Error running discovery: ' + err);
                                }
                              }
                            }}
                            style={{
                              background: '#4f46e5',
                              color: 'white',
                              border: 'none',
                              padding: '8px 16px',
                              borderRadius: '6px',
                              cursor: 'pointer',
                              fontSize: '14px',
                              fontWeight: '500',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '8px'
                            }}
                          >
                            <i className="fas fa-sync-alt"></i>
                            Run Auto Discovery
                          </button>
                        </InfoRow>
                        {(app.last_discovery_at || app.last_discovery_run_at) && (
                          <InfoRow style={{fontSize: '0.85em', color: '#64748b', marginTop: '8px'}}>
                            <i className="fas fa-clock"></i>
                            <span>
                              Last discovery: {new Date(app.last_discovery_at || app.last_discovery_run_at).toLocaleString()}
                              {app.last_discovery_run_by && ` by ${app.last_discovery_run_by}`}
                            </span>
                          </InfoRow>
                        )}
                      </>
                    )}
                  </AppInfo>
                </div>
                
                <CardActions>
                  <ActionButton onClick={() => handleManageRoles(app)}>
                    <i className="fas fa-user-shield"></i>
                    <span>Roles</span>
                  </ActionButton>
                  <ActionButton onClick={() => handleManageApiKeys(app)}>
                    <i className="fas fa-key"></i>
                    <span>API Keys</span>
                  </ActionButton>
                  {app.is_active ? (
                    <ActionButton className="primary" onClick={() => handleEditApp(app)}>
                      <i className="fas fa-edit"></i>
                      <span>Edit</span>
                    </ActionButton>
                  ) : (
                    <ActionButton className="warning" onClick={() => handleActivateApp(app)}>
                      <i className="fas fa-power-off"></i>
                      <span>Activate</span>
                    </ActionButton>
                  )}
                  <ActionButton className="danger" onClick={() => handleDeleteApp(app)}>
                    <i className="fas fa-trash"></i>
                    <span>Delete</span>
                  </ActionButton>
                </CardActions>
              </AppCardBody>
            </AppCard>
          ))}
        </AppsGrid>
      )}

      {showRolesModal && selectedApp && (
        <RolesModal
          isOpen={showRolesModal}
          onClose={() => setShowRolesModal(false)}
          clientId={selectedApp.client_id}
          appName={selectedApp.name}
        />
      )}
      
      {showApiKeyModal && selectedApp && (
        <APIKeyModal
          isOpen={showApiKeyModal}
          onClose={() => setShowApiKeyModal(false)}
          clientId={selectedApp.client_id}
          appName={selectedApp.name}
        />
      )}
      
      {/* Create App Modal */}
      <Modal $isOpen={showCreateModal}>
        <ModalContent>
          <ModalTitle>Register New Application</ModalTitle>
          <form onSubmit={handleSubmitCreate}>
            <FormGroup>
              <Label>Application Name *</Label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </FormGroup>
            
            <FormGroup>
              <Label>Description</Label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </FormGroup>
            
            <FormGroup>
              <Label>Owner Email *</Label>
              <Input
                type="email"
                value={formData.owner_email}
                onChange={(e) => setFormData({ ...formData, owner_email: e.target.value })}
                required
              />
            </FormGroup>
            
            <FormGroup>
              <Label>Redirect URIs</Label>
              {formData.redirect_uris.map((uri, index) => (
                <div key={index} style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                  <Input
                    type="url"
                    value={uri}
                    onChange={(e) => handleRedirectUriChange(index, e.target.value)}
                    placeholder="https://example.com/callback"
                  />
                  {formData.redirect_uris.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeRedirectUri(index)}
                      style={{ padding: '8px 12px', color: '#ef4444' }}
                    >
                      <i className="fas fa-times"></i>
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addRedirectUri}
                style={{ marginTop: '8px', color: '#0b3b63' }}
              >
                <i className="fas fa-plus"></i> Add Redirect URI
              </button>
            </FormGroup>
            
            <FormGroup>
              <Label>
                <Checkbox
                  type="checkbox"
                  checked={formData.allow_discovery}
                  onChange={(e) => setFormData({ ...formData, allow_discovery: e.target.checked })}
                />
                Allow Discovery
              </Label>
            </FormGroup>
            
            {formData.allow_discovery && (
              <FormGroup>
                <Label>Discovery Endpoint</Label>
                <Input
                  type="url"
                  value={formData.discovery_endpoint}
                  onChange={(e) => setFormData({ ...formData, discovery_endpoint: e.target.value })}
                  placeholder="https://api.example.com/discovery"
                />
              </FormGroup>
            )}
            
            <ModalActions>
              <ModalButton
                type="button"
                className="secondary"
                onClick={() => setShowCreateModal(false)}
              >
                Cancel
              </ModalButton>
              <ModalButton type="submit" className="primary">
                Register Application
              </ModalButton>
            </ModalActions>
          </form>
        </ModalContent>
      </Modal>
      
      {/* Edit App Modal */}
      <Modal $isOpen={showEditModal}>
        <ModalContent>
          <ModalTitle>Edit Application</ModalTitle>
          <form onSubmit={handleSubmitEdit}>
            <FormGroup>
              <Label>Application Name *</Label>
              <Input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </FormGroup>
            
            <FormGroup>
              <Label>Description</Label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </FormGroup>
            
            <FormGroup>
              <Label>Redirect URIs</Label>
              {formData.redirect_uris.map((uri, index) => (
                <div key={index} style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                  <Input
                    type="url"
                    value={uri}
                    onChange={(e) => handleRedirectUriChange(index, e.target.value)}
                    placeholder="https://example.com/callback"
                  />
                  {formData.redirect_uris.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeRedirectUri(index)}
                      style={{ padding: '8px 12px', color: '#ef4444' }}
                    >
                      <i className="fas fa-times"></i>
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addRedirectUri}
                style={{ marginTop: '8px', color: '#0b3b63' }}
              >
                <i className="fas fa-plus"></i> Add Redirect URI
              </button>
            </FormGroup>
            
            <FormGroup>
              <Label>
                <Checkbox
                  type="checkbox"
                  checked={formData.allow_discovery}
                  onChange={(e) => setFormData({ ...formData, allow_discovery: e.target.checked })}
                />
                Allow Discovery
              </Label>
            </FormGroup>
            
            {formData.allow_discovery && (
              <FormGroup>
                <Label>Discovery Endpoint</Label>
                <Input
                  type="url"
                  value={formData.discovery_endpoint}
                  onChange={(e) => setFormData({ ...formData, discovery_endpoint: e.target.value })}
                  placeholder="https://api.example.com/discovery"
                />
              </FormGroup>
            )}
            
            <ModalActions>
              <ModalButton
                type="button"
                className="secondary"
                onClick={() => setShowEditModal(false)}
              >
                Cancel
              </ModalButton>
              <ModalButton type="submit" className="primary">
                Update Application
              </ModalButton>
            </ModalActions>
          </form>
        </ModalContent>
      </Modal>
    </PageContainer>
  );
};

export default AppAdministration;