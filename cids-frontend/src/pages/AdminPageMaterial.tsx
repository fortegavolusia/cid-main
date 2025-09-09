import { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import adminService from '../services/adminService';
import type { AppInfo } from '../types/admin';
import {
  MaterialCard,
  MaterialButton,
  MaterialInput,
  MaterialLabel,
  MaterialTextField,
  MaterialTabs,
  MaterialTab,
  MaterialChip,
  MaterialFAB,
  MaterialDivider,
  MaterialContainer,
  MaterialProgress
} from '../components/MaterialComponents';
import { materialTheme } from '../styles/materialTheme';

// Material Design styled components
const PageContainer = styled.div`
  background: ${materialTheme.colors.background};
  min-height: 100vh;
  font-family: ${materialTheme.typography.fontFamily};
  color: ${materialTheme.colors.onBackground};
`;

const Header = styled.div`
  background: ${materialTheme.colors.surface};
  box-shadow: ${materialTheme.elevation[1]};
  padding: ${materialTheme.spacing.lg} 0;
  margin-bottom: ${materialTheme.spacing.lg};
  position: sticky;
  top: 0;
  z-index: 100;
`;

const HeaderContent = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 ${materialTheme.spacing.lg};
  display: flex;
  align-items: center;
  justify-content: between;
  gap: ${materialTheme.spacing.lg};
`;

const PageTitle = styled.h1`
  ${materialTheme.typography.headlineMedium};
  color: ${materialTheme.colors.onSurface};
  margin: 0;
  flex: 1;
`;

const StatsContainer = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: ${materialTheme.spacing.md};
  margin-bottom: ${materialTheme.spacing.lg};
`;

const StatCard = styled(MaterialCard)`
  text-align: center;
  padding: ${materialTheme.spacing.lg};
`;

const StatValue = styled.div`
  ${materialTheme.typography.displaySmall};
  color: ${materialTheme.colors.primary};
  font-weight: 600;
  margin-bottom: ${materialTheme.spacing.sm};
`;

const StatLabel = styled.div`
  ${materialTheme.typography.bodySmall};
  color: ${materialTheme.colors.onSurfaceVariant};
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const TabContent = styled.div<{ active: boolean }>`
  display: ${props => props.active ? 'block' : 'none'};
  animation: ${props => props.active ? 'fadeIn 0.3s ease-in' : 'none'};
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;

const AppCardGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: ${materialTheme.spacing.md};
`;

const AppCard = styled(MaterialCard)`
  position: relative;
  transition: all ${materialTheme.transitions.standard};
  
  &:hover {
    box-shadow: ${materialTheme.elevation[8]};
    transform: translateY(-2px);
  }
`;

const AppHeader = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: between;
  margin-bottom: ${materialTheme.spacing.md};
`;

const AppInfo = styled.div`
  flex: 1;
`;

const AppName = styled.h3`
  ${materialTheme.typography.titleLarge};
  color: ${materialTheme.colors.onSurface};
  margin: 0 0 ${materialTheme.spacing.xs} 0;
`;

const AppDescription = styled.p`
  ${materialTheme.typography.bodyMedium};
  color: ${materialTheme.colors.onSurfaceVariant};
  margin: 0 0 ${materialTheme.spacing.sm} 0;
  line-height: 1.4;
`;

const AppMeta = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${materialTheme.spacing.xs};
  margin-bottom: ${materialTheme.spacing.md};
`;

const MetaRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  ${materialTheme.typography.bodySmall};
`;

const MetaLabel = styled.span`
  color: ${materialTheme.colors.onSurfaceVariant};
  font-weight: 500;
`;

const MetaValue = styled.span`
  color: ${materialTheme.colors.onSurface};
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
`;

const ChipContainer = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${materialTheme.spacing.xs};
  margin-bottom: ${materialTheme.spacing.md};
`;

const ActionButtons = styled.div`
  display: flex;
  gap: ${materialTheme.spacing.xs};
  justify-content: flex-end;
`;

const EmptyState = styled.div`
  text-align: center;
  padding: ${materialTheme.spacing.xxl};
  color: ${materialTheme.colors.onSurfaceVariant};
`;

const EmptyStateIcon = styled.div`
  font-size: 48px;
  margin-bottom: ${materialTheme.spacing.md};
  opacity: 0.5;
`;

const LoadingContainer = styled.div`
  padding: ${materialTheme.spacing.xl};
  text-align: center;
`;

const ErrorAlert = styled(MaterialCard)<{ severity: 'error' | 'warning' | 'info' | 'success' }>`
  background: ${props => {
    switch(props.severity) {
      case 'error': return materialTheme.colors.errorContainer;
      case 'warning': return '#fff4e6';
      case 'success': return '#e8f5e8';
      default: return '#e3f2fd';
    }
  }};
  color: ${props => {
    switch(props.severity) {
      case 'error': return materialTheme.colors.onErrorContainer;
      case 'warning': return '#e65100';
      case 'success': return '#2e7d32';
      default: return '#0d47a1';
    }
  }};
  border-left: 4px solid ${props => {
    switch(props.severity) {
      case 'error': return materialTheme.colors.error;
      case 'warning': return materialTheme.colors.warning;
      case 'success': return materialTheme.colors.success;
      default: return materialTheme.colors.info;
    }
  }};
  margin-bottom: ${materialTheme.spacing.md};
`;

export default function AdminPageMaterial() {
  const { user } = useAuth();
  const [apps, setApps] = useState<AppInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('apps');
  const [searchTerm, setSearchTerm] = useState('');
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  
  useEffect(() => {
    fetchApps();
    fetchDashboardStats();
  }, []);
  
  const fetchDashboardStats = async () => {
    try {
      const response = await adminService.getDashboardStats();
      setDashboardStats(response);
    } catch (err) {
      console.error('Error fetching dashboard stats:', err);
    }
  };
  
  const fetchApps = async () => {
    try {
      setLoading(true);
      setError(null);
      const appsData = await adminService.getApps();
      console.log('Apps data received:', appsData); // Debug log
      setApps(appsData || []);
    } catch (err) {
      console.error('Error fetching apps:', err);
      setError('Failed to fetch applications. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleRegisterApp = async (appData: any) => {
    try {
      await adminService.registerApp(appData);
      await fetchApps();
    } catch (err) {
      console.error('Error registering app:', err);
      setError('Failed to register application.');
    }
  };
  
  const filteredApps = apps.filter(app => 
    app.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    app.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    app.client_id.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  const stats = {
    totalApps: apps.length,
    activeApps: apps.filter(app => app.is_active).length,
    recentApps: apps.filter(app => {
      const created = new Date(app.created_at || app.created || '');
      const weekAgo = new Date();
      weekAgo.setDate(weekAgo.getDate() - 7);
      return created > weekAgo;
    }).length
  };
  
  const tabs = [
    { id: 'apps', label: 'Applications', count: apps.length },
    { id: 'users', label: 'Users', count: 0 },
    { id: 'settings', label: 'Settings', count: 0 },
    { id: 'analytics', label: 'Analytics', count: 0 }
  ];
  
  return (
    <PageContainer>
      <Header>
        <HeaderContent>
          <PageTitle>Administration Dashboard</PageTitle>
          <MaterialChip selected color="primary">
            Admin User
          </MaterialChip>
        </HeaderContent>
      </Header>
      
      <MaterialContainer>
        {/* Stats Cards */}
        <StatsContainer>
          <StatCard elevation={2}>
            <StatValue>{stats.totalApps}</StatValue>
            <StatLabel>Total Applications</StatLabel>
          </StatCard>
          <StatCard elevation={2}>
            <StatValue>{stats.activeApps}</StatValue>
            <StatLabel>Active Applications</StatLabel>
          </StatCard>
          <StatCard elevation={2}>
            <StatValue>{dashboardStats?.apps?.discovered || 0}</StatValue>
            <StatLabel>Apps Discovered</StatLabel>
          </StatCard>
          <StatCard elevation={2}>
            <StatValue>{dashboardStats?.roles?.total || 0}</StatValue>
            <StatLabel>Total Roles</StatLabel>
          </StatCard>
          <StatCard elevation={2}>
            <StatValue>{dashboardStats?.permissions?.total || 0}</StatValue>
            <StatLabel>Total Permissions</StatLabel>
          </StatCard>
          <StatCard elevation={2}>
            <StatValue>{dashboardStats?.api_keys?.active || 0}</StatValue>
            <StatLabel>Active API Keys</StatLabel>
          </StatCard>
        </StatsContainer>
        
        {/* Error Display */}
        {error && (
          <ErrorAlert severity="error" elevation={2}>
            <strong>Error:</strong> {error}
            <MaterialButton 
              variant="text" 
              color="error" 
              size="small"
              onClick={() => setError(null)}
              style={{ float: 'right' }}
            >
              Dismiss
            </MaterialButton>
          </ErrorAlert>
        )}
        
        {/* Tab Navigation */}
        <MaterialCard elevation={1}>
          <MaterialTabs>
            {tabs.map(tab => (
              <MaterialTab
                key={tab.id}
                active={activeTab === tab.id}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label} {tab.count > 0 && `(${tab.count})`}
              </MaterialTab>
            ))}
          </MaterialTabs>
          
          {/* Applications Tab */}
          <TabContent active={activeTab === 'apps'}>
            <div style={{ padding: materialTheme.spacing.lg }}>
              {/* Search and Actions */}
              <div style={{ 
                display: 'flex', 
                gap: materialTheme.spacing.md, 
                marginBottom: materialTheme.spacing.lg,
                alignItems: 'flex-end'
              }}>
                <MaterialTextField style={{ flex: 1 }}>
                  <MaterialInput
                    type="text"
                    placeholder=" "
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                  <MaterialLabel hasValue={!!searchTerm}>
                    Search applications...
                  </MaterialLabel>
                </MaterialTextField>
                <MaterialButton variant="filled" color="primary">
                  Register New App
                </MaterialButton>
                <MaterialButton variant="outlined" onClick={fetchApps}>
                  Refresh
                </MaterialButton>
              </div>
              
              {/* Loading State */}
              {loading && (
                <LoadingContainer>
                  <MaterialProgress indeterminate />
                  <p style={{ marginTop: materialTheme.spacing.md }}>
                    Loading applications...
                  </p>
                </LoadingContainer>
              )}
              
              {/* Applications Grid */}
              {!loading && filteredApps.length > 0 && (
                <AppCardGrid>
                  {filteredApps.map(app => (
                    <AppCard key={app.client_id} elevation={2}>
                      <AppHeader>
                        <AppInfo>
                          <AppName>{app.name}</AppName>
                          <AppDescription>
                            {app.description || 'No description provided'}
                          </AppDescription>
                        </AppInfo>
                      </AppHeader>
                      
                      <AppMeta>
                        <MetaRow>
                          <MetaLabel>Client ID:</MetaLabel>
                          <MetaValue>{app.client_id.substring(0, 20)}...</MetaValue>
                        </MetaRow>
                        <MetaRow>
                          <MetaLabel>Owner:</MetaLabel>
                          <MetaValue>{app.owner_email || app.owner || 'Unknown'}</MetaValue>
                        </MetaRow>
                        <MetaRow>
                          <MetaLabel>Created:</MetaLabel>
                          <MetaValue>
                            {new Date(app.created_at || app.created || '').toLocaleDateString()}
                          </MetaValue>
                        </MetaRow>
                        <MetaRow>
                          <MetaLabel>Discovery URL:</MetaLabel>
                          <MetaValue style={{ fontSize: '0.85em', wordBreak: 'break-all' }}>
                            {app.discovery_endpoint || 'Not configured'}
                          </MetaValue>
                        </MetaRow>
                      </AppMeta>
                      
                      <ChipContainer>
                        {app.is_active && (
                          <MaterialChip 
                            selected={true} 
                            color="primary"
                          >
                            Active
                          </MaterialChip>
                        )}
                        {app.discovery_endpoint && (
                          <MaterialChip color="success">
                            Discovery Enabled
                          </MaterialChip>
                        )}
                        <MaterialChip>
                          {app.redirect_uris?.length || 0} Redirect URIs
                        </MaterialChip>
                      </ChipContainer>
                      
                      <MaterialDivider />
                      
                      <ActionButtons>
                        <MaterialButton variant="text" size="small">
                          View Details
                        </MaterialButton>
                        <MaterialButton variant="text" size="small">
                          Manage Roles
                        </MaterialButton>
                        <MaterialButton variant="text" size="small">
                          API Keys
                        </MaterialButton>
                        <MaterialButton variant="text" color="error" size="small">
                          Delete
                        </MaterialButton>
                      </ActionButtons>
                    </AppCard>
                  ))}
                </AppCardGrid>
              )}
              
              {/* Empty State */}
              {!loading && filteredApps.length === 0 && (
                <EmptyState>
                  <EmptyStateIcon>📱</EmptyStateIcon>
                  <h3>No Applications Found</h3>
                  <p>
                    {searchTerm 
                      ? `No applications match "${searchTerm}"`
                      : "Get started by registering your first application"
                    }
                  </p>
                  {!searchTerm && (
                    <MaterialButton variant="filled" color="primary">
                      Register Your First App
                    </MaterialButton>
                  )}
                </EmptyState>
              )}
            </div>
          </TabContent>
          
          {/* Other Tabs */}
          <TabContent active={activeTab === 'users'}>
            <div style={{ padding: materialTheme.spacing.lg }}>
              <EmptyState>
                <EmptyStateIcon>👥</EmptyStateIcon>
                <h3>User Management</h3>
                <p>User management features will be available soon.</p>
              </EmptyState>
            </div>
          </TabContent>
          
          <TabContent active={activeTab === 'settings'}>
            <div style={{ padding: materialTheme.spacing.lg }}>
              <EmptyState>
                <EmptyStateIcon>⚙️</EmptyStateIcon>
                <h3>System Settings</h3>
                <p>System configuration options will be available soon.</p>
              </EmptyState>
            </div>
          </TabContent>
          
          <TabContent active={activeTab === 'analytics'}>
            <div style={{ padding: materialTheme.spacing.lg }}>
              <EmptyState>
                <EmptyStateIcon>📊</EmptyStateIcon>
                <h3>Analytics Dashboard</h3>
                <p>Usage analytics and reports will be available soon.</p>
              </EmptyState>
            </div>
          </TabContent>
        </MaterialCard>
      </MaterialContainer>
      
      {/* Floating Action Button */}
      <MaterialFAB extended color="primary">
        ➕ Quick Action
      </MaterialFAB>
    </PageContainer>
  );
}