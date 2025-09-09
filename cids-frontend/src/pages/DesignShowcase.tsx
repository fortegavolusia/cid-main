import React, { useState } from 'react';
import styled, { createGlobalStyle, css } from 'styled-components';

// Global styles for each theme
const GlobalStyle = createGlobalStyle<{ theme: string }>`
  ${props => props.theme === 'glassmorphism' && css`
    body {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
  `}
  ${props => props.theme === 'enterprise' && css`
    body {
      background: #f8f9fa;
    }
  `}
  ${props => props.theme === 'dark' && css`
    body {
      background: #0a0a0a;
    }
  `}
  ${props => props.theme === 'material' && css`
    body {
      background: #fafafa;
    }
  `}
  ${props => props.theme === 'neumorphism' && css`
    body {
      background: #e0e5ec;
    }
  `}
`;

const Container = styled.div`
  min-height: 100vh;
  padding: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

const ThemeSelector = styled.div`
  display: flex;
  gap: 10px;
  margin-bottom: 40px;
  flex-wrap: wrap;
  justify-content: center;
`;

const ThemeButton = styled.button<{ active: boolean }>`
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  background: ${props => props.active ? '#667eea' : '#e0e5ec'};
  color: ${props => props.active ? 'white' : '#333'};
  font-weight: ${props => props.active ? 'bold' : 'normal'};
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
  }
`;

// Style variations for each theme
const LoginCard = styled.div<{ theme: string }>`
  width: 400px;
  padding: 40px;
  border-radius: 20px;
  transition: all 0.3s ease;
  
  ${props => props.theme === 'glassmorphism' && css`
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
    color: white;
    
    h2 { color: white; }
    p { color: rgba(255, 255, 255, 0.8); }
  `}
  
  ${props => props.theme === 'enterprise' && css`
    background: white;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
    border: 1px solid #e1e4e8;
    
    h2 { color: #0066cc; }
    p { color: #586069; }
  `}
  
  ${props => props.theme === 'dark' && css`
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    box-shadow: 0 0 20px rgba(0, 255, 255, 0.1);
    color: #ffffff;
    
    h2 { 
      color: #00ffff;
      text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
    }
    p { color: #b0b0b0; }
  `}
  
  ${props => props.theme === 'material' && css`
    background: white;
    box-shadow: 0 3px 5px -1px rgba(0,0,0,0.2),
                0 6px 10px 0 rgba(0,0,0,0.14),
                0 1px 18px 0 rgba(0,0,0,0.12);
    
    h2 { color: #3f51b5; }
    p { color: rgba(0, 0, 0, 0.6); }
  `}
  
  ${props => props.theme === 'neumorphism' && css`
    background: #e0e5ec;
    box-shadow: 20px 20px 60px #bebebe,
                -20px -20px 60px #ffffff;
    
    h2 { color: #6c7ee1; }
    p { color: #797979; }
  `}
`;

const StyledButton = styled.button<{ theme: string }>`
  width: 100%;
  padding: 12px 24px;
  margin-top: 20px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  
  ${props => props.theme === 'glassmorphism' && css`
    background: linear-gradient(135deg, #ff0080 0%, #ff8c00 100%);
    color: white;
    box-shadow: 0 4px 15px 0 rgba(255, 0, 128, 0.4);
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px 0 rgba(255, 0, 128, 0.6);
    }
  `}
  
  ${props => props.theme === 'enterprise' && css`
    background: #0066cc;
    color: white;
    
    &:hover {
      background: #0052a3;
      box-shadow: 0 4px 12px rgba(0, 102, 204, 0.3);
    }
  `}
  
  ${props => props.theme === 'dark' && css`
    background: linear-gradient(135deg, #00ffff 0%, #32ff7e 100%);
    color: #0a0a0a;
    font-weight: bold;
    
    &:hover {
      box-shadow: 0 0 20px rgba(0, 255, 255, 0.6);
      transform: scale(1.02);
    }
  `}
  
  ${props => props.theme === 'material' && css`
    background: #3f51b5;
    color: white;
    box-shadow: 0 3px 1px -2px rgba(0,0,0,0.2),
                0 2px 2px 0 rgba(0,0,0,0.14),
                0 1px 5px 0 rgba(0,0,0,0.12);
    
    &:hover {
      background: #303f9f;
      box-shadow: 0 6px 10px -4px rgba(0,0,0,0.2),
                  0 4px 4px 0 rgba(0,0,0,0.14),
                  0 2px 10px 0 rgba(0,0,0,0.12);
    }
  `}
  
  ${props => props.theme === 'neumorphism' && css`
    background: #e0e5ec;
    color: #6c7ee1;
    box-shadow: 9px 9px 16px #bebebe,
                -9px -9px 16px #ffffff;
    
    &:hover {
      box-shadow: inset 9px 9px 16px #bebebe,
                  inset -9px -9px 16px #ffffff;
    }
    
    &:active {
      box-shadow: inset 5px 5px 10px #bebebe,
                  inset -5px -5px 10px #ffffff;
    }
  `}
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-top: 40px;
  width: 100%;
  max-width: 900px;
`;

const StatCard = styled.div<{ theme: string }>`
  padding: 20px;
  border-radius: 12px;
  transition: all 0.3s ease;
  
  ${props => props.theme === 'glassmorphism' && css`
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: white;
    
    &:hover {
      background: rgba(255, 255, 255, 0.15);
      transform: translateY(-5px);
    }
  `}
  
  ${props => props.theme === 'enterprise' && css`
    background: white;
    border: 1px solid #e1e4e8;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    
    &:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
      transform: translateY(-2px);
    }
  `}
  
  ${props => props.theme === 'dark' && css`
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    color: white;
    
    &:hover {
      border-color: #00ffff;
      box-shadow: 0 0 15px rgba(0, 255, 255, 0.3);
    }
  `}
  
  ${props => props.theme === 'material' && css`
    background: white;
    box-shadow: 0 2px 4px -1px rgba(0,0,0,0.2),
                0 4px 5px 0 rgba(0,0,0,0.14),
                0 1px 10px 0 rgba(0,0,0,0.12);
    
    &:hover {
      box-shadow: 0 5px 5px -3px rgba(0,0,0,0.2),
                  0 8px 10px 1px rgba(0,0,0,0.14),
                  0 3px 14px 2px rgba(0,0,0,0.12);
    }
  `}
  
  ${props => props.theme === 'neumorphism' && css`
    background: #e0e5ec;
    box-shadow: 5px 5px 10px #bebebe,
                -5px -5px 10px #ffffff;
    
    &:hover {
      box-shadow: 8px 8px 16px #bebebe,
                  -8px -8px 16px #ffffff;
    }
  `}
  
  h3 {
    margin: 0 0 10px 0;
    font-size: 14px;
    text-transform: uppercase;
    opacity: 0.7;
  }
  
  p {
    margin: 0;
    font-size: 28px;
    font-weight: bold;
  }
`;

export default function DesignShowcase() {
  const [selectedTheme, setSelectedTheme] = useState('glassmorphism');
  
  const themes = [
    { id: 'glassmorphism', name: '🌟 Glass Morphism' },
    { id: 'enterprise', name: '💼 Enterprise Clean' },
    { id: 'dark', name: '🌙 Dark Mode Pro' },
    { id: 'material', name: '🎯 Material Design' },
    { id: 'neumorphism', name: '🔮 Neumorphism' }
  ];
  
  return (
    <>
      <GlobalStyle theme={selectedTheme} />
      <Container>
        <h1 style={{ color: selectedTheme === 'dark' ? 'white' : '#333' }}>
          CID Design Showcase
        </h1>
        
        <ThemeSelector>
          {themes.map(theme => (
            <ThemeButton
              key={theme.id}
              active={selectedTheme === theme.id}
              onClick={() => setSelectedTheme(theme.id)}
            >
              {theme.name}
            </ThemeButton>
          ))}
        </ThemeSelector>
        
        <LoginCard theme={selectedTheme}>
          <h2>Azure AD Authentication</h2>
          <p>Version 1.0.0 - Development</p>
          
          <div style={{ marginTop: '30px' }}>
            <input
              type="text"
              placeholder="Email"
              style={{
                width: '100%',
                padding: '10px',
                marginBottom: '10px',
                borderRadius: '8px',
                border: selectedTheme === 'dark' ? '1px solid #2a2a2a' : '1px solid #ddd',
                background: selectedTheme === 'dark' ? '#0a0a0a' : 'white',
                color: selectedTheme === 'dark' ? 'white' : '#333'
              }}
            />
            <input
              type="password"
              placeholder="Password"
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '8px',
                border: selectedTheme === 'dark' ? '1px solid #2a2a2a' : '1px solid #ddd',
                background: selectedTheme === 'dark' ? '#0a0a0a' : 'white',
                color: selectedTheme === 'dark' ? 'white' : '#333'
              }}
            />
          </div>
          
          <StyledButton theme={selectedTheme}>
            Sign in with Azure AD
          </StyledButton>
        </LoginCard>
        
        <StatsGrid>
          <StatCard theme={selectedTheme}>
            <h3>Active Users</h3>
            <p>1,234</p>
          </StatCard>
          <StatCard theme={selectedTheme}>
            <h3>API Calls</h3>
            <p>45.2K</p>
          </StatCard>
          <StatCard theme={selectedTheme}>
            <h3>Success Rate</h3>
            <p>99.9%</p>
          </StatCard>
        </StatsGrid>
      </Container>
    </>
  );
}