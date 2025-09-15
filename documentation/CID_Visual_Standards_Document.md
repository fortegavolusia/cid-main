# CID Visual Standards Document

## Executive Summary
The Centralized Identity Discovery Service (CID) interface employs a modern, professional design system that emphasizes clarity, accessibility, and user efficiency. The visual styling reflects enterprise-grade security software while maintaining approachable usability for administrators.

## Brand Identity

### Primary Purpose
CID serves as the central authentication and authorization hub for County Services, managing permissions, roles, and access control across all integrated applications.

### Design Philosophy
- **Security-First Visual Language**: Dark, professional aesthetic that conveys trust and security
- **Information Hierarchy**: Clear visual separation between different security levels and data types
- **Responsive & Accessible**: WCAG 2.1 AA compliant with full keyboard navigation support

## Color Palette

### Primary Colors
- **Primary Blue**: `#3B82F6` - Used for primary actions, links, and interactive elements
- **Primary Hover**: `#2563EB` - Hover state for primary buttons
- **Primary Dark**: `#1E40AF` - Active/pressed states

### Background Colors
- **Main Background**: `#0F172A` - Dark navy providing high contrast
- **Card Background**: `#1E293B` - Elevated surface color
- **Elevated Surface**: `#334155` - Modal backgrounds and overlays

### Semantic Colors
- **Success Green**: `#10B981` - Successful operations, active states
- **Warning Amber**: `#F59E0B` - Warnings, pending operations
- **Error Red**: `#EF4444` - Errors, destructive actions
- **Info Blue**: `#06B6D4` - Informational messages

### Text Colors
- **Primary Text**: `#F1F5F9` - Main content text
- **Secondary Text**: `#94A3B8` - Supporting text, descriptions
- **Muted Text**: `#64748B` - Disabled states, timestamps
- **Inverse Text**: `#0F172A` - Text on light backgrounds

## Typography

### Font Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
```

### Type Scale
- **Display**: 2.5rem (40px) - Page titles
- **Heading 1**: 2rem (32px) - Main section headers
- **Heading 2**: 1.5rem (24px) - Subsection headers
- **Heading 3**: 1.25rem (20px) - Card titles
- **Body**: 1rem (16px) - Standard text
- **Small**: 0.875rem (14px) - Supporting text
- **Caption**: 0.75rem (12px) - Labels, timestamps

### Font Weights
- **Bold**: 700 - Headers, emphasis
- **Semibold**: 600 - Subheaders, buttons
- **Regular**: 400 - Body text
- **Light**: 300 - Large display text (optional)

## Component Design Standards

### Buttons

#### Primary Button
```css
background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
color: white;
padding: 10px 20px;
border-radius: 8px;
font-weight: 600;
box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
transition: all 0.2s ease;
```

#### Secondary Button
```css
background: transparent;
color: #3B82F6;
border: 2px solid #3B82F6;
padding: 8px 18px;
border-radius: 8px;
font-weight: 600;
```

#### Danger Button
```css
background: #EF4444;
color: white;
padding: 10px 20px;
border-radius: 8px;
font-weight: 600;
```

### Cards
```css
background: #1E293B;
border: 1px solid #334155;
border-radius: 12px;
padding: 24px;
box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
```

### Form Controls

#### Input Fields
```css
background: #0F172A;
border: 1px solid #334155;
border-radius: 6px;
padding: 10px 12px;
color: #F1F5F9;
font-size: 14px;
transition: border-color 0.2s;

/* Focus state */
border-color: #3B82F6;
box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
```

#### Select Dropdowns
```css
background: #0F172A;
border: 1px solid #334155;
border-radius: 6px;
padding: 10px 36px 10px 12px;
color: #F1F5F9;
appearance: none;
background-image: url('chevron-down.svg');
background-position: right 12px center;
background-repeat: no-repeat;
```

#### Checkboxes & Radio Buttons
```css
width: 20px;
height: 20px;
border: 2px solid #334155;
border-radius: 4px; /* 50% for radio */
background: #0F172A;

/* Checked state */
background: #3B82F6;
border-color: #3B82F6;
```

### Tables
```css
/* Table container */
background: #1E293B;
border-radius: 8px;
overflow: hidden;

/* Table header */
background: #334155;
color: #94A3B8;
font-weight: 600;
text-transform: uppercase;
font-size: 12px;
padding: 12px;

/* Table rows */
border-bottom: 1px solid #334155;
padding: 16px 12px;

/* Hover state */
background: rgba(59, 130, 246, 0.05);
```

### Modals
```css
/* Overlay */
background: rgba(0, 0, 0, 0.7);
backdrop-filter: blur(4px);

/* Modal content */
background: #1E293B;
border-radius: 16px;
box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
max-width: 600px;
padding: 32px;
```

## Layout Principles

### Grid System
- **12-column grid** for main content areas
- **Responsive breakpoints**:
  - Mobile: < 640px
  - Tablet: 640px - 1024px
  - Desktop: > 1024px

### Spacing Scale
```css
--space-xs: 4px;
--space-sm: 8px;
--space-md: 16px;
--space-lg: 24px;
--space-xl: 32px;
--space-2xl: 48px;
--space-3xl: 64px;
```

### Container Widths
- **Max width**: 1280px
- **Content width**: 1024px
- **Narrow content**: 768px

## Icons & Imagery

### Icon System
- **Library**: Lucide React (formerly Feather Icons)
- **Size scale**: 16px, 20px, 24px, 32px
- **Stroke width**: 2px
- **Color**: Inherits from parent text color

### Icon Usage
- **Navigation**: 20px icons with text labels
- **Buttons**: 16px icons inline with text
- **Status indicators**: 16px colored icons
- **Empty states**: 48px muted icons

## Interactive States

### Hover Effects
- **Buttons**: Darken by 10%, slight scale (1.02)
- **Links**: Underline decoration, lighten color
- **Cards**: Subtle border highlight, elevation change
- **Table rows**: Background color change

### Focus States
- **Keyboard navigation**: 3px blue outline with offset
- **Form controls**: Blue border with soft shadow
- **Buttons**: Visible outline, no color change

### Loading States
- **Skeleton screens**: Animated gradient placeholders
- **Spinners**: 2px stroke, primary blue color
- **Progress bars**: Animated fill with percentage

### Disabled States
- **Opacity**: 0.5
- **Cursor**: not-allowed
- **No hover effects**

## Animation Guidelines

### Timing Functions
```css
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-in: cubic-bezier(0.4, 0, 1, 1);
```

### Duration Scale
```css
--duration-fast: 150ms;
--duration-normal: 250ms;
--duration-slow: 350ms;
```

### Animation Types
- **Micro-interactions**: 150ms, ease-out
- **Page transitions**: 250ms, ease-in-out
- **Modal/drawer**: 350ms, ease-in-out
- **Skeleton loading**: 1.5s pulse, infinite

## Accessibility Standards

### Color Contrast
- **Normal text**: Minimum 4.5:1 contrast ratio
- **Large text**: Minimum 3:1 contrast ratio
- **Interactive elements**: Minimum 3:1 against background

### Keyboard Navigation
- **Tab order**: Logical flow through interface
- **Focus indicators**: Always visible
- **Skip links**: Available for main navigation
- **Escape key**: Closes modals and dropdowns

### Screen Reader Support
- **ARIA labels**: All interactive elements
- **Role attributes**: Proper semantic HTML
- **Live regions**: For dynamic content updates
- **Heading hierarchy**: Logical h1-h6 structure

## Responsive Design

### Mobile Adaptations
- **Touch targets**: Minimum 44x44px
- **Font size**: Minimum 16px to prevent zoom
- **Stacked layouts**: Single column on small screens
- **Collapsible navigation**: Hamburger menu pattern

### Tablet Optimizations
- **Two-column layouts**: Where appropriate
- **Larger touch targets**: 48px minimum
- **Optimized tables**: Horizontal scroll or card view

### Desktop Enhancements
- **Multi-column layouts**: Utilize full width
- **Hover states**: Enhanced interactions
- **Keyboard shortcuts**: Power user features
- **Dense information display**: More data visible

## Dark Mode Specifications

The CID interface is primarily designed as a dark-themed application for reduced eye strain during extended administrative sessions.

### Benefits
- **Reduced eye fatigue** for security administrators
- **Better focus** on critical security data
- **Professional appearance** suitable for enterprise environments
- **Energy efficiency** on OLED displays

## Component Library

### Available Components
1. **Navigation**: AppBar, Sidebar, Breadcrumbs
2. **Data Display**: Tables, Cards, Lists, Trees
3. **Forms**: Input, Select, Checkbox, Radio, Switch
4. **Feedback**: Alerts, Toasts, Progress, Skeleton
5. **Overlays**: Modal, Drawer, Popover, Tooltip
6. **Actions**: Button, IconButton, FAB, Menu

### Component Composition
Components follow a consistent structure:
```jsx
<Component
  variant="primary|secondary|danger"
  size="small|medium|large"
  disabled={boolean}
  loading={boolean}
  className="custom-class"
>
  Content
</Component>
```

## Implementation Technologies

### Frontend Stack
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite for fast development
- **Styling**: Tailwind CSS with custom configuration
- **State Management**: React Context + Hooks
- **HTTP Client**: Axios with interceptors
- **Icons**: Lucide React
- **Date Handling**: date-fns
- **Form Validation**: Native HTML5 + custom validators

### CSS Architecture
- **Utility-First**: Tailwind CSS classes
- **Component Classes**: BEM methodology for custom components
- **CSS Variables**: For theming and dynamic values
- **PostCSS**: For optimizations and autoprefixing

## Usage Examples

### Creating a New Page
```jsx
import { PageHeader, Card, Button } from '@/components';

function NewFeaturePage() {
  return (
    <div className="container mx-auto p-6">
      <PageHeader
        title="Feature Name"
        description="Brief description of the feature"
        actions={
          <Button variant="primary" size="medium">
            Primary Action
          </Button>
        }
      />
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <Card title="Section One">
          {/* Content */}
        </Card>
        <Card title="Section Two">
          {/* Content */}
        </Card>
      </div>
    </div>
  );
}
```

### Styling a Custom Component
```css
.custom-component {
  /* Use CSS variables for consistency */
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  
  /* Follow spacing scale */
  margin-bottom: var(--space-xl);
  
  /* Consistent transitions */
  transition: all var(--duration-normal) var(--ease-in-out);
}

.custom-component:hover {
  /* Subtle hover effect */
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}
```

## Quality Checklist

Before implementing new UI features, ensure:

- [ ] Colors match the defined palette
- [ ] Typography follows the type scale
- [ ] Spacing uses the defined scale
- [ ] Interactive states are implemented
- [ ] Keyboard navigation works
- [ ] ARIA labels are present
- [ ] Component is responsive
- [ ] Loading states are handled
- [ ] Error states are designed
- [ ] Empty states are considered
- [ ] Dark mode is supported
- [ ] Animations follow guidelines

## Maintenance & Evolution

### Version Control
- Document all visual changes in CHANGELOG
- Version the design system (current: v2.0)
- Maintain backwards compatibility

### Review Process
1. Design proposal with mockups
2. Accessibility review
3. Technical implementation review
4. User testing feedback
5. Documentation update

### Future Enhancements
- **Component animations**: More sophisticated transitions
- **Theme customization**: User-selectable themes
- **Advanced visualizations**: D3.js charts for analytics
- **Mobile app**: React Native implementation
- **Design tokens**: Automated design system management

## Conclusion

The CID Visual Standards provide a comprehensive framework for maintaining consistency and quality across the application. These standards ensure that the interface remains professional, accessible, and user-friendly while conveying the security and reliability essential for an enterprise authentication system.

For questions or suggestions regarding these standards, please contact the CID Development Team.

---

*Document Version: 2.0*  
*Last Updated: January 2025*  
*Next Review: April 2025*