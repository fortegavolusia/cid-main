# CIDS IAM Extension Guide

This guide covers the new IAM (Identity and Access Management) features added to the CIDS authentication service.

## Overview

The IAM extensions provide:
- **JWKS & Metadata**: Standard endpoints for key discovery
- **App Endpoints Registry**: Define which endpoints each app handles
- **Roles & Mappings**: Map Azure AD groups to app-specific roles
- **Policy Documents**: Define permissions and role-based access
- **Effective Identity**: Compute user's permissions dynamically
- **Enhanced Tokens**: Include roles, permissions, and attributes

## Quick Start Example

### 1. Register an App

```bash
# First, register your app (if not already done)
curl -X POST https://cids.example.com/auth/admin/apps \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "HR System",
    "description": "Human Resources Management System",
    "redirect_uris": ["https://hr.example.com/auth/callback"],
    "owner_email": "hr-admin@example.com"
  }'

# Response:
{
  "app": {
    "client_id": "app_hr_123456",
    "name": "HR System",
    ...
  },
  "client_secret": "secret_xyz..."
}
```

### 2. Define App Endpoints

```bash
# Register which endpoints this app handles
curl -X PUT https://cids.example.com/apps/app_hr_123456/endpoints \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoints": [
      {
        "method": "GET",
        "path": "/api/employees",
        "desc": "List all employees"
      },
      {
        "method": "GET",
        "path": "/api/employees/*",
        "desc": "Get employee details"
      },
      {
        "method": "POST",
        "path": "/api/employees",
        "desc": "Create new employee"
      },
      {
        "method": "*",
        "path": "/api/payroll/*",
        "desc": "All payroll operations"
      }
    ]
  }'
```

### 3. Define Roles

```bash
# Define roles for the HR app
curl -X PUT https://cids.example.com/apps/app_hr_123456/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "roles": [
      {
        "name": "hr_viewer",
        "description": "Can view employee data",
        "permissions": ["employee.read", "department.read"]
      },
      {
        "name": "hr_admin",
        "description": "Full HR administration",
        "permissions": ["employee.*", "department.*", "payroll.*"]
      },
      {
        "name": "hr_manager",
        "description": "Department manager access",
        "permissions": ["employee.read", "employee.update", "department.read"]
      }
    ]
  }'
```

### 4. Map Azure AD Groups to Roles

```bash
# Map AD groups to app roles
curl -X PUT https://cids.example.com/role-mappings \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mappings": [
      {
        "azure_group": "HR Department",
        "app_client_id": "app_hr_123456",
        "role": "hr_viewer"
      },
      {
        "azure_group": "HR Administrators",
        "app_client_id": "app_hr_123456",
        "role": "hr_admin"
      },
      {
        "azure_group": "Department Managers",
        "app_client_id": "app_hr_123456",
        "role": "hr_manager",
        "tenant_id": "tenant-123"  
      }
    ]
  }'
```

### 5. Create Policy Document

```bash
# Define permissions and access rules
curl -X PUT https://cids.example.com/policy/app_hr_123456 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "HR System Access Policy v1.0",
    "permissions": [
      {
        "name": "employee.read",
        "description": "View employee records",
        "resource": "employee",
        "actions": ["read", "list"]
      },
      {
        "name": "employee.update",
        "description": "Update employee records",
        "resource": "employee",
        "actions": ["update"]
      },
      {
        "name": "employee.create",
        "description": "Create new employees",
        "resource": "employee",
        "actions": ["create"]
      },
      {
        "name": "payroll.manage",
        "description": "Manage payroll data",
        "resource": "payroll",
        "actions": ["read", "update", "approve"]
      }
    ],
    "role_permission_matrix": [
      {
        "role": "hr_viewer",
        "permissions": ["employee.read"]
      },
      {
        "role": "hr_manager",
        "permissions": ["employee.read", "employee.update"]
      },
      {
        "role": "hr_admin",
        "permissions": ["employee.read", "employee.update", "employee.create", "payroll.manage"]
      }
    ],
    "abac_rules": [
      {
        "name": "IT_dept_extra_access",
        "description": "IT department gets additional permissions",
        "condition": "attrs.department == 'IT' and attrs.level >= 3",
        "permissions": ["employee.update"]
      }
    ]
  }'
```

### 6. Check Effective Identity

```bash
# Get current user's effective permissions
curl https://cids.example.com/iam/me \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "X-Tenant-Id: tenant-123"

# Response:
{
  "sub": "user_12345",
  "email": "john.doe@example.com",
  "name": "John Doe",
  "aud": ["app_hr_123456"],
  "scope": "openid profile email",
  "roles": {
    "app_hr_123456": ["hr_manager", "hr_viewer"]
  },
  "effective_permissions": {
    "app_hr_123456": ["employee.read", "employee.update"]
  },
  "attrs": {
    "department": "IT",
    "tenant": "tenant-123",
    "groups": ["HR Department", "Department Managers", "IT Section Manager"]
  },
  "token_info": {
    "iss": "internal-auth-service",
    "iat": 1753974424,
    "exp": 1753975024,
    "ver": "2.0"
  }
}
```

## Token Structure

### Access Token Claims (JWT)

```json
{
  "iss": "internal-auth-service",
  "sub": "user_12345",
  "aud": ["app_hr_123456"],
  "email": "john.doe@example.com",
  "name": "John Doe",
  "groups": ["HR Department", "Department Managers"],
  "scope": "openid profile email",
  "roles": {
    "app_hr_123456": ["hr_manager"]
  },
  "attrs": {
    "department": "HR",
    "tenant": "tenant-123"
  },
  "token_version": "2.0",
  "iat": 1753974424,
  "exp": 1753975024,  // 10 minutes
  "jti": "unique-token-id"
}
```

### Refresh Token

- Stored as httpOnly cookie
- 7-day expiration
- Used with `/oauth/token` endpoint

## API Endpoints

### JWKS & Metadata

```bash
# Get public keys
GET /.well-known/jwks.json

# Get service configuration
GET /.well-known/cids-config
```

### App Management

```bash
# Endpoints registry
PUT /apps/{client_id}/endpoints
GET /apps/{client_id}/endpoints

# Roles
PUT /apps/{client_id}/roles
GET /apps/{client_id}/roles

# Role mappings
PUT /role-mappings
GET /role-mappings

# Policy
PUT /policy/{client_id}
GET /policy/{client_id}
GET /policy/{client_id}?version=20240731120000
```

### Identity & Tokens

```bash
# Effective identity
GET /iam/me

# Token refresh
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=xxx&client_id=app_hr_123456
```

## Integration Example

### Python Client

```python
import requests
import jwt

class CIDSClient:
    def __init__(self, base_url, client_id, client_secret):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._jwks = None
    
    def get_jwks(self):
        """Fetch JWKS for token validation"""
        if not self._jwks:
            resp = requests.get(f"{self.base_url}/.well-known/jwks.json")
            self._jwks = resp.json()
        return self._jwks
    
    def validate_token(self, token):
        """Validate and decode token"""
        # In production, use proper JWT validation with JWKS
        # This is simplified for example
        jwks = self.get_jwks()
        # ... implement JWT validation with public key
        return jwt.decode(token, options={"verify_signature": False})
    
    def get_effective_permissions(self, token, tenant_id=None):
        """Get user's effective permissions"""
        headers = {
            "Authorization": f"Bearer {token}"
        }
        if tenant_id:
            headers["X-Tenant-Id"] = tenant_id
        
        resp = requests.get(f"{self.base_url}/iam/me", headers=headers)
        return resp.json()
    
    def refresh_token(self, refresh_token):
        """Refresh access token"""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id
        }
        resp = requests.post(f"{self.base_url}/oauth/token", data=data)
        return resp.json()

# Usage
client = CIDSClient("https://cids.example.com", "app_hr_123456", "secret")
identity = client.get_effective_permissions(user_token)

# Check permissions
if "employee.update" in identity["effective_permissions"].get("app_hr_123456", []):
    # User can update employees
    pass
```

## Best Practices

1. **Token Lifetime**: Keep access tokens short (5-10 minutes)
2. **Refresh Tokens**: Store securely, use httpOnly cookies
3. **Permission Checks**: Always verify permissions server-side
4. **Audit Logging**: All permission changes are logged
5. **Version Policies**: Version your policy documents
6. **Group Naming**: Use consistent AD group naming conventions
7. **Wildcard Usage**: Use wildcards sparingly in endpoints

## Migration Guide

For existing apps using the old token format:

1. Tokens with `token_version: "1.0"` continue to work
2. New tokens include `token_version: "2.0"` with IAM claims
3. Use `/iam/me` to get full permission details
4. Gradually migrate to check `roles` and `effective_permissions`

## Troubleshooting

### No permissions showing

1. Check role mappings are configured
2. Verify user is in the mapped Azure AD groups
3. Ensure policy document is active
4. Check audit logs for configuration changes

### Token validation fails

1. Verify JWKS endpoint is accessible
2. Check token hasn't expired (10-minute TTL)
3. Ensure correct audience in token

### Endpoint conflicts

1. Check for duplicate endpoint definitions
2. Avoid overlapping wildcard patterns
3. Use versioning for endpoint updates