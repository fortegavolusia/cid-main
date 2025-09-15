import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';
import adminService from '../services/adminService';
import volusiaLogo from '../assets/volusialogo.png';

const LayoutContainer = styled.div`
  display: flex;
  min-height: 100vh;
  background-color: #f0f2f5;
`;

const Sidebar = styled.div<{ $collapsed: boolean }>`
  position: fixed;
  left: 0;
  top: 0;
  width: ${props => props.$collapsed ? '0' : '240px'};
  height: 100vh;
  background: #0b3b63;
  color: #ecf0f1;
  padding: ${props => props.$collapsed ? '0' : '0'};
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  z-index: 1000;
  transform: ${props => props.$collapsed ? 'translateX(-240px)' : 'translateX(0)'};
`;

const SidebarToggle = styled.button<{ $collapsed: boolean }>`
  position: fixed;
  left: ${props => props.$collapsed ? '0' : '240px'};
  top: 50%;
  transform: translateY(-50%);
  width: 30px;
  height: 60px;
  background: linear-gradient(180deg, #1e3a5f 0%, #0d2342 100%);
  color: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-left: none;
  border-radius: 0 6px 6px 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 2px 0 8px 0 rgba(29, 35, 41, 0.05);
  transition: all 0.3s ease;
  z-index: 999;
  font-size: 16px;

  &:hover {
    background: linear-gradient(180deg, #2a4a70 0%, #1a3355 100%);
    color: white;
  }
`;

const LogoContainer = styled.div`
  background: #0b3b63;
  padding: 20px 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 24px;
`;

const Logo = styled.img`
  width: 220px;
  height: auto;
  max-height: 110px;
  object-fit: contain;
`;

const SidebarContent = styled.div`
  flex: 1;
  padding: 0 16px;
`;

const SidebarFooter = styled.div`
  margin-top: auto;
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
`;

const UserSection = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
`;

const UserAvatar = styled.div<{ $hasPhoto?: boolean; $photoUrl?: string }>`
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: ${props => props.$hasPhoto && props.$photoUrl 
    ? `url(${props.$photoUrl}) center/cover` 
    : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'};
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
  color: white;
  border: 3px solid rgba(255, 255, 255, 0.2);
`;

const UserName = styled.div`
  color: rgba(255, 255, 255, 0.95);
  font-size: 16px;
  font-weight: 500;
  line-height: 1.2;
`;

const UserEmail = styled.div`
  color: rgba(255, 255, 255, 0.65);
  font-size: 13px;
  word-break: break-all;
  max-width: 100%;
`;

const MainContent = styled.div<{ $collapsed: boolean }>`
  margin-left: ${props => props.$collapsed ? '30px' : '240px'};
  padding: 24px;
  width: ${props => props.$collapsed ? 'calc(100% - 30px)' : 'calc(100% - 240px)'};
  min-height: 100vh;
  transition: all 0.3s ease;
`;

const NavButton = styled.button`
  background-color: #7a8a9a;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  margin: 3px 0;
  transition: all 0.3s ease;
  font-size: 13px;
  line-height: 1.5;
  font-weight: 400;
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.015);
  width: 100%;
  text-align: center;

  &:hover {
    background-color: #546474;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }

  &:active {
    background-color: #435363;
  }
`;

const LogoutButton = styled(NavButton)`
  background-color: #ffb74d;  /* Sun orange/amber color from Volusia logo */
  color: #0b3b63;  /* Dark blue text for contrast */
  font-weight: 500;

  &:hover {
    background-color: #ffa726;  /* Slightly darker on hover */
    color: #0b3b63;
  }

  &:active {
    background-color: #ff9800;  /* Even darker when pressed */
    color: #0b3b63;
  }
`;


interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [userPhotoUrl, setUserPhotoUrl] = useState<string | null>(null);
  const { user, logout, isAuthenticated } = useAuth();

  useEffect(() => {
    const saved = localStorage.getItem('sidebarCollapsed');
    if (saved === 'true') setSidebarCollapsed(true);
  }, []);

  useEffect(() => {
    // Check admin status by probing a known admin-only endpoint.
    // Avoids 404 noise if /auth/debug/admin-check isn't present in this backend build.
    if (!isAuthenticated) return;
    (async () => {
      try {
        await adminService.getAppLogs({ limit: 1 });
        setIsAdmin(true);
      } catch (e) {
        setIsAdmin(false);
      }
    })();
  }, [isAuthenticated]);

  useEffect(() => {
    // Check for user photo
    if (!user?.email) return;
    
    const checkUserPhoto = async () => {
      try {
        // Use adminService to check for photo (uses correct proxy settings)
        const data = await adminService.getUserPhoto(user.email);
        
        if (data.has_photo && data.photo_path) {
          // Use relative path that will be proxied by Vite
          setUserPhotoUrl(`/photos/${data.photo_path}`);
        }
      } catch (error) {
        // Photo doesn't exist, use default avatar
        console.log('No photo found for user, using default avatar');
      }
    };
    
    checkUserPhoto();
  }, [user]);

  const toggleSidebar = () => {
    const next = !sidebarCollapsed;
    setSidebarCollapsed(next);
    localStorage.setItem('sidebarCollapsed', String(next));
  };

  if (!isAuthenticated) {
    return <>{children}</>;
  }

  return (
    <LayoutContainer>
      <Sidebar $collapsed={sidebarCollapsed}>
        <LogoContainer>
          <Logo src={volusiaLogo} alt="Volusia County" />
        </LogoContainer>
        
        <SidebarContent>
          <NavButton onClick={() => window.location.href = '/dashboard'}>
            Dashboard
          </NavButton>
          
          <NavButton onClick={() => window.location.href = '/home'}>
            My Token
          </NavButton>
          
          <NavButton onClick={() => window.location.href = '/admin'}>
            App Administration
          </NavButton>

          <NavButton onClick={() => window.location.href = '/token-admin'}>
            Token Administration
          </NavButton>

          {isAdmin && (
            <NavButton onClick={() => window.location.href = '/cid-admin'}>
              CID Administration
            </NavButton>
          )}

          <NavButton onClick={() => window.location.href = '/query-builder'}>
            Query Builder
          </NavButton>
        </SidebarContent>
        
        <SidebarFooter>
          {user && (
            <UserSection>
              <UserAvatar $hasPhoto={!!userPhotoUrl} $photoUrl={userPhotoUrl || undefined}>
                {!userPhotoUrl && (user.name ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) : 'U')}
              </UserAvatar>
              <div>
                <UserName>{user.name || 'User'}</UserName>
                <UserEmail>{user.email || 'No email'}</UserEmail>
              </div>
            </UserSection>
          )}
          <div style={{ marginTop: '16px' }}>
            <LogoutButton onClick={logout}>
              Logout
            </LogoutButton>
          </div>
        </SidebarFooter>
      </Sidebar>

      <SidebarToggle $collapsed={sidebarCollapsed} onClick={toggleSidebar}>
        <span style={{ transform: sidebarCollapsed ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease' }}>
          ◀
        </span>
      </SidebarToggle>

      <MainContent $collapsed={sidebarCollapsed}>
        {children}
      </MainContent>
    </LayoutContainer>
  );
};

export default Layout;
