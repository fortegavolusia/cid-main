# Testing the Auth Flow

## Summary of Changes

I made changes to support app-specific authentication flows, but I was careful to:
1. **NOT change the Azure redirect URI** - it remains as configured in Azure AD
2. Added support for apps to register and get app-specific roles in tokens
3. The parameter for app callbacks is now `app_redirect_uri` to distinguish it from Azure's redirect URI

## Current Status

### Auth Service
- Running on https://localhost:8000
- Azure redirect URI unchanged: uses whatever is in your .env file
- Added support for app registration and role mappings

### Flask Test App  
- Running on http://localhost:5000
- Registered with client_id: `app_d46e0b0e76124e59`
- Configured with role mappings:
  - "Domain Users" → "viewer"
  - "Engineering" → "editor"

## To Test Normal Auth Service Login

1. Go to https://localhost:8000
2. Click "Sign in with Azure AD"
3. This should work exactly as before - no changes to the Azure flow

## To Test App Integration

1. Go to http://localhost:5000
2. Click "Login with Auth Service"
3. The flow is:
   - App redirects to auth service with `client_id` and `app_redirect_uri`
   - Auth service validates the app registration
   - Auth service redirects to Azure (using the original Azure redirect URI)
   - After Azure auth, auth service redirects back to the app
   - Token includes app-specific roles

## What I Changed

1. **Login endpoint** now accepts optional parameters:
   - `client_id` - identifies the registered app
   - `app_redirect_uri` - where to send user after auth (NOT the Azure redirect)
   - `state` - for CSRF protection

2. **Callback handler** checks if this is an app flow and:
   - Adds app-specific roles to the token
   - Redirects to the app's redirect URI instead of home page

3. **Azure redirect URI is NEVER changed** - it always uses your configured value

## If You're Getting Redirect URI Errors

This means Azure is rejecting the redirect URI. Check:
1. Your .env file has the correct REDIRECT_URI
2. The value matches exactly what's configured in Azure AD
3. The auth service is using the value from your .env file

The app integration should NOT affect your Azure configuration at all.