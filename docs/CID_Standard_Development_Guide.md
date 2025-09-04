# CID Standard Development Guide (v0.1)

This guide describes how to integrate internal applications with CID for both user and app-to-app authentication. It establishes standards for app registration, API key storage, environment configuration, and the end-to-end auth flows.

Note: This is the first entry; we will extend and refine this document in future iterations.

## 1) Concepts and Roles

- CID: Central Identity Directory, your single broker to Azure AD and source of internal access tokens
- App (client): Your internal service or UI that integrates with CID
- User flow: End users authenticate via CID (which federates to Azure) and receive a CID-issued token
- App-to-app (A2A) flow: A backend service presents a CID-issued API key to mint a short-lived service token, or calls with the API key directly where supported

## 2) Registering an App with CID

Use CID’s Admin UI to register each application. Provide:
- Name and description
- Redirect URIs (for frontend login callbacks)
- Owner email
- (Optional) Discovery endpoint

On registration, CID returns:
- client_id: your app’s unique identifier (string starting with `app_...`)
- client_secret: store safely if applicable; used for app confidential flows (not required for basic frontend code flow)
- (Optional) API key for the app if you create one during registration

Standards:
- Redirect URIs must exactly match the callback your frontend serves for login, e.g. `http://localhost:3100/auth/callback` for local dev
- Use `localhost` over HTTP in dev to avoid TLS complexity; for non-localhost (e.g., IPs/DNS), use HTTPS with a reverse proxy in front of CID

## 3) API Key Creation and Storage Standard

API keys are secrets that identify the application (not a user). They are used for:
- A2A token minting: `POST /auth/token/a2a` with `Authorization: Bearer cids_ak_...`
- Direct key validation (for services that accept API key calls): `GET /auth/validate` with `Authorization: Bearer cids_ak_...`

Storage Standard:
- Store the full API key only in the backend service’s `.env` file at the project root
- Recommended variable name: `CID_APP_API_KEY`
- Do not commit `.env` files or API keys to source control
- Rotate keys periodically; keep key scope minimal (permissions, TTL)

Example backend `.env` (root of your backend project):
```
# CID service base (backend API)
CID_BASE_URL=http://localhost:8000

# App API key secret (do not commit to VCS)
CID_APP_API_KEY=cids_ak_XXXXXXXXXXXXXXXXXXXXXXXX
```

Backend usage example (FastAPI/Node-like pseudocode):
```
# If calling a CID endpoint with API key authorization
headers = { 'Authorization': f'Bearer {os.environ["CID_APP_API_KEY"]}' }
resp = GET f"{CID_BASE_URL}/auth/validate" with headers
```

## 4) Frontend Environment Configuration Standard

Frontends should be configured via a `.env` (or `.env.local`) file in the frontend root. Vite requires variables to start with `VITE_`.

Recommended variables:
```
VITE_CID_BASE_URL=http://localhost:8000
VITE_APP_CLIENT_ID=<your CID client_id, e.g., app_fe80739ff4e547fb>
VITE_REDIRECT_URI=http://localhost:3100/auth/callback
# Optional: if the frontend calls your own app backend directly
VITE_BACKEND_BASE_URL=http://127.0.0.1:8091
```

Notes:
- Restart the dev server after editing the `.env`
- If variables appear ignored, ensure the file is in the frontend root, keys begin with `VITE_`, and the dev server was restarted
- You may also provide quick overrides via localStorage for debugging, but do not rely on that for production

## 5) User Login Flow (CID-brokered)

- The frontend starts login by redirecting the browser to CID:
  - `GET {CID_BASE_URL}/auth/login?client_id={VITE_APP_CLIENT_ID}&app_redirect_uri={VITE_REDIRECT_URI}&state={RANDOM}`
- CID redirects to Azure for the tenant configured on CID
- Azure redirects back to CID at its registered callback
- CID mints an internal token and forwards back to the app’s redirect URI, either:
  - With tokens in the URL fragment: `#{access_token, refresh_token, state}`
  - Or with an authorization code in the query string: `?code=...&state=...` (the app then POSTs to CID `/auth/token/exchange`)

Frontend handling guidelines:
- Validate and persist the returned `access_token` (and optional `refresh_token`)
- Validate `state` to mitigate CSRF
- Clear URL hash/query; do not log tokens
- Use the token in API calls to your backend (`Authorization: Bearer <access_token>`) and/or to CID `/auth/whoami`

## 6) App-to-App (Service) Flow

- Use the stored app API key to mint a short-lived service token:
  - `POST {CID_BASE_URL}/auth/token/a2a` with header `Authorization: Bearer cids_ak_...`
  - Response: `{ access_token, token_type, expires_in }`
- Validate service tokens or API keys as needed:
  - Token validation: `POST {CID_BASE_URL}/auth/validate` with `{ token }`
  - API key validation: `GET {CID_BASE_URL}/auth/validate` with `Authorization: Bearer cids_ak_...`

## 7) Backend Validation Patterns (Standard)

Incoming Authorization header could be:
- `Bearer cids_ak_...` (API key)
- `Bearer eyJ...` (CID-issued JWT for a user or service)

Validation:
- For API keys: call CID `GET /auth/validate` with the key in `Authorization`
- For JWTs: call CID `POST /auth/validate` with `{ token }` in JSON body

Return shapes:
- API key validation returns app identity (auth_type: `api_key`, `app_client_id`, permissions)
- Token validation returns `{ valid: true, claims: { ... } }` for user/service tokens

## 8) Local Dev vs. Non-Localhost (HTTPS)

- Local dev: prefer `localhost` with HTTP for both CID and the app (simplest path)
- Non-localhost (IP or DNS): Azure requires HTTPS redirect URIs
  - Put CID behind a reverse proxy (e.g., Nginx) with TLS
  - Set Azure redirect URI to `https://<host>/auth/callback`
  - Set frontend `VITE_CID_BASE_URL=https://<host>`

## 9) Security and Operations

- Never commit API keys or tokens; keep `.env` files local
- Scope API key permissions minimally; set TTLs; rotate regularly
- Prefer service tokens minted from API keys over long-lived secrets in transit
- Avoid logging `Authorization` headers or tokens; sanitize logs
- Use feature flags to toggle A2A and experimental flows

## 10) CID Discovery Compliance

CID Discovery enables automatic endpoint and permission discovery for enhanced role-based access control. When enabled, CID can automatically generate field-level permissions for your app's API endpoints.

### Discovery Endpoint Requirements

Your app must implement a `GET /discovery` endpoint that returns metadata about your API endpoints and response fields.

**Required Response Schema:**
```json
{
  "version": "2.0",
  "app_id": "your-app-identifier",
  "app_name": "Your App Display Name",
  "description": "App description (optional)",
  "endpoints": [
    {
      "path": "/api/endpoint",
      "method": "GET",
      "operation_id": "unique_operation_name",
      "description": "Endpoint description",
      "required_roles": ["admin"],  // Optional: required roles
      "response_fields": {
        "field_name": {
          "type": "string|number|boolean|object|array",
          "description": "Field description",
          "sensitive": false,  // true for sensitive data
          "pii": false,        // true for personally identifiable info
          "phi": false         // true for protected health info
        }
      }
    }
  ]
}
```

### Field Classification Standards

**PII (Personally Identifiable Information):**
- `email`, `name`, `sub` (user identifiers)
- Phone numbers, addresses, SSNs
- Any field that can identify a specific person

**Sensitive Fields:**
- `permissions`, `roles`, `identity` objects
- Financial data, internal IDs
- Any field requiring elevated access

**PHI (Protected Health Information):**
- Medical records, diagnoses, treatments
- Health-related personal information

### Nested Field Handling

For complex objects, use dot notation to represent nested fields:

```json
{
  "identity": {
    "type": "object",
    "description": "User identity information",
    "sensitive": true,
    "pii": true,
    "phi": false
  },
  "identity.email": {
    "type": "string",
    "description": "User email address",
    "sensitive": false,
    "pii": true,
    "phi": false
  },
  "identity.permissions": {
    "type": "array",
    "description": "User permissions list",
    "sensitive": true,
    "pii": false,
    "phi": false
  }
}
```

### Implementation Example (FastAPI)

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/discovery")
async def discovery():
    return {
        "version": "2.0",
        "app_id": "my-app-id",
        "app_name": "My Application",
        "description": "Sample application with CID discovery",
        "endpoints": [
            {
                "path": "/",
                "method": "GET",
                "operation_id": "health_check",
                "description": "Health check endpoint",
                "response_fields": {
                    "status": {
                        "type": "string",
                        "description": "Service status",
                        "sensitive": False,
                        "pii": False,
                        "phi": False
                    }
                }
            },
            {
                "path": "/users/me",
                "method": "GET",
                "operation_id": "get_current_user",
                "description": "Get current user information",
                "required_roles": ["user"],
                "response_fields": {
                    "email": {
                        "type": "string",
                        "description": "User email address",
                        "sensitive": False,
                        "pii": True,
                        "phi": False
                    },
                    "permissions": {
                        "type": "array",
                        "description": "User permissions",
                        "sensitive": True,
                        "pii": False,
                        "phi": False
                    }
                }
            }
        ]
    }
```

### Discovery Registration

1. **Enable Discovery**: Check "Allow Discovery" when registering your app
2. **Set Discovery Endpoint**: Provide the full URL (e.g., `http://localhost:8091/discovery`)
3. **Test Discovery**: Use CID's "🔍 Run Discovery" button to validate your endpoint
4. **Review Permissions**: Check generated permissions in the CID admin interface

### Expected Discovery Results

CID will automatically generate field-level permissions like:
- `app_xxxxx.endpoint_name.read.field_name`
- `app_xxxxx.endpoint_name.read.*` (wildcard permissions)
- Proper classification of PII/sensitive fields
- Hierarchical permission structure for role building

### Discovery Validation

CID validates your discovery response against a strict schema. Common validation errors:

- **Wrong field format**: `response_fields` must be `Dict[str, FieldMetadata]`, not `List[dict]`
- **Missing required fields**: `version`, `app_id`, `app_name` are required
- **Invalid field names**: Use `version` not `discovery_version`, `required_roles` not `required_permissions`
- **Nested field structure**: Use dot notation (`identity.email`) instead of nested objects

### Discovery Best Practices

- **Document all endpoints**: Include all API endpoints that return data
- **Classify fields accurately**: Proper PII/sensitive marking enables compliance
- **Use descriptive names**: Clear descriptions help with role building
- **Test thoroughly**: Validate discovery response before registration
- **Version your schema**: Use semantic versioning for discovery changes

## 11) Onboarding Checklist (Dev)

- [ ] Register your app in CID; capture `client_id`
- [ ] Add your frontend redirect URI to the app record in CID
- [ ] Generate an API key (if needed) and store it in backend `.env` as `CID_APP_API_KEY`
- [ ] Create frontend `.env` with `VITE_CID_BASE_URL`, `VITE_APP_CLIENT_ID`, `VITE_REDIRECT_URI`
- [ ] Implement login redirect to `GET {CID_BASE_URL}/auth/login`
- [ ] Handle CID callback tokens (fragment or code-exchange via `/auth/token/exchange`)
- [ ] Validate tokens/API keys through CID `/auth/validate`
- [ ] **[Optional] Implement `/discovery` endpoint for enhanced permissions**
- [ ] **[Optional] Enable discovery in CID app registration**
- [ ] For non-localhost, configure TLS in front of CID and use HTTPS everywhere

---

Appendix: Example redirects (dev)

- Start login:
  `http://localhost:8000/auth/login?client_id=app_XXXXXXXXXXXXYYYY&app_redirect_uri=http://localhost:3100/auth/callback&state=abc123`
- CID callback to app with fragment:
  `http://localhost:3100/auth/callback#access_token=...&refresh_token=...&state=abc123`
- Code exchange alternative:
  `POST http://localhost:8000/auth/token/exchange` with `{ code, redirect_uri }`

