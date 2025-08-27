# CIDS Integration Guide: Single-Page Applications (SPA)

Audience: Teams building SPAs (React, Vue, Angular, etc.) that want to use CIDS for authentication while keeping app state in the browser.

## Overview
Your SPA redirects the browser to CIDS for login. After the user signs in (CIDS uses Azure AD under the hood), the browser returns to your SPA callback route with a CIDS token (or a code you exchange). You verify state, store tokens, and attach the access token to API calls. Implement silent refresh or timed refresh if CIDS provides refresh tokens.

## Prerequisites
- CIDS_URL (e.g., https://cids.example.com)
- client_id assigned by CIDS for your SPA
- Your SPA’s REDIRECT_URI (callback route) registered/allowed in CIDS
- Agreement on roles/permissions mapping for your app (configured in CIDS)

## Typical CIDS Endpoints
- Initiate login: GET {CIDS_URL}/auth/login
  - query: client_id, app_redirect_uri, state
- Callback: Your SPA route (e.g., https://app.example.com/auth/callback)
- Token validation (optional if you verify locally): {CIDS_URL}/auth/validate
- Public key/JWKS (for local verification): {CIDS_URL}/auth/public-key
- Token refresh (if enabled): {CIDS_URL}/auth/token/refresh

Your CIDS admin will confirm exact endpoint names and availability.

## Flow
1) User clicks “Sign in” → generate state, store it (localStorage or cookie), and redirect to:
   - {CIDS_URL}/auth/login?client_id={CLIENT_ID}&app_redirect_uri={REDIRECT_URI}&state={STATE}
2) CIDS authenticates the user (with Azure AD) and redirects back to your REDIRECT_URI with either:
   - access_token (CIDS JWT), or
   - code you exchange at CIDS for a CIDS token.
3) Your callback route verifies state, obtains token, clears sensitive URL params, and initializes your auth state and token refresh.

## Minimal SPA Logic (Pseudocode)

Login/initiate:
```js
function login() {
  const state = randomSecureString();
  localStorage.setItem('oauth_state', state);
  window.location.href = `${CIDS_URL}/auth/login?client_id=${CLIENT_ID}&app_redirect_uri=${REDIRECT_URI}&state=${state}`;
}
```

Callback handler:
```js
async function handleCallback() {
  const params = new URLSearchParams(window.location.search); // or hash, per CIDS config
  const state = params.get('state');
  const storedState = localStorage.getItem('oauth_state');
  if (state !== storedState) throw new Error('Invalid state');
  localStorage.removeItem('oauth_state');

  let token = params.get('access_token');
  if (!token && params.get('code')) {
    const code = params.get('code');
    // Exchange at CIDS, include redirect_uri
    const res = await fetch(`${CIDS_URL}/auth/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id: CLIENT_ID, code, redirect_uri: REDIRECT_URI })
    });
    const data = await res.json();
    token = data.access_token;
  }

  if (!token) throw new Error('No token received');

  // Store token (beware XSS). Prefer in-memory if possible; otherwise, localStorage.
  auth.setToken(token);
  window.history.replaceState({}, document.title, window.location.pathname);

  // Optionally validate token
  // - remote: call CIDS /auth/validate
  // - local: verify with public key (JWKS) if you have a crypto lib available

  // Initialize refresh if you also received a refresh token
  if (data?.refresh_token) tokenManager.initialize(token, data.refresh_token);
}
```

## Token Use
- Send Authorization: Bearer <token> on API requests to your resource servers that trust CIDS.
- Resource servers validate tokens using CIDS public key or /auth/validate.

## Permissions and UI
- Decode the JWT (without verifying) on the client only for non-security UX decisions (e.g., show/hide menus). Always enforce on the server.
- Claims of interest: sub, email, name, groups, roles[CLIENT_ID], permissions[CLIENT_ID].

## Refresh and Expiry
- If CIDS issues refresh tokens to SPAs, use short-lived access tokens and refresh ~1 minute before expiry.
- If no refresh token, redirect to login when token is near expiry or when you receive 401s.

## Logout
- Clear stored tokens (and any app state derived from them).
- Optionally redirect to a CIDS logout endpoint, then back to your SPA.

## Security Considerations
- Always verify state at callback (CSRF protection).
- Prefer storing tokens in memory to reduce XSS exposure; if using storage, consider using a backend-for-frontend (BFF) pattern.
- Remove tokens/codes from the URL after processing (history.replaceState).
- Always validate JWT signature server-side for protected APIs; do not trust client-decoded claims for authorization.

## Integration Checklist
- [ ] Obtain CLIENT_ID and CIDS_URL; register REDIRECT_URI with CIDS
- [ ] Implement login redirect with state
- [ ] Implement callback that verifies state, retrieves token, and clears URL params
- [ ] Initialize token refresh or re-login on expiry
- [ ] Attach Bearer token to API calls; handle 401/403
- [ ] Implement logout and error handling
