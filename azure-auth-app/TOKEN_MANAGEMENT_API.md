# Token Management API Documentation

## Overview

The application now includes a comprehensive token management system that stores and tracks all internally issued tokens using session storage. This allows administrators to monitor, manage, and revoke tokens as needed.

## Token Storage

When a user successfully authenticates via Azure AD:
1. An internal token is automatically generated and stored
2. Token information is saved in both session storage and in-memory storage
3. Each token includes metadata about when it was issued, who it was issued to, and when it expires

## API Endpoints

### 1. Get Current User's Token
**Endpoint:** `GET /auth/my-token`

**Description:** Retrieves the current authenticated user's token information.

**Authentication:** Requires active session (user must be logged in)

**Response:**
```json
{
    "token_id": "uuid-string",
    "token": "internal_token_uuid-string",
    "issued_at": "2024-01-20T10:30:00",
    "expires_at": "2024-01-21T10:30:00",
    "is_expired": false,
    "subject": "user-azure-sub-id",
    "audience": "internal-api"
}
```

### 2. Issue New Token
**Endpoint:** `POST /auth/issue-token`

**Description:** Issues a new internal token for the authenticated user.

**Authentication:** Requires active session

**Response:**
```json
{
    "token": "internal_token_uuid-string",
    "token_type": "Bearer",
    "expires_in": 86400,
    "token_id": "uuid-string"
}
```

### 3. Get All Tokens (Admin Only)
**Endpoint:** `GET /auth/admin/tokens`

**Description:** Retrieves all issued tokens with detailed information.

**Authentication:** Requires admin access (configured via ADMIN_EMAILS or ADMIN_GROUPS environment variables)

**Response:**
```json
{
    "total_tokens": 5,
    "tokens": [
        {
            "token_id": "uuid-string",
            "issued_to": {
                "name": "John Doe",
                "email": "john.doe@example.com"
            },
            "issued_at": "2024-01-20T10:30:00",
            "expires_at": "2024-01-21T10:30:00",
            "is_expired": false,
            "subject": "user-azure-sub-id",
            "audience": "internal-api"
        }
    ],
    "retrieved_at": "2024-01-20T11:00:00",
    "retrieved_by": {
        "name": "Admin User",
        "email": "admin@example.com"
    }
}
```

### 4. Revoke Token (Admin Only)
**Endpoint:** `DELETE /auth/admin/tokens/{token_id}`

**Description:** Revokes a specific token by removing it from storage.

**Authentication:** Requires admin access

**Response:**
```json
{
    "message": "Token revoked successfully",
    "token_id": "uuid-string",
    "revoked_by": "admin@example.com",
    "revoked_at": "2024-01-20T11:00:00"
}
```

### 5. Clean Up Expired Tokens (Admin Only)
**Endpoint:** `GET /auth/admin/tokens/cleanup`

**Description:** Removes all expired tokens from storage.

**Authentication:** Requires admin access

**Response:**
```json
{
    "message": "Cleaned up 3 expired tokens",
    "expired_token_ids": ["uuid1", "uuid2", "uuid3"],
    "cleaned_by": "admin@example.com",
    "cleaned_at": "2024-01-20T11:00:00"
}
```

## Configuration

### Admin Access
Configure admin access using environment variables:

```bash
# Comma-separated list of admin email addresses
ADMIN_EMAILS=admin@example.com,superuser@example.com

# Comma-separated list of Azure AD groups that have admin access
ADMIN_GROUPS=Administrators,Token Managers
```

### Token Lifetime
By default, tokens are issued with a 24-hour lifetime. This can be modified in the code by changing the `timedelta(hours=24)` value.

## Security Considerations

1. **Session Storage**: Currently uses in-memory storage. In production, consider using Redis or a database for persistence across restarts.

2. **Token Format**: The current implementation uses a simple token format. In production, consider using proper JWT tokens with cryptographic signatures.

3. **HTTPS Required**: All endpoints should be accessed over HTTPS to prevent session hijacking.

4. **Admin Access**: Carefully control who has admin access to prevent unauthorized token management.

## Error Handling

All endpoints include proper error handling:
- 401 Unauthorized: User not authenticated
- 403 Forbidden: User lacks admin access (for admin endpoints)
- 404 Not Found: Token not found
- 500 Internal Server Error: Server-side errors with detailed messages

## Example Usage

```bash
# After authenticating via browser, save cookies
curl -c cookies.txt -k https://localhost:8000/login

# Get your current token
curl -b cookies.txt -k https://localhost:8000/auth/my-token

# Admin: Get all tokens
curl -b cookies.txt -k https://localhost:8000/auth/admin/tokens

# Admin: Revoke a token
curl -X DELETE -b cookies.txt -k https://localhost:8000/auth/admin/tokens/abc-123-def

# Admin: Clean up expired tokens
curl -b cookies.txt -k https://localhost:8000/auth/admin/tokens/cleanup
```

## Testing

Run the included test script to see example usage:
```bash
python test_token_endpoints.py
```

## Future Enhancements

1. **Persistent Storage**: Implement Redis or database storage for tokens
2. **Token Rotation**: Automatic token rotation before expiry
3. **Audit Logging**: Detailed audit logs for all token operations
4. **Rate Limiting**: Prevent token abuse with rate limiting
5. **Token Scopes**: Add scope-based permissions to tokens
6. **Webhook Notifications**: Notify services when tokens are revoked