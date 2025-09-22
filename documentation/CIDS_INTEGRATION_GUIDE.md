# 📚 CIDS Integration Guide for Developers
## Complete Guide for Integrating Applications with Centralized Identity Discovery Service

---

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Application Registration](#step-1-application-registration)
4. [Step 2: Implement Discovery Endpoint](#step-2-implement-discovery-endpoint)
5. [Step 3: Token Validation](#step-3-token-validation)
6. [Step 4: Permission Enforcement](#step-4-permission-enforcement)
7. [Step 5: A2A Integration (Optional)](#step-5-a2a-integration-optional)
8. [Testing Your Integration](#testing-your-integration)
9. [Common Issues & Solutions](#common-issues--solutions)
10. [API Reference](#api-reference)

---

## Overview

CIDS (Centralized Identity Discovery Service) provides centralized authentication, authorization, and permission management for all integrated applications. This guide will walk you through integrating your application with CIDS.

### Key Benefits:
- ✅ Single Sign-On (SSO) via Azure AD
- ✅ Centralized permission management
- ✅ Row-Level Security (RLS) support
- ✅ Token-based authentication with JWT
- ✅ A2A (Application-to-Application) authentication
- ✅ Automatic permission discovery

---

## Prerequisites

Before integrating with CIDS, ensure you have:

1. **Application Details Ready:**
   - Application name
   - Description
   - Owner email
   - Redirect URLs (for OAuth callbacks)

2. **Development Environment:**
   - HTTPS support (required for OAuth)
   - Ability to validate JWT tokens
   - Network access to CIDS endpoints

3. **Required Libraries:**
   - JWT validation library for your language
   - HTTP client for API calls
   - JSON parsing capabilities

---

## Step 1: Application Registration

### Request Registration

Contact the CIDS administrator to register your application. Provide:

```json
{
  "name": "Your Application Name",
  "description": "Brief description of your application",
  "owner_email": "owner@volusia.gov",
  "redirect_uris": [
    "https://yourapp.volusia.gov/auth/callback",
    "http://localhost:3000/auth/callback"  // for development
  ],
  "discovery_endpoint": "https://yourapp.volusia.gov/discovery/endpoints",
  "allow_discovery": true
}
```

### You'll Receive:

```json
{
  "client_id": "app_xxxxxxxxxxxxx",  // Your unique application ID
  "client_secret": "secret_xxxxxxxxx", // For confidential clients
  "api_key": "key_xxxxxxxxxxxx"       // For service-to-service calls
}
```

⚠️ **Security Note:** Store credentials securely in environment variables, never in code!

---

## Step 2: Implement Discovery Endpoint

### Required Endpoint

Your application **MUST** implement a discovery endpoint that CIDS will call to learn about your application's structure.

**URL:** `GET /discovery/endpoints`

### Required Response Format (Version 2.0)

```json
{
  "app_id": "app_xxxxxxxxxxxxx",  // MUST match your client_id exactly
  "app_name": "Your Application Name",
  "version": "2.0",  // REQUIRED: Must be "2.0" for field-level permissions
  "last_updated": "2025-09-15T12:00:00Z",  // ISO 8601 format
  "endpoints": [
    {
      "path": "/api/employees",
      "method": "GET",
      "description": "Get employee list",
      "resource": "employees",
      "action": "read",
      "response_fields": [
        "id",
        "name",
        "email",
        "department",
        "salary",
        "ssn"
      ]
    },
    {
      "path": "/api/employees/{id}",
      "method": "GET",
      "description": "Get specific employee",
      "resource": "employees",
      "action": "read",
      "response_fields": [
        "id",
        "name",
        "email",
        "department",
        "salary",
        "ssn",
        "phone",
        "address"
      ]
    },
    {
      "path": "/api/employees",
      "method": "POST",
      "description": "Create new employee",
      "resource": "employees",
      "action": "create",
      "response_fields": []
    },
    {
      "path": "/api/employees/{id}",
      "method": "PUT",
      "description": "Update employee",
      "resource": "employees",
      "action": "update",
      "response_fields": []
    },
    {
      "path": "/api/employees/{id}",
      "method": "DELETE",
      "description": "Delete employee",
      "resource": "employees",
      "action": "delete",
      "response_fields": []
    }
  ],
  "response_fields": {
    "employees": {
      "id": {
        "type": "string",
        "description": "Employee ID",
        "category": "base"
      },
      "name": {
        "type": "string",
        "description": "Employee full name",
        "category": "pii"
      },
      "email": {
        "type": "string",
        "description": "Employee email",
        "category": "pii"
      },
      "department": {
        "type": "string",
        "description": "Department name",
        "category": "base"
      },
      "salary": {
        "type": "number",
        "description": "Employee salary",
        "category": "financial"
      },
      "ssn": {
        "type": "string",
        "description": "Social Security Number",
        "category": "sensitive"
      },
      "phone": {
        "type": "string",
        "description": "Phone number",
        "category": "pii"
      },
      "address": {
        "type": "string",
        "description": "Home address",
        "category": "pii"
      }
    }
  }
}
```

### Field Categories

**IMPORTANT:** Categorize fields correctly for proper permission management:

- **`base`**: Public/non-sensitive information
- **`pii`**: Personally Identifiable Information
- **`phi`**: Protected Health Information (for healthcare data)
- **`financial`**: Financial data (salaries, accounts, etc.)
- **`sensitive`**: Highly sensitive data (SSN, passwords, etc.)

### Example Implementation (Python/FastAPI)

```python
from fastapi import FastAPI, Depends, HTTPException
from datetime import datetime

app = FastAPI()

@app.get("/discovery/endpoints")
async def discovery_endpoints():
    return {
        "app_id": os.getenv("CIDS_CLIENT_ID"),
        "app_name": "HR System",
        "version": "2.0",
        "last_updated": datetime.now().isoformat(),
        "endpoints": [
            {
                "path": "/api/employees",
                "method": "GET",
                "description": "Get employee list",
                "resource": "employees",
                "action": "read",
                "response_fields": ["id", "name", "email", "department"]
            },
            # ... more endpoints
        ],
        "response_fields": {
            "employees": {
                "id": {"type": "string", "description": "Employee ID", "category": "base"},
                "name": {"type": "string", "description": "Full name", "category": "pii"},
                # ... more fields
            }
        }
    }
```

### Example Implementation (Node.js/Express)

```javascript
app.get('/discovery/endpoints', (req, res) => {
  res.json({
    app_id: process.env.CIDS_CLIENT_ID,
    app_name: "HR System",
    version: "2.0",
    last_updated: new Date().toISOString(),
    endpoints: [
      {
        path: "/api/employees",
        method: "GET",
        description: "Get employee list",
        resource: "employees",
        action: "read",
        response_fields: ["id", "name", "email", "department"]
      }
      // ... more endpoints
    ],
    response_fields: {
      employees: {
        id: { type: "string", description: "Employee ID", category: "base" },
        name: { type: "string", description: "Full name", category: "pii" }
        // ... more fields
      }
    }
  });
});
```

---

## Step 3: Token Validation

### OAuth Flow

1. **Redirect user to CIDS login:**
```
https://cids.volusia.gov/auth/authorize?
  client_id=app_xxxxxxxxxxxxx&
  redirect_uri=https://yourapp.volusia.gov/auth/callback&
  response_type=code&
  scope=openid profile email
```

2. **Handle callback and exchange code for token:**

```python
# Python example
import httpx

async def handle_callback(code: str):
    response = await httpx.post(
        "https://cids.volusia.gov/auth/token/exchange",
        json={
            "code": code,
            "client_id": os.getenv("CIDS_CLIENT_ID"),
            "client_secret": os.getenv("CIDS_CLIENT_SECRET"),
            "redirect_uri": "https://yourapp.volusia.gov/auth/callback"
        }
    )
    tokens = response.json()
    # tokens contains: access_token, refresh_token, expires_in
```

### JWT Token Structure

The access token will contain:

```json
{
  "sub": "user@volusia.gov",
  "email": "user@volusia.gov",
  "name": "User Name",
  "roles": ["HR_Admin", "Finance_Viewer"],
  "permissions": [
    "employees.read.base",
    "employees.read.pii",
    "employees.create",
    "employees.update"
  ],
  "rls_filters": {
    "department": ["HR", "IT"],
    "location": "HQ"
  },
  "bound_ip": "192.168.1.100",      // Token bound to IP
  "bound_device": "device_hash_xxx", // Token bound to device
  "iat": 1234567890,
  "exp": 1234571490,
  "iss": "https://cids.volusia.gov",
  "aud": "app_xxxxxxxxxxxxx"
}
```

### Validate JWT Token

```python
# Python example using PyJWT
import jwt
import httpx
from typing import Optional

class TokenValidator:
    def __init__(self):
        self.jwks_client = None
        self.public_keys = {}

    async def get_public_key(self):
        """Fetch JWKS from CIDS"""
        if not self.public_keys:
            response = await httpx.get("https://cids.volusia.gov/.well-known/jwks.json")
            jwks = response.json()
            # Parse JWKS and extract public keys
            for key in jwks["keys"]:
                self.public_keys[key["kid"]] = key
        return self.public_keys

    async def validate_token(self, token: str, request_ip: str) -> Optional[dict]:
        """Validate JWT token"""
        try:
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            # Get public key
            keys = await self.get_public_key()
            public_key = keys.get(kid)

            if not public_key:
                return None

            # Validate token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=os.getenv("CIDS_CLIENT_ID"),
                issuer="https://cids.volusia.gov"
            )

            # Validate IP binding
            if payload.get("bound_ip") and payload["bound_ip"] != request_ip:
                raise ValueError("Token IP mismatch")

            return payload

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
```

### Node.js Example

```javascript
const jwt = require('jsonwebtoken');
const jwksClient = require('jwks-rsa');

const client = jwksClient({
  jwksUri: 'https://cids.volusia.gov/.well-known/jwks.json'
});

function getKey(header, callback) {
  client.getSigningKey(header.kid, (err, key) => {
    const signingKey = key.publicKey || key.rsaPublicKey;
    callback(null, signingKey);
  });
}

function validateToken(token, requestIp) {
  return new Promise((resolve, reject) => {
    jwt.verify(token, getKey, {
      audience: process.env.CIDS_CLIENT_ID,
      issuer: 'https://cids.volusia.gov',
      algorithms: ['RS256']
    }, (err, decoded) => {
      if (err) return reject(err);

      // Validate IP binding
      if (decoded.bound_ip && decoded.bound_ip !== requestIp) {
        return reject(new Error('Token IP mismatch'));
      }

      resolve(decoded);
    });
  });
}
```

---

## Step 4: Permission Enforcement

### Check Permissions

```python
def has_permission(token_payload: dict, resource: str, action: str, field: str = None) -> bool:
    """Check if user has permission"""
    permissions = token_payload.get("permissions", [])

    # Check denied permissions first (if using hybrid system)
    denied = token_payload.get("denied_permissions", [])

    if field:
        # Field-level permission check
        permission = f"{resource}.{action}.{field}"
        if permission in denied:
            return False
        return permission in permissions
    else:
        # Action-level permission check
        # Check if any field permission exists for this action
        prefix = f"{resource}.{action}."
        for perm in permissions:
            if perm.startswith(prefix):
                return True
        return False

@app.get("/api/employees")
async def get_employees(token: dict = Depends(validate_token)):
    if not has_permission(token, "employees", "read"):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Get all employees
    employees = await db.get_employees()

    # Filter fields based on permissions
    filtered_employees = []
    for emp in employees:
        filtered_emp = {}
        for field in emp.keys():
            if has_permission(token, "employees", "read", field):
                filtered_emp[field] = emp[field]
        filtered_employees.append(filtered_emp)

    # Apply RLS filters if present
    rls_filters = token.get("rls_filters", {})
    if "department" in rls_filters:
        filtered_employees = [
            emp for emp in filtered_employees
            if emp.get("department") in rls_filters["department"]
        ]

    return filtered_employees
```

### Example: Field-Level Filtering

```python
class FieldFilter:
    """Filter response fields based on permissions"""

    @staticmethod
    def filter_object(obj: dict, resource: str, permissions: list) -> dict:
        """Filter single object fields"""
        filtered = {}
        for field, value in obj.items():
            # Check if user has permission for this field
            field_perms = [
                f"{resource}.read.{field}",
                f"{resource}.read.base",  # Base fields always visible
                f"{resource}.read.*"      # Wildcard permission
            ]

            if any(perm in permissions for perm in field_perms):
                filtered[field] = value

        return filtered

    @staticmethod
    def filter_list(items: list, resource: str, permissions: list) -> list:
        """Filter list of objects"""
        return [
            FieldFilter.filter_object(item, resource, permissions)
            for item in items
        ]

# Usage in endpoint
@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: str, token: dict = Depends(validate_token)):
    employee = await db.get_employee(employee_id)

    # Filter fields based on permissions
    filtered = FieldFilter.filter_object(
        employee,
        "employees",
        token.get("permissions", [])
    )

    if not filtered:
        raise HTTPException(status_code=404, detail="Employee not found")

    return filtered
```

---

## Step 5: A2A Integration (Optional)

### Application-to-Application Authentication

For service-to-service calls, use A2A tokens:

```python
class A2AClient:
    def __init__(self, client_id: str, api_key: str):
        self.client_id = client_id
        self.api_key = api_key
        self.token = None
        self.token_expires = 0

    async def get_token(self) -> str:
        """Get or refresh A2A token"""
        if self.token and time.time() < self.token_expires:
            return self.token

        # Request new A2A token
        response = await httpx.post(
            "https://cids.volusia.gov/auth/a2a/token",
            headers={
                "X-API-Key": self.api_key
            },
            json={
                "client_id": self.client_id,
                "scope": "employees.read reports.write"
            }
        )

        data = response.json()
        self.token = data["access_token"]
        self.token_expires = time.time() + data["expires_in"] - 60

        return self.token

    async def call_service(self, url: str, method: str = "GET", data: dict = None):
        """Make authenticated service call"""
        token = await self.get_token()

        response = await httpx.request(
            method,
            url,
            headers={
                "Authorization": f"Bearer {token}"
            },
            json=data
        )

        return response.json()

# Usage
a2a_client = A2AClient(
    client_id=os.getenv("CIDS_CLIENT_ID"),
    api_key=os.getenv("CIDS_API_KEY")
)

# Call another service
employees = await a2a_client.call_service(
    "https://hr-system.volusia.gov/api/employees"
)
```

---

## Testing Your Integration

### 1. Test Discovery Endpoint

```bash
# CIDS will call your discovery endpoint
curl https://yourapp.volusia.gov/discovery/endpoints

# Response should be valid JSON with version 2.0
```

### 2. Test Token Validation

```python
# Test script
async def test_token_validation():
    # Get test token from CIDS
    test_token = "eyJ..."

    validator = TokenValidator()
    payload = await validator.validate_token(test_token, "192.168.1.100")

    assert payload is not None
    assert "permissions" in payload
    assert "email" in payload
    print("✅ Token validation working")
```

### 3. Test Permission Enforcement

```python
async def test_permissions():
    # Mock token payload
    token = {
        "email": "test@volusia.gov",
        "permissions": [
            "employees.read.base",
            "employees.read.pii"
        ]
    }

    # Test permission checks
    assert has_permission(token, "employees", "read", "name") == True
    assert has_permission(token, "employees", "read", "ssn") == False
    assert has_permission(token, "employees", "delete") == False
    print("✅ Permission enforcement working")
```

### 4. Integration Test Checklist

- [ ] Discovery endpoint returns valid JSON
- [ ] Version is exactly "2.0"
- [ ] app_id matches your client_id
- [ ] All endpoints are documented
- [ ] Field categories are correct
- [ ] Token validation works
- [ ] Expired tokens are rejected
- [ ] IP binding is enforced (if enabled)
- [ ] Permissions are enforced correctly
- [ ] RLS filters are applied
- [ ] A2A authentication works (if used)

---

## Common Issues & Solutions

### Issue 1: Discovery Returns 422 Error

**Cause:** Invalid discovery response format

**Solution:** Ensure:
- `app_id` matches your `client_id` exactly
- `version` is exactly `"2.0"` (string, not number)
- `last_updated` is in ISO 8601 format
- All required fields are present

### Issue 2: Token Validation Fails

**Cause:** Invalid public key or expired token

**Solution:**
- Refresh JWKS cache regularly
- Check token expiration
- Verify audience matches your client_id
- Ensure clock sync between servers

### Issue 3: Permissions Not Working

**Cause:** Permissions not properly discovered or assigned

**Solution:**
1. Trigger discovery: `POST https://cids.volusia.gov/discovery/endpoints/{client_id}`
2. Check discovered permissions in CIDS admin panel
3. Ensure roles are assigned to users
4. Verify permission format: `resource.action.field`

### Issue 4: IP Binding Errors

**Cause:** Token bound to different IP

**Solution:**
- Get client's real IP (check for proxies/load balancers)
- Use `X-Forwarded-For` header if behind proxy
- Request token without IP binding for testing

### Issue 5: CORS Errors

**Cause:** Cross-origin requests blocked

**Solution:**
```python
# Add CORS headers
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cids.volusia.gov"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## API Reference

### CIDS Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/authorize` | GET | Start OAuth flow |
| `/auth/token/exchange` | POST | Exchange code for tokens |
| `/auth/token` | POST | Refresh access token |
| `/auth/validate` | POST | Validate token or API key |
| `/auth/whoami` | GET | Get current user info |
| `/.well-known/jwks.json` | GET | Get public keys for validation |
| `/discovery/endpoints/{client_id}` | POST | Trigger discovery |
| `/auth/a2a/token` | POST | Get A2A token |

### Required Headers

| Header | Value | When to Use |
|--------|-------|-------------|
| `Authorization` | `Bearer {token}` | For authenticated requests |
| `X-API-Key` | `{api_key}` | For A2A authentication |
| `X-Client-IP` | `{real_ip}` | If behind proxy |
| `X-Device-ID` | `{device_id}` | For device binding |

### Token Claims

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | string | User identifier |
| `email` | string | User email |
| `name` | string | User full name |
| `roles` | array | User roles |
| `permissions` | array | Granted permissions |
| `denied_permissions` | array | Explicitly denied permissions |
| `rls_filters` | object | Row-level security filters |
| `bound_ip` | string | IP address token is bound to |
| `bound_device` | string | Device ID token is bound to |
| `iat` | number | Issued at timestamp |
| `exp` | number | Expiration timestamp |

---

## Security Best Practices

1. **Always use HTTPS** in production
2. **Store credentials securely** (environment variables, secrets manager)
3. **Validate tokens on every request**
4. **Implement rate limiting** to prevent abuse
5. **Log all authentication events** for auditing
6. **Rotate API keys regularly** (quarterly recommended)
7. **Implement proper error handling** (don't leak sensitive info)
8. **Use field-level permissions** for sensitive data
9. **Apply RLS filters** for multi-tenant scenarios
10. **Monitor for suspicious activity** (failed auth, permission denials)

---

## Support

For assistance with CIDS integration:

- **Documentation**: This guide
- **Admin Portal**: https://cids.volusia.gov
- **Email**: cids-support@volusia.gov
- **Issues**: Contact your CIDS administrator

---

## Appendix: Complete Example Application

See `/examples/sample-hr-app/` for a complete working example including:
- Discovery endpoint implementation
- Token validation
- Permission enforcement
- Field filtering
- RLS implementation
- A2A integration

---

**Last Updated**: September 15, 2025
**Version**: 2.0
**Status**: OFFICIAL INTEGRATION GUIDE