# App Registration Guide

This guide explains how to register and manage applications that will use the centralized authentication service.

## Overview

The app registration system allows internal applications to integrate with the centralized auth service. Each registered app receives:
- A unique `client_id` for identification
- A `client_secret` for secure authentication
- Configuration for allowed redirect URIs
- Role mappings between AD groups and app-specific roles

## Admin Interface

### Accessing the Admin UI

1. Navigate to https://localhost:8000/auth/admin/apps-ui
2. Log in with an admin account
3. You'll see the app management interface

### Registering a New App

1. Fill out the registration form:
   - **App Name**: A friendly name for your application
   - **Description**: What the app does
   - **Owner Email**: Contact email for the app owner
   - **Redirect URIs**: URLs where users will be redirected after authentication

2. Click "Register App"
3. **Important**: Save the client_id and client_secret immediately - the secret won't be shown again!

## API Endpoints

### Register an App (Admin Only)
```bash
POST /auth/admin/apps
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "My Application",
  "description": "Internal app for managing projects",
  "owner_email": "owner@company.com",
  "redirect_uris": [
    "https://myapp.company.com/auth/callback",
    "http://localhost:3000/auth/callback"
  ]
}
```

Response:
```json
{
  "app": {
    "client_id": "app_a1b2c3d4e5f6",
    "name": "My Application",
    "description": "Internal app for managing projects",
    "redirect_uris": ["https://myapp.company.com/auth/callback"],
    "owner_email": "owner@company.com",
    "is_active": true,
    "created_at": "2024-01-07T10:30:00Z",
    "updated_at": "2024-01-07T10:30:00Z"
  },
  "client_secret": "your_secret_here"
}
```

### List All Apps (Admin Only)
```bash
GET /auth/admin/apps
Authorization: Bearer {admin_token}
```

### Get App Details (Admin Only)
```bash
GET /auth/admin/apps/{client_id}
Authorization: Bearer {admin_token}
```

### Update App (Admin Only)
```bash
PUT /auth/admin/apps/{client_id}
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Updated App Name",
  "redirect_uris": ["https://newurl.company.com/callback"]
}
```

### Rotate Client Secret (Admin Only)
```bash
POST /auth/admin/apps/{client_id}/rotate-secret
Authorization: Bearer {admin_token}
```

### Delete (Deactivate) App (Admin Only)
```bash
DELETE /auth/admin/apps/{client_id}
Authorization: Bearer {admin_token}
```

## Role Mapping

### Set Role Mappings (Admin Only)
Map Azure AD groups to app-specific roles:

```bash
POST /auth/admin/apps/{client_id}/role-mappings
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "mappings": {
    "Engineering": "editor",
    "MyApp-Admins": "admin",
    "All Users": "viewer"
  }
}
```

### Get Role Mappings (Admin Only)
```bash
GET /auth/admin/apps/{client_id}/role-mappings
Authorization: Bearer {admin_token}
```

## Integration Guide for Apps

### 1. Authentication Flow

Apps should redirect users to the auth service for login:

```
https://localhost:8000/auth/login?client_id={your_client_id}&redirect_uri={your_redirect_uri}
```

### 2. Token Structure

After successful authentication, the user's token will include app-specific roles:

```json
{
  "sub": "user-123",
  "email": "user@company.com",
  "name": "John Doe",
  "groups": ["Engineering", "MyApp-Admins"],
  "client_id": "app_a1b2c3d4e5f6",
  "app_roles": ["editor", "admin"],
  "exp": 1704630000,
  "iat": 1704626400
}
```

### 3. Validating Tokens

Apps can validate tokens using:

```bash
POST /auth/validate
Content-Type: application/json

{
  "token": "eyJ0eXAiOiJKV1Q..."
}
```

Or by using the public key endpoint:
```bash
GET /auth/public-key
```

## Security Considerations

1. **Client Secret Storage**: Store client secrets securely (environment variables, secrets management system)
2. **HTTPS Only**: Always use HTTPS in production
3. **Redirect URI Validation**: Only exact matches are allowed for security
4. **Token Validation**: Always validate tokens on each request
5. **Regular Secret Rotation**: Rotate client secrets periodically

## Example Client Implementation

```python
import requests
from functools import wraps

class AuthClient:
    def __init__(self, client_id, client_secret, auth_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = auth_url
    
    def get_login_url(self, redirect_uri):
        return f"{self.auth_url}/auth/login?client_id={self.client_id}&redirect_uri={redirect_uri}"
    
    def validate_token(self, token):
        response = requests.post(
            f"{self.auth_url}/auth/validate",
            json={"token": token}
        )
        return response.json() if response.ok else None

# Usage in Flask/FastAPI
auth = AuthClient("app_123", "secret", "https://auth.company.com")

def require_auth(required_role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            user_info = auth.validate_token(token)
            
            if not user_info or not user_info.get('valid'):
                return jsonify({'error': 'Unauthorized'}), 401
            
            if required_role and required_role not in user_info.get('app_roles', []):
                return jsonify({'error': 'Forbidden'}), 403
            
            return f(user_info=user_info, *args, **kwargs)
        return decorated_function
    return decorator

@app.route('/api/admin/users')
@require_auth(required_role='admin')
def admin_users(user_info):
    return jsonify({'message': f'Hello admin {user_info["email"]}'})
```

## Next Steps

1. Register your app using the admin UI
2. Update your app to redirect to the auth service for login
3. Implement token validation in your app
4. Set up role mappings for your AD groups
5. Test the integration thoroughly