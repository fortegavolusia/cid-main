# 🎨 CID Design System Documentation

> **Version**: 1.0.0
> **Framework**: React + TypeScript + Styled Components
> **Design Language**: Material Design 3
> **Last Updated**: September 2025

---

## 📋 Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Color System](#color-system)
3. [Typography](#typography)
4. [Spacing & Layout](#spacing--layout)
5. [Components Library](#components-library)
6. [Icons & Imagery](#icons--imagery)
7. [Animations & Transitions](#animations--transitions)
8. [Best Practices](#best-practices)

---

## 🎯 Design Philosophy

CID follows **Material Design 3** principles with a government-appropriate aesthetic:
- **Clean & Professional**: Suitable for government/enterprise use
- **Accessible**: WCAG 2.1 AA compliant
- **Consistent**: Unified experience across all modules
- **Modern**: Contemporary UI without being trendy
- **Responsive**: Works on all device sizes

---

## 🎨 Color System

### Primary Palette
```javascript
primary: '#1976d2'        // Blue - Main brand color
primaryLight: '#42a5f5'    // Hover states
primaryDark: '#1565c0'     // Active states
onPrimary: '#ffffff'       // Text on primary
```

### Secondary Palette
```javascript
secondary: '#9c27b0'       // Purple - Accent actions
secondaryLight: '#ba68c8'  // Hover states
secondaryDark: '#7b1fa2'   // Active states
onSecondary: '#ffffff'     // Text on secondary
```

### Semantic Colors
```javascript
// Success States
success: '#4caf50'         // Green - Success messages
successLight: '#81c784'
successDark: '#388e3c'

// Error States
error: '#ba1a1a'           // Red - Error messages
errorContainer: '#ffdad6'  // Error backgrounds
onError: '#ffffff'
onErrorContainer: '#410002'

// Warning States
warning: '#ff9800'         // Orange - Warnings
warningLight: '#ffb74d'
warningDark: '#f57c00'

// Info States
info: '#2196f3'           // Blue - Information
infoLight: '#64b5f6'
infoDark: '#1976d2'
```

### Surface Colors
```javascript
surface: '#ffffff'         // Cards, modals
surfaceVariant: '#f5f5f5'  // Alternate surfaces
background: '#fafafa'      // Page background
```

### Usage Examples

```jsx
// Primary button
<MaterialButton variant="filled" color="primary">
  Save Changes
</MaterialButton>

// Error state card
<MaterialCard style={{ borderLeft: '4px solid #ba1a1a' }}>
  <ErrorMessage>Invalid credentials</ErrorMessage>
</MaterialCard>

// Success notification
<Alert color="success">
  ✓ Application registered successfully
</Alert>
```

---

## 📝 Typography

### Font Stack
```css
font-family: 'Roboto', 'Helvetica', 'Arial', sans-serif;
```

### Type Scale

#### Display (Large Headers)
```javascript
displayLarge: {
  fontSize: '57px',
  lineHeight: '64px',
  fontWeight: 400,
}

displayMedium: {
  fontSize: '45px',
  lineHeight: '52px',
  fontWeight: 400,
}

displaySmall: {
  fontSize: '36px',
  lineHeight: '44px',
  fontWeight: 400,
}
```

#### Headlines (Section Headers)
```javascript
headlineLarge: {
  fontSize: '32px',
  lineHeight: '40px',
  fontWeight: 400,
}

headlineMedium: {
  fontSize: '28px',
  lineHeight: '36px',
  fontWeight: 400,
}

headlineSmall: {
  fontSize: '24px',
  lineHeight: '32px',
  fontWeight: 400,
}
```

#### Body Text
```javascript
bodyLarge: {
  fontSize: '16px',
  lineHeight: '24px',
  fontWeight: 400,
}

bodyMedium: {
  fontSize: '14px',
  lineHeight: '20px',
  fontWeight: 400,
}

bodySmall: {
  fontSize: '12px',
  lineHeight: '16px',
  fontWeight: 400,
}
```

### Usage Examples
```jsx
// Page title
<PageTitle>Application Management</PageTitle>
// Renders: 32px, weight 600

// Section header
<SectionHeader>Registered Applications</SectionHeader>
// Renders: 24px, weight 500

// Body text
<BodyText>Configure your application settings below.</BodyText>
// Renders: 14px, weight 400
```

---

## 📐 Spacing & Layout

### Spacing Scale
```javascript
spacing: {
  xs: '4px',   // Tight spacing
  sm: '8px',   // Compact elements
  md: '16px',  // Default spacing
  lg: '24px',  // Section spacing
  xl: '32px',  // Large gaps
  xxl: '48px', // Page sections
}
```

### Layout Grid
```css
/* Desktop: 12 columns */
max-width: 1440px;
padding: 0 24px;
gap: 24px;

/* Tablet: 8 columns */
max-width: 960px;
padding: 0 16px;
gap: 16px;

/* Mobile: 4 columns */
max-width: 100%;
padding: 0 16px;
gap: 8px;
```

### Border Radius
```javascript
borderRadius: {
  none: '0px',      // Sharp corners
  xs: '4px',        // Subtle rounding
  sm: '8px',        // Small components
  md: '12px',       // Cards, modals
  lg: '16px',       // Large cards
  xl: '28px',       // Pills, badges
  full: '1000px',   // Circular
}
```

---

## 🧩 Components Library

### 1. Buttons

#### Material Button
```jsx
<MaterialButton
  variant="filled|outlined|text|elevated|tonal"
  color="primary|secondary|error|success|warning"
  size="small|medium|large"
  fullWidth={false}
  startIcon={<Icon />}
  endIcon={<Icon />}
>
  Button Text
</MaterialButton>
```

#### Button Variants
- **Filled**: Primary actions, high emphasis
- **Outlined**: Secondary actions, medium emphasis
- **Text**: Tertiary actions, low emphasis
- **Elevated**: Floating actions with shadow
- **Tonal**: Colored background with darker text

#### Real Examples
```jsx
// Primary CTA
<MaterialButton variant="filled" color="primary">
  Register Application
</MaterialButton>

// Secondary action
<MaterialButton variant="outlined" color="primary">
  View Details
</MaterialButton>

// Danger action
<MaterialButton variant="filled" color="error">
  Delete Application
</MaterialButton>

// Subtle action
<MaterialButton variant="text" color="primary">
  Learn More
</MaterialButton>
```

### 2. Cards

#### Material Card
```jsx
<MaterialCard elevation={1-24} clickable={true}>
  <CardHeader>
    <CardTitle>Application Name</CardTitle>
    <CardStatus active={true} />
  </CardHeader>
  <CardBody>
    Content here...
  </CardBody>
  <CardActions>
    <MaterialButton>Action</MaterialButton>
  </CardActions>
</MaterialCard>
```

#### Elevation Levels
- `0`: No shadow (flat)
- `1`: Default card
- `2`: Raised card
- `4`: Hover state
- `8`: Active/pressed
- `16`: Sticky elements
- `24`: Modals, dialogs

### 3. Inputs

#### Text Input
```jsx
<MaterialInput
  type="text"
  placeholder="Enter application name"
  error={hasError}
  value={value}
  onChange={handleChange}
/>
```

#### Styled Input Properties
```css
/* Default state */
background: #f5f5f5;
border: 2px solid transparent;
border-radius: 12px;
padding: 12px 16px;
font-size: 14px;

/* Focus state */
background: white;
border-color: #1976d2;
box-shadow: 0 0 0 4px rgba(25, 118, 210, 0.12);

/* Error state */
border-color: #ba1a1a;
background: #fff5f5;
```

### 4. Modals

#### Modal Structure
```jsx
<Modal isOpen={isOpen} onClose={handleClose}>
  <ModalHeader>
    <ModalTitle>Modal Title</ModalTitle>
    <CloseButton onClick={handleClose}>×</CloseButton>
  </ModalHeader>

  <ModalBody>
    Content here...
  </ModalBody>

  <ModalFooter>
    <MaterialButton variant="text">Cancel</MaterialButton>
    <MaterialButton variant="filled">Confirm</MaterialButton>
  </ModalFooter>
</Modal>
```

### 5. Tables

#### Data Table
```jsx
<DataTable>
  <TableHeader>
    <TableRow>
      <TableHead>Name</TableHead>
      <TableHead>Status</TableHead>
      <TableHead>Actions</TableHead>
    </TableRow>
  </TableHeader>

  <TableBody>
    <TableRow>
      <TableCell>HR System</TableCell>
      <TableCell><StatusBadge active /></TableCell>
      <TableCell>
        <MaterialButton size="small">Edit</MaterialButton>
      </TableCell>
    </TableRow>
  </TableBody>
</DataTable>
```

### 6. Navigation

#### Sidebar
```jsx
<Sidebar collapsed={isCollapsed}>
  <SidebarHeader>
    <Logo />
    <Title>CIDS</Title>
  </SidebarHeader>

  <NavSection>
    <NavItem active={isActive} to="/dashboard">
      <NavIcon>📊</NavIcon>
      <NavLabel>Dashboard</NavLabel>
    </NavItem>
  </NavSection>

  <SidebarFooter>
    <UserInfo />
    <LogoutButton />
  </SidebarFooter>
</Sidebar>
```

#### Sidebar Styling
```css
/* Expanded state */
width: 280px;
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Collapsed state */
width: 80px;
/* Icons only, labels hidden */
```

### 7. Alerts & Notifications

#### Alert Component
```jsx
<Alert
  severity="success|error|warning|info"
  dismissible={true}
>
  <AlertIcon />
  <AlertMessage>Your changes have been saved</AlertMessage>
  <AlertAction>
    <MaterialButton size="small">Undo</MaterialButton>
  </AlertAction>
</Alert>
```

### 8. Badges & Chips

#### Status Badge
```jsx
<StatusBadge variant="success|error|warning|info">
  Active
</StatusBadge>
```

#### Chip Component
```jsx
<Chip
  label="Admin"
  color="primary"
  deletable={true}
  onDelete={handleDelete}
/>
```

---

## 🎭 Icons & Imagery

### Icon System
Currently using emoji for simplicity, but ready for icon library integration:

```javascript
// Navigation Icons
'🏠' Home
'📊' Dashboard
'⚙️' Settings
'🔐' Security
'👥' Users
'📱' Applications
'🔑' API Keys
'📝' Logs
'🚪' Logout

// Action Icons
'➕' Add/Create
'✏️' Edit
'🗑️' Delete
'👁️' View
'📋' Copy
'🔄' Refresh
'⬇️' Download
'⬆️' Upload

// Status Icons
'✅' Success/Active
'❌' Error/Inactive
'⚠️' Warning
'ℹ️' Information
'🔄' Processing
'⏱️' Pending
```

### Future Icon Library
Ready to integrate:
- Material Icons
- Font Awesome
- Feather Icons
- Custom SVG icons

---

## 🎬 Animations & Transitions

### Transition Timing
```javascript
transitions: {
  fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
  standard: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
  slow: '450ms cubic-bezier(0.4, 0, 0.2, 1)',
}
```

### Common Animations

#### Ripple Effect (Buttons)
```css
@keyframes ripple {
  0% {
    transform: scale(0);
    opacity: 1;
  }
  100% {
    transform: scale(4);
    opacity: 0;
  }
}
```

#### Fade In
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
animation: fadeIn 300ms ease-in;
```

#### Slide In
```css
@keyframes slideIn {
  from {
    transform: translateX(-100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
```

---

## 📏 Best Practices

### 1. Consistency
- Use design tokens from `materialTheme`
- Don't hardcode colors or spacing
- Follow the established patterns

### 2. Accessibility
- Minimum touch target: 44x44px
- Color contrast: 4.5:1 for normal text
- Focus indicators on all interactive elements
- ARIA labels for icons and buttons

### 3. Responsive Design
```jsx
// Mobile-first approach
const Container = styled.div`
  padding: 16px;

  @media (min-width: 768px) {
    padding: 24px;
  }

  @media (min-width: 1024px) {
    padding: 32px;
    max-width: 1440px;
    margin: 0 auto;
  }
`;
```

### 4. Performance
- Lazy load heavy components
- Use React.memo for expensive renders
- Implement virtual scrolling for long lists
- Optimize images and assets

### 5. Code Organization
```
components/
├── common/           # Reusable components
│   ├── Button.tsx
│   ├── Card.tsx
│   └── Modal.tsx
├── layout/          # Layout components
│   ├── Sidebar.tsx
│   └── Header.tsx
└── features/        # Feature-specific
    ├── RolesModal.tsx
    └── TokenBuilder.tsx
```

---

## 🎯 Component Usage Quick Reference

### Page Structure
```jsx
<PageContainer>
  <PageHeader>
    <PageTitle>Page Title</PageTitle>
    <PageSubtitle>Description text</PageSubtitle>
  </PageHeader>

  <ControlBar>
    <SearchInput placeholder="Search..." />
    <MaterialButton>Add New</MaterialButton>
  </ControlBar>

  <ContentGrid>
    <MaterialCard>
      {/* Content */}
    </MaterialCard>
  </ContentGrid>
</PageContainer>
```

### Form Layout
```jsx
<Form>
  <FormGroup>
    <Label>Field Label</Label>
    <MaterialInput
      type="text"
      placeholder="Enter value"
      error={errors.field}
    />
    <HelperText error={errors.field}>
      {errors.field || 'Helper text'}
    </HelperText>
  </FormGroup>

  <FormActions>
    <MaterialButton variant="text">Cancel</MaterialButton>
    <MaterialButton variant="filled" type="submit">
      Submit
    </MaterialButton>
  </FormActions>
</Form>
```

### Card with Actions
```jsx
<MaterialCard elevation={2}>
  <CardHeader>
    <CardTitle>Application Name</CardTitle>
    <StatusBadge active={true}>Active</StatusBadge>
  </CardHeader>

  <CardBody>
    <InfoRow>
      <Label>Client ID:</Label>
      <Value>app_xxxxx</Value>
      <CopyButton onClick={handleCopy}>📋</CopyButton>
    </InfoRow>
  </CardBody>

  <CardActions>
    <MaterialButton variant="text">View</MaterialButton>
    <MaterialButton variant="outlined">Edit</MaterialButton>
    <MaterialButton variant="text" color="error">
      Delete
    </MaterialButton>
  </CardActions>
</MaterialCard>
```

---

## 🚀 Implementation Examples

### Creating a New Feature Page
```jsx
import React from 'react';
import styled from 'styled-components';
import { materialTheme } from '../styles/materialTheme';
import { MaterialButton, MaterialCard } from '../components/MaterialComponents';

const PageContainer = styled.div`
  padding: ${materialTheme.spacing.lg};
  max-width: 1440px;
  margin: 0 auto;
`;

const PageHeader = styled.div`
  margin-bottom: ${materialTheme.spacing.xl};
`;

const PageTitle = styled.h1`
  ${materialTheme.typography.headlineLarge};
  color: ${materialTheme.colors.onBackground};
  margin: 0 0 ${materialTheme.spacing.sm} 0;
`;

export const MyFeaturePage: React.FC = () => {
  return (
    <PageContainer>
      <PageHeader>
        <PageTitle>My Feature</PageTitle>
      </PageHeader>

      <MaterialCard elevation={1}>
        <p>Feature content here</p>
        <MaterialButton variant="filled" color="primary">
          Take Action
        </MaterialButton>
      </MaterialCard>
    </PageContainer>
  );
};
```

### Custom Styled Component
```jsx
import styled from 'styled-components';
import { materialTheme } from '../styles/materialTheme';

export const CustomAlert = styled.div<{ severity: 'error' | 'success' }>`
  padding: ${materialTheme.spacing.md};
  border-radius: ${materialTheme.borderRadius.md};
  margin-bottom: ${materialTheme.spacing.md};
  display: flex;
  align-items: center;
  gap: ${materialTheme.spacing.sm};

  background: ${props => props.severity === 'error'
    ? materialTheme.colors.errorContainer
    : materialTheme.colors.success + '14'};

  color: ${props => props.severity === 'error'
    ? materialTheme.colors.onErrorContainer
    : materialTheme.colors.successDark};

  border-left: 4px solid ${props => props.severity === 'error'
    ? materialTheme.colors.error
    : materialTheme.colors.success};
`;
```

---

## 📚 Resources

- [Material Design 3 Guidelines](https://m3.material.io/)
- [React Styled Components](https://styled-components.com/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Government Design System](https://designsystem.digital.gov/)

---

## 🔄 Version History

- **v1.0.0** (Sept 2025): Initial design system documentation
- Components based on Material Design 3
- Government-appropriate styling
- Full accessibility compliance

---

**Last Updated**: September 16, 2025
**Maintained By**: CIDS Development Team
**Contact**: dev@volusia.gov