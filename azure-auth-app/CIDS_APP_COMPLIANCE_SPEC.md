# CIDS Application Compliance Specification

## Overview
This document defines the requirements for applications to integrate with the Central Identity Service (CIDS) for authentication and field-level authorization.

## Core Requirements

### 1. Application Registration
- Register your application with CIDS admin interface
- Obtain `client_id` and `client_secret`
- Configure redirect URIs for OAuth flow
- Enable discovery endpoint

### 2. Discovery Endpoint Implementation

Every CIDS-compliant app MUST expose a discovery endpoint:

```python
@app.get("/discovery/endpoints")
async def discover_endpoints(authorization: Optional[str] = Header(None)):
    # Validate the request is from CIDS (optional but recommended)
    # Return complete field-level metadata
```

#### Discovery Response Format:
```json
{
  "version": "2.0",
  "app_id": "your_app_client_id",
  "service_name": "HR System",
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/users/{id}",
      "operation_id": "get_user",
      "description": "Retrieve user details",
      "parameters": [
        {
          "name": "id",
          "in": "path",
          "type": "string",
          "required": true
        }
      ],
      "response_fields": {
        "id": {
          "type": "string",
          "description": "User ID"
        },
        "email": {
          "type": "string",
          "description": "User email address"
        },
        "name": {
          "type": "string",
          "description": "Full name"
        },
        "salary": {
          "type": "number",
          "description": "Annual salary",
          "sensitive": true
        },
        "ssn": {
          "type": "string",
          "description": "Social Security Number",
          "sensitive": true,
          "pii": true
        },
        "department": {
          "type": "object",
          "fields": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "budget": {"type": "number", "sensitive": true}
          }
        }
      },
      "request_fields": {
        // For POST/PUT operations
        "name": {
          "type": "string",
          "required": true
        },
        "salary": {
          "type": "number",
          "required": false
        }
      }
    }
  ]
}
```

### 3. Authentication Flow

#### For Web Applications:
```python
# 1. Redirect to CIDS login
@app.get("/login")
def login():
    return redirect(
        f"{CIDS_URL}/auth/login?client_id={CLIENT_ID}"
        f"&app_redirect_uri={REDIRECT_URI}&state={state}"
    )

# 2. Handle callback
@app.get("/auth/callback")
def callback(access_token: str, state: str):
    # Validate state
    # Validate token with CIDS
    # Store in session
```

#### For API Services:
```python
# Use the shared cids_auth library
from cids_auth import require_permissions, extract_token_claims

@app.get("/api/users/{id}")
@require_permissions("users.read")
async def get_user(id: str, request: Request):
    token_claims = extract_token_claims(request)
    # Use token_claims["permissions"] to filter response
```

### 4. Token Validation

All apps MUST validate tokens with CIDS:

```python
async def validate_token(token: str) -> dict:
    response = await httpx.get(
        f"{CIDS_URL}/auth/validate",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code != 200:
        raise AuthenticationError()
    return response.json()
```

### 5. Permission Enforcement

Apps MUST respect field-level permissions from the token:

```python
def filter_response_fields(data: dict, permissions: list, resource: str) -> dict:
    filtered = {}
    for field, value in data.items():
        permission = f"{resource}.read.{field}"
        if permission in permissions:
            if isinstance(value, dict):
                # Recursively filter nested objects
                filtered[field] = filter_response_fields(
                    value, permissions, f"{resource}.{field}"
                )
            else:
                filtered[field] = value
    return filtered

# Usage
@app.get("/api/users/{id}")
async def get_user(id: str, token_claims: dict):
    user = db.get_user(id)
    return filter_response_fields(
        user, 
        token_claims["permissions"],
        "users"
    )
```

### 6. Audit Logging

Apps SHOULD log permission checks:

```python
async def log_access(user_id: str, resource: str, action: str, granted: bool):
    logger.info(f"Access {action} on {resource} by {user_id}: {'granted' if granted else 'denied'}")
```

## Compliance Checklist

- [ ] Application registered in CIDS
- [ ] Discovery endpoint implemented at `/discovery/endpoints`
- [ ] Discovery returns ALL fields with metadata
- [ ] No hardcoded permissions in code
- [ ] Token validation implemented
- [ ] Field-level filtering based on token permissions
- [ ] Audit logging for access attempts
- [ ] Handles token expiration gracefully
- [ ] Supports token refresh flow
- [ ] No sensitive data in logs

## Permission Naming Convention

Permissions follow this pattern:
```
{app_id}.{resource}.{action}.{field}
```

Examples:
- `hr_system.users.read.email`
- `hr_system.users.write.salary`
- `hr_system.payroll.delete`
- `hr_system.reports.execute.financial`

## Security Requirements

1. **HTTPS Only** - All endpoints must use TLS
2. **Token Storage** - Never log or store tokens in plain text
3. **Internal Services** - Should not be directly accessible from internet
4. **State Parameter** - Always validate state in OAuth flow
5. **Token Expiry** - Handle expired tokens gracefully

## Microservice Considerations

For apps with multiple microservices:

1. **Single Registration** - Register the main app, not each service
2. **Aggregated Discovery** - Main app aggregates all service endpoints
3. **Shared Auth** - All services use the same auth library
4. **Internal Trust** - Services trust headers from gateway/main app

Example structure:
```
hr_system/ (registered with CIDS)
├── gateway.py (handles CIDS auth)
├── services/
│   ├── users_service.py
│   ├── payroll_service.py
│   └── reports_service.py
└── cids_auth.py (shared library)
```

## Testing Your Integration

1. **Discovery Test**: 
   ```bash
   curl https://your-app/discovery/endpoints
   ```

2. **Permission Test**: Create a test role with limited permissions and verify filtering

3. **Token Expiry Test**: Verify app handles expired tokens

4. **Field Access Test**: Confirm fields are filtered based on permissions

## Support

For questions about CIDS integration:
- Documentation: [CIDS Auth Docs]
- Examples: See `test_app.py` in CIDS repository
- Issues: File at CIDS GitHub repository