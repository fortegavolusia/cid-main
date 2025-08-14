# Azure Auth App

A centralized authentication service that integrates with Azure Active Directory to provide secure token-based authentication for internal applications.

## Features

- Azure AD OAuth2 integration
- JWT token issuance and validation
- Refresh token support with rotation
- Admin endpoints for token management
- Activity logging for security auditing
- Support for viewing both internal and Azure tokens

## Quick Start

1. Set up environment variables in `.env`:
   ```
   AZURE_CLIENT_ID=your-client-id
   AZURE_CLIENT_SECRET=your-client-secret
   AZURE_TENANT_ID=your-tenant-id
   SECRET_KEY=your-secret-key
   ADMIN_EMAILS=admin@example.com
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the service:
   ```bash
   python3 main.py
   ```
   
   Or use the restart script:
   ```bash
   ./restart_server.sh
   ```

4. Access the service at https://localhost:8000

## Key Endpoints

- `/` - Test page with authentication status
- `/auth/login` - Initiate Azure AD login
- `/auth/callback` - OAuth callback (handled automatically)
- `/auth/logout` - Clear session and logout
- `/auth/validate` - Validate a JWT token
- `/auth/public-key` - Get public key for token validation
- `/auth/admin/tokens` - View all internal tokens (admin only)
- `/auth/admin/azure-tokens` - View all Azure tokens (admin only)

## Architecture

The service acts as a bridge between Azure AD and your internal applications:

1. Users authenticate with Azure AD
2. Service receives Azure tokens and validates them
3. Service issues lightweight internal JWT tokens
4. Internal applications validate tokens using the public key

## Files

- `main.py` - Main application server
- `jwt_utils.py` - JWT token management utilities
- `refresh_token_store.py` - Refresh token storage and rotation
- `token_activity_logger.py` - Security audit logging
- `auth_middleware.py` - Middleware for protecting other services
- `client_example.py` - Example of how to integrate with the service

## Security

- All tokens are signed with RSA keys
- Refresh tokens support rotation for enhanced security
- Admin access is restricted by email or AD group membership
- All token activities are logged for auditing
- SSL/TLS required for all communications

## Development

For development and testing, self-signed certificates are provided (`cert.pem` and `key.pem`). 
In production, use proper SSL certificates.

## Database Schema

See `DATABASE_SCHEMA.md` for details on the data structures used, which will help when migrating to a production database.