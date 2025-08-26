Frontend monorepo root

Purpose:
- Hold all browser-based UI apps and shared UI libraries.
- Nothing moved here yet. Existing UI apps (e.g., CIDS/cids-frontend) can be migrated later.

Structure (proposed):
- apps/   -> individual frontend applications (e.g., portals, admin UIs)
- libs/   -> shared UI libraries/components/hooks/utilities
- public/ -> shared static assets (favicons, logos) if needed
- tests/  -> cross-app e2e or shared test utilities
- docs/   -> frontend-specific documentation

