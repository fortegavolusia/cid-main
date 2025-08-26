Backend monorepo root

Purpose:
- Hold all server-side services, APIs, workers, and shared server libraries.
- Nothing moved here yet. Existing backends (e.g., CIDS/azure-auth-app, CIDS/bff-service) can be migrated later.

Structure (proposed):
- services/ -> individual deployable services/APIs (FastAPI/Flask/etc.)
- libs/     -> shared backend libraries/utilities/domain modules
- infra/    -> infra as code (compose, terraform, helm) if adopted
- tests/    -> cross-service integration tests or shared test utilities
- docs/     -> backend-specific documentation

