import React, { useState, useEffect } from 'react';
import styled, { createGlobalStyle } from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import adminService from '../services/adminService';
import type { AppInfo } from '../types/admin';
import RolesModal from '../components/RolesModal';
import APIKeyModal from '../components/APIKeyModal';
import RedirectLoader from '../components/RedirectLoader';
import MarkdownViewer from '../components/MarkdownViewer';

// Global styles similar to App Administration
const GlobalStyles = createGlobalStyle`
  :root {
    --bg-color: transparent;
    --card-bg: #ffffff;
    --sidebar-bg: #0b3b63;
    --primary-color: #0b3b63;
    --secondary-color: #10b981;
    --text-color: #334155;
    --secondary-text-color: #64748b;
    --border-color: #e1e8ed;
    --shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }
`;

const MainContent = styled.main`
  flex-grow: 1;
  padding: 0;
  display: flex;
  flex-direction: column;
  background-color: transparent;
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


const DashboardGrid = styled.div`
  display: flex;
  flex-direction: column;
  gap: 28px;
  flex-grow: 1;
  padding: 0 40px 40px 40px;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
`;

const ContentArea = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
`;

const TopRowCards = styled.div`
  display: flex;
  gap: 20px;
  flex-wrap: wrap;

  & > :first-child {
    flex: 1 1 45%;
    min-width: 350px;
  }

  & > :nth-child(2) {
    flex: 1 1 25%;
    min-width: 250px;
  }

  & > :nth-child(3) {
    flex: 1 1 20%;
    min-width: 250px;
  }
`;

const BottomRowCards = styled.div`
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  align-items: stretch;

  & > :first-child {
    flex: 1 1 45%;
    min-width: 350px;
  }

  & > :last-child {
    flex: 1 1 50%;
    min-width: 400px;
  }
`;

const Card = styled.div`
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #e1e8ed;
  padding: 24px;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  }
`;


const CardHeader = styled.div`
  display: flex;
  align-items: center;
  margin: -24px -24px 20px -24px;
  padding: 16px 24px;
  background: #6b7280;
  border-bottom: 1px solid #e1e8ed;
  border-radius: 16px 16px 0 0;
  
  i {
    font-size: 1.2rem;
    margin-right: 12px;
    color: white;
  }
  
  h3, h4 {
    margin: 0;
    font-weight: 600;
    color: white;
    font-size: 18px;
  }
`;

const KpiGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 20px;
  margin-top: 15px;
`;

const KpiItem = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e1e8ed;
  border-radius: 12px;
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }
  
  i {
    font-size: 2rem;
    margin-bottom: 10px;
    color: #0b3b63;
  }
  
  h5 {
    margin: 0;
    font-size: 0.9rem;
    color: #64748b;
    font-weight: 500;
  }
  
  .kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #334155;
  }
`;

const QuickAccessList = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 280px;
  max-height: 350px;
  overflow-y: auto;
  padding-right: 4px;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
  }
`;

const QuickLink = styled.button<{ $appColor?: string }>`
  display: flex;
  align-items: center;
  padding: 14px 16px;
  margin-bottom: 10px;
  background: white;
  border: 2px solid ${props => props.$appColor ? `${props.$appColor}30` : '#e1e8ed'};
  border-radius: 12px;
  color: #334155;
  text-decoration: none;
  transition: all 0.3s ease;
  cursor: pointer;
  text-align: left;
  width: 100%;
  font-size: 14px;
  position: relative;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);

  &:hover {
    background: ${props => props.$appColor ? `${props.$appColor}10` : '#f8fafc'};
    border-color: ${props => props.$appColor || '#0b3b63'};
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .app-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 14px;
    background: ${props => props.$appColor ? `linear-gradient(135deg, ${props.$appColor}, ${props.$appColor}dd)` : 'linear-gradient(135deg, #0b3b63, #0a3357)'};
    color: white;
    font-size: 1.2rem;
    flex-shrink: 0;
    box-shadow: 0 2px 8px ${props => props.$appColor ? `${props.$appColor}40` : 'rgba(11, 59, 99, 0.25)'};

    i {
      margin: 0;
    }
  }

  .app-name {
    flex-grow: 1;
    font-size: 15px;
    font-weight: 500;
    color: #1e293b;
  }

  .app-description {
    font-size: 12px;
    color: #64748b;
    margin-top: 2px;
  }
`;

const StatusIndicator = styled.div<{ $healthy: boolean }>`
  position: absolute;
  right: 15px;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: ${props => props.$healthy ? '#10b981' : '#ef4444'};
  box-shadow: 0 0 0 2px ${props => props.$healthy ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'};
  animation: ${props => props.$healthy ? 'pulse-green' : 'pulse-red'} 2s infinite;
  
  @keyframes pulse-green {
    0% {
      box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
    }
    70% {
      box-shadow: 0 0 0 8px rgba(16, 185, 129, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
    }
  }
  
  @keyframes pulse-red {
    0% {
      box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
    }
    70% {
      box-shadow: 0 0 0 8px rgba(239, 68, 68, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
    }
  }
`;

const ChartPlaceholder = styled.div`
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e1e8ed;
  min-height: 250px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 12px;
  color: #64748b;
  font-size: 14px;
`;

const ActivityStats = styled.div`
  padding: 6px 12px 8px 12px;
  min-height: 180px;
  max-height: 250px;
  overflow-y: auto;
  
  &::-webkit-scrollbar {
    width: 8px;
  }
  
  &::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 4px;
  }
  
  &::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
  }
`;

const StatItem = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: 4px;
  gap: 6px;
`;

const StatLabel = styled.div`
  min-width: 140px;
  color: #334155;
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  padding-right: 8px;
  text-transform: capitalize;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const StatBarContainer = styled.div`
  flex: 1;
  display: flex;
  align-items: center;
  gap: 4px;
`;

const StatBar = styled.div<{ $percentage: number }>`
  height: 8px;
  background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 ${props => props.$percentage}%, #f1f5f9 ${props => props.$percentage}%);
  border-radius: 5px;
  transition: all 0.5s ease;
  position: relative;
  overflow: hidden;
  flex: 1;
  max-width: ${props => props.$percentage}%;
  min-width: 20px;
  
  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.2) 50%, transparent 100%);
    animation: shimmer 2s infinite;
  }
  
  @keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
`;

const StatValue = styled.div`
  min-width: 40px;
  color: #0f172a;
  font-size: 13px;
  font-weight: 600;
  text-align: right;
`;

const NewsList = styled.div`
  display: flex;
  flex-direction: column;
  text-align: left;
  padding: 0;
`;

const NewsItem = styled.button`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 5px;
  border-bottom: 1px solid var(--border-color);
  text-decoration: none;
  color: var(--text-color);
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;

  &:hover {
    color: var(--primary-color);
    background-color: rgba(11, 59, 99, 0.05);
    padding-left: 10px;
  }

  span {
    display: flex;
    align-items: center;
    text-align: left;
  }
`;

const LlmCard = styled(Card)`
  grid-column: 2;
  display: flex;
  flex-direction: column;
  max-height: 500px;
  min-width: 280px;
`;

const ChatHistory = styled.div`
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 10px;
  max-height: 400px;
`;

const Message = styled.div`
  padding: 15px;
  margin-bottom: 15px;
  border-radius: 20px;
  line-height: 1.6;
  
  &.llm-message {
    background-color: #f0f4f8;
    color: #444;
    border-bottom-left-radius: 4px;
  }
  
  &.user-message {
    background-color: var(--primary-color);
    color: white;
    border-bottom-right-radius: 4px;
    margin-left: 20px;
  }
`;

const ChatInputContainer = styled.div`
  display: flex;
  margin-top: 20px;
  border-top: 1px solid var(--border-color);
  padding-top: 20px;
`;

const ChatInput = styled.input`
  flex-grow: 1;
  padding: 15px 20px;
  border: 1px solid var(--border-color);
  border-radius: 30px;
  margin-right: 10px;
  font-size: 1rem;
  outline: none;
  
  &:focus {
    border-color: var(--primary-color);
  }
`;

const SendBtn = styled.button`
  background: #0b3b63;
  color: white;
  border: none;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  transition: all 0.3s ease;
  
  &:hover {
    background: #0a3357;
    transform: scale(1.05);
  }
`;

const AdminPageNew: React.FC = () => {
  const { user } = useAuth();
  const [apps, setApps] = useState<AppInfo[]>([]);
  const [authorizedApps, setAuthorizedApps] = useState<Array<{clientId: string, name: string, description: string}>>([]);
  const [appHealthStatus, setAppHealthStatus] = useState<Record<string, boolean>>({});
  const [appStats, setAppStats] = useState({
    apps: { total: 0, active: 0, inactive: 0 },
    tokens: { active: 0 },
    api_keys: { total: 0 }
  });
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  const [showRolesModal, setShowRolesModal] = useState(false);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [activityStats, setActivityStats] = useState<{type: string, count: number}[]>([]);
  const [redirectingApp, setRedirectingApp] = useState<{name: string} | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [messages, setMessages] = useState([
    { type: 'llm', text: "Hello! I'm your CID assistant. How can I help you manage your identity services today?" }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [markdownDoc, setMarkdownDoc] = useState<{name: string, title: string} | null>(null);
  const [a2aConnections, setA2aConnections] = useState<any[]>([]);

  useEffect(() => {
    loadApps();
    loadStats();
    loadDashboardStats();
    loadActivityStats();
    loadA2AConnections();
  }, []);

  // Separate useEffect for loading authorized apps when user changes or on mount
  useEffect(() => {
    // Add a small delay to ensure token is available after login
    const timer = setTimeout(() => {
      loadAuthorizedApps();
    }, 500);
    
    return () => clearTimeout(timer);
  }, [user]); // Re-run when user changes (login/logout)

  const loadApps = async () => {
    try {
      const appsData = await adminService.getApps();
      setApps(appsData);
    } catch (error) {
      console.error('Failed to load apps:', error);
    }
  };

  const decodeJWT = (token: string) => {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return null;
      const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
      return payload;
    } catch (err) {
      console.error('Failed to decode JWT:', err);
      return null;
    }
  };

  // Function to check app health status
  const checkAppHealth = async (appId: string): Promise<boolean> => {
    try {
      // Define health endpoints for known apps
      const healthEndpoints: Record<string, string> = {
        'app_fba7654e91e6413c': 'http://localhost:8005/health', // HR System
        // Add more apps here as needed
      };
      
      const healthUrl = healthEndpoints[appId];
      if (!healthUrl) return true; // Default to healthy if no endpoint defined
      
      const response = await fetch(healthUrl, {
        method: 'GET',
        mode: 'cors',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      return response.ok;
    } catch (error) {
      console.error(`Health check failed for ${appId}:`, error);
      return false;
    }
  };

  const loadAuthorizedApps = async () => {
    try {
      // Clear previous apps when loading
      setAuthorizedApps([]);
      setAppHealthStatus({});
      
      // Get the access token
      const accessToken = localStorage.getItem('access_token');
      if (!accessToken) {
        console.log('No access token found - user might not be logged in yet');
        return;
      }

      // Decode the JWT to get roles
      const tokenPayload = decodeJWT(accessToken);
      if (!tokenPayload) {
        console.log('Failed to decode token');
        return;
      }

      // Get app IDs from either roles (if it's an object) or permissions
      let appIds: string[] = [];
      
      // First try to get from roles if it's an object with app IDs as keys
      if (tokenPayload.roles && typeof tokenPayload.roles === 'object' && !Array.isArray(tokenPayload.roles)) {
        appIds = Object.keys(tokenPayload.roles);
        console.log('Got app IDs from roles object');
      }
      
      // If roles is an array or we didn't get app IDs, try to extract from permissions
      if (appIds.length === 0 && tokenPayload.permissions && typeof tokenPayload.permissions === 'object') {
        appIds = Object.keys(tokenPayload.permissions);
        console.log('Got app IDs from permissions object');
      }
      
      console.log('Token roles:', tokenPayload.roles);
      console.log('Token permissions:', tokenPayload.permissions);
      console.log('Authorized app IDs extracted:', appIds);
      
      if (appIds.length === 0) {
        console.log('No app IDs found in token');
        return;
      }

      // Fetch all registered apps
      const allApps = await adminService.getApps();
      console.log('All registered apps:', allApps);
      
      // Filter to only apps the user has roles for
      const userAuthorizedApps = allApps
        .filter(app => {
          // Check if the app's client_id is in the user's roles
          const hasRole = appIds.includes(app.client_id);
          console.log(`Checking app ${app.name} (${app.client_id}): ${hasRole ? 'YES' : 'NO'}`);
          return hasRole;
        })
        .map(app => ({
          clientId: app.client_id,
          name: app.name,
          description: app.description || '',
          redirect_uris: app.redirect_uris || []
        }));
      
      console.log('Authorized apps loaded:', userAuthorizedApps);
      setAuthorizedApps(userAuthorizedApps);
      
      // Check health status for each app
      const healthStatus: Record<string, boolean> = {};
      for (const app of userAuthorizedApps) {
        const isHealthy = await checkAppHealth(app.clientId);
        healthStatus[app.clientId] = isHealthy;
      }
      setAppHealthStatus(healthStatus);
      console.log('App health status:', healthStatus);
    } catch (error) {
      console.error('Failed to load authorized apps:', error);
      setAuthorizedApps([]);
    }
  };

  const loadStats = async () => {
    try {
      const stats = await adminService.getAppsStats();
      setAppStats(stats);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const loadDashboardStats = async () => {
    try {
      const stats = await adminService.getDashboardStats();
      console.log('Dashboard stats received:', stats);
      setDashboardStats(stats);
    } catch (error) {
      console.error('Failed to load dashboard stats:', error);
    }
  };

  const loadA2AConnections = async () => {
    try {
      const response = await fetch('http://localhost:8001/auth/admin/a2a-connections', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setA2aConnections(data.connections || []);
      }
    } catch (error) {
      console.error('Failed to load A2A connections:', error);
    }
  };

  const loadActivityStats = async () => {
    setLoadingStats(true);
    try {
      // Get activity stats from activity_log table (last 6 months)
      const response = await adminService.getActivityStats();
      
      if (response && response.items) {
        setActivityStats(response.items);
      } else {
        setActivityStats([]);
      }
    } catch (error) {
      console.error('Failed to load activity stats:', error);
      setActivityStats([]);
    } finally {
      setLoadingStats(false);
    }
  };

  const handleSendMessage = () => {
    if (chatInput.trim()) {
      setMessages([...messages, 
        { type: 'user', text: chatInput },
        { type: 'llm', text: 'I understand your request. This feature is coming soon!' }
      ]);
      setChatInput('');
    }
  };

  const handleRefreshCache = async () => {
    try {
      const result = await adminService.refreshCache();
      alert(`Cache refreshed successfully! ${result.message || ''}`);
      // Reload stats after cache refresh
      loadDashboardStats();
      loadStats();
    } catch (error) {
      console.error('Failed to refresh cache:', error);
      alert('Failed to refresh cache. Please try again.');
    }
  };

  return (
    <>
      <GlobalStyles />
      {redirectingApp && <RedirectLoader appName={redirectingApp.name} />}
      <MainContent>
        <PageHeader>
          <HeaderContent>
            <div>
              <PageTitle>
                <i className="fas fa-tachometer-alt"></i>
                CID Dashboard
              </PageTitle>
              <PageSubtitle>Welcome back, {user?.name || 'Administrator'}</PageSubtitle>
            </div>
          </HeaderContent>
        </PageHeader>

        <DashboardGrid>
          <ContentArea>
            <TopRowCards>
              <Card>
                <CardHeader>
                  <i className="fas fa-database"></i>
                  <h4>CID Database Info</h4>
                </CardHeader>
                <KpiGrid style={{ gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', padding: '8px 12px 12px 12px', marginTop: '-4px', display: 'grid' }}>
                  <KpiItem style={{ border: '1px solid #e0e0e0', borderRadius: '12px', padding: '0', overflow: 'hidden', background: '#ffffff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 0', background: '#0b3b63', color: 'white', width: '100%' }}>
                      <h5 style={{ margin: 0, fontSize: '0.75rem', color: 'white', fontWeight: '600', textAlign: 'center', whiteSpace: 'nowrap' }}>Registered Apps</h5>
                    </div>
                    <div style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#2ecc71', fontSize: '1.3rem', fontWeight: 'bold' }}>{appStats.apps.active}</div>
                          <div style={{ fontSize: '0.6rem', color: '#2ecc71', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Active</div>
                        </div>
                        <div style={{ color: '#95a5a6', fontSize: '0.7rem' }}>/</div>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#e74c3c', fontSize: '1.3rem', fontWeight: 'bold' }}>{appStats.apps.inactive}</div>
                          <div style={{ fontSize: '0.6rem', color: '#e74c3c', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Inactive</div>
                        </div>
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#7f8c8d', marginTop: '4px', fontWeight: '500' }}>
                        Total: {appStats.apps.total}
                      </div>
                    </div>
                  </KpiItem>
                  
                  <KpiItem style={{ border: '1px solid #e0e0e0', borderRadius: '12px', padding: '0', overflow: 'hidden', background: '#ffffff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 0', background: '#0b3b63', color: 'white', width: '100%' }}>
                      <h5 style={{ margin: 0, fontSize: '0.75rem', color: 'white', fontWeight: '600', textAlign: 'center', whiteSpace: 'nowrap' }}>Apps Discovered</h5>
                    </div>
                    <div style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#3498db', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.apps?.discovered || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#3498db', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Apps</div>
                        </div>
                        <div style={{ color: '#95a5a6', fontSize: '0.7rem' }}>/</div>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#3498db', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.endpoints_total || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#3498db', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Endpoints</div>
                        </div>
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#7f8c8d', marginTop: '4px', fontWeight: '500' }}>
                        Discovered
                      </div>
                    </div>
                  </KpiItem>
                  
                  <KpiItem style={{ border: '1px solid #e0e0e0', borderRadius: '12px', padding: '0', overflow: 'hidden', background: '#ffffff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 0', background: '#0b3b63', color: 'white', width: '100%' }}>
                      <h5 style={{ margin: 0, fontSize: '0.75rem', color: 'white', fontWeight: '600', textAlign: 'center', whiteSpace: 'nowrap' }}>Total Roles</h5>
                    </div>
                    <div style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#2ecc71', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.roles?.active || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#2ecc71', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Active</div>
                        </div>
                        <div style={{ color: '#95a5a6', fontSize: '0.7rem' }}>/</div>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#e74c3c', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.roles?.inactive || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#e74c3c', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Inactive</div>
                        </div>
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#7f8c8d', marginTop: '4px', fontWeight: '500' }}>
                        Total: {dashboardStats?.roles?.total || 0}
                      </div>
                    </div>
                  </KpiItem>
                  
                  <KpiItem style={{ border: '1px solid #e0e0e0', borderRadius: '12px', padding: '0', overflow: 'hidden', background: '#ffffff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 0', background: '#0b3b63', color: 'white', width: '100%' }}>
                      <h5 style={{ margin: 0, fontSize: '0.75rem', color: 'white', fontWeight: '600', textAlign: 'center', whiteSpace: 'nowrap' }}>Permissions</h5>
                    </div>
                    <div style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#e67e22', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.permissions?.total || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#e67e22', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total</div>
                        </div>
                      </div>
                      <div style={{ fontSize: '0.6rem', color: '#7f8c8d', marginTop: '2px', maxHeight: '40px', overflowY: 'auto' }}>
                        {dashboardStats?.permissions?.by_role && dashboardStats.permissions.by_role.length > 0 ? (
                          dashboardStats.permissions.by_role.map((role: any, index: number) => (
                            <div key={index} style={{ display: 'flex', justifyContent: 'space-between', padding: '1px 0' }}>
                              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '70%' }}>{role.role_name}</span>
                              <span style={{ fontWeight: '600', color: '#e67e22' }}>{role.count}</span>
                            </div>
                          ))
                        ) : (
                          <div style={{ textAlign: 'center', color: '#95a5a6' }}>No roles</div>
                        )}
                      </div>
                    </div>
                  </KpiItem>
                  
                  <KpiItem style={{ border: '1px solid #e0e0e0', borderRadius: '12px', padding: '0', overflow: 'hidden', background: '#ffffff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 0', background: '#0b3b63', color: 'white', width: '100%' }}>
                      <h5 style={{ margin: 0, fontSize: '0.75rem', color: 'white', fontWeight: '600', textAlign: 'center', whiteSpace: 'nowrap' }}>Api Keys</h5>
                    </div>
                    <div style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#2ecc71', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.api_keys?.active || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#2ecc71', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Active</div>
                        </div>
                        <div style={{ color: '#95a5a6', fontSize: '0.7rem' }}>/</div>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#f39c12', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.api_keys?.total || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#f39c12', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total</div>
                        </div>
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#7f8c8d', marginTop: '4px', fontWeight: '500' }}>
                        API Keys
                      </div>
                    </div>
                  </KpiItem>
                  
                  <KpiItem style={{ border: '1px solid #e0e0e0', borderRadius: '12px', padding: '0', overflow: 'hidden', background: '#ffffff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 0', background: '#0b3b63', color: 'white', width: '100%' }}>
                      <h5 style={{ margin: 0, fontSize: '0.75rem', color: 'white', fontWeight: '600', textAlign: 'center', whiteSpace: 'nowrap' }}>Rotation Policies</h5>
                    </div>
                    <div style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#8e44ad', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.rotation_policies_total || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#8e44ad', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Policies</div>
                        </div>
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#7f8c8d', marginTop: '4px', fontWeight: '500' }}>
                        Configured
                      </div>
                    </div>
                  </KpiItem>

                  <KpiItem style={{ border: '1px solid #e0e0e0', borderRadius: '12px', padding: '0', overflow: 'hidden', background: '#ffffff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 0', background: '#0b3b63', color: 'white', width: '100%' }}>
                      <h5 style={{ margin: 0, fontSize: '0.75rem', color: 'white', fontWeight: '600', textAlign: 'center', whiteSpace: 'nowrap' }}>A2A Perm.</h5>
                    </div>
                    <div style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#2ecc71', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.a2a_permissions?.active || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#2ecc71', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Active</div>
                        </div>
                        <div style={{ color: '#95a5a6', fontSize: '0.7rem' }}>/</div>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#e74c3c', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.a2a_permissions?.inactive || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#e74c3c', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Inactive</div>
                        </div>
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#7f8c8d', marginTop: '4px', fontWeight: '500' }}>
                        Total: {dashboardStats?.a2a_permissions?.total || 0}
                      </div>
                    </div>
                  </KpiItem>

                  <KpiItem style={{ border: '1px solid #e0e0e0', borderRadius: '12px', padding: '0', overflow: 'hidden', background: '#ffffff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 0', background: '#0b3b63', color: 'white', width: '100%' }}>
                      <h5 style={{ margin: 0, fontSize: '0.75rem', color: 'white', fontWeight: '600', textAlign: 'center', whiteSpace: 'nowrap' }}>RLS Filters</h5>
                    </div>
                    <div style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#3498db', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.rls_filters?.active || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#3498db', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Active</div>
                        </div>
                        <div style={{ color: '#95a5a6', fontSize: '0.7rem' }}>/</div>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#95a5a6', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.rls_filters?.inactive || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#95a5a6', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Inactive</div>
                        </div>
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#7f8c8d', marginTop: '4px', fontWeight: '500' }}>
                        Total: {dashboardStats?.rls_filters?.total || 0}
                      </div>
                    </div>
                  </KpiItem>

                  <KpiItem style={{ border: '1px solid #e0e0e0', borderRadius: '12px', padding: '0', overflow: 'hidden', background: '#ffffff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 0', background: '#0b3b63', color: 'white', width: '100%' }}>
                      <h5 style={{ margin: 0, fontSize: '0.75rem', color: 'white', fontWeight: '600', textAlign: 'center', whiteSpace: 'nowrap' }}>Total Endpoints</h5>
                    </div>
                    <div style={{ padding: '8px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div className="kpi-value" style={{ color: '#16a085', fontSize: '1.3rem', fontWeight: 'bold' }}>{dashboardStats?.discovery_endpoints_total || 0}</div>
                          <div style={{ fontSize: '0.6rem', color: '#16a085', marginTop: '2px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Discovered</div>
                        </div>
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#7f8c8d', marginTop: '4px', fontWeight: '500' }}>
                        Endpoints in DB
                      </div>
                    </div>
                  </KpiItem>
                </KpiGrid>
              </Card>

              <Card style={{ minHeight: '400px' }}>
                <CardHeader>
                  <i className="fas fa-th-large"></i>
                  <h4>Authorized Apps</h4>
                  <span style={{ marginLeft: 'auto', fontSize: '12px', color: '#64748b' }}>
                    {authorizedApps.length} apps
                  </span>
                </CardHeader>
                <QuickAccessList>
                  {authorizedApps.length > 0 ? (
                    authorizedApps
                      .sort((a, b) => a.name.localeCompare(b.name))
                      .map((app, index) => {
                        const appColors = [
                          '#3b82f6', // Blue
                          '#10b981', // Green
                          '#f59e0b', // Amber
                          '#8b5cf6', // Purple
                          '#ef4444', // Red
                          '#06b6d4', // Cyan
                          '#ec4899', // Pink
                          '#84cc16', // Lime
                        ];
                        const appColor = appColors[index % appColors.length];
                        const appIcons = {
                          'Hr System': 'fa-users',
                          'Bank': 'fa-university',
                          'Inventory': 'fa-warehouse',
                          'HR System': 'fa-users',
                          'Bank System': 'fa-university',
                          'Inventory Management': 'fa-boxes',
                          'Inventory System': 'fa-warehouse',
                        };
                        const iconClass = appIcons[app.name] || 'fa-cube';

                        // Check if this app has A2A connections
                        const connectsTo = a2aConnections
                          .filter(conn => conn.source.client_id === app.clientId && conn.is_active)
                          .map(conn => conn.target.name);
                        const connectsFrom = a2aConnections
                          .filter(conn => conn.target.client_id === app.clientId && conn.is_active)
                          .map(conn => conn.source.name);

                        return (
                      <QuickLink
                        key={app.clientId}
                        $appColor={appColor}
                        onClick={async () => {
                          // Get the current access token
                          const accessToken = localStorage.getItem('access_token');
                          if (!accessToken) {
                            alert('No valid session. Please login again.');
                            return;
                          }

                          // Show loading screen
                          setRedirectingApp({ name: app.name });

                          // Check if app has redirect URIs configured for SSO
                          if (app.redirect_uris && app.redirect_uris.length > 0) {
                            try {
                              // Add a small delay to show the loading screen
                              await new Promise(resolve => setTimeout(resolve, 1500));

                              // Get the first redirect URI (should be the SSO endpoint)
                              const ssoUrl = app.redirect_uris[0];
                              console.log(`Redirecting to ${app.name} SSO endpoint: ${ssoUrl}`);

                              // Create a form and submit it to the app's SSO endpoint
                              const form = document.createElement('form');
                              form.method = 'POST';
                              form.action = ssoUrl;
                              form.target = '_self'; // Open in same window

                              // Add token as hidden input
                              const tokenInput = document.createElement('input');
                              tokenInput.type = 'hidden';
                              tokenInput.name = 'access_token';
                              tokenInput.value = accessToken;
                              form.appendChild(tokenInput);

                              // Add form to page and submit
                              document.body.appendChild(form);
                              form.submit();

                              // Note: The page will redirect, so no need to remove the form
                            } catch (error) {
                              console.error('SSO error:', error);
                              setRedirectingApp(null);
                              alert(`Failed to connect to ${app.name}`);
                            }
                          } else {
                            console.log(`Navigate to app: ${app.name} (no redirect URI configured)`);
                            // For apps without SSO configured, just hide the loader
                            setTimeout(() => setRedirectingApp(null), 2000);
                            // Optionally show a message
                            alert(`${app.name} does not have SSO configured. Please configure redirect URIs in the app settings.`);
                          }
                        }}
                        title={app.description || app.name}
                      >
                        <div className="app-icon">
                          <i className={`fas ${iconClass}`}></i>
                        </div>
                        <div>
                          <div className="app-name">{app.name}</div>
                          {app.description && (
                            <div className="app-description">
                              {app.description.length > 50
                                ? app.description.substring(0, 50) + '...'
                                : app.description}
                            </div>
                          )}
                        </div>
                        {(connectsTo.length > 0 || connectsFrom.length > 0) && (
                          <div style={{
                            position: 'absolute',
                            top: '5px',
                            right: '40px',
                            display: 'flex',
                            gap: '6px',
                            alignItems: 'center'
                          }}>
                            {connectsTo.length > 0 && (
                              <div
                                title={`Connects to: ${connectsTo.join(', ')}`}
                                style={{
                                  background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                                  color: 'white',
                                  padding: '3px 8px',
                                  borderRadius: '12px',
                                  fontSize: '11px',
                                  fontWeight: '600',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  boxShadow: '0 2px 4px rgba(59, 130, 246, 0.3)'
                                }}
                              >
                                <i className="fas fa-arrow-right" style={{ fontSize: '10px' }}></i>
                                {connectsTo.length}
                              </div>
                            )}
                            {connectsFrom.length > 0 && (
                              <div
                                title={`Receives from: ${connectsFrom.join(', ')}`}
                                style={{
                                  background: 'linear-gradient(135deg, #10b981, #059669)',
                                  color: 'white',
                                  padding: '3px 8px',
                                  borderRadius: '12px',
                                  fontSize: '11px',
                                  fontWeight: '600',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  boxShadow: '0 2px 4px rgba(16, 185, 129, 0.3)'
                                }}
                              >
                                <i className="fas fa-arrow-left" style={{ fontSize: '10px' }}></i>
                                {connectsFrom.length}
                              </div>
                            )}
                          </div>
                        )}
                        <StatusIndicator $healthy={appHealthStatus[app.clientId] !== false} />
                      </QuickLink>
                        );
                      })
                  ) : (
                    <QuickLink style={{ cursor: 'default', opacity: 0.6 }}>
                      <i className="fas fa-info-circle"></i>
                      No authorized apps found
                    </QuickLink>
                  )}
                </QuickAccessList>
              </Card>
            </TopRowCards>

            <BottomRowCards>
              <Card>
                <CardHeader>
                  <i className="fas fa-chart-bar"></i>
                  <h4>Activity Stats - Last 6 Months</h4>
                </CardHeader>
                <ActivityStats>
                  {loadingStats ? (
                    <p style={{ textAlign: 'center', color: '#64748b' }}>Loading activity statistics...</p>
                  ) : activityStats.length === 0 ? (
                    <p style={{ textAlign: 'center', color: '#94a3b8' }}>No activity data available</p>
                  ) : (
                    activityStats.map(stat => {
                      // Calculate percentage based on the maximum value
                      const maxCount = Math.max(...activityStats.map(s => s.count));
                      const percentage = (stat.count / maxCount) * 100;
                      
                      return (
                        <StatItem key={stat.type}>
                          <StatLabel title={stat.type}>
                            {stat.type.replace(/_/g, ' ')}
                          </StatLabel>
                          <StatBarContainer>
                            <StatBar $percentage={percentage} />
                          </StatBarContainer>
                          <StatValue>{stat.count}</StatValue>
                        </StatItem>
                      );
                    })
                  )}
                </ActivityStats>
              </Card>

              <Card>
                <CardHeader>
                  <i className="fas fa-book"></i>
                  <h4>Guidelines & Documentation</h4>
                </CardHeader>
                <NewsList style={{ maxHeight: '400px', overflowY: 'auto' }}>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'CIDS_MANDATORY_SPECIFICATION.md', title: 'CIDS Mandatory Specification' })}
                    title="Mandatory requirements for CIDS integration"
                    style={{ background: '#fef2f2', borderLeft: '3px solid #dc2626' }}>
                    <span style={{ flex: 1 }}>🔴 <strong>CIDS Mandatory Specification (NEW)</strong></span>
                    <small style={{ color: '#dc2626', fontSize: '11px', whiteSpace: 'nowrap', fontWeight: 'bold' }}>Sep 15, 2025 - 19:30</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'CIDS_INTEGRATION_GUIDE.md', title: 'CIDS Integration Guide' })}
                    title="Complete integration guide for developers"
                    style={{ background: '#f0f9ff', borderLeft: '3px solid #0b3b63' }}>
                    <span style={{ flex: 1 }}>🚀 <strong>CIDS Integration Guide</strong></span>
                    <small style={{ color: '#0b3b63', fontSize: '11px', whiteSpace: 'nowrap', fontWeight: 'bold' }}>Sep 15, 2025 - 18:45</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'CID_MIGRATION_REPORT_ES.md', title: 'CID Migration Report (ES)' })}
                    title="Spanish version of complete migration report">
                    <span style={{ flex: 1 }}>📄 CID Migration Report (ES)</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 15, 2025 - 16:20</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'CID_MIGRATION_REPORT_EN.md', title: 'CID Migration Report (EN)' })}
                    title="English version of complete migration report">
                    <span style={{ flex: 1 }}>📄 CID Migration Report (EN)</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 15, 2025 - 16:18</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'PRESENTACION_CAMBIOS.md', title: 'Presentation of Changes' })}
                    title="Executive presentation of changes">
                    <span style={{ flex: 1 }}>📊 Presentation of Changes</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 15, 2025 - 16:15</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'CIDS_SECURITY_INTEGRATION_GUIDELINES_v4.md', title: 'Security Integration v4' })}
                    title="Latest security integration guidelines">
                    <span style={{ flex: 1 }}>🔒 Security Integration v4</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 15, 2025 - 14:22</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'SECURITY_COMPLIANCE.md', title: 'Security Compliance' })}
                    title="Security compliance documentation">
                    <span style={{ flex: 1 }}>✅ Security Compliance</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 13, 2025 - 11:45</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'HYBRID_PERMISSIONS_SYSTEM.md', title: 'Hybrid Permissions System' })}
                    title="Hybrid permissions system guide">
                    <span style={{ flex: 1 }}>🔄 Hybrid Permissions System</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 13, 2025 - 10:30</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'CHANGES_20250911.md', title: 'Changes Sep 11' })}
                    title="Changes implemented on Sep 11">
                    <span style={{ flex: 1 }}>📝 Changes Sep 11</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 11, 2025 - 17:45</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'CAMBIOS_IMPLEMENTADOS_20250910.md', title: 'Changes Sep 10' })}
                    title="Changes implemented on Sep 10">
                    <span style={{ flex: 1 }}>📝 Changes Sep 10</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 10, 2025 - 15:30</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'DISCOVERY_FLOW_DOCUMENTATION_ES.md', title: 'Discovery Flow (ES)' })}
                    title="Discovery flow documentation">
                    <span style={{ flex: 1 }}>🔍 Discovery Flow (ES)</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 09, 2025 - 14:20</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'CID_Visual_Standards_Document.md', title: 'Visual Standards' })}
                    title="Visual standards document">
                    <span style={{ flex: 1 }}>🎨 Visual Standards</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 09, 2025 - 09:15</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'MIGRATION_REPORT.md', title: 'Migration Report' })}
                    title="Initial migration report">
                    <span style={{ flex: 1 }}>📋 Migration Report</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 08, 2025 - 16:30</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'CLAUDE.md', title: 'Claude Integration' })}
                    title="Claude AI integration guide">
                    <span style={{ flex: 1 }}>🤖 Claude Integration</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 08, 2025 - 14:00</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'ARCHITECTURE.md', title: 'Architecture' })}
                    title="System architecture documentation">
                    <span style={{ flex: 1 }}>🏗️ Architecture</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 07, 2025 - 10:00</small>
                  </NewsItem>
                  <NewsItem
                    onClick={() => setMarkdownDoc({ name: 'README.md', title: 'README' })}
                    title="Project README">
                    <span style={{ flex: 1 }}>📖 README</span>
                    <small style={{ color: '#666', fontSize: '11px', whiteSpace: 'nowrap' }}>Sep 06, 2025 - 12:00</small>
                  </NewsItem>
                </NewsList>
              </Card>
            </BottomRowCards>
          </ContentArea>

        </DashboardGrid>
      </MainContent>

      {showRolesModal && apps.length > 0 && (
        <RolesModal
          isOpen={showRolesModal}
          onClose={() => setShowRolesModal(false)}
          clientId={apps[0].client_id}
          appName={apps[0].name}
        />
      )}
      
      {showApiKeyModal && apps.length > 0 && (
        <APIKeyModal
          isOpen={showApiKeyModal}
          onClose={() => setShowApiKeyModal(false)}
          clientId={apps[0].client_id}
          appName={apps[0].name}
        />
      )}

      {markdownDoc && (
        <MarkdownViewer
          isOpen={!!markdownDoc}
          onClose={() => setMarkdownDoc(null)}
          docName={markdownDoc.name}
          docTitle={markdownDoc.title}
        />
      )}
    </>
  );
};

export default AdminPageNew;