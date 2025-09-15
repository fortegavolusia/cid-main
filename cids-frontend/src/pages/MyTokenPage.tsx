import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import authService from '../services/authService';
import adminService from '../services/adminService';

// Styled Components
const Container = styled.div`
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
`;

const Header = styled.div`
  background: #0b3b63;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  text-align: left;
`;

const Title = styled.h1`
  color: white;
  font-size: 1.875rem;
  font-weight: 600;
  margin: 0 0 8px 0;
  letter-spacing: -0.025em;
`;

const Subtitle = styled.p`
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.875rem;
  margin: 0;
`;

// Stats Cards (50% smaller)
const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
`;

const StatCard = styled.div<{ $status?: 'valid' | 'warning' | 'expired' }>`
  background: white;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  border-left: 3px solid ${props =>
    props.$status === 'valid' ? '#10b981' :
    props.$status === 'warning' ? '#f59e0b' :
    props.$status === 'expired' ? '#ef4444' : '#6366f1'
  };
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  }
`;

const StatIcon = styled.div`
  font-size: 16px;
  margin-bottom: 6px;
`;

const StatLabel = styled.div`
  color: #666;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 4px;
`;

const StatValue = styled.div`
  color: #1a1a1a;
  font-size: 16px;
  font-weight: 600;
`;

const StatSubtext = styled.div`
  color: #999;
  font-size: 10px;
  margin-top: 2px;
`;

// Main Content Grid
const ContentGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
  
  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
`;

const Section = styled.div`
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
`;

const SectionHeader = styled.div`
  padding: 20px 24px;
  border-bottom: 1px solid #f0f0f0;
  background-color: #f8f9fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const SectionTitle = styled.h2`
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const SectionContent = styled.div`
  padding: 24px;
`;

// Token Display
const TokenContainer = styled.div`
  position: relative;
  background: #1e1e1e;
  border-radius: 8px;
  padding: 16px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  color: #d4d4d4;
  overflow-x: auto;
  max-height: 200px;
  overflow-y: auto;
  
  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  
  &::-webkit-scrollbar-track {
    background: #2d2d2d;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #565656;
    border-radius: 4px;
  }
`;

const TokenPart = styled.span<{ $type: 'header' | 'payload' | 'signature' }>`
  color: ${props => 
    props.$type === 'header' ? '#ff79c6' :
    props.$type === 'payload' ? '#50fa7b' :
    '#8be9fd'
  };
  word-break: break-all;
`;

const CopyButton = styled.button`
  position: absolute;
  top: 12px;
  right: 12px;
  background: #4a5568;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
  
  &:hover {
    background: #2d3748;
  }
  
  &:active {
    transform: scale(0.95);
  }
`;

const TokenToggle = styled.button`
  background: #f0f0f0;
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
  
  &:hover {
    background: #e0e0e0;
  }
`;

// Permissions Matrix
const PermissionsTable = styled.table`
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
`;

const TableHeader = styled.th`
  background: #f8f9fa;
  padding: 12px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  color: #666;
  border-bottom: 2px solid #e0e0e0;
  
  &:first-child {
    border-top-left-radius: 8px;
  }
  
  &:last-child {
    border-top-right-radius: 8px;
  }
`;

const TableRow = styled.tr`
  &:hover {
    background: #f8f9fa;
  }
`;

const TableCell = styled.td`
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 14px;
  color: #333;
`;

const PermissionBadge = styled.span<{ $granted: boolean }>`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: ${props => props.$granted ? '#10b981' : '#ef4444'};
  color: white;
  font-size: 14px;
`;

// Activity Timeline
const Timeline = styled.div`
  position: relative;
  padding-left: 32px;
  
  &::before {
    content: '';
    position: absolute;
    left: 12px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: #e0e0e0;
  }
`;

const TimelineItem = styled.div`
  position: relative;
  margin-bottom: 24px;
  
  &::before {
    content: '';
    position: absolute;
    left: -24px;
    top: 8px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #6366f1;
    border: 2px solid white;
    box-shadow: 0 0 0 4px #f0f0f0;
  }
`;

const TimelineTime = styled.div`
  color: #999;
  font-size: 12px;
  margin-bottom: 4px;
`;

const TimelineContent = styled.div`
  color: #333;
  font-size: 14px;
`;

// Quick Actions
const ActionsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
`;

const ActionCard = styled.button`
  background: white;
  border: 2px solid #f0f0f0;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  
  &:hover {
    border-color: #6366f1;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
  }
  
  &:active {
    transform: translateY(0);
  }
`;

const ActionIcon = styled.div`
  font-size: 32px;
  margin-bottom: 8px;
`;

const ActionTitle = styled.div`
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
`;

const ActionDescription = styled.div`
  font-size: 12px;
  color: #666;
`;

// JSON Display
const JSONBlock = styled.pre`
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  color: #333;
  margin: 0;
  max-height: 400px;
  overflow-y: auto;
`;

// Component
// Helper functions
const formatTimeAgo = (date: Date): string => {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
};

const formatAction = (action: string, details?: any): string => {
  const actionMap: { [key: string]: string } = {
    'token_issued': 'Token issued',
    'token_refreshed': 'Token refreshed',
    'token_validated': 'Token validated',
    'login': 'Logged in via Azure AD',
    'logout': 'Logged out',
    'api_access': 'API access granted',
    'permission_check': 'Permission validated',
    'app_access': 'Application accessed'
  };

  // Handle application usage patterns (uso.hr, uso.payroll, etc.)
  if (action.startsWith('uso.')) {
    const appName = action.replace('uso.', '');
    return `Used ${appName.toUpperCase()} application`;
  }

  const formattedAction = actionMap[action] || action.replace(/_/g, ' ');
  if (details?.application) {
    return `${formattedAction} (${details.application})`;
  }
  return formattedAction;
};

const MyTokenPage: React.FC = () => {
  const { user } = useAuth();
  const [showToken, setShowToken] = useState(false);
  const [tokenCopied, setTokenCopied] = useState(false);
  const [tokenInfo, setTokenInfo] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [apiResponse, setApiResponse] = useState<any>(null);
  const [activityLogCount, setActivityLogCount] = useState(0);

  useEffect(() => {
    loadTokenInfo();
    loadActivities();
  }, []);

  const loadTokenInfo = () => {
    const token = authService.getAuthToken();
    if (token) {
      try {
        const parts = token.split('.');
        const payload = JSON.parse(atob(parts[1]));
        setTokenInfo(payload);
      } catch (error) {
        console.error('Error decoding token:', error);
      }
    }
  };

  const loadActivities = async () => {
    try {
      // Get activity log count for the user from database
      const countResponse = await adminService.getActivityLogCount(user?.email);
      setActivityLogCount(countResponse.count || 0);

      // Get recent token activity from backend
      const response = await adminService.getTokenActivityLogs({
        limit: 10,
        user_email: user?.email
      });

      if (response.items && response.items.length > 0) {
        // Format recent activities - prioritize app usage and logins
        const formattedActivities = response.items
          .slice(0, 5)  // Take only the 5 most recent
          .map(item => ({
            time: formatTimeAgo(new Date(item.timestamp || item.created_at)),
            action: formatAction(item.action, item.details)
          }));

        setActivities(formattedActivities);
      } else {
        // Fallback to basic activities if no logs found
        setActivities([
          { time: 'Just now', action: 'Viewing token information' },
          { time: formatTimeAgo(new Date(tokenInfo?.iat * 1000 || Date.now() - 3600000)), action: 'Token issued' }
        ]);
      }
    } catch (error) {
      console.error('Failed to load activities:', error);
      // Fallback activities if API fails
      setActivityLogCount(0);
      setActivities([
        { time: 'Just now', action: 'Viewing token information' },
        { time: formatTimeAgo(new Date(tokenInfo?.iat * 1000 || Date.now() - 3600000)), action: 'Token issued' }
      ]);
    }
  };

  const copyToken = () => {
    const token = authService.getAuthToken();
    if (token) {
      navigator.clipboard.writeText(token);
      setTokenCopied(true);
      setTimeout(() => setTokenCopied(false), 2000);
    }
  };

  const getTokenExpiry = () => {
    if (!tokenInfo?.exp) return { status: 'expired', time: 'Expired' };
    
    const exp = new Date(tokenInfo.exp * 1000);
    const now = new Date();
    const diff = exp.getTime() - now.getTime();
    
    if (diff <= 0) return { status: 'expired', time: 'Expired' };
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    
    if (minutes < 15) return { status: 'warning', time: `${minutes}m` };
    if (hours > 0) return { status: 'valid', time: `${hours}h ${minutes % 60}m` };
    return { status: 'valid', time: `${minutes}m` };
  };

  const getPermissionMatrix = () => {
    const permissions = tokenInfo?.permissions || {};
    const matrix: any[] = [];
    
    Object.entries(permissions).forEach(([appId, perms]: [string, any]) => {
      const appPermissions = {
        app: appId === 'app_fba7654e91e6413c' ? 'HR System' : appId,
        base: false,
        pii: false,
        financial: false,
        sensitive: false,
      };
      
      if (Array.isArray(perms)) {
        perms.forEach((perm: string) => {
          if (perm.includes('.base')) appPermissions.base = true;
          if (perm.includes('.pii')) appPermissions.pii = true;
          if (perm.includes('.financial')) appPermissions.financial = true;
          if (perm.includes('.sensitive')) appPermissions.sensitive = true;
        });
      }
      
      matrix.push(appPermissions);
    });
    
    return matrix;
  };

  const tokenExpiry = getTokenExpiry();
  const permissionMatrix = getPermissionMatrix();
  const token = authService.getAuthToken() || '';
  const tokenParts = token.split('.');

  return (
    <Container>
      <Header>
        <Title>My Token</Title>
        <Subtitle>View and manage your authentication token, permissions, and access details</Subtitle>
      </Header>

      <StatsGrid>
        <StatCard $status={tokenExpiry.status as any}>
          <StatIcon>🎫</StatIcon>
          <StatLabel>Token Status</StatLabel>
          <StatValue>{tokenExpiry.status === 'valid' ? 'Valid' : tokenExpiry.status === 'warning' ? 'Expiring Soon' : 'Expired'}</StatValue>
          <StatSubtext>JWT Authentication Token</StatSubtext>
        </StatCard>

        <StatCard>
          <StatIcon>⏰</StatIcon>
          <StatLabel>Time Remaining</StatLabel>
          <StatValue>{tokenExpiry.time}</StatValue>
          <StatSubtext>Until token expiration</StatSubtext>
        </StatCard>

        <StatCard>
          <StatIcon>📊</StatIcon>
          <StatLabel>Activity Logs Counter</StatLabel>
          <StatValue>{activityLogCount}</StatValue>
          <StatSubtext>Total activities in database</StatSubtext>
        </StatCard>

        <StatCard>
          <StatIcon>🔐</StatIcon>
          <StatLabel>Total Permissions</StatLabel>
          <StatValue>
            {Object.values(tokenInfo?.permissions || {}).reduce((acc: number, perms: any) => 
              acc + (Array.isArray(perms) ? perms.length : 0), 0
            )}
          </StatValue>
          <StatSubtext>Across all applications</StatSubtext>
        </StatCard>
      </StatsGrid>

      <ContentGrid>
        <Section>
          <SectionHeader>
            <SectionTitle>
              <span>🎟️</span> JWT Token
            </SectionTitle>
            <TokenToggle onClick={() => setShowToken(!showToken)}>
              {showToken ? 'Hide' : 'Show'} Token
            </TokenToggle>
          </SectionHeader>
          <SectionContent>
            {showToken ? (
              <TokenContainer>
                <CopyButton onClick={copyToken}>
                  {tokenCopied ? '✓ Copied!' : '📋 Copy'}
                </CopyButton>
                <TokenPart $type="header">{tokenParts[0]}</TokenPart>
                <span style={{ color: '#ff6b6b' }}>.</span>
                <TokenPart $type="payload">{tokenParts[1]}</TokenPart>
                <span style={{ color: '#ff6b6b' }}>.</span>
                <TokenPart $type="signature">{tokenParts[2]}</TokenPart>
              </TokenContainer>
            ) : (
              <TokenContainer style={{ textAlign: 'center', padding: '40px' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔒</div>
                <div style={{ color: '#999' }}>Token hidden for security</div>
                <div style={{ color: '#666', fontSize: '11px', marginTop: '8px' }}>
                  Click "Show Token" to reveal
                </div>
              </TokenContainer>
            )}
            
            <h3 style={{ marginTop: '24px', marginBottom: '16px' }}>Decoded Claims</h3>
            <JSONBlock>{JSON.stringify(tokenInfo, null, 2)}</JSONBlock>
          </SectionContent>
        </Section>

        <Section>
          <SectionHeader>
            <SectionTitle>
              <span>🛡️</span> Permission Matrix
            </SectionTitle>
          </SectionHeader>
          <SectionContent>
            <PermissionsTable>
              <thead>
                <tr>
                  <TableHeader>Application</TableHeader>
                  <TableHeader style={{ textAlign: 'center' }}>BASE</TableHeader>
                  <TableHeader style={{ textAlign: 'center' }}>PII</TableHeader>
                  <TableHeader style={{ textAlign: 'center' }}>FINANCIAL</TableHeader>
                  <TableHeader style={{ textAlign: 'center' }}>SENSITIVE</TableHeader>
                </tr>
              </thead>
              <tbody>
                {permissionMatrix.map((app, idx) => (
                  <TableRow key={idx}>
                    <TableCell style={{ fontWeight: 600 }}>{app.app}</TableCell>
                    <TableCell style={{ textAlign: 'center' }}>
                      <PermissionBadge $granted={app.base}>
                        {app.base ? '✓' : '✗'}
                      </PermissionBadge>
                    </TableCell>
                    <TableCell style={{ textAlign: 'center' }}>
                      <PermissionBadge $granted={app.pii}>
                        {app.pii ? '✓' : '✗'}
                      </PermissionBadge>
                    </TableCell>
                    <TableCell style={{ textAlign: 'center' }}>
                      <PermissionBadge $granted={app.financial}>
                        {app.financial ? '✓' : '✗'}
                      </PermissionBadge>
                    </TableCell>
                    <TableCell style={{ textAlign: 'center' }}>
                      <PermissionBadge $granted={app.sensitive}>
                        {app.sensitive ? '✓' : '✗'}
                      </PermissionBadge>
                    </TableCell>
                  </TableRow>
                ))}
              </tbody>
            </PermissionsTable>
          </SectionContent>
        </Section>
      </ContentGrid>

      <ContentGrid>
        <Section>
          <SectionHeader>
            <SectionTitle>
              <span>⚡</span> Quick Actions
            </SectionTitle>
          </SectionHeader>
          <SectionContent>
            <ActionsGrid>
              <ActionCard onClick={async () => {
                const data = await authService.validateToken(token);
                setApiResponse({ title: 'Token Validation', data });
              }}>
                <ActionIcon>✅</ActionIcon>
                <ActionTitle>Validate Token</ActionTitle>
                <ActionDescription>Check token validity</ActionDescription>
              </ActionCard>

              <ActionCard onClick={async () => {
                const data = await authService.getSessionToken();
                setApiResponse({ title: 'Session Info', data });
              }}>
                <ActionIcon>🔍</ActionIcon>
                <ActionTitle>Session Info</ActionTitle>
                <ActionDescription>View session details</ActionDescription>
              </ActionCard>

              <ActionCard onClick={async () => {
                const refreshToken = localStorage.getItem('refresh_token');
                if (refreshToken) {
                  await authService.refreshToken(refreshToken);
                  loadTokenInfo();
                } else {
                  setApiResponse({ title: 'Error', data: { error: 'No refresh token available' } });
                }
              }}>
                <ActionIcon>🔄</ActionIcon>
                <ActionTitle>Refresh Token</ActionTitle>
                <ActionDescription>Force token refresh</ActionDescription>
              </ActionCard>
            </ActionsGrid>
          </SectionContent>
        </Section>

        <Section>
          <SectionHeader>
            <SectionTitle>
              <span>📜</span> Recent Activity
            </SectionTitle>
          </SectionHeader>
          <SectionContent>
            <Timeline>
              {activities.map((activity, idx) => (
                <TimelineItem key={idx}>
                  <TimelineTime>{activity.time}</TimelineTime>
                  <TimelineContent>{activity.action}</TimelineContent>
                </TimelineItem>
              ))}
            </Timeline>
          </SectionContent>
        </Section>
      </ContentGrid>

      {apiResponse && (
        <Section style={{ marginTop: '24px' }}>
          <SectionHeader>
            <SectionTitle>
              <span>📡</span> API Response: {apiResponse.title}
            </SectionTitle>
            <TokenToggle onClick={() => setApiResponse(null)}>Close</TokenToggle>
          </SectionHeader>
          <SectionContent>
            <JSONBlock>{JSON.stringify(apiResponse.data, null, 2)}</JSONBlock>
          </SectionContent>
        </Section>
      )}
    </Container>
  );
};

export default MyTokenPage;