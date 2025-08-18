# FastAPI CIDS Integration Guide

This guide walks you through registering a FastAPI application with CIDS (Central Identity Service) and implementing authentication with field-level permissions.

## Overview

The FastAPI test app demonstrates:
- OAuth 2.0 authentication flow through CIDS
- Field-level permission enforcement
- Discovery endpoint for automatic permission generation
- Token validation and user session management

## Architecture

```
User → FastAPI App → CIDS → Azure AD
         ↓             ↓
    Product API    JWT Tokens
         ↓             ↓
  Filtered Data   Permissions
```

## Step 1: Prerequisites

Install required dependencies:

```bash
pip install fastapi uvicorn httpx python-jose[cryptography] python-dotenv jinja2
```

## Step 2: Register Your App with CIDS

### Option A: Using the Registration Script

Run the provided registration script:

```bash
python register_fastapi_app.py
```

This will:
1. Register your app with CIDS
2. Generate a `client_id` and `client_secret`
3. Save credentials to `.env` file
4. Set up initial role mappings

### Option B: Manual Registration via API

```python
import requests

# Register app with CIDS
response = requests.post(
    "http://localhost:8000/auth/admin/apps",
    json={
        "name": "FastAPI Test App",
        "description": "FastAPI with field-level permissions",
        "redirect_uris": [
            "http://localhost:5001/auth/callback"
        ],
        "owner_email": "admin@company.com",
        "discovery_endpoint": "http://localhost:5001/discovery/endpoints",
        "allow_discovery": True
    },
    headers={
        "Authorization": "Bearer <admin_token>"
    }
)

result = response.json()
print(f"Client ID: {result['client_id']}")
print(f"Client Secret: {result['client_secret']}")
```

## Step 3: Configure Your FastAPI App

Create a `.env` file with your credentials:

```env
# CIDS Credentials
FASTAPI_CLIENT_ID=app_xxxxxxxxxxxxx
FASTAPI_CLIENT_SECRET=your_secret_here

# URLs
CIDS_URL=http://localhost:8000
APP_URL=http://localhost:5001
```

## Step 4: Implement Discovery Endpoint

The discovery endpoint tells CIDS about your app's fields and their sensitivity:

```python
@app.get("/discovery/endpoints")
async def discover_endpoints(version: str = "2.0"):
    """
    NO AUTHENTICATION REQUIRED - CIDS needs access to discover fields
    """
    return {
        "version": "2.0",
        "app_name": "FastAPI Test App",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/products",
                "operation_id": "list_products",
                "response_fields": {
                    "id": {"type": "string", "required": True},
                    "name": {"type": "string", "required": True},
                    "price": {"type": "number", "required": True},
                    "cost": {
                        "type": "number",
                        "sensitive": True,  # Mark sensitive fields
                        "required": True
                    },
                    "supplier": {
                        "type": "string",
                        "sensitive": True
                    }
                }
            }
        ]
    }
```

## Step 5: Implement Authentication Flow

### 5.1 Login Redirect

```python
@app.get("/login")
async def login():
    redirect_uri = f"{APP_URL}/auth/callback"
    auth_url = f"{CIDS_URL}/auth/authorize?client_id={CLIENT_ID}&redirect_uri={redirect_uri}"
    return RedirectResponse(url=auth_url)
```

### 5.2 Handle OAuth Callback

```python
@app.get("/auth/callback")
async def auth_callback(code: str):
    # Exchange authorization code for token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CIDS_URL}/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": f"{APP_URL}/auth/callback"
            }
        )
    
    token_data = response.json()
    access_token = token_data['access_token']
    
    # Store in session and redirect to dashboard
    # ... session management code ...
```

## Step 6: Validate Tokens and Check Permissions

### 6.1 Token Validation

```python
async def validate_cids_token(authorization: str) -> Dict:
    """Validate token with CIDS"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CIDS_URL}/auth/validate",
            json={
                "token": authorization.replace("Bearer ", ""),
                "client_id": CLIENT_ID
            }
        )
    
    result = response.json()
    if not result.get('valid'):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return result.get('claims', {})
```

### 6.2 Field-Level Permission Filtering

```python
def filter_by_permissions(data: Dict, permissions: List[str], resource: str) -> Dict:
    """Filter response based on field permissions"""
    
    # Check for wildcard permission
    if f"{CLIENT_ID}:{resource}:read:*" in permissions:
        return data  # Full access
    
    # Filter specific fields
    filtered = {}
    for field, value in data.items():
        field_perm = f"{CLIENT_ID}:{resource}:read:{field}"
        if field_perm in permissions or field not in SENSITIVE_FIELDS:
            filtered[field] = value
    
    return filtered
```

## Step 7: Protected API Endpoints

```python
@app.get("/api/products")
async def get_products(authorization: Optional[str] = Header(None)):
    # Validate token
    user_info = await validate_cids_token(authorization)
    
    # Get permissions
    permissions = user_info.get('permissions', {}).get(CLIENT_ID, [])
    
    # Filter data based on permissions
    products = []
    for product in PRODUCTS.values():
        filtered = filter_by_permissions(product, permissions, "products")
        products.append(filtered)
    
    return {"products": products}
```

## Step 8: Configure Permissions in CIDS

### 8.1 Run Discovery

In the CIDS admin panel:
1. Navigate to "Registered Apps"
2. Find your FastAPI app
3. Click "Run Discovery"
4. CIDS will fetch your field metadata

### 8.2 Create Permission Roles

Create roles with specific field access:

```javascript
// Example: Finance Role
{
    "role_name": "finance_user",
    "permissions": [
        "app_xxx:products:read:*",  // All product fields
        "app_xxx:products:write:cost",  // Can update costs
        "app_xxx:products:write:price"  // Can update prices
    ]
}

// Example: Viewer Role
{
    "role_name": "viewer",
    "permissions": [
        "app_xxx:products:read:id",
        "app_xxx:products:read:name",
        "app_xxx:products:read:price"
        // No access to cost, supplier, profit_margin
    ]
}
```

### 8.3 Map AD Groups to Roles

In CIDS admin:
1. Go to your app's "Role Mappings"
2. Map Azure AD groups to app roles:
   - "Finance Team" → "finance_user"
   - "All Users" → "viewer"
   - "Administrators" → "admin"

## Step 9: Start and Test

### Start the FastAPI App

```bash
uvicorn fastapi_test_app:app --reload --port 5001
```

### Test the Flow

1. Open http://localhost:5001
2. Click "Login with CIDS"
3. Authenticate with Azure AD
4. View dashboard with filtered data based on your permissions

### Test API Directly

```bash
# Get token first (via UI login)
TOKEN="your_access_token"

# Test product listing
curl -H "Authorization: Bearer $TOKEN" http://localhost:5001/api/products

# Response will be filtered based on your permissions
```

## Permission Examples

### User with Basic Viewer Role
```json
{
    "products": [
        {
            "id": "prod001",
            "name": "Laptop Pro X1",
            "price": 1299.99
            // cost, supplier, profit_margin are hidden
        }
    ]
}
```

### User with Finance Role
```json
{
    "products": [
        {
            "id": "prod001",
            "name": "Laptop Pro X1",
            "price": 1299.99,
            "cost": 850.00,
            "profit_margin": 34.6
            // supplier still hidden if not permitted
        }
    ]
}
```

### User with Admin Role
```json
{
    "products": [
        {
            "id": "prod001",
            "name": "Laptop Pro X1",
            "price": 1299.99,
            "cost": 850.00,
            "supplier": "TechCorp Industries",
            "profit_margin": 34.6
            // All fields visible
        }
    ]
}
```

## Troubleshooting

### Discovery Not Working

1. Ensure discovery endpoint is accessible without authentication
2. Check the discovery_endpoint URL in app registration
3. Verify the app is running when discovery is triggered
4. Check logs for connection errors

### Token Validation Failing

1. Verify CIDS_URL is correct
2. Check client_id and client_secret match
3. Ensure token hasn't expired (30 min default)
4. Check CIDS logs for validation errors

### Permissions Not Applied

1. Run discovery first to generate permissions
2. Create permission roles in CIDS admin
3. Map AD groups to roles
4. Check token claims include expected permissions
5. Verify permission format: `client_id:resource:action:field`

## Security Best Practices

1. **Always use HTTPS in production**
2. **Never expose client_secret in frontend code**
3. **Implement proper session management**
4. **Use secure cookie settings (HttpOnly, Secure, SameSite)**
5. **Validate all tokens on every API request**
6. **Log authentication events for audit**
7. **Implement rate limiting on auth endpoints**
8. **Rotate client secrets periodically**

## Advanced Features

### Custom Permission Checks

```python
def require_permission(permission: str):
    """Decorator for permission-based access control"""
    def decorator(func):
        async def wrapper(*args, authorization: str = Header(None), **kwargs):
            user_info = await validate_cids_token(authorization)
            permissions = user_info.get('permissions', {}).get(CLIENT_ID, [])
            
            if permission not in permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            return await func(*args, **kwargs, user_info=user_info)
        return wrapper
    return decorator

@app.post("/api/products")
@require_permission(f"{CLIENT_ID}:products:create:*")
async def create_product(product: Product, user_info: dict):
    # Only users with create permission can access
    pass
```

### Caching Public Keys

```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1)
def get_cids_public_key(cache_time: int = 0):
    """Cache CIDS public key for 1 hour"""
    response = requests.get(f"{CIDS_URL}/auth/public-key")
    return response.json()

# Invalidate cache every hour
def get_public_key():
    cache_time = int(datetime.now().timestamp() // 3600)
    return get_cids_public_key(cache_time)
```

## Next Steps

1. Implement refresh token handling
2. Add comprehensive error handling
3. Implement audit logging
4. Add rate limiting
5. Set up monitoring and alerts
6. Deploy with proper TLS/SSL
7. Implement token blacklisting for revocation
8. Add multi-tenancy support if needed

## Support

For issues or questions:
- Check CIDS logs: `/auth/admin/audit`
- Review app registration: `/auth/admin/apps`
- Test token validation: `/auth/validate`
- View discovered permissions: `/discovery/v2/permissions/{client_id}`