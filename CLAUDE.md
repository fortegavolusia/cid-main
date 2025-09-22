# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
CIDS (Centralized Identity Discovery Service) is a comprehensive authentication and authorization service with row-level security (RLS) capabilities. The system consists of:
- **FastAPI Backend** (`backend/`): JWT issuing, token validation, API key management, roles, and policies
- **React Frontend** (`cids-frontend/`): Admin UI for permission management and token administration  
- **Integration Apps**: Example applications demonstrating CIDS integration

## Development Commands

### Frontend (React + Vite + TypeScript)
```bash
# Install dependencies
cd cids-frontend
npm install

# Development server (HTTPS required for Azure AD)
npm run dev                    # Runs on https://localhost:3000

# Build commands
npm run build                  # Skips build in dev unless FORCE_BUILD=1
npm run build:force            # Forces build regardless of environment
npm run build:ci               # Always builds (for CI environments)

# Code quality
npm run lint                   # Run ESLint

# Preview production build
npm run preview
```

### Backend (FastAPI + Python)
```bash
# Install dependencies (no requirements.txt currently)
pip install fastapi "uvicorn[standard]" pydantic httpx python-dotenv jinja2

# Start backend with development CORS
cd backend
DEV_CROSS_ORIGIN=true uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

# Alternative: using legacy script (if available)
cd azure-auth-app
DEV_CROSS_ORIGIN=true bash restart_server.sh

# Start test app with UI
python3 azure-auth-app/test_apps/compliant_app_with_ui.py
```

## Architecture & Code Structure

### Backend Architecture (`backend/`)
- **`api/`**: FastAPI application
  - `main.py`: Application entrypoint with all route definitions
  - `auth_app.py`: Legacy compatibility layer
- **`services/`**: Core business logic
  - `jwt.py`, `jwks.py`: Token generation and key management
  - `discovery.py`, `endpoints.py`: Service discovery and registration
  - `roles.py`, `permission_registry.py`: Role and permission management
  - `api_keys.py`, `app_registration.py`: App registration and API keys
  - `token_templates.py`: JWT template management with AD group mapping
  - `resource_filters.py`: RLS filter management
  - `refresh_tokens.py`, `token_activity.py`: Token lifecycle
- **`infra/data/app_data/`**: JSON file storage
  - `registered_apps.json`: App registrations
  - `role_permissions.json`: Permissions AND RLS filters (unified storage)
  - `discovered_permissions.json`: Valid permissions from discovery
  - `token_templates.json`: JWT claim templates
  - `app_role_mappings.json`: AD group to role mappings

### Frontend Architecture (`cids-frontend/src/`)
- **`components/`**: Reusable UI components
  - `PermissionSelector`: Resource/action/field permission management with RLS
  - `RuleBuilder`: SQL WHERE clause editor for RLS filters
  - `TokenBuilder`: Visual JWT structure editor
  - `TokenTemplates`: Template management with AD group associations
  - `RolesModal`: Role configuration and export
- **`pages/`**: Route components
  - `AdminPage`: App registration, API keys, role mappings
  - `TokenAdministrationPage`: Token builder, templates, and logs
- **`services/`**: API clients and utilities
  - `authService.ts`: OAuth flow, token exchange, refresh
  - `adminService.ts`: Admin API operations
  - `tokenManager.ts`: Token storage and refresh logic
- **`contexts/`**: React contexts
  - `AuthContext`: Authentication state and user info

## Authentication Flow

1. **React initiates OAuth** → Azure AD login
2. **Callback with auth code** → `/auth/callback` route
3. **Exchange code for JWT** → `/auth/token/exchange` endpoint
   - Fetches AD groups via Microsoft Graph API
   - Resolves roles from AD group mappings
   - Applies matching token templates (AD group or default)
   - Includes permissions and RLS filters in token
4. **Store tokens** → localStorage (access + refresh)
5. **Auto refresh** → 1 minute before expiry

## Critical Implementation Details

### Token Template System
- Templates define JWT claim structure with types and defaults
- AD group templates matched by display name (not ID)
- Priority system: AD group templates > default template
- Template claims filtered to only include specified fields
- Version 2.0 tokens indicate template was applied

### Permission & RLS Storage
- **Unified format**: Permissions + RLS filters stored together
- **Backend persistence**: `role_permissions.json` for stateless operation
- **Frontend cache**: localStorage with key pattern `cids_unified_role_{clientId}_{roleName}`
- **RLS filter format**: Multiple SQL WHERE clauses per field
- **Auto sync**: Frontend saves trigger backend updates

### Discovery Requirements
- **Version 2.0 format required** for field-level permissions
- **App ID must match** registered client_id exactly
- **JWT auth for discovery** (not API keys)
- **Response validation** against FieldMetadata schema
- **Automatic permission generation** from discovered endpoints

### AD Group Integration
- Groups fetched fresh on token exchange and refresh
- Stored as objects with `id` and `displayName`
- Multiple apps can map same group to different roles
- Roles aggregated across all registered apps

### Environment Variables (Backend)
```bash
AZURE_TENANT_ID=...           # Required: Azure AD tenant
AZURE_CLIENT_ID=...           # Required: App registration client ID
AZURE_CLIENT_SECRET=...       # Required: App registration secret
DEV_CROSS_ORIGIN=true         # Development: Enable CORS for React
ADMIN_EMAILS=...              # Comma-separated admin emails
ADMIN_GROUP_IDS=...           # Comma-separated AD group IDs for admins
PERSIST_KEYS=true             # Store JWT signing keys to disk
```

### Frontend Environment
```bash
VITE_API_ORIGIN=http://localhost:8000  # Backend API URL
```

## Common Development Tasks

### Adding New Permissions
1. Trigger discovery: `POST /discovery/endpoints/{client_id}`
2. Permissions auto-populate from discovery response
3. Assign permissions in UI → saves to backend automatically

### Creating Role Mappings
1. Register app if needed: `POST /auth/admin/apps`
2. Set AD group mappings: `POST /auth/admin/apps/{client_id}/role-mappings`
3. Format: `{"AD Group Name": "Role Name"}`

### Managing Token Templates
1. Create template in Token Builder UI
2. Associate with AD groups (live search)
3. Set priority for conflict resolution
4. Mark as default for all users (optional)

### Debugging Token Issues
1. Check Token Administration → Logs tab
2. View decoded claims in modal
3. Verify template application metadata
4. Check AD group membership and mappings

## Known Issues & Solutions

### HTTPS Certificate Warnings
- Self-signed certs required for local Azure AD redirects
- Generate with: `openssl req -x509 -nodes -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365`
- Accept browser warning for development

### Permission Not Appearing in Tokens
1. Ensure discovery completed successfully
2. Check `discovered_permissions.json` has the permission
3. Verify role saved to backend via UI save button
4. Confirm user's AD groups map to the role

### Template Not Applied
1. Verify AD group display name matches exactly
2. Check template is enabled
3. Confirm priority if multiple templates match
4. Look for `_template_applied` in token claims

### Discovery 422 Errors
- Ensure `app_id` in response matches registered `client_id`
- Use `app_name` not `service_name` in response
- Include required `last_updated` field
- Validate `response_fields` format

### Role Creation Failures
- Role mappings must be Dict format: `{"Group": "Role"}`
- Not array format: `[{"group": "...", "role": "..."}]`
- Frontend handles conversion automatically

## 🔑 IMPORTANT: App Registration Process

### After registering a new app in CIDS, ALWAYS provide to the app owner:
1. **Client ID** (e.g., `app_8a6f505227654477`) - Must match the `app_id` in discovery response
2. **API Key** (e.g., `cids_ak_Zws0hOaeAjUlwz5sYF2DD5zfsJm9WoFd`) - For authentication
3. **Discovery Requirements**:
   - The `app_id` field in discovery response MUST match the registered `client_id`
   - Discovery endpoint must be accessible from CID backend network
   - Use version "2.0" format for field-level permissions

### Common Integration Errors:
- **"Discovery step 2 failed: Connection refused"** - Usually means `app_id` mismatch
- **Discovery 422 Error** - `app_id` doesn't match registered `client_id`

## API Endpoint Reference

### Core Authentication
- `POST /auth/token/exchange` - Exchange Azure auth code for JWT
- `POST /auth/token` - OAuth2 refresh token endpoint
- `GET /auth/validate` - Validate JWT or API key
- `GET /auth/whoami` - Current user info
- `GET /.well-known/jwks.json` - Public keys for token validation

### Admin Operations (Requires Admin Auth)
- `GET/POST /auth/admin/token-templates` - Template management
- `POST /auth/admin/apps` - Register applications
- `POST /discovery/endpoints/{client_id}` - Trigger discovery
- `GET /auth/admin/azure-groups?search={query}` - Search AD groups
- `GET /auth/admin/token-activity` - View active tokens

### Permission Management
- `POST /permissions/{client_id}/roles` - Create role with permissions
- `PUT /permissions/{client_id}/roles/{role_name}` - Update role
- `DELETE /permissions/{client_id}/roles/{role_name}` - Delete role

## Testing Considerations

- No test framework configured yet (add pytest for backend, Jest/Vitest for frontend)
- Manual testing via test apps in `azure-auth-app/test_apps/`
- Validate JWT signatures using public key endpoint
- Test discovery format with compliant test app