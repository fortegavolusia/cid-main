# CIDS Frontend Schema (Initial)

## 1. App Architecture Overview
- Framework: React + TypeScript + Vite
- State/Async: @tanstack/react-query (QueryClientProvider)
- Routing: react-router-dom (BrowserRouter)
- Auth: Custom AuthContext + authService (JWT in localStorage)
- HTTP: Axios wrapper (apiService) with interceptors
- Styling: CSS + styled-components

Entry points
- src/main.tsx -> renders <App />
- src/App.tsx -> providers, routes, and guards

## 2. Routes and Providers
- Providers
  - QueryClientProvider (QueryClient with retry:1, no refetchOnWindowFocus)
  - AuthProvider (AuthContext)
- Route Guards
  - ProtectedRoute(children): requires isAuthenticated, shows Loading while auth state loads; redirects to /login
  - PublicRoute(children): redirects to / if already authenticated
- Routes
  - /login -> LoginPage (PublicRoute)
  - /auth/callback -> CallbackPage
  - / -> Layout(HomePage) (ProtectedRoute)
  - /admin -> Layout(AdminPage) (ProtectedRoute)
  - /query-builder -> Layout(QueryBuilderPage) (ProtectedRoute)
  - /token-admin -> Layout(TokenAdministrationPage) (ProtectedRoute)

## 3. Components
- Layout (src/components/Layout.tsx)
  - Props: { children }
  - Context: useAuth() -> user, isAuthenticated, logout
  - State: sidebarCollapsed (persisted in localStorage)
  - Structure: Fixed Sidebar + Toggle + MainContent
  - Navigation buttons: window.location.href = '/', '/admin', '/token-admin', '/query-builder'
  - Displays user.name/email when authenticated
  - Exposes Logout button (calls logout)

- Modal (src/components/Modal.tsx)
  - Generic modal. See file task for details.

- APIKeyModal (src/components/APIKeyModal.tsx)
  - Shows and copies API key. See file task for details.

- PermissionSelector (src/components/PermissionSelector.tsx)
  - UI to select permissions, likely uses adminService.getAppPermissions/Tree.

- RolesModal (src/components/RolesModal.tsx)
  - Manage role mappings per app; uses adminService.setRoleMappings/getRoleMappings.

- RuleBuilder (src/components/RuleBuilder.tsx)
  - UI for building rules (details TBA).

- TokenBuilder (src/components/TokenBuilder.tsx)
  - Props: { templateToLoad? }
  - Manages token claims (standard/custom), drag/drop and editing.

- TokenDetailsModal (src/components/TokenDetailsModal.tsx)
  - Displays generated token details.

- TokenTemplates (src/components/TokenTemplates.tsx)
  - List, load, export, delete token templates via adminService.

## 4. Pages
- LoginPage
  - Uses AuthContext.login() to start OAuth flow.

- CallbackPage
  - Handles Azure OAuth redirect; exchanges code via authService.exchangeCodeForToken -> stores token in apiService; navigates.

- HomePage
  - Shows "My Token Information" via authService.getMyToken() (TBC in code).

- AdminPage
  - App administration: apps, API keys, endpoints, role mappings; depends on adminService.

- QueryBuilderPage
  - Integrates @react-awesome-query-builder (AntdConfig). Fields defined locally; persistence via localPolicyService (savePolicy/loadPolicy/listPolicies/deletePolicy).

- TokenAdministrationPage
  - Multi-tab: builder (TokenBuilder), templates (TokenTemplates), testing/settings placeholders.

## 5. Context
- AuthContext (src/contexts/AuthContext.tsx)
  - State: { isAuthenticated, user, token, loading, error }
  - Actions: LOGIN_START, LOGIN_SUCCESS, LOGIN_FAILURE, LOGOUT, SET_LOADING, SET_ERROR, CLEAR_ERROR
  - Methods: login(), logout(), checkAuth(), clearError()
  - External deps: authService (login/logout/getCurrentUser/validateToken, token storage)

## 6. Services
- apiService (src/services/api.ts)
  - Axios instance with baseURL '/'
  - Request interceptor: attaches Authorization Bearer <localStorage.access_token>
  - Response interceptor: on 401 -> clears token and redirects to /login
  - Methods: get/post/put/delete/patch; setAuthToken/getAuthToken/clearAuthToken

- authService (src/services/authService.ts)
  - login(): redirects to Azure authorize URL with state stored in localStorage
  - exchangeCodeForToken(code): POST /auth/token/exchange
  - logout(): GET /auth/logout, clears token, redirects '/'
  - validateToken(token?): POST /auth/validate
  - getCurrentUser(): GET /auth/whoami
  - getMyToken(): GET /auth/my-token
  - refreshToken(refreshToken): POST /auth/token
  - getOAuthToken(grantType, refreshToken?): POST /oauth/token (multipart/form-data)
  - Helpers: isAuthenticated(), get/set/clear token via apiService
  - getEffectiveIdentity(tenantId?): GET /iam/me with optional X-Tenant-ID
  - revokeToken(token, tokenTypeHint?): POST /auth/revoke

- adminService (src/services/adminService.ts)
  - Token mgmt: getInternalTokens/getAzureTokens/getTokenActivity/removeToken/removeAzureToken
  - App mgmt: getApps/getApp/createApp/updateApp/deleteApp
  - API keys: getAppAPIKeys/createAPIKey/revokeAPIKey/rotateAPIKey/rotateAppSecret
  - Endpoints: getAppEndpoints/updateAppEndpoints/triggerDiscovery
  - Permissions: getAppPermissions/getAppPermissionTree
  - Azure Groups: searchAzureGroups
  - Rotation policies: manualRotationCheck/getRotationPolicies/setRotationPolicy
  - Debug: getDebugInfo/getAdminCheck/getStorageDebug
  - Token templates: getTokenTemplates/getTokenTemplate/saveTokenTemplate/deleteTokenTemplate/importTokenTemplates

- localPolicyService (src/services/localPolicyService.ts)
  - Simple localStorage-based policy persistence for QueryBuilderPage.

## 7. Types
- src/types/auth.ts: User, AuthState, LoginResponse, TokenValidationResponse
- src/types/api.ts: API-level types
- src/types/admin.ts: TokenListResponse, AppInfo, APIKey, CreateAPIKeyRequest, TokenActivityResponse, AppRegistrationResult, RotateSecretResult, etc.

## 8. Backend Integration Placeholders (to be expanded in Step 3)
- Map each service method to backend endpoint (path, method, expected payload/response)
- Note auth requirements for each route
- Identify where react-query could wrap service calls for caching/async state

## 9. File Index (for tracking)
- src/App.tsx
- src/main.tsx
- src/components/{APIKeyModal,Layout,Modal,PermissionSelector,RolesModal,RuleBuilder,TokenBuilder,TokenDetailsModal,TokenTemplates}.tsx
- src/pages/{AdminPage,CallbackPage,HomePage,LoginPage,QueryBuilderPage,TokenAdministrationPage}.tsx
- src/contexts/AuthContext.tsx
- src/services/{api,authService,adminService,localPolicyService}.ts
- src/types/{admin,api,auth}.ts


[Work-in-progress document; per-file sections will be appended below in Step 3.]


---

### File: src/App.tsx
- Exports: default App component
- Local components: ProtectedRoute, PublicRoute, AppRoutes
- Providers: QueryClientProvider, AuthProvider
- Routing: BrowserRouter with routes to /login, /auth/callback, /, /admin, /query-builder, /token-admin; fallback * -> /
- Dependencies: react-router-dom, @tanstack/react-query, AuthContext, pages, Layout
- Behavior:
  - ProtectedRoute reads isAuthenticated/loading from AuthContext and either renders children, redirects to /login, or shows Loading UI
  - PublicRoute redirects to / when authenticated
  - App creates QueryClient and composes providers and Router around AppRoutes


### File: src/main.tsx
- Entry point that mounts React app using React 18 createRoot
- Imports global styles index.css and App component
- Renders <App /> into #root from index.html


### File: src/components/Layout.tsx
- Purpose: App shell with sidebar navigation, user info, and logout
- Props: { children: React.ReactNode }
- Context: useAuth() -> { user, isAuthenticated, logout }
- State: sidebarCollapsed (boolean) persisted under 'sidebarCollapsed' in localStorage
- Structure:
  - Sidebar (fixed, styled-components) with Header, Content (buttons), Footer (Logout)
  - SidebarToggle button (fixed) to collapse/expand sidebar
  - MainContent renders children and shifts width based on collapsed state
- Navigation: onClick handlers set window.location.href to '/', '/admin', '/token-admin', '/query-builder'
- Notes: If not authenticated, returns children without shell (guards at route-level still apply)


### File: src/contexts/AuthContext.tsx
- Types: AuthState, User; local AuthAction union with actions LOGIN_START, LOGIN_SUCCESS, LOGIN_FAILURE, LOGOUT, SET_LOADING, SET_ERROR, CLEAR_ERROR
- State shape: { isAuthenticated: boolean; user: User|null; token: string|null; loading: boolean; error: string|null }
- Reducer transitions implement standard auth lifecycle
- Provider behavior:
  - On mount: if current path is public (/login or /auth/callback), dispatch LOGOUT; else run checkAuth()
  - checkAuth(): reads token from authService; if absent -> LOGOUT; else parallel validateToken + getCurrentUser; if valid -> LOGIN_SUCCESS with user+token; if invalid or error -> clearAuthToken + LOGOUT
  - login(): dispatch LOGIN_START then authService.login() (redirect)
  - logout(): await authService.logout(); finally dispatch LOGOUT
  - clearError(): CLEAR_ERROR
- Exports: AuthProvider, useAuth() hook, default AuthContext


### File: src/services/api.ts
- Purpose: Axios wrapper with auth and error handling
- Setup:
  - baseURL: '/'
  - timeout: 10s
  - withCredentials: false
  - Request interceptor: attaches Authorization: Bearer <localStorage.access_token>
  - Response interceptor: on 401 -> remove token and redirect to /login
- Methods: request<T>(), get/post/put/delete/patch
- Token helpers: setAuthToken(token), clearAuthToken(), getAuthToken()


### File: src/services/authService.ts
- Purpose: Auth/OAuth flows and user/token operations
- Constants: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_REDIRECT_URI, AZURE_SCOPE
- Key methods:
  - login(): build Azure authorize URL with state; persist state; redirect
  - exchangeCodeForToken(code): POST /auth/token/exchange { code, redirect_uri }
  - logout(): GET /auth/logout; clear token; redirect '/'
  - validateToken(token?): POST /auth/validate
  - getCurrentUser(): GET /auth/whoami
  - getMyToken(): GET /auth/my-token
  - refreshToken(refreshToken): POST /auth/token
  - getOAuthToken(grantType, refreshToken?): POST /oauth/token (multipart/form-data)
  - isAuthenticated(): boolean via local token presence
  - getAuthToken/setAuthToken/clearAuthToken(): proxy to apiService
  - getEffectiveIdentity(tenantId?): GET /iam/me with optional X-Tenant-ID header
  - revokeToken(token, tokenTypeHint?): POST /auth/revoke


### File: src/services/adminService.ts
- Purpose: Admin API client for tokens, apps, keys, endpoints, permissions, groups, rotation, debug, and token templates
- Methods (grouped):
  - Tokens: getInternalTokens(), getAzureTokens(), getTokenActivity(id), getAzureTokenActivity(id), removeToken(id), removeAzureToken(id)
  - Apps: getApps(), getApp(clientId), createApp(data), updateApp(clientId, data), deleteApp(clientId)
  - API Keys: getAppAPIKeys(clientId), createAPIKey(clientId, request), revokeAPIKey(clientId, keyId), rotateAPIKey(clientId, keyId, gracePeriodHours), rotateAppSecret(clientId)
  - Endpoints: getAppEndpoints(clientId), updateAppEndpoints(clientId, endpoints), triggerDiscovery(clientId)
  - Permissions: getAppPermissions(clientId), getAppPermissionTree(clientId)
  - Azure AD Groups: searchAzureGroups(search?, top=20)
  - Rotation: manualRotationCheck(), getRotationPolicies(), setRotationPolicy(clientId, daysBeforeExpiry, gracePeriodHours, autoRotate, notifyWebhook?)
  - Debug: getDebugInfo(), getAdminCheck(), getStorageDebug()
  - Token Templates: getTokenTemplates(), getTokenTemplate(name), saveTokenTemplate(template), deleteTokenTemplate(name), importTokenTemplates(templates)
- Types used: TokenListResponse, AppInfo, APIKey, APIKeyCreationResponse, CreateAPIKeyRequest, TokenActivityResponse, AppRegistrationResult, RotateSecretResult


### File: src/services/localPolicyService.ts
- Purpose: Persist query-builder policies per clientId/role in localStorage
- Storage key: 'cids:policies'
- Types: SavedPolicyEntry { clientId, role, updatedAt, tree }
- Methods:
  - savePolicy(clientId, role, tree): upsert entry with current ISO timestamp
  - loadPolicy(clientId, role): returns SavedPolicyEntry | null
  - deletePolicy(clientId, role): removes entry and prunes empty clientId buckets
  - listPolicies(): returns SavedPolicyEntry[] sorted by updatedAt desc
- Notes: Uses JSON.parse/stringify with basic error tolerance on read


### File: src/pages/QueryBuilderPage.tsx
- Purpose: UI for building and persisting query policies (using RAQB Antd UI)
- Libraries: @react-awesome-query-builder/ui + antd theme config; styled-components
- Local state: clientId (default 'demo-app'), role ('admin'), tree (immutable), savedOpen (bool)
- Derived: jsonTree = QbUtils.getTree(tree)
- Fields: name(text), email(text), department(select IT/Finance/HR), age(number)
- Actions:
  - New: reset tree to empty group
  - Load: read from localPolicyService.loadPolicy(clientId, role) and setTree
  - Save: localPolicyService.savePolicy(clientId, role, tree)
  - Export: download JSON { clientId, role, tree: QbUtils.getTree(tree) }
  - Import: file input -> parse -> set clientId/role/tree
  - Reset: reset tree to empty group
- Saved Policies section: listPolicies() table with Load/Delete
- Output: shows JSON of current tree


### File: src/pages/TokenAdministrationPage.tsx
- Purpose: Token admin UI with tabs (Builder, Templates, Testing, Settings, Logs)
- Composition: TokenBuilder, TokenTemplates, TokenDetailsModal; relies on adminService for logs
- State: activeTab, templateToLoad, internalTokens, azureTokens, loading, error, filterText, sortKey, selectedToken, isDetailsModalOpen
- Effects: when activeTab === 'logs', fetchTokens()
- fetchTokens(): parallel getInternalTokens + getAzureTokens; sets state
- Logs view: filter/sort combined internal+azure tokens; actions: Details (open modal), Activity (fetch per-token activity), Revoke (remove token)
- Helpers: formatDate, shorten


### File: src/components/TokenTemplates.tsx
- Props: { onLoadTemplate?(template) }
- State: templates[], selectedTemplate, showImport, importJson, searchTerm, editingGroups, groupInput, selectedGroups[], showSuggestions, azureGroups[], activeSuggestionIndex, loadingGroups, searchTimeout
- Effects: on mount -> loadTemplates()
- Backend interactions: adminService.getTokenTemplates(), importTokenTemplates(), saveTokenTemplate(), deleteTokenTemplate(), searchAzureGroups()
- Features:
  - List/filter templates; select to preview/details
  - Import/export single/all templates; dedupe/overwrite handling
  - Edit AD groups with Azure search autocomplete (debounced); save to backend and localStorage
  - Toggle enabled; set default; adjust priority; persist changes
  - onLoadTemplate callback or localStorage handoff to TokenBuilder
- Helpers: generateTokenStructure(claims)


### File: src/components/TokenBuilder.tsx
- Props: { templateToLoad?: any }
- State: claims[], selectedClaim, showAddClaim, newClaimKey/type/description, templateName
- Data: standardClaims (JWT std claims), customClaimTemplates (common app claims)
- Initialization:
  - If templateToLoad provided: set claims/name from it
  - Else try localStorage 'cids_token_template_current'; if not custom, load predefined current production structure (std + CIDS custom claims)
- Actions:
  - addStandardClaim(claim): add to claims with unique id
  - addCustomClaim(): add new custom claim from input
  - removeClaim(id), updateClaim(id, partial)
  - saveTemplate(): persist to backend via adminService.saveTokenTemplate and cache to localStorage
  - loadCurrentProductionTemplate(): reset to predefined current structure
- Derived: tokenStructure: JSON skeleton from claims by type
- UI: three panels (claims library; editor with active claims + details; right preview of JSON and sample token)


### File: src/components/TokenDetailsModal.tsx
- Props: { isOpen: boolean; onClose: () => void; token: any }
- Uses generic Modal component; CSS module for styling
- Behavior:
  - On open with token, attempts to decode JWT from token.full_access_token/access_token or id_token variants; adds formatted timestamps
  - Tabs: Decoded Claims (header, payload, signature) and Raw Token (with Copy to Clipboard)
  - Token info header with user, type, issued/expires, subject, issuer, audience, revoked status
- Helpers: decodeJWT(cleanToken), formatValue


### File: src/pages/CallbackPage.tsx
- Purpose: Handle Azure OAuth redirect; exchange code or extract token; set token; verify; redirect
- Hooks: useNavigate, useSearchParams, useAuth().checkAuth
- Flow:
  - If error param -> show error
  - If code present: verify state vs localStorage('oauth_state'); clear; call authService.exchangeCodeForToken(code); set token; replace URL; checkAuth(); success -> redirect to /admin
  - Else if URL fragment has access_token: set token; replace URL; checkAuth(); success -> redirect to /
  - Else: error
- UI: Card with processing/success/error states; Retry navigates to /login


### File: src/pages/HomePage.tsx
- Purpose: Display current user's session and token info; quick test actions
- Hooks: useAuth() for user/isAuthenticated; local state for token info and collapsible sections
- Effects: on isAuthenticated -> fetchTokenInfo() via authService.getMyToken()
- Sections:
  - Available Actions: buttons to get session tokens (authService.getSessionToken()), validate token, fetch public key via apiService
  - Current Session: shows user identity and AD groups
  - Internal Access Token: shows raw token and decoded claims from myToken.claims or user.raw_claims
  - API Response: shows last action response JSON


### File: src/pages/AdminPage.tsx
- Purpose: Admin portal to manage apps, endpoints, discovery, API keys, and role mappings
- Hooks: useAuth(); local state for apps list, modals, registration form
- Effects: on mount -> loadApps() via adminService.getApps()
- Actions:
  - Register app: adminService.createApp(payload) with optional initial API key
  - Rotate secret, Delete app
  - View endpoints: getAppPermissionTree or fallback getAppEndpoints; triggerDiscovery
  - Role mappings: view via getRoleMappings; open RolesModal to edit (separate component)
  - API Keys: open APIKeyModal to manage
- UI: Registered apps list with details and actions; App Registration form

### File: src/pages/LoginPage.tsx
- Purpose: Azure AD login screen
- Hooks: useAuth() for login(), loading, error, clearError
- Behavior: Clicking login clears error and calls login() which redirects to Azure authorize URL
- UI: Styled card with description and Sign in button; shows error and loading spinner


### File: src/components/Modal.tsx
- Props: { isOpen, onClose, title, children, width?='80%', maxHeight?='80vh' }
- Behavior: Adds keydown Escape listener when open; locks body scroll; overlay click closes; click inside content stops propagation
- Structure: overlay -> content -> header (title + close) -> body(children)
- Used by: TokenDetailsModal, APIKeyModal, RolesModal


### File: src/components/APIKeyModal.tsx
- Props: { isOpen, onClose, clientId, appName }
- State: loading, apiKeys[], generatedKey, formData { name, permissions, ttl_days }
- Effects: when opened with clientId -> loadAPIKeys() via adminService.getAppAPIKeys
- Actions:
  - Generate: adminService.createAPIKey(clientId, { name, permissions[], ttl_days|undefined }) -> sets generatedKey and reloads list
  - Rotate: adminService.rotateAPIKey(clientId, keyId, 24) -> sets generatedKey and reloads
  - Revoke: adminService.revokeAPIKey(clientId, keyId) -> reloads
  - Copy to clipboard for generated key
- UI: Key generation form; list of existing keys with status badges and actions


### File: src/components/PermissionSelector.tsx
- Props: { isOpen, onClose, clientId, appName, roleName, currentPermissions, currentResourceScopes, onSave(permissions, resourceScopes) }
- State: loading, permissionTree, error, expandedResources(Set), ruleBuilderOpen/context, resourcePermissions map, actionPermissions map, savedFilters map, viewFiltersModal/context, editingFilterId
- Effects: when opened -> fetchPermissions() via adminService.getAppPermissionTree; migrateOldFilters(); persist savedFilters to localStorage per clientId+role
- Behavior:
  - Toggle resource/action allow/deny/unset; propagate resource-level to actions; sync resource state when all actions match
  - Open RuleBuilder for resource/action/field to create filters; manage multiple filters per key; view/edit/delete existing filters
  - Save permissions compiles allowed actions and resourceScopes from filters; stores unified role config in localStorage and calls onSave
- UI: Modal with tree of resources -> actions -> fields, badges for wildcard/sensitive, endpoint info, filter counts, Save Permissions


### File: src/components/RolesModal.tsx
- Props: { isOpen, onClose, clientId, appName }
- State: roles[], loading, error, createMode, selectedRole, permissionSelectorOpen, AD group search UI state
- Effects: on open -> fetchRoles(): loads role mappings via adminService.getRoleMappings and merges with saved permissions from localStorage
- Actions:
  - Create role: build mappings dict combining existing roles; adminService.setRoleMappings; refresh
  - Edit AD groups: debounced Azure search via adminService.searchAzureGroups; add/remove groups; persists by recomputing all mappings and setRoleMappings
  - Delete role: recompute mappings without role; setRoleMappings
  - Edit Permissions: opens PermissionSelector; onSave updates local roles state; unified role config stored in PermissionSelector
  - Export: per-role or all-roles export to JSON with permissions and RLS filters derived from saved unified config
- UI: Modal listing roles with stats and actions; Create Role form with AD group suggestions; embeds PermissionSelector


### File: src/components/RuleBuilder.tsx
- Props: { isOpen, onClose, onSave?(filterKey, expression), context?: { type: 'resource'|'action'|'field'; clientId; appName; resource?; action?; field?; fieldMetadata?; filterKey?; existingFilter? } }
- State: ruleExpression, selectedTemplate, showHelp, testResult, isTesting
- Behavior:
  - On open: load context.existingFilter into editor
  - Templates: click to preload common SQL WHERE snippets (User Email Match, Department Match, etc.)
  - Insert function buttons: insert common variables/functions (@current_user_id, CURRENT_DATE, etc.)
  - Validate SQL: local checks to ensure expression is a WHERE clause fragment (no SELECT/DROP/etc.)
  - Save: calls onSave(filterKey, ruleExpression) and closes
- UI: Modal with left panel (templates/functions), main editor with help and examples, footer actions


### File: src/types/admin.ts
- TokenInfo: token metadata and previews
- TokenListResponse: { total, tokens: TokenInfo[], admin_user }
- AppInfo: client details + discovery fields
- AppRegistrationResult: app + client_secret + optional api_key
- RotateSecretResult: rotation output
- APIKey: key metadata and usage
- APIKeyCreationResponse: { api_key, metadata }
- CreateAPIKeyRequest: { name, permissions[], ttl_days? }
- TokenActivity, TokenActivityResponse: audit trail models

### File: src/types/api.ts
- ApiResponse<T>
- PaginatedResponse<T>
- Endpoint { method, path, desc, discovered? }
- AppEndpoints { endpoints: Endpoint[]; version; updated_at; updated_by; has_discovered? }
- DiscoveryResponse
- EffectiveIdentity: computed permissions and identity
- DebugResponse: server/platform/time info + examples

### File: src/types/auth.ts
- User: identity, groups, permissions, token timestamps, raw_claims
- AuthState: global auth state shape
- LoginResponse: OAuth token response
- TokenValidationResponse: result of /auth/validate
- SessionData: aggregate of tokens/claims/user
