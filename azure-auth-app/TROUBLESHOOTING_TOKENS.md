# Token Storage Troubleshooting Guide

## Overview
This guide helps troubleshoot issues with token storage in the Azure AD authentication application.

## How Token Storage Works

1. **Authentication Flow**:
   - User clicks "Sign in with Azure AD" → redirected to Azure AD
   - Azure AD authenticates → redirects back to `/callback`
   - Callback endpoint processes the authentication

2. **Token Creation** (lines 184-214 in main.py):
   ```python
   # Automatically issue an internal token upon successful authentication
   token_id = str(uuid.uuid4())
   issued_at = datetime.utcnow()
   expires_at = issued_at + timedelta(hours=24)
   
   # Token is stored in the issued_tokens dictionary
   issued_tokens[token_id] = {
       'token': token,
       'issued_to': {...},
       'issued_at': issued_at.isoformat(),
       ...
   }
   ```

3. **Session Storage** (lines 217-218):
   ```python
   request.session['issued_token_id'] = token_id
   request.session['internal_token'] = token
   ```

## Common Issues and Solutions

### 1. Tokens Not Being Stored

**Symptoms**:
- `/auth/admin/tokens` returns empty list
- `/auth/my-token` returns 404

**Possible Causes**:
- Callback endpoint failing before token creation
- Session not persisting
- Exception during token creation

**Solutions**:
1. Check application logs for errors during callback
2. Verify all environment variables are set correctly
3. Add debug logging after line 220:
   ```python
   logger.info(f"Token stored successfully: {token_id}")
   logger.info(f"Total tokens in storage: {len(issued_tokens)}")
   ```

### 2. Admin Endpoint Returns 403 Forbidden

**Symptoms**:
- `/auth/admin/tokens` returns "Admin access required"

**Possible Causes**:
- User not in admin group
- ADMIN_EMAILS or ADMIN_GROUPS not configured

**Solutions**:
1. Add your email to `.env`:
   ```
   ADMIN_EMAILS=your-email@domain.com
   ```
2. Or add your Azure AD group:
   ```
   ADMIN_GROUPS=Administrators,YourGroupName
   ```

### 3. Session Not Persisting

**Symptoms**:
- User appears logged out after refresh
- Token ID lost between requests

**Possible Causes**:
- Cookie settings incompatible with HTTPS/self-signed certs
- Session middleware misconfiguration

**Solutions**:
1. Check session middleware settings (lines 23-30)
2. For development with self-signed certs, ensure:
   ```python
   https_only=False  # For self-signed certs
   same_site="lax"
   ```

## Testing Token Functionality

### Quick Test Steps:
1. Start the application:
   ```bash
   python main.py
   ```

2. Authenticate:
   ```bash
   # Open browser to https://localhost:8000/login
   # Complete Azure AD authentication
   ```

3. Check your token:
   ```bash
   curl -k -c cookies.txt -b cookies.txt https://localhost:8000/auth/my-token
   ```

4. Check all tokens (admin):
   ```bash
   curl -k -c cookies.txt -b cookies.txt https://localhost:8000/auth/admin/tokens
   ```

### Manual Token Creation Test:
If automatic token creation fails, test manual creation:
```bash
curl -k -X POST -c cookies.txt -b cookies.txt https://localhost:8000/auth/issue-token
```

## Debug Mode

To enable debug endpoints, add to your `.env`:
```
DEBUG_MODE=true
```

Then modify main.py to include debug endpoints:
```python
from debug_tokens import add_debug_endpoints

if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
    add_debug_endpoints(app, issued_tokens)
```

Debug endpoints:
- `GET /debug/tokens` - View all tokens and session info
- `GET /debug/session` - View current session data
- `POST /debug/create-test-token` - Create a test token

## Verification Checklist

- [ ] Azure AD authentication completes successfully
- [ ] Callback endpoint reaches token creation code (line 184)
- [ ] No exceptions thrown during token creation
- [ ] Token stored in `issued_tokens` dictionary (line 203)
- [ ] Token ID saved in session (line 217)
- [ ] Session cookies maintained between requests
- [ ] Admin access properly configured in `.env`

## Log Points for Debugging

Add these log statements to track token flow:

1. After successful Azure AD auth (line 180):
   ```python
   logger.info(f"User authenticated: {user_info['email']}")
   ```

2. After token creation (line 220):
   ```python
   logger.info(f"Token created: {token_id} for {user_info['email']}")
   logger.info(f"Tokens in storage: {list(issued_tokens.keys())}")
   ```

3. In the admin tokens endpoint (line 319):
   ```python
   logger.info(f"Admin {user['email']} accessing tokens. Found: {len(issued_tokens)}")
   ```

## Contact Support

If issues persist after following this guide:
1. Check the application logs for specific error messages
2. Verify all environment variables are correctly set
3. Ensure Azure AD app registration has correct redirect URIs
4. Test with the provided test scripts