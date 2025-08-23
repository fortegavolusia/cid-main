# CIDS Project Documentation

## Project Overview
CIDS (Centralized Identity Discovery Service) is a comprehensive authentication and authorization service with row-level security (RLS) capabilities.

## Architecture
- **Backend Auth Service**: Handles authentication and JWT token management
  - Token template management system
  - Azure AD group integration
  - Automatic template application based on user groups
- **React Frontend**: Permission management interface  
  - Token Administration with Builder and Templates
  - Real-time Azure AD group search
- **FastAPI Test Apps**: Example applications demonstrating integration

## Development Environment

### Starting Services
```bash
# Start backend auth service with DEV CORS
DEV_CROSS_ORIGIN=true bash restart_server.sh

# Start React frontend
cd cids-frontend
npm run dev

# Start FastAPI test app
python3 azure-auth-app/test_apps/fastapi_app/fastapi_test_app.py
```

## Key Components

### PermissionSelector (React)
- Manages permissions at resource, action, and field levels
- Supports Allow/Deny permissions for endpoints
- Implements multiple SQL filters per resource/action/field for RLS
- Unified persistence via localStorage (per app + role)
- Save button to persist all permission settings
- Field name extraction from API 'path' property

### RuleBuilder (React)
- Power BI style SQL WHERE clause editor
- Template library for common filter patterns
- Support for context variables (@current_user_email, etc.)
- Edit existing filters or add new ones

### RolesModal (React)
- Display permission and resource scope counts
- Export individual role configurations
- Export all roles for an application
- Database-ready JSON export format

### Token Administration (React)
- **Token Builder**: Visual JWT token structure editor
  - Drag-and-drop claim management
  - Standard and custom JWT claims
  - Real-time JSON structure preview
  - Save/load token templates
- **Token Templates**: Manage saved token structures
  - Azure AD group associations with live autocomplete search
  - Default template support (applied to all authenticated users)
  - Template priority for conflict resolution
  - Enable/disable templates
  - Import/export templates as JSON
- **Backend Integration**: Automatic template application
  - Default template applies to all authenticated users
  - AD group templates override default based on priority
  - Matches templates to user's AD groups
  - Applies highest priority matching template
  - Filters token claims based on template

## Permission & RLS System

### Unified Storage Structure
- **Permissions**: Endpoint allow/deny states (e.g., `products.read`)
- **Resource Scopes**: SQL WHERE clauses for RLS filtering
- Storage keys: 
  - `cids_unified_role_{clientId}_{roleName}` - Complete role config
  - `cids_filters_{clientId}_{roleName}` - RLS filters only

### Filter Management Features
- **Multiple filters per field**: Unlimited SQL WHERE clauses
- **CRUD operations**: Add, view, edit, delete individual filters  
- **Filter count badges**: Visual indicators showing total filters
- **Persistence**: Both permissions and filters saved together

### Export Format
```json
{
  "app_id": "client_123",
  "role_name": "Admin",
  "permissions": [
    {
      "endpoint": "products.read",
      "resource": "products",
      "action": "read",
      "allowed": true
    }
  ],
  "rls_filters": [
    {
      "filter_type": "field",
      "filter_path": "products.read.created_by",
      "expression": "created_by = @current_user_id",
      "created_at": "2024-01-01T..."
    }
  ]
}
```

## Testing & Validation

### Linting and Type Checking
```bash
# Run if available (check package.json for exact commands)
npm run lint
npm run typecheck
```

## Common Issues & Solutions

### React Key Warnings
- Fixed by using index fallback when field_name is undefined
- Key format: `${resource}-${action}-${field.field_name || field-${index}}`

### Filter Storage Migration
- Automatic migration from single-filter to multi-filter format
- Handles corrupted data gracefully with try/catch
- Migration for old field-N format to actual field names
- Field names extracted from API 'path' property

## Git Workflow
- Feature branch: `feature/resource-permissions`
- Commit messages follow conventional format
- Co-authored commits with Claude

## Dependencies
- React 18+ with TypeScript
- Vite for build tooling
- CSS modules for styling
- localStorage for persistence

## API Endpoints

### Token Template Management
- `GET /auth/admin/token-templates` - List all templates
- `GET /auth/admin/token-templates/{name}` - Get specific template
- `POST /auth/admin/token-templates` - Create/update template
- `DELETE /auth/admin/token-templates/{name}` - Delete template
- `POST /auth/admin/token-templates/import` - Bulk import templates

### Azure AD Integration
- `GET /auth/admin/azure-groups?search={query}` - Search Azure AD groups

## Security Considerations
- RLS filters apply SQL WHERE clauses at data access layer
- Context variables prevent SQL injection
- Filters scoped to app + role combination
- No secrets or keys in frontend code
- Token templates applied based on Azure AD group membership
- Template priority system for handling multiple group matches
- Default template ensures baseline token structure for all users
- Only one template can be marked as default at a time