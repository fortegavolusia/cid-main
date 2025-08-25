# CIDS API Registration & Compliance Guide

## Table of Contents
1. [Overview](#overview)
2. [Registration Requirements](#registration-requirements)
3. [Authentication Methods](#authentication-methods)
4. [Discovery Endpoint](#discovery-endpoint)
5. [Permission Model](#permission-model)
6. [Implementation Requirements](#implementation-requirements)
7. [Security Standards](#security-standards)
8. [Testing & Validation](#testing--validation)
9. [API Key Management](#api-key-management)
10. [Compliance Checklist](#compliance-checklist)

## Overview

The Centralized Identity Discovery Service (CIDS) provides unified authentication, authorization, and row-level security (RLS) for enterprise applications. This document outlines the requirements for applications to become CIDS-compliant and integrate with the service.

### Authentication Options

CIDS offers two primary authentication methods:

1. **API Keys (RECOMMENDED for Services)**: 
   - Replaces client_id/client_secret completely
   - Each service gets unique keys with specific permissions
   - No shared secrets to manage
   - Format: `Bearer cids_ak_...`

2. **OAuth 2.0 Flow (Web Applications)**:
   - For user-facing applications
   - Requires client_id and client_secret
   - Supports Azure AD integration

### Key Benefits
- **Centralized Authentication**: Single sign-on via Azure AD
- **Fine-grained Authorization**: Field-level permissions and RLS
- **API Key Management**: Service-to-service authentication without shared secrets
- **Automatic Permission Discovery**: Dynamic endpoint and field detection
- **Token Templates**: Standardized JWT claim structures
- **Audit Logging**: Comprehensive access tracking

## Registration Requirements

### Step 1: Application Registration

Applications must be registered through the CIDS Admin Portal:

1. **Access the Admin Portal**: Navigate to `https://localhost:8000` and login with admin credentials
2. **Go to App Administration**: Click "App Administration" in the sidebar
3. **Register Your Application**: Click "Register New App" and provide:
   - **App Name**: Unique identifier for your application
   - **Description**: Brief description of the application's purpose  
   - **Owner Email**: Contact email for the app owner
   - **Redirect URIs**: OAuth callback URLs (e.g., `http://localhost:8005/callback`)
   - **Discovery Settings**: 
     - Check "Allow Endpoint Discovery"
     - Provide discovery endpoint URL (e.g., `http://localhost:8005/discovery/endpoints`)
   - **Initial API Key** (Optional but recommended):
     - Check "Create Initial API Key"
     - Provide key name (e.g., "Development Key")
     - Set permissions (e.g., "admin" or specific permissions)

4. **Save Credentials**: After registration, you'll receive:
   - **Client ID**: Public identifier for your app (e.g., `app_dd8c554784594b11`)
   - **Client Secret**: Private key for OAuth authentication (only for web apps)
   - **API Key**: Service authentication key (if requested, format: `cids_ak_...`)

### Step 2: Configure Your Application

For applications using OAuth 2.0 (user authentication):
```python
# config.py for web applications
CIDS_CONFIG = {
    "client_id": "your_client_id_here",
    "client_secret": "your_client_secret_here",  # Required for OAuth flow
    "cids_base_url": "http://localhost:8000",
    "redirect_uri": "http://yourapp.com/auth/callback",
    "discovery_enabled": True
}
```

For service-to-service authentication (RECOMMENDED):
```python
# config.py for backend services/APIs
CIDS_CONFIG = {
    "api_key": "cids_ak_...",  # API key replaces client_id/secret
    "cids_base_url": "http://localhost:8000",
    "discovery_enabled": True
}
# API keys eliminate the need for client_secret management
```

## Authentication Methods

CIDS supports three authentication methods:

### 1. OAuth 2.0 Flow (Web Applications)

For user-facing web applications:

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
import httpx
import secrets

app = FastAPI()

@app.get("/login")
async def login(request: Request):
    """Redirect user to CIDS login"""
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    
    login_url = (
        f"{CIDS_CONFIG['cids_base_url']}/auth/login"
        f"?client_id={CIDS_CONFIG['client_id']}"
        f"&app_redirect_uri={CIDS_CONFIG['redirect_uri']}"
        f"&state={state}"
    )
    return RedirectResponse(url=login_url)

@app.get("/auth/callback")
async def auth_callback(
    request: Request,
    access_token: str,
    state: str,
    id_token: str = None
):
    """Handle CIDS callback"""
    # Verify state to prevent CSRF
    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state")
    
    # Validate token with CIDS
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CIDS_CONFIG['cids_base_url']}/auth/validate",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    token_data = response.json()
    request.session["user"] = token_data["user"]
    request.session["access_token"] = access_token
    request.session["permissions"] = token_data.get("permissions", [])
    
    return RedirectResponse(url="/dashboard")
```

### 2. API Key Authentication (Service-to-Service)

For backend services and automated systems (REPLACES client_id/client_secret):

```python
from fastapi import Header, HTTPException, Depends
from typing import Optional
import httpx

async def validate_api_key(
    authorization: Optional[str] = Header(None)
) -> dict:
    """Validate API key directly with CIDS - no client_secret needed!"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    # API keys use Bearer format: "Bearer cids_ak_..."
    if not authorization.startswith("Bearer cids_ak_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")
    
    # Validate directly with CIDS /auth/validate endpoint
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CIDS_CONFIG['cids_base_url']}/auth/validate",
            headers={"Authorization": authorization}
        )
    
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Returns validated app info and permissions
    return response.json()

@app.get("/api/data")
async def get_data(auth_data: dict = Depends(validate_api_key)):
    """Protected endpoint using API key"""
    # auth_data contains:
    # - app_client_id: The app this key belongs to
    # - permissions: List of granted permissions
    # - auth_type: "api_key"
    return {
        "message": "Authenticated via API key",
        "app": auth_data["app_client_id"],
        "permissions": auth_data.get("permissions", [])
    }

# Simple usage in requests
headers = {
    "Authorization": f"Bearer {CIDS_CONFIG['api_key']}",
    "Content-Type": "application/json"
}
```

### 3. Bearer Token (JWT)

For API clients with existing tokens:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Validate JWT token"""
    token = credentials.credentials
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CIDS_CONFIG['cids_base_url']}/auth/validate",
            headers={"Authorization": f"Bearer {token}"}
        )
    
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return response.json()

@app.get("/api/users")
async def get_users(token_data: dict = Depends(validate_token)):
    """Protected endpoint using Bearer token"""
    permissions = token_data.get("permissions", [])
    # Filter data based on permissions
    return {"users": filtered_users}
```

## Discovery Endpoint

### Understanding Discovery Authentication

**IMPORTANT**: Discovery uses a different authentication flow than your app's normal operations:

1. **Discovery is initiated BY CIDS** to learn about your endpoints
2. **CIDS creates a JWT token** specifically for the discovery operation
3. **Your discovery endpoint receives this JWT** (not your API key)
4. **API keys are for YOUR app** to authenticate when calling other services

```
Discovery Flow:
CIDS → [JWT Token] → Your App's Discovery Endpoint
     (CIDS proves its identity to your app)

Your App Using API Key:
Your App → [API Key] → Other Protected Service
     (Your app proves its identity to other services)
```

**Key Points:**
- Discovery endpoints should generally be **publicly accessible**
- If you validate authentication, accept **JWT tokens from CIDS**
- **Never** expect CIDS to send your app's API key for discovery
- Your API key is for **outbound** requests, not **inbound** discovery

### Implementation Requirements

Every CIDS-compliant application MUST implement a discovery endpoint that provides complete metadata about available endpoints and fields:

```python
from typing import List, Dict, Any
from pydantic import BaseModel

class FieldMetadata(BaseModel):
    type: str
    description: str
    required: bool = False
    sensitive: bool = False
    pii: bool = False
    phi: bool = False
    financial: bool = False

class EndpointMetadata(BaseModel):
    method: str
    path: str
    operation_id: str
    description: str
    resource: str  # Resource category (e.g., "users", "orders")
    action: str    # Action type (e.g., "read", "write", "delete")
    response_fields: Dict[str, FieldMetadata]
    request_fields: Optional[Dict[str, FieldMetadata]] = None
    parameters: Optional[List[Dict[str, Any]]] = None

@app.get("/discovery/endpoints")
async def discover_endpoints(
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    Endpoint discovery for CIDS
    
    IMPORTANT: This endpoint should accept BOTH:
    - JWT tokens from CIDS (service-to-service discovery)
    - API keys from external services (if needed)
    - Or be publicly accessible (recommended)
    """
    
    # Optional: Log authentication type for debugging
    if authorization:
        if authorization.startswith("Bearer cids_ak_"):
            # API key from external service
            logger.info("Discovery called with API key")
        elif authorization.startswith("Bearer ey"):
            # JWT token from CIDS service
            logger.info("Discovery called with JWT token from CIDS")
    
    return {
        "version": "2.0",
        "app_id": "your_app_id",
        "app_name": "Your Application Name",  # REQUIRED: Must be "app_name" not "service_name"
        "description": "Application description",
        "base_url": "https://yourapp.com",
        "last_updated": datetime.utcnow().isoformat(),  # Use last_updated instead of discovery_timestamp
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/users/{user_id}",
                "operation_id": "get_user",
                "description": "Retrieve user information",
                "resource": "users",
                "action": "read",
                "parameters": [
                    {
                        "name": "user_id",
                        "in": "path",
                        "type": "string",
                        "required": True,
                        "description": "User identifier"
                    }
                ],
                "response_fields": {
                    "id": {
                        "type": "string",
                        "description": "User ID",
                        "required": True
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address",
                        "required": True,
                        "pii": True
                    },
                    "name": {
                        "type": "string",
                        "description": "Full name",
                        "pii": True
                    },
                    "salary": {
                        "type": "number",
                        "description": "Annual salary",
                        "sensitive": True,
                        "financial": True
                    },
                    "ssn": {
                        "type": "string",
                        "description": "Social Security Number",
                        "sensitive": True,
                        "pii": True
                    },
                    "medical_records": {
                        "type": "object",
                        "description": "Medical history",
                        "sensitive": True,
                        "phi": True
                    },
                    "department": {
                        "type": "object",
                        "description": "Department information",
                        "fields": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "budget": {
                                "type": "number",
                                "sensitive": True,
                                "financial": True
                            }
                        }
                    }
                }
            },
            {
                "method": "POST",
                "path": "/api/users",
                "operation_id": "create_user",
                "description": "Create new user",
                "resource": "users",
                "action": "write",
                "request_fields": {
                    "email": {
                        "type": "string",
                        "required": True,
                        "pii": True
                    },
                    "name": {
                        "type": "string",
                        "required": True,
                        "pii": True
                    },
                    "department_id": {
                        "type": "string",
                        "required": True
                    }
                },
                "response_fields": {
                    "id": {"type": "string"},
                    "created_at": {"type": "datetime"}
                }
            }
        ]
    }
```

### Field Metadata Tags

- **sensitive**: General sensitive data flag
- **pii**: Personally Identifiable Information
- **phi**: Protected Health Information (HIPAA)
- **financial**: Financial data (PCI DSS, SOX)

## Permission Model

### Permission Structure

Permissions follow a hierarchical structure:

```
{app_id}.{resource}.{action}[.{field}]
```

Examples:
- `hr_system.users.read` - Can read user resources
- `hr_system.users.read.email` - Can read email field
- `hr_system.users.write.salary` - Can update salary field
- `hr_system.users.delete` - Can delete users

### Implementing Permission Checks

```python
from typing import Dict, List, Any

class PermissionManager:
    @staticmethod
    def has_permission(
        permissions: List[str],
        resource: str,
        action: str,
        field: str = None
    ) -> bool:
        """Check if user has required permission"""
        if field:
            # Check field-specific permission
            specific = f"{resource}.{action}.{field}"
            if specific in permissions:
                return True
            
            # Check wildcard permission
            wildcard = f"{resource}.{action}.*"
            if wildcard in permissions:
                return True
        
        # Check resource-level permission
        resource_perm = f"{resource}.{action}"
        return resource_perm in permissions
    
    @staticmethod
    def filter_fields(
        data: Dict[str, Any],
        permissions: List[str],
        resource: str,
        action: str = "read"
    ) -> Dict[str, Any]:
        """Filter response fields based on permissions"""
        filtered = {}
        
        for field, value in data.items():
            if PermissionManager.has_permission(
                permissions, resource, action, field
            ):
                if isinstance(value, dict):
                    # Recursively filter nested objects
                    filtered[field] = PermissionManager.filter_fields(
                        value, permissions, f"{resource}.{field}", action
                    )
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    # Filter list of objects
                    filtered[field] = [
                        PermissionManager.filter_fields(
                            item, permissions, f"{resource}.{field}", action
                        )
                        for item in value
                    ]
                else:
                    filtered[field] = value
        
        return filtered

# Usage in endpoint
@app.get("/api/users/{user_id}")
async def get_user(
    user_id: str,
    token_data: dict = Depends(validate_token)
):
    # Get user from database
    user = await db.get_user(user_id)
    
    # Apply field-level filtering
    filtered_user = PermissionManager.filter_fields(
        user.dict(),
        token_data["permissions"],
        "users",
        "read"
    )
    
    # Apply RLS filters if present
    if "rls_filters" in token_data:
        filtered_user = apply_rls_filters(
            filtered_user,
            token_data["rls_filters"],
            token_data["user"]
        )
    
    return filtered_user
```

## Implementation Requirements

### 1. Row-Level Security (RLS)

Implement SQL WHERE clause filtering based on token claims:

```python
from typing import Dict, Any
import re

class RLSManager:
    @staticmethod
    def apply_rls_filter(
        query: str,
        rls_filters: List[Dict[str, str]],
        context: Dict[str, Any]
    ) -> str:
        """Apply RLS filters to SQL query"""
        where_clauses = []
        
        for filter_rule in rls_filters:
            if filter_rule["resource"] == "users" and filter_rule["action"] == "read":
                # Replace context variables
                sql_filter = filter_rule["expression"]
                for key, value in context.items():
                    placeholder = f"@{key}"
                    if placeholder in sql_filter:
                        # Safely escape and quote value
                        safe_value = f"'{value}'" if isinstance(value, str) else str(value)
                        sql_filter = sql_filter.replace(placeholder, safe_value)
                
                where_clauses.append(f"({sql_filter})")
        
        if where_clauses:
            where_condition = " AND ".join(where_clauses)
            if "WHERE" in query.upper():
                query += f" AND ({where_condition})"
            else:
                query += f" WHERE ({where_condition})"
        
        return query

# Context variables available for RLS:
# @current_user_id - Current user's ID
# @current_user_email - Current user's email
# @current_user_department - User's department
# @current_user_role - User's role in the app
# @current_timestamp - Current UTC timestamp
```

### 2. Audit Logging

Implement comprehensive audit logging:

```python
import logging
from datetime import datetime
from typing import Optional

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger("audit")
    
    def log_access(
        self,
        user_id: str,
        user_email: str,
        resource: str,
        action: str,
        resource_id: Optional[str] = None,
        granted: bool = True,
        reason: Optional[str] = None
    ):
        """Log access attempt"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "user_email": user_email,
            "resource": resource,
            "action": action,
            "resource_id": resource_id,
            "granted": granted,
            "reason": reason
        }
        
        if granted:
            self.logger.info(f"ACCESS_GRANTED: {log_entry}")
        else:
            self.logger.warning(f"ACCESS_DENIED: {log_entry}")
    
    def log_data_access(
        self,
        user_id: str,
        resource: str,
        fields_accessed: List[str],
        fields_denied: List[str] = None
    ):
        """Log field-level data access"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "resource": resource,
            "fields_accessed": fields_accessed,
            "fields_denied": fields_denied or []
        }
        self.logger.info(f"DATA_ACCESS: {log_entry}")

audit = AuditLogger()
```

### 3. Token Refresh

Implement automatic token refresh:

```python
from datetime import datetime, timedelta
import jwt

class TokenManager:
    @staticmethod
    async def refresh_token_if_needed(
        token: str,
        refresh_threshold_minutes: int = 5
    ) -> str:
        """Refresh token if close to expiry"""
        try:
            # Decode without verification to check expiry
            payload = jwt.decode(token, options={"verify_signature": False})
            exp = datetime.fromtimestamp(payload["exp"])
            
            if datetime.utcnow() + timedelta(minutes=refresh_threshold_minutes) > exp:
                # Token expires soon, refresh it
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{CIDS_CONFIG['cids_base_url']}/auth/refresh",
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    
                if response.status_code == 200:
                    return response.json()["access_token"]
        except:
            pass
        
        return token
```

## Security Standards

### Required Security Measures

1. **HTTPS Only**
   - All endpoints must use TLS 1.2 or higher
   - HTTP Strict Transport Security (HSTS) headers

2. **Token Security**
   ```python
   # Never log tokens
   logger.info(f"User authenticated: {user_id}")  # Good
   logger.info(f"Token: {token}")  # BAD - Never do this!
   
   # Store tokens securely
   # Use httpOnly, secure cookies for web apps
   # Use secure key storage for API keys
   ```

3. **Input Validation**
   ```python
   from pydantic import BaseModel, validator
   
   class UserInput(BaseModel):
       email: str
       name: str
       
       @validator('email')
       def validate_email(cls, v):
           # Validate email format
           if '@' not in v:
               raise ValueError('Invalid email')
           return v
   ```

4. **Rate Limiting**
   ```python
   from fastapi_limiter import FastAPILimiter
   from fastapi_limiter.depends import RateLimiter
   
   @app.get("/api/users", dependencies=[Depends(RateLimiter(times=100, seconds=60))])
   async def get_users():
       # Rate limited to 100 requests per minute
       pass
   ```

5. **CORS Configuration**
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://cids.yourcompany.com"],
       allow_credentials=True,
       allow_methods=["GET", "POST"],
       allow_headers=["Authorization", "Content-Type"],
   )
   ```

## Testing & Validation

### 1. Discovery Endpoint Test

```bash
# Test discovery endpoint
curl -X GET https://yourapp.com/discovery/endpoints \
  -H "Authorization: Bearer ${CIDS_TOKEN}"
```

### 2. Permission Testing

```python
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_field_filtering():
    """Test that sensitive fields are filtered correctly"""
    
    # Mock user with limited permissions
    mock_token = {
        "permissions": ["users.read.id", "users.read.name"],
        "user": {"id": "test123", "email": "test@example.com"}
    }
    
    # Full user data
    user_data = {
        "id": "user456",
        "name": "John Doe",
        "email": "john@example.com",
        "salary": 100000,
        "ssn": "123-45-6789"
    }
    
    # Apply filtering
    filtered = PermissionManager.filter_fields(
        user_data,
        mock_token["permissions"],
        "users",
        "read"
    )
    
    # Verify only permitted fields are present
    assert "id" in filtered
    assert "name" in filtered
    assert "email" not in filtered  # No permission
    assert "salary" not in filtered  # No permission
    assert "ssn" not in filtered  # No permission
```

### 3. Integration Test

```python
import httpx
import asyncio

async def test_cids_integration():
    """Full integration test with CIDS"""
    
    async with httpx.AsyncClient() as client:
        # 1. Get token from CIDS
        token_response = await client.post(
            f"{CIDS_URL}/auth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            }
        )
        token = token_response.json()["access_token"]
        
        # 2. Test protected endpoint
        api_response = await client.get(
            "https://yourapp.com/api/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert api_response.status_code == 200
        
        # 3. Verify discovery endpoint
        discovery_response = await client.get(
            "https://yourapp.com/discovery/endpoints"
        )
        
        assert discovery_response.status_code == 200
        assert "endpoints" in discovery_response.json()

asyncio.run(test_cids_integration())
```

## API Key Management

### Why Use API Keys Instead of Client Secret?

API keys provide several advantages over traditional client_id/client_secret:

1. **No Shared Secrets**: Each service gets its own unique key
2. **Granular Permissions**: Each key can have specific permissions
3. **Easy Rotation**: Rotate individual keys without affecting others
4. **Better Security**: Keys are hashed, not stored in plain text
5. **Usage Tracking**: Monitor which key is making requests
6. **Multiple Keys**: One app can have multiple keys for different services

### Generating API Keys

API keys are managed through the CIDS Admin Portal:

1. Navigate to App Administration
2. Click "API Keys" for your application
3. Generate new key with:
   - **Name**: Descriptive name (e.g., "Production Server", "CI/CD Pipeline")
   - **Permissions**: Comma-separated list (e.g., "read:users, write:logs, admin")
   - **TTL**: Expiration period (30 days to 10 years)

**IMPORTANT**: The API key is shown only once when generated. Save it securely!

### Using API Keys

```python
# Environment variable (recommended)
# .env file
CIDS_API_KEY="cids_ak_..."  # This replaces client_id AND client_secret!

# In your application
import os
API_KEY = os.getenv("CIDS_API_KEY")

# Make authenticated request - no client_secret needed!
headers = {
    "Authorization": f"Bearer {API_KEY}",  # Note: Bearer format
    "Content-Type": "application/json"
}

# Direct API call
response = requests.get(
    "https://api.yourservice.com/data",
    headers=headers
)

# Or validate with CIDS
validation_response = requests.get(
    f"{CIDS_BASE_URL}/auth/validate",
    headers={"Authorization": f"Bearer {API_KEY}"}
)
```

### API Key Rotation

Best practices for key rotation:

1. **Schedule Regular Rotation**: Every 90 days for production keys
2. **Use Grace Period**: 24-hour overlap when rotating
3. **Automate Rotation**: Use CIDS rotation API
4. **Monitor Usage**: Track last used timestamps

```python
# Automated rotation script
async def rotate_api_keys():
    """Rotate API keys approaching expiry"""
    
    # Get current keys
    keys = await get_api_keys(CLIENT_ID)
    
    for key in keys:
        days_until_expiry = (key.expires_at - datetime.now()).days
        
        if days_until_expiry < 7:
            # Rotate key with 24-hour grace period
            new_key = await rotate_api_key(
                CLIENT_ID,
                key.key_id,
                grace_period_hours=24
            )
            
            # Update application configuration
            update_config(new_key.api_key)
            
            # Notify administrators
            send_notification(f"API key {key.name} rotated")
```

## Compliance Checklist

### Pre-Registration
- [ ] Application architecture documented
- [ ] Authentication method chosen (OAuth/API Key/Both)
- [ ] Redirect URIs identified (for OAuth)
- [ ] Discovery endpoint URL determined

### Registration
- [ ] Application registered in CIDS Admin Portal
- [ ] Client ID and Secret stored securely
- [ ] API keys generated (if needed)
- [ ] Discovery enabled in registration

### Implementation
- [ ] Discovery endpoint implemented at `/discovery/endpoints`
- [ ] All endpoints documented in discovery response
- [ ] Field metadata includes sensitivity flags (PII, PHI, etc.)
- [ ] Token validation implemented
- [ ] Permission checking logic implemented
- [ ] Field-level filtering active
- [ ] RLS filters applied when present
- [ ] Audit logging configured
- [ ] Token refresh mechanism in place

### Security
- [ ] HTTPS enforced on all endpoints
- [ ] Tokens never logged or exposed
- [ ] Input validation on all endpoints
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Security headers implemented

### Testing
- [ ] Discovery endpoint returns valid JSON
- [ ] Permissions correctly filter responses
- [ ] Token expiry handled gracefully
- [ ] API key authentication works
- [ ] Audit logs generated correctly
- [ ] Load testing completed

### Documentation
- [ ] API documentation updated
- [ ] Permission matrix documented
- [ ] Emergency procedures documented
- [ ] Rotation schedule established

## Troubleshooting

### Common Issues

1. **Discovery Endpoint Not Found**
   - Verify endpoint is at exact path registered
   - Check that endpoint is publicly accessible to CIDS
   - Ensure URL protocol matches (http vs https)

2. **Discovery Fails with 401 Unauthorized**
   - Discovery endpoint should NOT require authentication from CIDS
   - CIDS sends JWT tokens for discovery, not API keys
   - Make endpoint public or accept JWT tokens from CIDS

3. **Discovery Validation Error**
   - Ensure response has `app_name` field (NOT `service_name`)
   - Use `last_updated` instead of `discovery_timestamp`
   - All required fields must be present per DiscoveryResponse model

4. **Token Validation Fails**
   - Ensure token hasn't expired
   - Verify CIDS_BASE_URL is correct (use https://localhost:8000 for local)
   - Check network connectivity to CIDS

5. **Permissions Not Working**
   - Verify permission format matches pattern: `app_id.resource.action[.field]`
   - Check discovery endpoint returns correct resource/action
   - Ensure token contains expected permissions

6. **API Key Rejected**
   - Verify key hasn't expired
   - Check key is active (not revoked)
   - Ensure correct Authorization header format: `Bearer cids_ak_...`
   - API keys are for YOUR app to call OTHER services, not for discovery

## Support & Resources

- **CIDS Admin Portal**: `https://cids.yourcompany.com/admin`
- **API Documentation**: `https://cids.yourcompany.com/docs`
- **Example Applications**: See `/test_apps` directory
- **Support Email**: cids-support@yourcompany.com
- **GitHub Issues**: File at CIDS repository

## Key Lessons Learned

### API Key vs JWT Token Usage

1. **API Keys** (`cids_ak_...`):
   - Generated during app registration or via Admin Portal
   - Used by YOUR app to authenticate TO other services
   - Replaces client_secret for service-to-service authentication
   - Has specific permissions attached
   - Never shared with CIDS for discovery

2. **JWT Tokens**:
   - Created by CIDS for service-to-service operations
   - Used by CIDS when discovering YOUR app
   - Short-lived (5 minutes for discovery)
   - Signed with CIDS's private RSA key
   - Contains service metadata

### Discovery Best Practices

1. **Make discovery endpoints public** or accept JWT tokens
2. **Use correct field names**: `app_name` not `service_name`
3. **Include all required fields** per DiscoveryResponse model
4. **Test with actual CIDS discovery** not just curl
5. **Check logs** for authentication type received

### Common Pitfalls to Avoid

1. **Don't expect API keys for discovery** - CIDS uses JWT tokens
2. **Don't confuse authentication directions** - API keys are for outbound
3. **Don't hardcode URLs** - Use configuration for flexibility
4. **Don't skip field metadata** - It's crucial for permissions
5. **Don't forget sensitivity flags** - Mark PII, PHI, financial data

## Version History

- **v2.1** (Current): Clarified JWT vs API key usage, fixed discovery auth
- **v2.0**: Field-level permissions, RLS support, API keys
- **v1.0**: Basic authentication and resource-level permissions