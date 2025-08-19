# API Key Authentication Guide for CIDS

## Overview

CIDS now supports API key authentication for service-to-service communication, providing an alternative to OAuth flows for backend services and automation tools.

## Features

- **Secure API Key Generation**: Cryptographically secure random keys with configurable TTL
- **Permission Scoping**: Each key can have specific permissions, subset of app's permissions
- **Key Rotation**: Zero-downtime rotation with grace periods
- **Audit Logging**: Complete audit trail for key creation, usage, rotation, and revocation
- **Expiration Management**: Automatic expiration with configurable time-to-live
- **Usage Tracking**: Track when and how often keys are used

## Architecture

### Storage
API keys are stored in `app_data/app_api_keys.json` with the following structure:
- Keys are hashed using SHA-256 (original key never stored)
- Only key prefix is stored for identification
- Metadata includes permissions, expiry, creation info

### Key Format
- Format: `cids_ak_[32 random alphanumeric characters]`
- Example: `cids_ak_A1b2C3d4E5f6G7h8I9j0K1L2M3N4O5P6`

## Admin UI Usage

### Creating an API Key

1. Navigate to the Admin Panel (`/admin/apps`)
2. Click on the app card you want to create a key for
3. Click the "API Keys" button
4. Fill in the form:
   - **Name**: Descriptive name for the key
   - **Permissions**: Comma-separated list (e.g., `read, write, admin`)
   - **TTL**: Select expiration period
5. Click "Generate API Key"
6. **IMPORTANT**: Copy the key immediately - it won't be shown again!

### Managing API Keys

- **View Keys**: Click "API Keys" on any app card to see all keys
- **Revoke**: Click "Revoke" next to any key to immediately invalidate it
- **Rotate**: Click "Rotate" to generate a replacement key with grace period

## API Endpoints

### Create API Key
```http
POST /auth/admin/apps/{client_id}/api-keys
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Production API Key",
  "permissions": ["read", "write"],
  "ttl_days": 90
}
```

Response:
```json
{
  "api_key": "cids_ak_...",  // Only shown once!
  "metadata": {
    "key_id": "unique_id",
    "key_prefix": "cids_ak_A1b2C3d4",
    "name": "Production API Key",
    "permissions": ["read", "write"],
    "expires_at": "2025-04-01T00:00:00",
    "created_at": "2025-01-01T00:00:00"
  }
}
```

### List API Keys
```http
GET /auth/admin/apps/{client_id}/api-keys
Authorization: Bearer {admin_token}
```

### Revoke API Key
```http
DELETE /auth/admin/apps/{client_id}/api-keys/{key_id}
Authorization: Bearer {admin_token}
```

### Rotate API Key
```http
POST /auth/admin/apps/{client_id}/api-keys/{key_id}/rotate
Authorization: Bearer {admin_token}
```

## Using API Keys for Authentication

### Basic Usage
Include the API key in the Authorization header:
```http
GET /api/protected-resource
Authorization: Bearer cids_ak_...
```

### Python Example
```python
import httpx

api_key = "cids_ak_..."
headers = {"Authorization": f"Bearer {api_key}"}

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.example.com/data",
        headers=headers
    )
```

### FastAPI Integration
The auth middleware automatically supports API keys:
```python
from auth_middleware import AuthMiddleware

auth = AuthMiddleware()

@app.get("/protected")
async def protected_endpoint(
    claims = Depends(auth.validate_token)
):
    # Works with both JWT tokens and API keys
    if claims.get('auth_type') == 'api_key':
        app_id = claims.get('app_client_id')
        permissions = claims.get('permissions', [])
    return {"message": "Authenticated!"}
```

## Security Best Practices

### Key Management
1. **Never commit API keys** to version control
2. **Store keys securely** in environment variables or secret management systems
3. **Use different keys** for different environments (dev, staging, prod)
4. **Rotate keys regularly** - at least every 90 days for production

### Permission Scoping
1. **Principle of least privilege** - only grant necessary permissions
2. **Environment-specific permissions** - dev keys shouldn't have prod access
3. **Service-specific keys** - don't share keys between services

### Rotation Strategy
1. **Schedule regular rotations** - quarterly for production keys
2. **Use grace periods** - allow both old and new keys during transition
3. **Update dependencies** - ensure all services update to new keys
4. **Monitor usage** - track which services still use old keys

### Monitoring
1. **Track key usage** - monitor which keys are actively used
2. **Alert on suspicious activity** - unusual usage patterns
3. **Audit regularly** - review audit logs for unauthorized access
4. **Clean up unused keys** - revoke keys that are no longer needed

## TTL Recommendations

- **Development**: 30 days
- **Testing/CI**: 7-30 days  
- **Staging**: 90 days
- **Production**: 90-365 days
- **Emergency/Temporary**: 1-7 days

## Troubleshooting

### Invalid API Key Error
- Check key hasn't expired
- Verify key hasn't been revoked
- Ensure proper Bearer format in header
- Confirm app is still active

### Permission Denied
- Verify key has required permissions
- Check if permissions were updated after key creation
- Ensure app itself has the permissions

### Key Not Working After Rotation
- Grace period may have expired
- Old key may have been explicitly revoked
- Check audit logs for rotation details

## Migration from Client Credentials

To migrate from client_id/client_secret to API keys:

1. **Generate API key** with same permissions as OAuth flow
2. **Update service** to use API key instead of OAuth
3. **Test thoroughly** in staging environment
4. **Deploy with fallback** - support both auth methods initially
5. **Monitor and validate** - ensure no service disruption
6. **Deprecate OAuth** - once all services migrated

## Audit Log Events

API key operations generate the following audit events:
- `API_KEY_CREATED` - New key generated
- `API_KEY_USED` - Key used for authentication
- `API_KEY_ROTATED` - Key rotation initiated
- `API_KEY_REVOKED` - Key manually revoked
- `API_KEY_EXPIRED` - Key expired (automatic)

## Future Enhancements

Planned improvements for the API key system:
- Rate limiting per API key
- IP allowlisting for keys
- Webhook notifications for key events
- Automatic rotation scheduling
- Key usage analytics dashboard
- Integration with external secret managers