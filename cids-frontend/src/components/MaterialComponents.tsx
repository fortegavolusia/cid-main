import React, { ReactNode } from 'react';
import styled, { css, keyframes } from 'styled-components';
import { materialTheme } from '../styles/materialTheme';

// Ripple effect animation
const rippleAnimation = keyframes`
  0% {
    transform: scale(0);
    opacity: 1;
  }
  100% {
    transform: scale(4);
    opacity: 0;
  }
`;

// Material Card Component
export const MaterialCard = styled.div<{ elevation?: number; clickable?: boolean }>`
  background: ${materialTheme.colors.surface};
  border-radius: ${materialTheme.borderRadius.md};
  padding: ${materialTheme.spacing.lg};
  box-shadow: ${props => materialTheme.elevation[props.elevation || 1]};
  transition: box-shadow ${materialTheme.transitions.standard};
  position: relative;
  overflow: hidden;
  
  ${props => props.clickable && css`
    cursor: pointer;
    &:hover {
      box-shadow: ${materialTheme.elevation[4]};
    }
    &:active {
      box-shadow: ${materialTheme.elevation[2]};
    }
  `}
`;

// Material Button Component
const ButtonBase = styled.button<{ 
  variant?: 'filled' | 'outlined' | 'text' | 'elevated' | 'tonal';
  color?: 'primary' | 'secondary' | 'error' | 'success' | 'warning';
  size?: 'small' | 'medium' | 'large';
  fullWidth?: boolean;
}>`
  position: relative;
  overflow: hidden;
  border: none;
  cursor: pointer;
  font-family: ${materialTheme.typography.fontFamily};
  font-weight: 500;
  text-transform: none;
  transition: all ${materialTheme.transitions.standard};
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: ${props => props.fullWidth ? '100%' : 'auto'};
  
  // Size variations
  ${props => {
    switch(props.size) {
      case 'small':
        return css`
          padding: 6px 12px;
          font-size: 13px;
          height: 32px;
          border-radius: ${materialTheme.borderRadius.sm};
        `;
      case 'large':
        return css`
          padding: 12px 24px;
          font-size: 15px;
          height: 48px;
          border-radius: ${materialTheme.borderRadius.md};
        `;
      default: // medium
        return css`
          padding: 10px 24px;
          font-size: 14px;
          height: 40px;
          border-radius: ${materialTheme.borderRadius.lg};
        `;
    }
  }}
  
  // Color and variant combinations
  ${props => {
    const color = materialTheme.colors[props.color || 'primary'];
    const colorLight = materialTheme.colors[`${props.color || 'primary'}Light`];
    const colorDark = materialTheme.colors[`${props.color || 'primary'}Dark`];
    
    switch(props.variant) {
      case 'outlined':
        return css`
          background: transparent;
          color: ${color};
          border: 1px solid ${materialTheme.colors.outline};
          &:hover {
            background: ${color}08;
            border-color: ${color};
          }
          &:active {
            background: ${color}14;
          }
        `;
      case 'text':
        return css`
          background: transparent;
          color: ${color};
          &:hover {
            background: ${color}08;
          }
          &:active {
            background: ${color}14;
          }
        `;
      case 'elevated':
        return css`
          background: ${materialTheme.colors.surfaceVariant};
          color: ${color};
          box-shadow: ${materialTheme.elevation[1]};
          &:hover {
            box-shadow: ${materialTheme.elevation[2]};
            background: ${materialTheme.colors.surface};
          }
          &:active {
            box-shadow: ${materialTheme.elevation[1]};
          }
        `;
      case 'tonal':
        return css`
          background: ${color}14;
          color: ${colorDark};
          &:hover {
            background: ${color}1f;
            box-shadow: ${materialTheme.elevation[1]};
          }
          &:active {
            background: ${color}29;
          }
        `;
      default: // filled
        return css`
          background: ${color};
          color: white;
          box-shadow: ${materialTheme.elevation[2]};
          &:hover {
            background: ${colorDark};
            box-shadow: ${materialTheme.elevation[4]};
          }
          &:active {
            box-shadow: ${materialTheme.elevation[8]};
          }
        `;
    }
  }}
  
  &:disabled {
    opacity: 0.38;
    cursor: not-allowed;
    box-shadow: none;
  }
  
  // Ripple effect container
  &::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.5);
    opacity: 0;
    transform: translate(-50%, -50%) scale(0);
  }
  
  &:active::after {
    animation: ${rippleAnimation} 0.6s ease-out;
  }
`;

export const MaterialButton: React.FC<{
  children: ReactNode;
  variant?: 'filled' | 'outlined' | 'text' | 'elevated' | 'tonal';
  color?: 'primary' | 'secondary' | 'error' | 'success' | 'warning';
  size?: 'small' | 'medium' | 'large';
  fullWidth?: boolean;
  onClick?: () => void;
  disabled?: boolean;
  type?: 'button' | 'submit' | 'reset';
  startIcon?: ReactNode;
  endIcon?: ReactNode;
}> = ({ children, startIcon, endIcon, ...props }) => {
  return (
    <ButtonBase {...props}>
      {startIcon}
      {children}
      {endIcon}
    </ButtonBase>
  );
};

// Material FAB (Floating Action Button)
export const MaterialFAB = styled.button<{ 
  size?: 'small' | 'medium' | 'large';
  extended?: boolean;
  color?: 'primary' | 'secondary';
}>`
  position: fixed;
  bottom: ${materialTheme.spacing.lg};
  right: ${materialTheme.spacing.lg};
  border: none;
  cursor: pointer;
  background: ${props => materialTheme.colors[props.color || 'primary']};
  color: white;
  box-shadow: ${materialTheme.elevation[6]};
  transition: all ${materialTheme.transitions.standard};
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: ${materialTheme.typography.fontFamily};
  font-weight: 500;
  
  ${props => {
    switch(props.size) {
      case 'small':
        return css`
          width: ${props.extended ? 'auto' : '40px'};
          height: 40px;
          border-radius: ${props.extended ? '20px' : '50%'};
          padding: ${props.extended ? '0 16px' : '0'};
          font-size: 14px;
        `;
      case 'large':
        return css`
          width: ${props.extended ? 'auto' : '96px'};
          height: 96px;
          border-radius: ${props.extended ? '48px' : '50%'};
          padding: ${props.extended ? '0 32px' : '0'};
          font-size: 18px;
        `;
      default: // medium
        return css`
          width: ${props.extended ? 'auto' : '56px'};
          height: 56px;
          border-radius: ${props.extended ? '28px' : '50%'};
          padding: ${props.extended ? '0 20px' : '0'};
          font-size: 16px;
        `;
    }
  }}
  
  &:hover {
    box-shadow: ${materialTheme.elevation[8]};
    transform: scale(1.05);
  }
  
  &:active {
    box-shadow: ${materialTheme.elevation[12]};
    transform: scale(0.98);
  }
`;

// Material Chip Component
export const MaterialChip = styled.div<{ 
  selected?: boolean;
  clickable?: boolean;
  deletable?: boolean;
  color?: 'primary' | 'secondary' | 'success' | 'error' | 'warning';
}>`
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  border-radius: ${materialTheme.borderRadius.sm};
  font-size: 14px;
  font-family: ${materialTheme.typography.fontFamily};
  transition: all ${materialTheme.transitions.fast};
  border: 1px solid ${materialTheme.colors.outline};
  background: ${props => props.selected 
    ? materialTheme.colors[props.color || 'primary'] 
    : materialTheme.colors.surface};
  color: ${props => props.selected 
    ? 'white' 
    : materialTheme.colors.onSurface};
  
  ${props => props.clickable && css`
    cursor: pointer;
    &:hover {
      background: ${props.selected 
        ? materialTheme.colors[`${props.color || 'primary'}Dark`]
        : materialTheme.colors.surfaceVariant};
      box-shadow: ${materialTheme.elevation[1]};
    }
    &:active {
      box-shadow: ${materialTheme.elevation[2]};
    }
  `}
`;

// Material TextField Component
export const MaterialTextField = styled.div`
  position: relative;
  margin-top: 16px;
`;

export const MaterialInput = styled.input<{ error?: boolean }>`
  width: 100%;
  padding: 16px 14px;
  font-size: 16px;
  font-family: ${materialTheme.typography.fontFamily};
  border: 1px solid ${props => props.error 
    ? materialTheme.colors.error 
    : materialTheme.colors.outline};
  border-radius: ${materialTheme.borderRadius.xs};
  background: ${materialTheme.colors.surface};
  color: ${materialTheme.colors.onSurface};
  transition: all ${materialTheme.transitions.fast};
  
  &:hover {
    border-color: ${props => props.error 
      ? materialTheme.colors.error 
      : materialTheme.colors.onSurface};
  }
  
  &:focus {
    outline: none;
    border-width: 2px;
    border-color: ${props => props.error 
      ? materialTheme.colors.error 
      : materialTheme.colors.primary};
    padding: 15px 13px;
  }
  
  &:disabled {
    background: ${materialTheme.colors.surfaceVariant};
    color: ${materialTheme.colors.onSurfaceVariant};
    cursor: not-allowed;
  }
`;

export const MaterialLabel = styled.label<{ focused?: boolean; hasValue?: boolean; error?: boolean }>`
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 16px;
  font-family: ${materialTheme.typography.fontFamily};
  color: ${props => props.error 
    ? materialTheme.colors.error 
    : materialTheme.colors.onSurfaceVariant};
  background: ${materialTheme.colors.surface};
  padding: 0 4px;
  pointer-events: none;
  transition: all ${materialTheme.transitions.fast};
  
  ${props => (props.focused || props.hasValue) && css`
    top: 0;
    font-size: 12px;
    color: ${props.error 
      ? materialTheme.colors.error 
      : materialTheme.colors.primary};
  `}
`;

// Material AppBar Component
export const MaterialAppBar = styled.header<{ elevation?: number }>`
  background: ${materialTheme.colors.surface};
  color: ${materialTheme.colors.onSurface};
  padding: 0 ${materialTheme.spacing.lg};
  height: 64px;
  display: flex;
  align-items: center;
  box-shadow: ${props => materialTheme.elevation[props.elevation || 2]};
  position: sticky;
  top: 0;
  z-index: ${materialTheme.zIndex.drawer};
`;

// Material Container
export const MaterialContainer = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: ${materialTheme.spacing.lg};
`;

// Material Grid
export const MaterialGrid = styled.div<{ cols?: number; gap?: string }>`
  display: grid;
  grid-template-columns: repeat(${props => props.cols || 12}, 1fr);
  gap: ${props => props.gap || materialTheme.spacing.md};
`;

// Material Divider
export const MaterialDivider = styled.hr`
  border: none;
  height: 1px;
  background: ${materialTheme.colors.outlineVariant};
  margin: ${materialTheme.spacing.md} 0;
`;

// Material Tab Component
export const MaterialTabs = styled.div`
  display: flex;
  border-bottom: 1px solid ${materialTheme.colors.outlineVariant};
  position: relative;
`;

export const MaterialTab = styled.button<{ active?: boolean }>`
  padding: ${materialTheme.spacing.md} ${materialTheme.spacing.lg};
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: ${materialTheme.typography.fontFamily};
  font-size: 14px;
  font-weight: 500;
  color: ${props => props.active 
    ? materialTheme.colors.primary 
    : materialTheme.colors.onSurfaceVariant};
  position: relative;
  transition: all ${materialTheme.transitions.fast};
  text-transform: uppercase;
  letter-spacing: 0.5px;
  
  &:hover {
    background: ${materialTheme.colors.primary}08;
  }
  
  ${props => props.active && css`
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: ${materialTheme.colors.primary};
    }
  `}
`;

// Material Progress Component
export const MaterialProgress = styled.div<{ value?: number; indeterminate?: boolean }>`
  width: 100%;
  height: 4px;
  background: ${materialTheme.colors.surfaceVariant};
  border-radius: 2px;
  overflow: hidden;
  position: relative;
  
  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background: ${materialTheme.colors.primary};
    border-radius: 2px;
    ${props => props.indeterminate 
      ? css`
          width: 30%;
          animation: indeterminate 1.5s linear infinite;
        `
      : css`
          width: ${props.value || 0}%;
          transition: width ${materialTheme.transitions.standard};
        `
    }
  }
  
  @keyframes indeterminate {
    0% {
      left: -30%;
    }
    100% {
      left: 100%;
    }
  }
`;