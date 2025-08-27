# CIDS Integration Guide: Server-rendered Web Applications

Audience: Teams building traditional server-rendered web apps (Flask, Django, ASP.NET MVC, Rails, Spring MVC, Express with server views) that want CIDS to manage user sign-in and issue a CIDS token.

## Overview
Your app redirects users to CIDS for login. CIDS handles Azure AD, then redirects back to your app with a CIDS-issued JWT (access token), or with an intermediate code you exchange at CIDS. You validate the token, establish a session, and authorize requests using roles/permissions in the token.

## Prerequisites
- CIDS_URL (e.g., https://cids.example.com)
- client_id assigned by CIDS for your app
- (Optional) client_secret for confidential apps if required by your CIDS admin
- Your app's REDIRECT_URI registered/allowed in CIDS
- Agreement on roles/permissions mapping for your app (configured in CIDS)

## Typical CIDS Endpoints
- Initiate login: GET {CIDS_URL}/auth/login
  - query: client_id, app_redirect_uri, state
- Callback: Your app’s REDIRECT_URI
- Token validation: {CIDS_URL}/auth/validate (or validate locally using CIDS public key)
- Public key/JWKS: {CIDS_URL}/auth/public-key (path name may vary)
- Token refresh (if enabled): {CIDS_URL}/auth/token/refresh

Your CIDS admin will confirm exact endpoint names and availability.

## Flow
1) User hits your /login route → you generate a cryptographically strong state and 302 redirect to CIDS:
   - {CIDS_URL}/auth/login?client_id={CLIENT_ID}&app_redirect_uri={REDIRECT_URI}&state={STATE}
2) User signs in at CIDS (which uses Azure AD internally).
3) CIDS redirects the browser to your REDIRECT_URI with either:
   - access_token (CIDS JWT), or
   - code you must exchange at CIDS for a CIDS token.
4) Your callback verifies state, obtains/validates the token, stores session, and redirects to your app’s protected area.

## Minimal Server Routes (Pseudocode)

Login/initiate:
```pseudo
GET /login
  state = random_secure_string()
  save state in user session
  redirect to `${CIDS_URL}/auth/login?client_id=${CLIENT_ID}&app_redirect_uri=${REDIRECT_URI}&state=${state}`
```

Callback:
```pseudo
GET /auth/callback?state=...&access_token=... (or code=...)
  if state != session.state: reject (possible CSRF)

  if access_token present:
    token = access_token
  else if code present:
    token = POST {CIDS_URL}/auth/token with body { client_id, client_secret?, code, redirect_uri }

  // Validate token
  if using remote validation:
    valid = POST {CIDS_URL}/auth/validate with Bearer token
  else (preferred for performance):
    public_key = GET {CIDS_URL}/auth/public-key (cache it)
    claims = jwt_decode_and_verify(token, public_key, algorithms=[RS256], audience includes your CLIENT_ID)

  // Establish session
  store token (or claims) in server session / issue secure httpOnly cookie
  redirect to your app’s home/dashboard
```

## Token Validation (Examples)

Python (PyJWT):
```python
import jwt
claims = jwt.decode(
    token,
    public_key_pem,
    algorithms=['RS256'],
    audience=[CLIENT_ID, 'internal-services']
)
# use claims['roles'][CLIENT_ID], claims['permissions'][CLIENT_ID], claims['groups'], etc.
```

Node (jsonwebtoken):
```js
const jwt = require('jsonwebtoken');
const claims = jwt.verify(token, publicKeyPem, {
  algorithms: ['RS256'],
  audience: [CLIENT_ID, 'internal-services']
});
```

## Session Management
- Preferred: store only a session identifier in a secure, httpOnly, SameSite=strict cookie; keep the token server-side.
- Alternative: set the CIDS token as a secure, httpOnly cookie. Never expose it to JS if you can avoid it.
- On each request, load the session, check token validity/expiry, and enforce permissions.

## Authorization
- Extract roles/permissions for your CLIENT_ID from token claims.
- Gate endpoints and UI features accordingly.

## Refresh and Expiry
- If CIDS issues refresh tokens to your app, store them securely server-side and implement a refresh call to CIDS before access token expiry.
- Otherwise, when nearing expiry or on 401, re-initiate the login redirect to CIDS.

## Logout
- Clear your server session and cookies.
- Optionally redirect to a CIDS logout endpoint if exposed (global sign-out), then back to your app.

## Security Considerations
- Always verify state in callback (CSRF protection).
- Use HTTPS everywhere; set secure cookies; enable HSTS.
- Validate JWT audience includes your CLIENT_ID; validate issuer if provided.
- Cache and rotate CIDS public keys as advised.
- Enforce least privilege using permissions embedded in token.

## Integration Checklist
- [ ] Obtain CLIENT_ID (and CLIENT_SECRET if required) and CIDS_URL
- [ ] Register REDIRECT_URI with CIDS
- [ ] Implement /login redirect with state
- [ ] Implement /auth/callback verifying state, retrieving token, and validating it
- [ ] Store session securely; protect routes; enforce permissions
- [ ] Implement refresh or re-authentication on expiry
- [ ] Implement logout and error handling
