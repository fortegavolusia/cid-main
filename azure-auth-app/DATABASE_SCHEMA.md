# Database Schema Documentation

This document captures all data fields currently used in the application's in-memory storage.
It will be used as a reference when migrating to a real database.

## Current Data Storage

### 1. Sessions Table
Currently stored in: `main.py` - `sessions: Dict[str, dict]`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| session_id | UUID (Primary Key) | Unique session identifier | "f47ac10b-58cc-4372-a567-0e02b2c3d479" |
| oauth_state | String | OAuth state parameter for CSRF protection | "lg45y9LkDrREMw44Y2MbSnCYc3bgVxV3DDGovujgaqw" |
| return_url | String | URL to redirect after auth | "/" |
| internal_token | String | Internal JWT access token (deprecated field) | "eyJ0eXAiOiJKV1Q..." |
| access_token | String | Internal JWT access token | "eyJ0eXAiOiJKV1Q..." |
| refresh_token | String | Internal refresh token | "Ws7yQKq7h_KXuGh..." |
| azure_id_token | String | Original Azure ID token | "eyJ0eXAiOiJKV1Q..." |
| azure_claims | JSON | Decoded Azure token claims | {"sub": "...", "name": "...", ...} |
| user | JSON | User information object | See User Info structure below |
| token_id | String | Reference to issued_tokens entry | "550e8400-e29b-41d4-a716-446655440000" |

#### User Info Structure (stored in session.user)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| name | String | User's display name | "John N Bailey" |
| email | String | User's email address | "john.bailey@company.com" |
| sub | String | Azure AD subject identifier | "XnidUzlFgv9N6Mny9QFn0qQ3FwauUT7vK2o0L7eeFBU" |
| groups | Array[Object] | User's AD groups | See Group structure below |
| token_issued | String | When token was issued | "2024-01-07 10:30:45" |
| token_expires | String | When token expires | "2024-01-07 11:30:45" |
| token_valid | Boolean | Token validity status | true |
| raw_claims | JSON | Original Azure claims | {...} |

#### Group Structure (stored in user.groups)
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | String | Azure AD Group ID | "abc123def-4567-890a-bcde-f1234567890a" |
| displayName | String | Group display name | "Engineering Team" |
| type | String | Group type | "group" |

### 2. Refresh Tokens Table
Currently stored in: `refresh_token_store.py` - `tokens: Dict[str, Tuple[dict, float]]`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| token_hash | String (Primary Key) | SHA256 hash of refresh token | "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3" |
| user_info | JSON | User information (see below) | {...} |
| expiry | Float | Unix timestamp of expiry | 1707307845.123456 |

#### Refresh Token User Info
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| sub | String | User's Azure AD subject ID | "XnidUzlFgv9N6Mny9QFn0qQ3FwauUT7vK2o0L7eeFBU" |
| name | String | User's display name | "John N Bailey" |
| email | String | User's email | "john.bailey@company.com" |
| groups | Array[Object] | User's AD groups | Same as session user groups |
| family_id | String | Token family ID for rotation | "ADKbCAWJya-35qyWs6vKYQ" |

### 3. Token Families Table
Currently stored in: `refresh_token_store.py` - `token_families: Dict[str, str]`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| family_id | String (Primary Key) | Token family identifier | "ADKbCAWJya-35qyWs6vKYQ" |
| latest_token_hash | String | Hash of latest token in family | "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3" |

## Data Relationships

1. **Sessions** ↔ **Users**: One-to-one (user info embedded in session)
2. **Refresh Tokens** ↔ **Users**: Many-to-one (multiple tokens per user possible)
3. **Token Families** ↔ **Refresh Tokens**: One-to-many (family tracks token rotation)

## Indexes Needed

When migrating to a real database, create indexes on:
- sessions.session_id (Primary Key)
- refresh_tokens.token_hash (Primary Key)
- refresh_tokens.user_info.sub (for user token lookups)
- refresh_tokens.expiry (for cleanup queries)
- token_families.family_id (Primary Key)

## TTL/Expiry Requirements

- **Sessions**: No explicit TTL currently (should be ~24 hours)
- **Refresh Tokens**: 30 days (2,592,000 seconds)
- **OAuth State**: Should expire after 5-10 minutes if unused

### 4. Issued Tokens Table
Currently stored in: `main.py` - `issued_tokens: Dict[str, dict]`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | UUID (Primary Key) | Unique token identifier (same as token_id) | "550e8400-e29b-41d4-a716-446655440000" |
| access_token | String | Full JWT access token | "eyJ0eXAiOiJKV1Q..." |
| refresh_token | String | Full refresh token | "Ws7yQKq7h_KXuGh..." |
| user | JSON | User information object | See User structure below |
| issued_at | String | When token was issued (ISO format) | "2024-01-07T10:30:45.123456Z" |
| expires_at | String | When token expires (ISO format) | "2024-01-07T11:30:45.123456Z" |
| source | String | How token was created | "azure_callback", "refresh_token", "admin_test_token" |
| session_id | String | Reference to session (optional) | "5131626a-9508-4216-beb0-df20dee72b61" |
| parent_refresh_token | String | Parent token for refresh (optional) | "previous_refresh_token..." |
| revoked | Boolean | Whether token has been revoked | false |
| revoked_at | String | When token was revoked (ISO format) | "2024-01-07T11:00:00.000000Z" |
| revoked_by | String | Email of admin who revoked | "admin@company.com" |
| created_by | String | Admin who created test token (optional) | "admin@company.com" |

#### Issued Token User Structure
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| name | String | User's display name | "John N Bailey" |
| email | String | User's email | "john.bailey@company.com" |
| sub | String | Azure AD subject ID | "XnidUzlFgv9N6Mny9QFn0qQ3FwauUT7vK2o0L7eeFBU" |
| groups | Array[Object] | User's AD groups | [{"id": "abc123", "displayName": "Engineering"}] |

### 5. Azure Tokens Table
Currently stored in: `main.py` - `azure_tokens: Dict[str, dict]`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | UUID (Primary Key) | Unique Azure token identifier | "770e8400-e29b-41d4-a716-446655440002" |
| id_token | String | Full Azure ID token | "eyJ0eXAiOiJKV1Q..." |
| access_token | String | Full Azure access token | "eyJ0eXAiOiJKV1Q..." |
| user | JSON | User information object | See User structure below |
| issued_at | String | When token was received (ISO format) | "2024-01-07T10:30:45.123456Z" |
| expires_at | String | When Azure token expires (ISO format) | "2024-01-07T11:30:45.123456Z" |
| subject | String | Azure AD subject identifier | "XnidUzlFgv9N6Mny9QFn0qQ3FwauUT7vK2o0L7eeFBU" |
| issuer | String | Azure token issuer URL | "https://login.microsoftonline.com/{tenant_id}/v2.0" |
| audience | String | Azure token audience | "{client_id}" |
| claims | JSON | Full Azure token claims | {...} |

#### Azure Token User Structure
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| name | String | User's display name | "John N Bailey" |
| email | String | User's email | "john.bailey@company.com" |

### 6. Token Activity Log Table
Currently stored in: `token_activity_logger.py` - `activity_logs: Dict[str, List[Dict[str, Any]]]`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | UUID (Primary Key) | Unique log entry ID | "660e8400-e29b-41d4-a716-446655440001" |
| token_id | UUID (Foreign Key) | Reference to issued token | "550e8400-e29b-41d4-a716-446655440000" |
| timestamp | String | When action occurred (ISO format) | "2024-01-07T10:30:45.123456Z" |
| action | String | Type of action performed | "created", "refreshed", "validated", "revoked", "admin_view" |
| performed_by | JSON | User who performed action (optional) | {"email": "admin@company.com", "name": "Admin User"} |
| details | JSON | Additional action details | {"source": "azure_callback", "endpoint": "/auth/validate"} |
| ip_address | String | Client IP address (optional) | "192.168.1.100" |
| user_agent | String | Client user agent (optional) | "Mozilla/5.0..." |

#### Action Types (from TokenAction enum)
- `created` - Token was created
- `refreshed` - Token was refreshed
- `validated` - Token was validated
- `revoked` - Token was revoked
- `expired` - Token expired
- `login` - User logged in
- `logout` - User logged out
- `access_denied` - Access was denied
- `admin_view` - Admin viewed token details
- `admin_action` - Admin performed an action

## Data Relationships

1. **Sessions** ↔ **Users**: One-to-one (user info embedded in session)
2. **Sessions** ↔ **Issued Tokens**: One-to-many (session_id reference in issued tokens)
3. **Refresh Tokens** ↔ **Users**: Many-to-one (multiple tokens per user possible)
4. **Token Families** ↔ **Refresh Tokens**: One-to-many (family tracks token rotation)
5. **Issued Tokens** ↔ **Users**: Many-to-one (multiple tokens can be issued to same user)
6. **Azure Tokens** ↔ **Users**: Many-to-one (multiple Azure tokens per user over time)
7. **Token Activity Log** ↔ **Issued Tokens**: Many-to-one (multiple log entries per token)

## Indexes Needed

When migrating to a real database, create indexes on:
- sessions.session_id (Primary Key)
- sessions.token_id (for token lookup)
- refresh_tokens.token_hash (Primary Key)
- refresh_tokens.user_info.sub (for user token lookups)
- refresh_tokens.expiry (for cleanup queries)
- token_families.family_id (Primary Key)
- issued_tokens.id (Primary Key)
- issued_tokens.user.sub (for user token lookups)
- issued_tokens.user.email (for user token lookups)
- issued_tokens.expires_at (for cleanup queries)
- issued_tokens.revoked (for filtering active tokens)
- issued_tokens.source (for token source analysis)
- issued_tokens.session_id (for session correlation)
- azure_tokens.id (Primary Key)
- azure_tokens.subject (for user token lookups)
- azure_tokens.user.email (for user token lookups)
- azure_tokens.expires_at (for cleanup queries)
- azure_tokens.issuer (for multi-tenant scenarios)
- token_activity_log.id (Primary Key)
- token_activity_log.token_id (for token history lookups)
- token_activity_log.timestamp (for time-based queries)
- token_activity_log.action (for filtering by action type)
- token_activity_log.performed_by.email (for user activity queries)

## TTL/Expiry Requirements

- **Sessions**: No explicit TTL currently (should be ~24 hours)
- **Refresh Tokens**: 30 days (2,592,000 seconds)
- **OAuth State**: Should expire after 5-10 minutes if unused
- **Issued Tokens**: Variable based on use case (30 minutes default for access tokens)
- **Azure Tokens**: 1 hour (as issued by Azure AD)
- **Token Activity Log**: Retain for compliance period (e.g., 90 days or as required)

## API Endpoints to Database Mapping

When migrating to a real database, these endpoints will map to database operations:

### Read Operations
- `GET /` → Render home page, query `sessions` table by session_id
- `GET /auth/admin/tokens` → Query `issued_tokens` table
- `GET /auth/admin/tokens/{token_id}/activities` → Query `token_activity_log` table by token_id
- `GET /auth/admin/azure-tokens` → Query `azure_tokens` table
- `GET /auth/admin/azure-tokens/{token_id}/activities` → Query `token_activity_log` table by token_id
- `GET /auth/validate` → Query `issued_tokens` table to check token validity
- `GET /auth/whoami` → Query `issued_tokens` table to get current user info
- `GET /auth/public-key` → Return cached public key (no DB query)
- `GET /auth/my-token` → Query `issued_tokens` table by access_token
- `GET /auth/debug/admin-check` → Query `issued_tokens` table and check admin status
- `GET /debug/token-storage` → Query counts from all tables (admin only)
- `GET /debug/timestamps` → Debug endpoint for timestamp testing (no DB query)

### Write Operations
- `GET /auth/login` → Insert into `sessions` (create OAuth state)
- `GET /auth/callback` → Update `sessions`, Insert into `issued_tokens`, `azure_tokens`, `token_activity_log`
- `POST /auth/token` → Insert/Update `issued_tokens`, `refresh_tokens`, `token_families`, `token_activity_log`
- `GET /auth/logout` → Update `sessions` (clear session), Insert into `token_activity_log`
- `POST /auth/revoke` → Update `issued_tokens` (set revoked=true), Update `refresh_tokens`, Insert into `token_activity_log`
- `POST /auth/introspect` → Query `issued_tokens` table, Insert into `token_activity_log` (for validation tracking)
- `POST /auth/admin/tokens/create-test` → Insert into `issued_tokens`, Insert into `token_activity_log` (admin only)
- `DELETE /auth/admin/tokens/{token_id}` → Update `issued_tokens` (set revoked=true), Insert into `token_activity_log`
- `DELETE /auth/admin/azure-tokens/{token_id}` → Delete from `azure_tokens`, Insert into `token_activity_log`
- `GET /auth/admin/tokens/cleanup` → Delete from `issued_tokens` where expires_at < NOW()
- `GET /auth/admin/azure-tokens/cleanup` → Delete from `azure_tokens` where expires_at < NOW()

### Session Operations
- `POST /auth/token/session` → Query `sessions` table by session_id (from cookie)
- OAuth state validation → Query `sessions` table by oauth_state

## UI Considerations for Database Migration

When implementing the database layer, consider these UI features that depend on data queries:

1. **Administration Panel** (`/auth/admin/*` endpoints):
   - Unified token view combines both internal and Azure tokens
   - Requires efficient queries to merge and sort tokens by issued_at
   - Search functionality needs full-text search or LIKE queries across multiple fields
   - Filtering by type (Internal/Azure) and status (Active/Expired/Revoked)
   - Sorting capability on all columns

2. **Token Activity Logs**:
   - Activity logs are shared between internal and Azure tokens
   - Need efficient queries by token_id regardless of token type
   - Consider indexing token_activity_log.token_id for performance

3. **Session Management**:
   - Sessions are identified by HTTP-only cookies
   - Session lookup happens on every page load
   - Consider session caching strategy for performance

### 7. Registered Apps Table
Currently stored in: `app_registration.py` - `registered_apps: Dict[str, dict]`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| client_id | String (Primary Key) | Unique app identifier | "app_a1b2c3d4e5f6" |
| name | String | App display name | "My Application" |
| description | String | App description | "Internal project management app" |
| redirect_uris | JSON Array | Allowed redirect URIs | ["https://myapp.com/callback"] |
| owner_email | String | App owner email | "owner@company.com" |
| is_active | Boolean | Whether app is active | true |
| created_at | String | When app was registered (ISO format) | "2024-01-07T10:30:00Z" |
| updated_at | String | Last update time (ISO format) | "2024-01-07T10:30:00Z" |

### 8. App Secrets Table
Currently stored in: `app_registration.py` - `app_secrets: Dict[str, str]`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| client_id | String (Primary Key) | App identifier | "app_a1b2c3d4e5f6" |
| secret_hash | String | SHA256 hash of client secret | "a665a45920422f9d..." |

### 9. App Role Mappings Table
Currently stored in: `app_registration.py` - `app_role_mappings: Dict[str, List[dict]]`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| client_id | String (Foreign Key) | App identifier | "app_a1b2c3d4e5f6" |
| ad_group | String | Azure AD group name | "Engineering" |
| app_role | String | App-specific role | "editor" |
| created_by | String | Who created the mapping | "admin@company.com" |
| created_at | String | When mapping was created (ISO format) | "2024-01-07T10:30:00Z" |

## Data Relationships

1. **Sessions** ↔ **Users**: One-to-one (user info embedded in session)
2. **Sessions** ↔ **Issued Tokens**: One-to-many (session_id reference in issued tokens)
3. **Refresh Tokens** ↔ **Users**: Many-to-one (multiple tokens per user possible)
4. **Token Families** ↔ **Refresh Tokens**: One-to-many (family tracks token rotation)
5. **Issued Tokens** ↔ **Users**: Many-to-one (multiple tokens can be issued to same user)
6. **Azure Tokens** ↔ **Users**: Many-to-one (multiple Azure tokens per user over time)
7. **Token Activity Log** ↔ **Issued Tokens**: Many-to-one (multiple log entries per token)
8. **Registered Apps** ↔ **App Secrets**: One-to-one (each app has one active secret)
9. **Registered Apps** ↔ **App Role Mappings**: One-to-many (multiple role mappings per app)
10. **Issued Tokens** ↔ **Registered Apps**: Many-to-one (via client_id when app-specific tokens are issued)

## Indexes Needed

When migrating to a real database, create indexes on:
- sessions.session_id (Primary Key)
- sessions.token_id (for token lookup)
- refresh_tokens.token_hash (Primary Key)
- refresh_tokens.user_info.sub (for user token lookups)
- refresh_tokens.expiry (for cleanup queries)
- token_families.family_id (Primary Key)
- issued_tokens.id (Primary Key)
- issued_tokens.user.sub (for user token lookups)
- issued_tokens.user.email (for user token lookups)
- issued_tokens.expires_at (for cleanup queries)
- issued_tokens.revoked (for filtering active tokens)
- issued_tokens.source (for token source analysis)
- issued_tokens.session_id (for session correlation)
- issued_tokens.client_id (for app-specific token lookups)
- azure_tokens.id (Primary Key)
- azure_tokens.subject (for user token lookups)
- azure_tokens.user.email (for user token lookups)
- azure_tokens.expires_at (for cleanup queries)
- azure_tokens.issuer (for multi-tenant scenarios)
- token_activity_log.id (Primary Key)
- token_activity_log.token_id (for token history lookups)
- token_activity_log.timestamp (for time-based queries)
- token_activity_log.action (for filtering by action type)
- token_activity_log.performed_by.email (for user activity queries)
- registered_apps.client_id (Primary Key)
- registered_apps.owner_email (for owner lookups)
- registered_apps.is_active (for filtering active apps)
- app_secrets.client_id (Primary Key)
- app_role_mappings.client_id (for app role lookups)
- app_role_mappings.ad_group (for group-based lookups)

## TTL/Expiry Requirements

- **Sessions**: No explicit TTL currently (should be ~24 hours)
- **Refresh Tokens**: 30 days (2,592,000 seconds)
- **OAuth State**: Should expire after 5-10 minutes if unused
- **Issued Tokens**: Variable based on use case (30 minutes default for access tokens)
- **Azure Tokens**: 1 hour (as issued by Azure AD)
- **Token Activity Log**: Retain for compliance period (e.g., 90 days or as required)
- **Registered Apps**: No expiry (manually managed)
- **App Secrets**: No expiry (manually rotated)
- **App Role Mappings**: No expiry (manually managed)

## Notes

- Timestamps are stored as:
  - Unix timestamps (float) for: Refresh Tokens
  - ISO 8601 DateTime format for: Issued Tokens, Azure Tokens, Token Activity Log, Registered Apps, App Role Mappings
- Token hashes use SHA256
- All IDs (session_id, token_id, azure_token_id) use UUID4
- Client IDs use "app_" prefix + 16 hex characters
- Family IDs use token_urlsafe for URL safety
- No persistent storage of RSA keys (regenerated on restart unless PERSIST_KEYS=true)
- Azure tokens are stored for administrative tracking and debugging purposes only
- All DELETE operations should be soft deletes where appropriate (e.g., tokens should be marked as revoked rather than deleted)
- Token validation should check both expiry time and revoked status
- The `/auth/introspect` endpoint follows OAuth 2.0 Token Introspection RFC 7662
- Admin access is determined by email list (ADMIN_EMAILS env var) or AD group membership (ADMIN_GROUP_IDS env var)
- App client secrets are stored as SHA256 hashes and cannot be retrieved after initial creation