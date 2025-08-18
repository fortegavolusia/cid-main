# CIDS Deployment Guide for Compliant Applications

This guide explains how to deploy applications that integrate with CIDS (Central Identity Service) for field-level authorization.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Application Registration](#application-registration)
4. [Environment Configuration](#environment-configuration)
5. [Using the CIDS Auth Library](#using-the-cids-auth-library)
6. [Implementing Discovery](#implementing-discovery)
7. [Field-Level Authorization](#field-level-authorization)
8. [Testing Your Integration](#testing-your-integration)
9. [Production Checklist](#production-checklist)
10. [Troubleshooting](#troubleshooting)

## Overview

CIDS provides centralized authentication and field-level authorization for microservices. Applications register with CIDS, expose their field metadata through discovery, and enforce permissions from CIDS tokens.

### Key Concepts
- **Field-Level Permissions**: Control access to individual fields, not just endpoints
- **Discovery**: Apps expose their complete structure to CIDS
- **Zero-Trust**: Every field access is explicitly authorized
- **Role-Based**: Permissions are grouped into roles assigned to users

## Prerequisites

- Python 3.8+ (for Python apps)
- Access to CIDS admin interface
- Client ID and Secret from CIDS registration

## Application Registration

1. **Access CIDS Admin Interface**
   ```
   https://<cids-server>/
   ```
   Login with your admin credentials.

2. **Register Your Application**
   - Click "App Management"
   - Click "Register New App"
   - Fill in:
     - **App Name**: Human-readable name (e.g., "HR Service")
     - **Client ID**: Unique identifier (e.g., "hr_service")
     - **Description**: Brief description of your service
     - **Redirect URIs**: Add all valid redirect URIs
     - **Allow Discovery**: Check this box to enable field-level permissions

3. **Save Client Secret**
   After registration, you'll receive a client secret. Store it securely - you'll need it for your application.

## Environment Configuration

Set these environment variables for your application:

```bash
# Required
export CIDS_URL="https://cids.example.com"
export CIDS_CLIENT_ID="your_client_id"
export CIDS_CLIENT_SECRET="your_client_secret"

# Optional
export CIDS_VERIFY_SSL="true"  # Set to false for development with self-signed certs
export APP_HOST="0.0.0.0"
export APP_PORT="8001"
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV CIDS_URL=${CIDS_URL}
ENV CIDS_CLIENT_ID=${CIDS_CLIENT_ID}
ENV CIDS_CLIENT_SECRET=${CIDS_CLIENT_SECRET}

# Run application
CMD ["python", "app.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-cids-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-cids-app
  template:
    metadata:
      labels:
        app: my-cids-app
    spec:
      containers:
      - name: app
        image: my-cids-app:latest
        ports:
        - containerPort: 8001
        env:
        - name: CIDS_URL
          valueFrom:
            configMapKeyRef:
              name: cids-config
              key: url
        - name: CIDS_CLIENT_ID
          valueFrom:
            configMapKeyRef:
              name: cids-config
              key: client-id
        - name: CIDS_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: cids-secrets
              key: client-secret
```

## Using the CIDS Auth Library

### Installation

```bash
# Copy cids_auth.py to your project
cp /path/to/cids_auth.py ./

# Or install dependencies manually
pip install requests pyjwt
```

### Basic Usage

```python
from cids_auth import CIDSAuth, from_env

# Initialize from environment variables
auth = from_env()

# Or initialize manually
auth = CIDSAuth(
    cids_url="https://cids.example.com",
    client_id="my_app",
    client_secret="secret",
    verify_ssl=True
)
```

### FastAPI Integration

```python
from fastapi import FastAPI, Header, HTTPException, Depends
from cids_auth import CIDSAuth, CIDSTokenError

app = FastAPI()
auth = from_env()

@app.get("/protected")
async def protected_route(
    authorization: Optional[str] = Header(None)
):
    try:
        user_info = auth.validate_token(authorization)
        return {"message": f"Hello {user_info['email']}"}
    except CIDSTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))
```

### Flask Integration

```python
from flask import Flask, g, jsonify
from cids_auth import from_env

app = Flask(__name__)
auth = from_env()

@app.route('/protected')
@auth.require_auth
def protected_route():
    user_info = g.user_info
    return jsonify({"message": f"Hello {user_info['email']}"})
```

## Implementing Discovery

Your application MUST expose a discovery endpoint that returns field metadata:

```python
@app.get("/discovery/endpoints")
async def discover_endpoints(version: str = "2.0"):
    return {
        "version": "2.0",
        "app_id": "my_app",
        "app_name": "My Application",
        "endpoints": [
            {
                "method": "GET",
                "path": "/users/{id}",
                "operation_id": "get_user",
                "description": "Get user details",
                "response_fields": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "email": {"type": "string", "pii": True},
                    "salary": {
                        "type": "number",
                        "sensitive": True,
                        "description": "Annual salary"
                    }
                }
            }
        ]
    }
```

### Field Metadata Schema

Each field should include:
- `type`: Data type (string, number, boolean, object, array)
- `description`: Human-readable description
- `sensitive`: Boolean flag for sensitive data
- `pii`: Boolean flag for Personally Identifiable Information
- `phi`: Boolean flag for Protected Health Information
- `required`: Whether field is required (for request fields)

## Field-Level Authorization

### Automatic Field Filtering

Use the auth library to automatically filter response fields:

```python
@app.get("/users")
async def list_users(authorization: Optional[str] = Header(None)):
    user_info = auth.validate_token(authorization)
    
    # Get all data
    all_users = get_all_users_from_db()
    
    # Filter based on permissions
    filtered_users = auth.filter_fields(
        data=all_users,
        user_permissions=user_info['permissions'],
        resource='users',
        action='read'
    )
    
    return {"users": filtered_users}
```

### Manual Permission Checks

For specific operations, check permissions manually:

```python
@app.put("/users/{user_id}/salary")
async def update_salary(
    user_id: str,
    new_salary: float,
    authorization: Optional[str] = Header(None)
):
    user_info = auth.validate_token(authorization)
    
    # Check specific permission
    if not auth.check_permission(user_info, "users.write.salary"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Update salary
    update_user_salary(user_id, new_salary)
    return {"status": "success"}
```

### Permission Decorators

Use decorators for cleaner code:

```python
@app.get("/users/{user_id}/ssn")
@auth.require_permission("users.read.ssn")
async def get_user_ssn(
    user_id: str,
    user_info: dict = Depends(auth.get_current_user)
):
    return {"ssn": get_user_ssn_from_db(user_id)}
```

## Testing Your Integration

### 1. Test Discovery

```bash
# Should work without authentication
curl https://your-app/discovery/endpoints?version=2.0
```

### 2. Register App with CIDS

1. Go to CIDS admin interface
2. Register your app
3. Run discovery to import field metadata
4. Create roles with specific field permissions

### 3. Test Authentication

```bash
# Get token from CIDS
TOKEN="your-token-here"

# Test protected endpoint
curl -H "Authorization: Bearer $TOKEN" https://your-app/users
```

### 4. Verify Field Filtering

Compare responses with different permission sets:
- User with `users.read.*`: Should see all fields
- User with only `users.read.name`: Should only see name field
- User with no permissions: Should see empty objects

## Production Checklist

- [ ] **Environment Variables**: All CIDS configuration set
- [ ] **SSL/TLS**: Valid certificates for production
- [ ] **Discovery Endpoint**: Accessible to CIDS without authentication
- [ ] **Error Handling**: Proper error responses for auth failures
- [ ] **Logging**: Authentication events logged for audit
- [ ] **Token Caching**: Public key cached to reduce CIDS calls
- [ ] **Health Checks**: Include CIDS connectivity in health endpoint
- [ ] **Monitoring**: Track authentication failures and permission denials
- [ ] **Documentation**: API docs show required permissions per endpoint

## Troubleshooting

### Common Issues

1. **"No authorization header" error**
   - Ensure client sends: `Authorization: Bearer <token>`
   - Check header name casing

2. **"Invalid token" error**
   - Verify token hasn't expired (10-minute lifetime)
   - Check client_id matches token audience
   - Ensure CIDS public key is accessible

3. **Empty responses (no fields)**
   - User lacks permissions for requested fields
   - Check role assignments in CIDS
   - Verify discovery ran successfully

4. **Discovery not working**
   - Ensure `/discovery/endpoints` is not authenticated
   - Check discovery version (2.0 for field-level)
   - Verify response matches schema

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In your auth initialization
auth = CIDSAuth(
    cids_url="...",
    client_id="...",
    verify_ssl=False  # Only for development!
)
```

### Testing Permissions

Use CIDS token debug endpoint:

```bash
curl -H "Authorization: Bearer $TOKEN" https://cids/auth/whoami
```

This shows all claims including permissions in the token.

## Best Practices

1. **Minimize Permission Requests**: Only request fields you need
2. **Cache Permissions**: Store permission checks for repeated operations
3. **Fail Securely**: Default to denying access on errors
4. **Audit Access**: Log who accessed what sensitive fields
5. **Version Your API**: Plan for permission structure changes
6. **Document Permissions**: Clearly state required permissions in API docs

## Example Applications

See `example_cids_app.py` for a complete working example of a CIDS-compliant application with:
- Field-level discovery
- Automatic field filtering
- Manual permission checks
- Proper error handling

## Support

For issues or questions:
1. Check application logs for detailed errors
2. Verify configuration with CIDS admin
3. Review token contents with debug endpoints
4. Contact CIDS administrator for role/permission issues