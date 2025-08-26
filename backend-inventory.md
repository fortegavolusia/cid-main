## Backend Inventory (CIDS Azure Auth Service)

This document inventories backend endpoints, key models (and notable fields), primary classes, and important globals/config variables for the CIDS azure-auth-app backend.

### Endpoints (FastAPI app in azure-auth-app/main.py)
- GET /auth/login — Initiate Azure AD OAuth flow and start session
- GET /auth/callback — Handle Azure AD callback; mint internal token; store Azure claims
- POST /auth/token — OAuth2 token endpoint (refresh grant) issuing new access token
- POST /oauth/token — OAuth2 token endpoint with httpOnly refresh token cookies
- POST /auth/token/session — Return current session token (back-compat)
- POST /auth/token/exchange — Exchange Azure authorization code for internal CIDS token
- GET /auth/validate — Validate an internal JWT or API key; returns token claims
- GET /.well-known/jwks.json — Return JWKS public keys for token verification
- GET /.well-known/cids-config — Return auth service metadata/config
- POST /auth/introspect — RFC 7662 token introspection for internal tokens
- POST /auth/revoke — RFC 7009 token revocation for refresh/access tokens
- GET /auth/logout — Clear auth session and logout
- GET /auth/admin/tokens — [Admin] List issued internal tokens (with optional revoked)
- DELETE /auth/admin/tokens/{token_id} — [Admin] Revoke a specific issued token
- GET /auth/admin/tokens/{token_id}/activities — [Admin] Activity log for a token
- GET /auth/admin/azure-groups — [Admin] Search Azure AD groups via Graph API
- GET /auth/admin/azure-tokens — [Admin] List stored Azure-issued tokens
- DELETE /auth/admin/azure-tokens/{token_id} — [Admin] Remove stored Azure token record
- GET /auth/admin/azure-tokens/cleanup — [Admin] Purge expired stored Azure tokens
- GET /auth/admin/azure-tokens/{token_id}/activities — [Admin] Activity log for Azure token
- POST /auth/admin/apps — [Admin] Register a new client application; returns client_secret
- GET /auth/admin/apps — [Admin] List registered applications
- GET /auth/admin/apps/{client_id} — [Admin] Get one app’s registration details
- PUT /auth/admin/apps/{client_id} — [Admin] Update app registration
- POST /auth/admin/apps/{client_id}/rotate-secret — [Admin] Rotate an app’s client secret
- DELETE /auth/admin/apps/{client_id} — [Admin] Deactivate/delete an app registration
- POST /auth/admin/apps/{client_id}/role-mappings — [Admin] Upsert Azure group→role mappings
- GET /auth/admin/apps/{client_id}/role-mappings — [Admin] Get an app’s group→role mappings
- POST /auth/admin/apps/{client_id}/api-keys — [Admin] Create API key for an app
- GET /auth/admin/apps/{client_id}/api-keys — [Admin] List API keys for an app
- DELETE /auth/admin/apps/{client_id}/api-keys/{key_id} — [Admin] Revoke/deactivate API key
- POST /auth/admin/apps/{client_id}/api-keys/{key_id}/rotate — [Admin] Rotate an API key
- GET /debug/app-storage — [Admin] Inspect app registration store (debug)
- GET /debug/token-storage — [Admin] Inspect issued token store (debug)
- GET /auth/my-token — Return claims/details of caller’s own token
- POST /auth/validate — Validate token provided in request body JSON
- GET /auth/debug/admin-check — [Admin] Test endpoint to verify admin access
- GET /debug/timestamps — Server time, tz, system info (debug)
- PUT /apps/{client_id}/endpoints — Upsert endpoints for a registered app
- GET /apps/{client_id}/endpoints — Get endpoints for app (with discovery fallback)
- GET /auth/admin/apps/{client_id}/endpoints — [Admin] Get endpoints for an app
- GET /auth/user/groups — Return current user’s Azure AD groups
- PUT /apps/{client_id}/roles — Upsert role definitions for an app
- GET /apps/{client_id}/roles — Get role definitions for an app
- PUT /role-mappings — Upsert global Azure group→app role mappings
- GET /role-mappings — Get all global role mappings
- PUT /policy/{client_id} — Upsert policy document (permissions, role map, ABAC) for app
- GET /policy/{client_id} — Get active policy (or by version) for app
- GET /iam/me — Return effective identity with roles and computed permissions
- POST /discovery/endpoints/{client_id} — Trigger legacy discovery for specific app
- POST /discovery/endpoints — Trigger legacy discovery for all apps
- GET /discovery/status — Get discovery job status (optionally filtered by app)
- GET /discovery/endpoints — Service discovery endpoint for UI/tools
- POST /discovery/v2/endpoints/{client_id} — Trigger enhanced field-level discovery
- GET /discovery/v2/permissions/{client_id} — Get discovered permissions (optional filters)
- GET /discovery/v2/permissions/{client_id}/tree — Get permissions organized by resource/action
- POST /permissions/{client_id}/roles — Create permission role with selected fields
- GET /permissions/{client_id}/roles/{role_name} — Get one role’s permissions + metadata
- GET /permissions/{client_id}/roles — List roles + permissions with metadata
- PUT /permissions/{client_id}/roles/{role_name} — Update a role’s permissions/description
- DELETE /permissions/{client_id}/roles/{role_name} — Delete a role from permission registry
- GET /health — Health check for the auth service
- GET /auth/whoami — Return caller’s user info (using provided token)
- GET / — HTML admin/test page for the auth service UI
- POST /auth/admin/rotation/check — [Admin] Manually trigger API key rotation checks
- GET /auth/admin/rotation/policies — [Admin] Get all API key rotation policies
- PUT /auth/admin/apps/{client_id}/rotation-policy — [Admin] Set rotation policy for app
- GET /auth/admin/token-templates — [Admin] List token templates
- GET /auth/admin/token-templates/{template_name} — [Admin] Get a token template
- POST /auth/admin/token-templates — [Admin] Create or update token template
- DELETE /auth/admin/token-templates/{template_name} — [Admin] Delete token template
- POST /auth/admin/token-templates/import — [Admin] Import multiple token templates

### Request/Response Models (Pydantic)
- TokenRequest — Fields: grant_type, refresh_token; used by /auth/token
- TokenExchangeRequest — Fields: code, redirect_uri; used by /auth/token/exchange
- RevokeTokenRequest — Fields: token, token_type_hint; used by /auth/revoke
- CreateAPIKeyRequest — Fields: name, permissions, ttl_days; for API key creation
- APIKeyResponse — Fields: key_id, key_prefix, name, permissions, expires_at, created_at, created_by, is_active, last_used_at, usage_count; describes an API key
- APIKeyCreationResponse — Fields: api_key, metadata; returned after creating/rotating API key
- RegisterAppRequest — Fields: name, description, redirect_uris, owner_email, discovery_endpoint, allow_discovery, create_api_key, api_key_name, api_key_permissions; app registration payload
- UpdateAppRequest — Fields: name, description, redirect_uris, is_active, discovery_endpoint, allow_discovery; app update payload
- AppResponse — Fields: client_id, name, description, redirect_uris, owner_email, is_active, created_at, updated_at, discovery_endpoint, allow_discovery, last_discovery_at, discovery_status; app details
- AppRegistrationResponse — Fields: app, client_secret, api_key, api_key_metadata; app registration response
- SetRoleMappingRequest — Fields: mappings (dict of AD group→app role(s)); upsert role mapping
- RolesUpdate — Fields: roles (list of Role); role definitions per app
- Role (model) — Fields: name, description, permissions; a role within an app
- RoleMapping — Fields: azure_group, app_client_id, role, tenant_id; one mapping entry
- RoleMappingsUpdate — Fields: mappings (list of RoleMapping); upsert mappings
- PolicyDocument — Fields: permissions(list), role_permission_matrix(list), abac_rules(list, optional), version, description; app policy document
- Permission (policy) — Fields: name, description, resource, actions; a policy permission
- RolePermissionMapping — Fields: role, permissions; maps role to named permissions
- ABACRule — Fields: name, description, condition, permissions; attribute-based rule
- Endpoint (registry) — Fields: method, path, desc; describes an app endpoint
- EndpointsUpdate — Fields: endpoints(list of Endpoint), version(optional); registry upsert
- Discovery Models (discovery_models.py) — FieldType/ParameterLocation enums; FieldMetadata (type, sensitive/pii/phi flags, required/read_only/write_only, format, fields/items for nesting); ParameterMetadata (name, in, type, required, sensitive); EndpointMetadata (method, path, operation_id, description, parameters, request_fields, response_fields, required_roles, tags, metadata); ServiceMetadata (name, version, description, base_path, endpoints); DiscoveryResponse (version, app_id, app_name, endpoints or services, metadata)

### Core Classes (Services/Managers)
- JWTManager — RSA key mgmt and JWT mint/validate utilities
- JWKSHandler — Builds JWKS and metadata responses from JWTManager
- DiscoveryService — Legacy endpoint discovery for registered apps
- EnhancedDiscoveryService — Field-level discovery and permission generation (v2)
- AppEndpointsRegistry — Persist and validate registered app endpoints (JSON store)
- PermissionRegistry — Persist discovered permissions; manage roles keyed to field-level perms
- RolesManager — Persist app roles and Azure AD group→role mappings
- PolicyManager — Persist policy documents, versions, and active selection per app
- APIKeyManager — Create/validate/rotate/revoke API keys with metadata and usage tracking
- TokenActivityLogger — Records token lifecycle events (create/validate/revoke/etc.)
- AuditLogger — Records system/audit events for IAM operations
- CIDSAuth (cids_auth.py) — Client library for apps to validate tokens and filter fields
- AuthMiddleware (auth_middleware.py) — Client-side middleware/decorators for auth/group checks

### Notable Functions (main.py helpers)
- datetime_filter(ts) — Jinja2 filter to render Unix timestamps
- get_session(session_id) — Fetch in-memory session dict
- set_session(session_id, data) — Store in-memory session dict
- validate_api_key_auth(auth_header) — Validate API key Bearer and build claims-like metadata
- check_admin_access(authorization) — Validate bearer (JWT or API key) and confirm admin
- generate_token_with_iam_claims(user_info, client_id?) — Build an internal token enriched with IAM claims

### Key Globals / Config and Storage Paths
- DEV_CROSS_ORIGIN — Enable relaxed CORS for local React development
- SAMESITE_POLICY — Cookie SameSite policy based on dev cross-origin mode
- sessions — In-memory dict of session_id→data (dev only)
- issued_tokens — In-memory dict of internal token_id→token+claims data (admin/debug)
- azure_tokens — In-memory dict of Azure token tracking data (admin/debug)
- DATA_DIR (app_registration) — Storage dir for registered apps
- APPS_FILE / SECRETS_FILE / ROLE_MAPPINGS_FILE — JSON files for app registration data
- API_KEYS_DB — JSON file storing API key metadata
- API_KEY_PREFIX / API_KEY_LENGTH / HASH_ALGORITHM — API key format and hashing config
- PERMISSIONS_DB / ROLE_PERMISSIONS_DB / ROLE_METADATA_DB — Permission registry JSON stores
- RolesManager.roles_file / mappings_file — JSON stores for roles and role mappings
- PolicyManager.policies_dir / active_policies_file — Storage for policy versions and active map

Notes
- Admin endpoints require a bearer token or API key with admin permission.
- Discovery v2 surfaces field-level metadata enabling granular permission generation.
- In-memory stores in dev should be replaced with Redis/DB in production.

