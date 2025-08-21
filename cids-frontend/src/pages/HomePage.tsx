import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import authService from '../services/authService';
import apiService from '../services/api';

const Container = styled.div`
  background-color: white;
  border-radius: var(--border-radius);
  box-shadow: var(--card-shadow);
  padding: 24px;
  margin-bottom: 24px;
`;

const Title = styled.h1`
  color: rgba(0, 0, 0, 0.85);
  margin: 0 0 24px 0;
  font-size: 24px;
  font-weight: 500;
`;

const InfoSection = styled.div`
  background-color: white;
  border-radius: var(--border-radius);
  padding: 0;
  margin: 24px 0;
  border: 1px solid var(--border-color);
  box-shadow: var(--card-shadow);
`;

const SectionHeader = styled.div`
  padding: 16px 24px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
  transition: all 0.3s ease;
  border-bottom: 1px solid var(--border-color);
`;

const SectionContent = styled.div`
  padding: 24px;
`;


const InfoGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
`;

const InfoCard = styled.div`
  background-color: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 16px;
`;

const InfoItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  
  &:last-child {
    margin-bottom: 0;
  }
`;

const InfoLabel = styled.span`
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
`;

const InfoValue = styled.span`
  color: rgba(0, 0, 0, 0.65);
  font-family: 'Courier New', monospace;
  font-size: 12px;
`;

const Status = styled.span<{ type: 'auth' | 'warn' }>`
  display: inline-block;
  padding: 4px 12px;
  border-radius: 4px;
  font-weight: 400;
  font-size: 12px;
  margin: 8px 0;
  background-color: ${p => p.type === 'auth' ? '#f6ffed' : '#fff2e8'};
  color: ${p => p.type === 'auth' ? 'var(--success-color)' : 'var(--warning-color)'};
  border: 1px solid ${p => p.type === 'auth' ? '#b7eb8f' : '#ffbb96'};
`;

const GroupsList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
`;

const GroupItem = styled.li`
  background-color: #e1f5fe;
  padding: 8px 12px;
  margin: 5px 0;
  border-radius: 4px;
  font-size: 14px;
`;

const TokenDisplay = styled.div`
  background-color: #f6f8fa;
  padding: 16px;
  border-radius: var(--border-radius);
  font-family: 'SF Mono', Monaco, 'Cascadia Mono', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 13px;
  word-break: break-all;
  margin: 16px 0;
  border: 1px solid var(--border-color);
`;


const LoadingSpinner = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  font-size: 16px;
  color: #666;
`;

const ErrorMessage = styled.div`
  background-color: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
`;

const HomePage: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [myToken, setMyToken] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionsOpen, setActionsOpen] = useState(true);
  const [sessionOpen, setSessionOpen] = useState(true);
  const [tokenOpen, setTokenOpen] = useState(true);
  const [apiResponse, setApiResponse] = useState<any>(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchTokenInfo();
    }
  }, [isAuthenticated]);

  const fetchTokenInfo = async () => {
    try {
      setLoading(true);
      const info = await authService.getMyToken();
      setMyToken(info);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch token information');
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return null; // This will be handled by the router
  }

  if (loading) {
    return (
      <Container>
        <LoadingSpinner>Loading token information...</LoadingSpinner>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <Title>My Token Information</Title>
        <ErrorMessage>{error}</ErrorMessage>
      </Container>
    );
  }

  return (
    <Container>
      <Title>My Token Information</Title>

      <InfoSection>
        <SectionHeader onClick={() => setActionsOpen(!actionsOpen)}>
          <h2 style={{ margin: 0 }}>Available Actions</h2>
          <span style={{ transform: actionsOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease', color: 'var(--text-secondary)' }}>▼</span>
        </SectionHeader>
        {actionsOpen && (
          <SectionContent>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 15, marginTop: 20 }}>
              <div>
                <button className="button" onClick={async() => {
                  const data = await authService.getSessionToken();
                  setApiResponse({ title: 'Session Tokens', data });
                }}>Get Internal Tokens</button>
                <p style={{ fontSize: 12, color: '#666', margin: 0 }}>Retrieve current internal access and refresh tokens</p>
              </div>
              <div>
                <button className="button" onClick={async() => {
                  const token = authService.getAuthToken();
                  if (!token) return setApiResponse({ title: 'Error', data: { error: 'No token' } });
                  const data = await authService.validateToken(token);
                  setApiResponse({ title: 'Token Validation Response', data });
                }}>Validate Internal Access Token</button>
                <p style={{ fontSize: 12, color: '#666', margin: 0 }}>Test validation of your internal access token</p>
              </div>
              <div>
                <button className="button" onClick={async() => {
                  const data = await apiService.get('/auth/public-key');
                  setApiResponse({ title: 'Public Key Response', data });
                }}>View Internal Public Key</button>
                <p style={{ fontSize: 12, color: '#666', margin: 0 }}>Get our public key for internal token validation</p>
              </div>
            </div>
          </SectionContent>
        )}
      </InfoSection>

      <InfoSection>
        <SectionHeader onClick={() => setSessionOpen(!sessionOpen)}>
          <h2 style={{ margin: 0 }}>Current Session</h2>
          <span style={{ transform: sessionOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease', color: 'var(--text-secondary)' }}>▼</span>
        </SectionHeader>
        {sessionOpen && (
          <SectionContent>
            <p className="explanation">This section shows your current authentication status and session information.</p>
            <Status type="auth">Authenticated</Status>
            {user && (
              <InfoGrid>
                <InfoCard>
                  <InfoItem>
                    <InfoLabel>User:</InfoLabel>
                    <InfoValue>{user.name}</InfoValue>
                  </InfoItem>
                  <InfoItem>
                    <InfoLabel>Email:</InfoLabel>
                    <InfoValue>{user.email}</InfoValue>
                  </InfoItem>
                  <InfoItem>
                    <InfoLabel>Azure AD Subject ID:</InfoLabel>
                    <InfoValue>{user.sub}</InfoValue>
                  </InfoItem>
                </InfoCard>
              </InfoGrid>
            )}
            {user?.groups?.length ? (
              <>
                <h3>Active Directory Groups</h3>
                <p>These are the AD groups you belong to:</p>
                <GroupsList>
                  {user.groups.map((group, idx) => (
                    <GroupItem key={idx}>
                      <span className="group-name">{group.displayName}</span>
                    </GroupItem>
                  ))}
                </GroupsList>
              </>
            ) : null}
          </SectionContent>
        )}
      </InfoSection>

      <InfoSection>
        <SectionHeader onClick={() => setTokenOpen(!tokenOpen)}>
          <h2 style={{ margin: 0 }}>Internal Access Token (JWT)</h2>
          <span style={{ transform: tokenOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease', color: 'var(--text-secondary)' }}>▼</span>
        </SectionHeader>
        {tokenOpen && (
          <SectionContent>
            <p>This is the internal JWT access token your applications use for API authentication:</p>
            <TokenDisplay>{authService.getAuthToken() || ''}</TokenDisplay>
            <h3>Decoded Token Claims:</h3>
            <p>These are the claims contained in your internal JWT token:</p>
            <pre style={{ background: '#f6f8fa', padding: 16, borderRadius: 6, border: '1px solid var(--border-color)' }}>
              {JSON.stringify(myToken?.claims || user?.raw_claims || {}, null, 2)}
            </pre>
          </SectionContent>
        )}
      </InfoSection>

      {apiResponse && (
        <InfoSection>
          <SectionHeader onClick={() => setActionsOpen(!actionsOpen)}>
            <h2 style={{ margin: 0 }}>API Response</h2>
            <span style={{ color: 'var(--text-secondary)' }}>▼</span>
          </SectionHeader>
          <SectionContent>
            <pre style={{ background: '#f6f8fa', padding: 16, borderRadius: 6, border: '1px solid var(--border-color)' }}>
              {JSON.stringify(apiResponse.data, null, 2)}
            </pre>
          </SectionContent>
        </InfoSection>
      )}
    </Container>
  );
};

export default HomePage;
