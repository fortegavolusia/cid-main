# Admin Token Management Endpoints

This document describes the admin token management endpoints added to the authentication service.

## Configuration

To enable admin access, set the following environment variables in your `.env` file:

```bash
# Comma-separated list of admin email addresses
ADMIN_EMAILS=admin@example.com,john.doe@company.com

# Comma-separated list of Azure AD group IDs that have admin access (optional)
ADMIN_GROUP_IDS=group-id-1,group-id-2
```

## Endpoints

### 1. View Your Own Token - `/auth/my-token`

**Method:** GET  
**Authorization:** Required (any valid token)  
**Description:** View information about your current token

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://localhost:8000/auth/my-token
```

**Response:**
```json
{
  "valid": true,
  "claims": {
    "sub": "user-id",
    "email": "user@example.com",
    "name": "User Name",
    "groups": []
  },
  "token_info": {
    "token_id": "uuid",
    "issued_at": "2024-01-01T12:00:00",
    "expires_at": "2024-01-01T12:30:00",
    "source": "azure_callback"
  },
  "token_preview": "eyJhbGciOiJSUzI1NiIs..."
}
```

### 2. View All Tokens (Admin Only) - `/auth/admin/tokens`

**Method:** GET  
**Authorization:** Required (admin token)  
**Description:** View all issued tokens with user information

**Example:**
```bash
curl -H "Authorization: Bearer ADMIN_TOKEN" https://localhost:8000/auth/admin/tokens
```

**Response:**
```json
{
  "total": 5,
  "tokens": [
    {
      "id": "token-id",
      "user": {
        "name": "John Doe",
        "email": "john@example.com"
      },
      "issued_at": "2024-01-01T12:00:00",
      "expires_at": "2024-01-01T12:30:00",
      "source": "azure_callback",
      "session_id": "session-id",
      "access_token_preview": "eyJhbGciOiJSUzI1NiIs..."
    }
  ],
  "admin_user": "admin@example.com"
}
```

### 3. Create Test Token (Admin Only) - `/auth/admin/tokens/create-test`

**Method:** POST  
**Authorization:** Required (admin token)  
**Content-Type:** application/json  
**Description:** Create a test token for development/testing purposes

**Request Body:**
```json
{
  "test_user_email": "test@example.com",
  "test_user_name": "Test User",
  "token_lifetime_minutes": 30
}
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_user_email":"dev@example.com","test_user_name":"Developer","token_lifetime_minutes":60}' \
  https://localhost:8000/auth/admin/tokens/create-test
```

**Response:**
```json
{
  "token_id": "uuid",
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "refresh_token_here",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "name": "Developer",
    "email": "dev@example.com",
    "sub": "test-uuid",
    "groups": []
  },
  "created_by": "admin@example.com"
}
```

### 4. Debug Token Storage (Admin Only) - `/debug/token-storage`

**Method:** GET  
**Authorization:** Required (admin token)  
**Description:** View storage statistics for debugging

**Example:**
```bash
curl -H "Authorization: Bearer ADMIN_TOKEN" https://localhost:8000/debug/token-storage
```

**Response:**
```json
{
  "issued_tokens_count": 10,
  "sessions_count": 5,
  "refresh_tokens_count": 8,
  "storage_details": {
    "issued_tokens_ids": ["id1", "id2", "id3"],
    "session_ids": ["session1", "session2"],
    "refresh_token_count_by_user": {}
  }
}
```

## Testing the Admin Endpoints

A test script is provided to test all admin endpoints:

```bash
# First, ensure your email is in ADMIN_EMAILS in .env
# Then login via the web interface to get a token
# Finally, run the test script with your admin token

python test_admin_endpoints.py YOUR_ADMIN_TOKEN
```

## Security Notes

1. **Admin Access Control**: All admin endpoints check if the user is an admin by verifying:
   - The user's email is in the `ADMIN_EMAILS` environment variable
   - OR the user is a member of a group listed in `ADMIN_GROUP_IDS`

2. **Token Storage**: Currently, tokens are stored in memory. In production, this should be replaced with Redis or a database.

3. **Sensitive Data**: Access tokens are truncated in responses to prevent accidental exposure in logs.

4. **HTTPS Required**: Always use HTTPS in production to protect bearer tokens in transit.

## Implementation Details

The implementation includes:

1. **`issued_tokens` dictionary**: Tracks all issued tokens with metadata
2. **`check_admin_access()` function**: Validates admin permissions
3. **Token tracking**: Both Azure callback and refresh token flows store tokens
4. **Proper error handling**: Returns appropriate HTTP status codes

## Future Enhancements

1. Add token revocation endpoint for admins
2. Add filtering and pagination to the token list
3. Add token usage statistics
4. Implement persistent storage (Redis/Database)
5. Add audit logging for admin actions
6. Add role-based access control (RBAC) for finer-grained permissions