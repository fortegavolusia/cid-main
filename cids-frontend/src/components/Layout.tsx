import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { useAuth } from '../contexts/AuthContext';

const LayoutContainer = styled.div`
  display: flex;
  min-height: 100vh;
  background-color: #f0f2f5;
`;

const Sidebar = styled.div<{ $collapsed: boolean }>`
  position: fixed;
  left: 0;
  top: 0;
  width: ${props => props.$collapsed ? '0' : '280px'};
  height: 100vh;
  background-color: #001529;
  color: rgba(255, 255, 255, 0.85);
  padding: ${props => props.$collapsed ? '0' : '24px'};
  box-shadow: 2px 0 8px 0 rgba(29, 35, 41, 0.05);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  z-index: 1000;
  transform: ${props => props.$collapsed ? 'translateX(-280px)' : 'translateX(0)'};
`;

const SidebarToggle = styled.button<{ $collapsed: boolean }>`
  position: fixed;
  left: ${props => props.$collapsed ? '0' : '280px'};
  top: 50%;
  transform: translateY(-50%);
  width: 30px;
  height: 60px;
  background-color: #001529;
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
    background-color: #1890ff;
    color: white;
  }
`;

const SidebarHeader = styled.h2`
  color: rgba(255, 255, 255, 0.85);
  margin-bottom: 24px;
  font-size: 16px;
  font-weight: 500;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  padding-bottom: 16px;
`;

const SidebarContent = styled.div`
  flex: 1;
`;

const SidebarFooter = styled.div`
  margin-top: auto;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
`;

const MainContent = styled.div<{ $collapsed: boolean }>`
  margin-left: ${props => props.$collapsed ? '30px' : '280px'};
  padding: 24px;
  width: ${props => props.$collapsed ? 'calc(100% - 30px)' : 'calc(100% - 280px)'};
  min-height: 100vh;
  transition: all 0.3s ease;
`;

const NavButton = styled.button`
  background-color: #1890ff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  margin: 4px 0;
  transition: all 0.3s ease;
  font-size: 14px;
  line-height: 1.5715;
  font-weight: 400;
  box-shadow: 0 2px 0 rgba(0, 0, 0, 0.015);
  width: 100%;
  text-align: center;

  &:hover {
    background-color: #40a9ff;
    box-shadow: 0 2px 0 rgba(0, 0, 0, 0.045);
  }

  &:active {
    background-color: #096dd9;
  }
`;

const LogoutButton = styled(NavButton)`
  background-color: #ff4d4f;

  &:hover {
    background-color: #ff7875;
  }

  &:active {
    background-color: #d9363e;
  }
`;

const UserInfo = styled.div`
  margin-bottom: 16px;
  padding: 12px;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  font-size: 12px;
`;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { user, logout, isAuthenticated } = useAuth();

  useEffect(() => {
    const saved = localStorage.getItem('sidebarCollapsed');
    if (saved === 'true') setSidebarCollapsed(true);
  }, []);

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
        <SidebarHeader>CIDS Auth Service</SidebarHeader>
        <SidebarContent>
          {user && (
            <UserInfo>
              <div><strong>{user.name}</strong></div>
              <div>{user.email}</div>
            </UserInfo>
          )}
          
          <NavButton onClick={() => window.location.href = '/'}>
            Home / My Token Information
          </NavButton>
          
          <NavButton onClick={() => window.location.href = '/admin'}>
            Administration
          </NavButton>

          <NavButton onClick={() => window.location.href = '/query-builder'}>
            Query Builder
          </NavButton>
        </SidebarContent>
        
        <SidebarFooter>
          <LogoutButton onClick={logout}>
            Logout
          </LogoutButton>
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
