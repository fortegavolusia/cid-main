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
cd azure-auth-app
DEV_CROSS_ORIGIN=true bash restart_server.sh

# Start React frontend (HTTPS enabled)
cd cids-frontend
npm run dev
# Access at: https://10.1.5.58:3000

# Start CIDS-compliant test app with UI (optional)
python3 azure-auth-app/test_apps/compliant_app_with_ui.py
```

### Authentication Flow
- **React OAuth Flow**: Direct Azure AD authentication from React (Primary)
  - No dependency on backend session/cookies
  - React initiates OAuth flow directly with Azure AD
  - Callback handled by React at `/auth/callback`
  - Authorization code exchanged for CIDS JWT via `/auth/token/exchange`
  - Fetches AD groups via Microsoft Graph API
  - Resolves app-specific roles based on AD group mappings
  - Access tokens stored in localStorage
  - Refresh tokens stored in localStorage for automatic renewal
  - Admin status validated against env file during token creation
- **Token Refresh & Session Management**:
  - Automatic token refresh 1 minute before expiry
  - Inactivity monitoring with 8-minute warning
  - Session timeout modal with 2-minute countdown
  - "Stay Logged In" option to extend session
  - Refresh tokens maintain AD group to role mappings
- **Legacy HTML/JS Flow**: Commented out, replaced by React flow
  - Previously used `/auth/login` and `/auth/callback` endpoints
  - Server-side OAuth flow with session management

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
- **NEW**: Automatic backend synchronization when saving permissions
- **NEW**: Creates empty role in permission registry when new role added

### AdminPage (React)
- **NEW**: Registered Applications section displays first (always visible)
- **NEW**: App Registration section is collapsible below
- Apps load automatically on page mount
- Manage registered apps, API keys, role mappings
- Trigger endpoint discovery for apps

### Token Administration (React)
- **Token Builder**: Visual JWT token structure editor
  - Drag-and-drop claim management
  - Standard and custom JWT claims
  - Real-time JSON structure preview
  - Save/load token templates
  - Backend synchronization for templates
- **Token Templates**: Manage saved token structures
  - Azure AD group associations with live autocomplete search
  - Default template support (applied to all authenticated users)
  - Template priority for conflict resolution
  - Enable/disable templates
  - Import/export templates as JSON
  - Full backend API integration for persistence
  - Default template badge display and persistence
- **Logs Tab**: Token activity monitoring
  - View active Internal and Azure tokens with proper storage
  - Filter by user, email, or subject
  - Sort by issue date or expiration
  - View full decoded token claims in modal
  - Token details modal with formatted JSON display
  - Copy raw token to clipboard
  - Revoke tokens
- **Backend Integration**: Automatic template application
  - Default template applies to all authenticated users
  - AD group templates always take precedence over default templates
  - Among AD group templates, higher priority wins
  - Matches templates to user's AD groups (by display name)
  - Includes all template-defined claims with proper defaults
  - Initializes empty arrays/objects for collection types
  - Token version 2.0 for templated tokens
  - Template metadata (_template_applied, _template_priority) included
  - App-specific roles resolved from AD group → role mappings
  - Roles aggregated across all registered apps for user

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

### HTTPS Configuration
- React dev server requires HTTPS for Azure AD redirect
- Self-signed certificates generated with OpenSSL
- Vite config updated to use HTTPS with certificates
- Accept browser certificate warning for development

### OAuth State Management
- State parameter stored in localStorage (not sessionStorage)
- Persists across redirects to Azure AD and back
- Prevents CSRF attacks during OAuth flow

### React Key Warnings
- Fixed by using index fallback when field_name is undefined
- Key format: `${resource}-${action}-${field.field_name || field-${index}}`

### Filter Storage Migration
- Automatic migration from single-filter to multi-filter format
- Handles corrupted data gracefully with try/catch
- Migration for old field-N format to actual field names
- Field names extracted from API 'path' property

### Token Template Synchronization
- Templates saved to both localStorage and backend
- Backend is authoritative source on page load
- Fallback to localStorage if backend unavailable
- Automatic sync of localStorage templates to backend on first load
- Default template setting persists to backend properly

### Token Storage in Logs
- Internal and Azure tokens stored during /auth/token/exchange
- Each token gets unique ID for tracking
- Token metadata includes user info, timestamps, and type

### Template Application Issues
- Template manager properly handles frontend claim structure
- Supports type, description, required fields in claims
- Initializes empty arrays/objects for collection types
- Includes default values from template when specified
- AD group templates always override default templates
- Template priority logic: Group templates > Default template

### Role Creation 422 Error
- Backend expects role mappings as Dict[str, Union[str, List[str]]]
- Frontend was sending array of objects, now sends dictionary
- Format: `{"AD Group Name": "Role Name"}` or `{"AD Group": ["Role1", "Role2"]}`

### Discovery Authentication
- Discovery uses JWT tokens created by CIDS (NOT API keys)
- API keys are for YOUR app to call OTHER services
- Discovery endpoints should be publicly accessible or accept JWT tokens
- JWT tokens for discovery are short-lived (5 minutes)
- Required fields: `app_name` (not `service_name`), `last_updated`

### Discovery Format Requirements
- **CRITICAL**: Discovery response `app_id` must match CIDS registration `client_id`
- Discovery v2.0 format required for field-level permissions
- `response_fields` must be Dict[str, FieldMetadata] format
- FieldMetadata supports: type, description, sensitive, pii, phi flags
- Permissions only generated for apps with proper discovery response

### AD Groups and Role Resolution
- `/auth/token/exchange` fetches AD groups from Microsoft Graph
- Groups stored as objects with `id` and `displayName`
- Role mappings stored in `app_role_mappings.json`
- Roles resolved by matching user's AD group display names to mappings
- Multiple apps can map the same AD group to different roles
- Token includes all resolved roles across registered apps
- Refresh tokens also fetch fresh AD groups to maintain current roles

### Role Permission Synchronization
- Permissions must be saved to backend (`role_permissions.json`) to appear in tokens
- Frontend saves to localStorage AND syncs to backend via `/permissions/{client_id}/roles/{role_name}`
- New roles automatically create empty permission entry in backend
- Discovery must complete successfully before permissions can be assigned
- Permissions validated against `permissions_registry.json` during save

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

### Authentication
- `POST /auth/token/exchange` - Exchange Azure AD auth code for CIDS JWT token
- `POST /auth/token` - OAuth2 token endpoint for refresh tokens
- `GET /auth/validate` - Validate JWT token or API key
- `GET /auth/whoami` - Get current user info
- `POST /auth/logout` - Logout user

### Token Template Management
- `GET /auth/admin/token-templates` - List all templates
- `GET /auth/admin/token-templates/{name}` - Get specific template
- `POST /auth/admin/token-templates` - Create/update template
- `DELETE /auth/admin/token-templates/{name}` - Delete template
- `POST /auth/admin/token-templates/import` - Bulk import templates

### App Registration & Discovery
- `POST /auth/admin/apps` - Register new app with optional API key creation
- `POST /discovery/endpoints/{client_id}` - Trigger discovery for app
- `GET /discovery/v2/permissions/{client_id}` - Get discovered permissions
- `POST /auth/admin/apps/{client_id}/api-keys` - Create API key for app
- `POST /auth/admin/apps/{client_id}/role-mappings` - Set AD group to role mappings

### Permission Management
- `POST /permissions/{client_id}/roles` - Create role with permissions
- `PUT /permissions/{client_id}/roles/{role_name}` - Update role permissions

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
- Template claim filtering ensures only specified claims are included in tokens
- Required JWT claims (iss, sub, aud, exp, iat, nbf, jti, token_type, token_version) always included