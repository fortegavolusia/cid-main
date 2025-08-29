## CIDS Azure Auth App → Backend Migration Plan

This document proposes where to relocate each file from CIDS/azure-auth-app into the organized backend/ layout, and the adjustments required after moving. The goal is plan-and-document only; no code is moved yet.

### Backend target structure (current dirs)
- backend/api
- backend/background
- backend/core
- backend/docs
- backend/infra
- backend/libs
- backend/models
- backend/schemas
- backend/services
- backend/tests
- backend/utils

---

## Mappings by file/folder

### API surface and FastAPI app
- azure-auth-app/main.py → backend/api/auth_app.py
  - Purpose: FastAPI routes and composition of services (JWT, endpoints, roles, policy, discovery, templates, API keys, admin endpoints)
  - Required changes:
    - Update intra-package imports to absolute, e.g. `from app_endpoints import ...` → `from backend.services.endpoints import ...` (see services mapping below).
    - Replace file-relative data paths with `backend` data path helper (see utils/storage).
    - Consider splitting very large router into multiple routers under backend/api/routes/* (optional in later refactor).

### Services and business logic
- azure-auth-app/jwt_utils.py → backend/services/jwt.py
  - Exposes JWTManager and JWKS operations consumed by app and middleware.
  - Changes: adjust import of TokenTemplateManager `from backend.services.token_templates import TokenTemplateManager`.

- azure-auth-app/jwks_handler.py → backend/services/jwks.py
  - JWKSHandler used for /.well-known & metadata.
  - Changes: import JWTManager from backend/services/jwt.

- azure-auth-app/app_registration.py → backend/services/app_registration.py
  - App CRUD, secret hashing, role mappings, JSON persistence.
  - Changes: path handling for `app_data` via utils; remove module-level `load_data()` side effects in favor of explicit service init (optional follow-up).

- azure-auth-app/app_endpoints.py → backend/services/endpoints.py
  - Endpoints registry for apps, JSON persistence.
  - Changes: unify with discovery upsert signature; file path helper.

- azure-auth-app/enhanced_discovery_service.py → backend/services/discovery.py
  - Single consolidated discovery service (previously v2) with field metadata and permission generation. supersedes v1; no versioning in code or data.
  - Changes: imports to services; storage paths; endpoints registry import. Remove any `version` branching; always use enhanced format.

- azure-auth-app/discovery_service.py → [DEPRECATED] Do not migrate (v1 removed)
  - Rationale: We no longer maintain v1 discovery. All discovery uses the consolidated discovery service.

- azure-auth-app/discovery_models.py → backend/schemas/discovery.py
  - Pydantic models used by discovery v2 and permission generation.
  - Changes: adjust imports in `discovery_v2.py` and `permission_registry.py`.

- azure-auth-app/permission_registry.py → backend/services/permission_registry.py
  - Central registry of discovered permissions, role permissions, RLS.
  - Changes: update imports to `from backend.schemas.discovery import PermissionMetadata` and use utils path helper.

- azure-auth-app/roles_manager.py → backend/services/roles.py
  - Role CRUD and Azure group mappings.
  - Changes: storage paths via utils; import locations in main.

- azure-auth-app/policy_manager.py → backend/services/policy.py
  - Policy model and active version tracking.
  - Changes: adjust imports; utils path helper.

- azure-auth-app/resource_filter_policy.py → backend/services/resource_filters.py
  - PolicyCompiler/Store/Pusher for RLS-like filters.
  - Changes: storage paths via utils; import sites in main if used.

- azure-auth-app/api_key_manager.py → backend/services/api_keys.py
  - API key CRUD, hashing, validation and DB file.
  - Changes: storage paths; class imports in main; `APIKeyTTL` used in request models → import path in api/auth_app.py.

- azure-auth-app/api_key_rotation_scheduler.py → backend/background/api_key_rotation.py
  - Background scheduler for rotating/cleaning API keys.
  - Changes: update imports to `from backend.services.api_keys import api_key_manager, APIKeyTTL` and `from backend.services.audit import audit_logger` (see below). Update startup registration location in FastAPI app module.

- azure-auth-app/refresh_token_store.py → backend/services/refresh_tokens.py
  - In-memory refresh token rotation and family management.
  - Changes: import path in api/auth_app.py; consider persistence in future.

- azure-auth-app/audit_logger.py → backend/services/audit.py
  - AuditAction enum and AuditLogger with jsonl daily rotation.
  - Changes: import path changes for all callers.

- azure-auth-app/token_activity_logger.py → backend/services/token_activity.py
  - In-memory token activity logs for admin views.
  - Changes: import path in main.

- azure-auth-app/token_templates.py → backend/services/token_templates.py
  - TokenTemplateManager and file-backed templates.
  - Changes: update default path to backend/config/token_templates.json (see infra/config) or keep alongside if preferred; update jwt_utils and main imports.

- azure-auth-app/auth_middleware.py → backend/libs/auth_middleware.py
  - FastAPI middleware/decorators for downstream services.
  - Changes: change `auth_service_url` default to env-driven; import JWT JWKS endpoint path if needed.

- azure-auth-app/cids_auth.py → backend/libs/cids_auth.py
  - Client library for microservices (Flask/FastAPI) to validate and filter.
  - Changes: point public-key endpoint path to backend/api; consider packaging as pip-able later.

### API/CLI scripts and utilities
- azure-auth-app/register_app_api.py → backend/utils/scripts/register_app_api.py
  - CLI script for registering an app via admin token.
  - Changes: update API base URL; paths to .env; requests verify flags.

- azure-auth-app/generate_secret.py → backend/utils/scripts/generate_secret.py
  - Secret generation helper.
  - Changes: none.

- azure-auth-app/debug_* (debug_save_data.py, debug_session.py) → backend/utils/dev/
  - Local debug helpers.
  - Changes: adjust imports.

- azure-auth-app/check_apps.py, check_discovery_ui.py, fix_discovery_persistence.py → backend/utils/maintenance/
  - Ad-hoc maintenance scripts.

### Data and config files
- azure-auth-app/app_data/* → backend/infra/data/app_data/*
  - Files and owners:
    - registered_apps.json (owned by services/app_registration.py)
    - app_secrets.json (owned by services/app_registration.py)
    - app_role_mappings.json (owned by services/app_registration.py)
    - app_endpoints.json (owned by services/endpoints.py)
    - discovered_permissions.json (owned by services/permission_registry.py and services/discovery.py)
    - field_metadata.json (owned by services/discovery.py)
    - role_permissions.json (owned by services/permission_registry.py)
    - role_metadata.json (owned by services/permission_registry.py)
    - rotation_policies.json (owned by background/api_key_rotation.py)
    - audit/*.jsonl (owned by services/audit.py)
  - Changes: introduce a central path resolver utility, e.g., backend/utils/paths.py with functions like data_path("registered_apps.json"). Update all services to use it.

- azure-auth-app/token_templates.json → backend/infra/config/token_templates.json
  - Update TokenTemplateManager default path accordingly.

- azure-auth-app/templates/* → backend/api/templates/*
  - Jinja templates used by main.py endpoints.
  - Changes: Jinja2Templates(directory=...) path in api/auth_app.py.

- azure-auth-app/cert.pem, key.pem → backend/infra/certs/
  - Dev certs only; ensure not committed for prod.

- azure-auth-app/server.log → remove or move to backend/infra/logs/ (ignored).

- azure-auth-app/requirements*.txt, venv/, test_app_venv/, node_modules/ → DO NOT MOVE
  - These are environment or dependency artifacts and should be deleted/ignored. Consolidate Python deps at repo root or backend/pyproject/requirements as per project standards.

### Test apps and examples
- azure-auth-app/test_apps/* → backend/tests/fixtures/test_apps/* (or top-level examples/)
  - Includes FastAPI sample apps and data used for discovery testing.
  - Changes: ensure any relative imports updated; mark as fixtures not shipped in prod.

- example_cids_app.py, client_example.py, enable_discovery_for_flask.py → backend/examples/*
  - Example integrations; keep out of runtime code.

### Admin/registration endpoints wrappers
- azure-auth-app/register_any_app.py, register_app_api.py → backend/utils/scripts/

### Miscellaneous
- build-and-push.sh, restart_server.sh → backend/infra/scripts/
  - Changes: update paths after relocation.

---

## Cross-cutting refactor notes (import and path changes)

1) Import paths
- Change all intra-module imports to package-qualified, e.g.:
  - from app_registration import app_store → from backend.services.app_registration import app_store
  - from app_endpoints import AppEndpointsRegistry → from backend.services.endpoints import AppEndpointsRegistry
  - from jwt_utils import JWTManager → from backend.services.jwt import JWTManager
  - from jwks_handler import JWKSHandler → from backend.services.jwks import JWKSHandler
  - from roles_manager import RolesManager → from backend.services.roles import RolesManager
  - from policy_manager import PolicyManager → from backend.services.policy import PolicyManager
  - from permission_registry import PermissionRegistry → from backend.services.permission_registry import PermissionRegistry
  - from token_templates import TokenTemplateManager → from backend.services.token_templates import TokenTemplateManager
  - from api_key_manager import api_key_manager, APIKeyTTL → from backend.services.api_keys import api_key_manager, APIKeyTTL
  - from api_key_rotation_scheduler import rotation_scheduler, start_rotation_scheduler → from backend.background.api_key_rotation import rotation_scheduler, start_rotation_scheduler
  - from refresh_token_store import refresh_token_store → from backend.services.refresh_tokens import refresh_token_store
  - from audit_logger import audit_logger, AuditAction → from backend.services.audit import audit_logger, AuditAction

2) Data path handling
- Introduce backend/utils/paths.py with helpers:
  - data_path(*parts) → backend/infra/data/app_data/...
  - config_path(*parts) → backend/infra/config/...
  - logs_path(*parts) → backend/infra/logs/...
- Replace hardcoded Path("app_data/...") usages with helpers in services mentioned above.

3) Templates location
- In api/auth_app.py, `templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))` after moving templates to backend/api/templates.

4) Security and env
- Default URLs such as auth_middleware.AuthMiddleware(auth_service_url=...) should be driven by env (e.g., CIDS_URL) with sane local default.

5) Module initialization side effects
- app_registration.load_data() currently runs at import. Prefer explicit initialization in api startup to avoid import-time side effects. Optionally defer to later refactor.

---

## Items to deprecate or exclude from move
- __pycache__ directories, venv/, test_app_venv/, node_modules/, server.log

---

## Open questions / confirmations needed
- Keep discovery v1 and v2 both? Plan maps to discovery_v1.py and discovery_v2.py; confirm deprecation timeline.
- Should token templates live under infra/config or remain adjacent to service? Plan assumes infra/config.
- Tests for services after relocation: create backend/tests/unit for JWT, discovery, permission registry.

---

## Next steps
1) Create utils/paths.py and update 3–4 core services (app_registration, endpoints, permission_registry, api_keys) to use it.
2) Move files per mapping and fix imports in api/auth_app.py and services.
3) Relocate data and templates; adjust paths.
4) Run unit tests and smoke the FastAPI app locally.

