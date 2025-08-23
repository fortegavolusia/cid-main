# CIDS Project Documentation

## Project Overview
CIDS (Centralized Identity Discovery Service) is a comprehensive authentication and authorization service with row-level security (RLS) capabilities.

## Architecture
- **Backend Auth Service**: Handles authentication and JWT token management
- **React Frontend**: Permission management interface  
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
- Supports Allow/Deny permissions
- Implements multiple SQL filters per resource/action/field for RLS
- Filter persistence via localStorage (per app + role)

### RuleBuilder (React)
- Power BI style SQL WHERE clause editor
- Template library for common filter patterns
- Support for context variables (@current_user_email, etc.)
- Test filter functionality

## RLS Filter System

### Filter Storage Structure
- Filters stored as arrays per key: `resource:name`, `action:resource.action`, `field:resource.action.field`
- Each filter has unique ID, expression, and timestamp
- Storage key: `cids_filters_{clientId}_{roleName}`

### Filter Management Features
- **Multiple filters per field**: Unlimited SQL WHERE clauses
- **CRUD operations**: Add, view, edit, delete individual filters  
- **Filter count badges**: Visual indicators on resources/actions
- **Bulk management**: View all filters for a resource/action

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

## Git Workflow
- Feature branch: `feature/resource-permissions`
- Commit messages follow conventional format
- Co-authored commits with Claude

## Dependencies
- React 18+ with TypeScript
- Vite for build tooling
- CSS modules for styling
- localStorage for persistence

## Security Considerations
- RLS filters apply SQL WHERE clauses at data access layer
- Context variables prevent SQL injection
- Filters scoped to app + role combination
- No secrets or keys in frontend code