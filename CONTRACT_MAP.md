# CIDS Frontend-to-Backend API Contract Map

Last updated: 2025-08-26

This document maps all frontend calls (services/components) to backend FastAPI endpoints, including method, path, request shape, and response shape used by the UI.

## Conventions
- All requests include Authorization: Bearer <access_token> via axios interceptor unless noted
- Responses list only the fields used by the UI
- Admin-only endpoints require an internal admin token

---

## Auth

- POST /auth/token/exchange
  - Frontend: authService.exchangeCodeForToken(code)
  - Body: { code: string, redirect_uri: string }
  - Returns: { access_token, token_type, expires_in, refresh_token? }

- POST /auth/token
  - Frontend: authService.refreshToken(refreshToken)
  - Body: { grant_type: 'refresh_token', refresh_token }
  - Returns: { access_token, token_type, expires_in, refresh_token? }

- POST /oauth/token
  - Frontend: authService.getOAuthToken(grantType, refreshToken?)
  - Body (form-data): grant_type, refresh_token?
  - Returns: { access_token, token_type, expires_in, refresh_token? }

- POST /auth/validate
  - Frontend: authService.validateToken(token?)
  - Body: { token }
  - Returns: { valid: boolean, sub?, email?, name?, permissions?, app_client_id?, auth_type?, error? }

- GET /auth/whoami
  - Frontend: authService.getCurrentUser()
  - Returns: { sub, email, name, groups?, permissions?, token_issued?, token_expires?, raw_claims? }

- GET /auth/my-token
  - Frontend: authService.getMyToken()
  - Returns: token info and claims for display

- GET /auth/logout
  - Frontend: authService.logout()
  - Effect: Clears session on server; UI clears local token

- POST /auth/revoke
  - Frontend: authService.revokeToken(token, tokenTypeHint?)
  - Body: { token, token_type_hint: 'refresh_token' (default) }
  - Returns: 200 OK on accepted

- GET /iam/me
  - Frontend: authService.getEffectiveIdentity(tenantId?)
  - Headers: X-Tenant-ID optional
  - Returns: effective identity with computed permissions

---

## Admin: Tokens

- GET /auth/admin/tokens
  - Frontend: adminService.getInternalTokens()
  - Returns: { total, tokens: TokenInfo[], admin_user }

- GET /auth/admin/azure-tokens
  - Frontend: adminService.getAzureTokens()
  - Returns: { total, tokens: TokenInfo[], admin_user }

- GET /auth/admin/tokens/{token_id}/activities
  - Frontend: adminService.getTokenActivity(id)
  - Returns: TokenActivityResponse

- GET /auth/admin/azure-tokens/{token_id}/activities
  - Frontend: adminService.getAzureTokenActivity(id)
  - Returns: TokenActivityResponse

- DELETE /auth/admin/tokens/{token_id}
  - Frontend: adminService.removeToken(id)
  - Returns: void

- DELETE /auth/admin/azure-tokens/{token_id}
  - Frontend: adminService.removeAzureToken(id)
  - Returns: void

---

## Admin: Apps

- GET /auth/admin/apps
  - Frontend: adminService.getApps()
  - Returns: AppInfo[]

- GET /auth/admin/apps/{client_id}
  - Frontend: adminService.getApp(clientId)
  - Returns: AppInfo

- POST /auth/admin/apps
  - Frontend: adminService.createApp(appData)
  - Body: Partial<AppInfo> (RegisterAppRequest on backend)
  - Returns: { app: AppInfo, client_secret, api_key?, api_key_metadata? }

- PUT /auth/admin/apps/{client_id}
  - Frontend: adminService.updateApp(clientId, appData)
  - Body: Partial<AppInfo> (UpdateAppRequest)
  - Returns: AppInfo

- DELETE /auth/admin/apps/{client_id}
  - Frontend: adminService.deleteApp(clientId)
  - Returns: void

- POST /auth/admin/apps/{client_id}/rotate-secret
  - Frontend: adminService.rotateAppSecret(clientId)
  - Returns: { client_id, client_secret, message }

---

## Admin: Role Mappings & Groups

- GET /auth/admin/apps/{client_id}/role-mappings
  - Frontend: adminService.getRoleMappings(clientId)
  - Returns: { app_name, client_id, mappings: Array<{ ad_group, app_role }> }

- POST /auth/admin/apps/{client_id}/role-mappings
  - Frontend: adminService.setRoleMappings(clientId, mappingsDict)
  - Body: { mappings: Record<string, string | string[]> }
  - Returns: { message, mappings }

- GET /auth/admin/azure-groups
  - Frontend: adminService.searchAzureGroups(search?, top?)
  - Query: ?search=...&top=...
  - Returns: { groups: Array<{ id, displayName, description? }> }

---

## Admin: API Keys

- GET /auth/admin/apps/{client_id}/api-keys
  - Frontend: adminService.getAppAPIKeys(clientId)
  - Returns: { api_keys: APIKey[] }

- POST /auth/admin/apps/{client_id}/api-keys
  - Frontend: adminService.createAPIKey(clientId, request)
  - Body: { name: string, permissions: string[], ttl_days?: number }
  - Returns: { api_key: string, metadata: APIKey }

- DELETE /auth/admin/apps/{client_id}/api-keys/{key_id}
  - Frontend: adminService.revokeAPIKey(clientId, keyId)
  - Returns: void

- POST /auth/admin/apps/{client_id}/api-keys/{key_id}/rotate
  - Frontend: adminService.rotateAPIKey(clientId, keyId, graceHours)
  - Query: ?grace_period_hours=number
  - Returns: { api_key: string, metadata: APIKey }

---

## Admin: App Endpoints

- GET /auth/admin/apps/{client_id}/endpoints
  - Frontend: adminService.getAppEndpoints(clientId)
  - Returns: endpoints registry object { endpoints: [...], version, updated_at, ... }

- PUT /auth/admin/apps/{client_id}/endpoints
  - Frontend: adminService.updateAppEndpoints(clientId, endpoints)
  - Body: endpoints payload (if used)
  - Returns: registry update response

---

## Discovery

- POST /discovery/endpoints/{client_id}
  - Frontend: adminService.triggerDiscovery(clientId)
  - Returns: { status: 'success' | 'skipped' | 'error', endpoints_discovered?, endpoints_stored?, error?, message? }

- GET /discovery/v2/permissions/{client_id}
  - Frontend: adminService.getAppPermissions(clientId)
  - Returns: discovered permissions (flat view)

- GET /discovery/v2/permissions/{client_id}/tree
  - Frontend: adminService.getAppPermissionTree(clientId)
  - Returns: { permission_tree: {
      [resource: string]: {
        [action: string]: { fields: FieldInfo[], endpoint?: string, method?: string }
      }
    } }

---

## Token Templates

- GET /auth/admin/token-templates
  - Frontend: adminService.getTokenTemplates()
  - Returns: { templates: any[] }

- GET /auth/admin/token-templates/{template_name}
  - Frontend: adminService.getTokenTemplate(name)
  - Returns: template object

- POST /auth/admin/token-templates
  - Frontend: adminService.saveTokenTemplate(template)
  - Body: template object (requires name)
  - Returns: { message: 'Template saved successfully', template_name }

- DELETE /auth/admin/token-templates/{template_name}
  - Frontend: adminService.deleteTokenTemplate(name)
  - Returns: { message: 'Template deleted successfully' }

- POST /auth/admin/token-templates/import
  - Frontend: adminService.importTokenTemplates(templates)
  - Body: { templates: any[] }
  - Returns: import result message

---

## Debug and Well-known

- GET /auth/debug/admin-check
  - Frontend: adminService.getAdminCheck()
  - Returns: diagnostic payload

- GET /debug/storage
  - Frontend: adminService.getStorageDebug()
  - Note: Backend exposes /debug/app-storage and /debug/token-storage. /debug/storage may 404 unless aliased.

- GET /.well-known/jwks.json
  - Consumed indirectly; internal public key also available at GET /auth/public-key
  - Returns: { keys: [ { kty, use, kid, alg, n, e } ] }

---

## Types (used by UI)

- AppInfo: { client_id, name, is_active, created_at, redirect_uris?, description?, owner_email?, allow_discovery?, discovery_endpoint?, last_discovery_at?, discovery_status? }
- AppRegistrationResult: { app: AppInfo, client_secret, api_key?, api_key_metadata? }
- APIKey: { key_id, key_prefix, name, permissions[], expires_at, created_at, created_by, is_active, last_used_at?, usage_count }
- APIKeyCreationResponse: { api_key: string, metadata: APIKey }
- TokenInfo (subset for UI): { id, user { name, email }, issued_at, expires_at, subject, issuer, audience, revoked? }
- TokenListResponse: { total, tokens: TokenInfo[], admin_user }
- TokenActivityResponse: { token_id, token_info { ... }, activities[], activity_count }
- User: { sub, email, name, groups?, permissions?, token_issued?, token_expires?, raw_claims? }
- TokenValidationResponse: { valid, sub?, email?, name?, permissions?, app_client_id?, auth_type?, error? }

---

## Known Mismatch to Address

- adminService.getStorageDebug() calls GET /debug/storage. Backend provides:
  - GET /debug/app-storage
  - GET /debug/token-storage
  Consider adding a backend alias or updating the frontend to call the specific endpoints as needed.

