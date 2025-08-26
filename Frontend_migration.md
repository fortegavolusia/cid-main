# Frontend Migration - Current Status (So Far)

## Status
- [x] Create new top-level structure without moving any code yet
  - [x] frontend/
    - [x] apps/
    - [x] libs/
    - [x] tests/
    - [x] docs/
  - [x] backend/ (scaffolded for completeness; no backend moves yet)
    - [x] services/
    - [x] libs/
    - [x] infra/
    - [x] tests/
    - [x] docs/

## Scope
- [x] This document captures only what we have decided and prepared so far for frontend migration.
- [x] No files have been moved yet.

## Planned relocation: cids-frontend app (including node_modules and dist)
Base destination folder for the app:
- [ ] Create folder: CIDS/frontend/apps/cids-frontend

## File/Folder mapping (to be moved as-is)
- [ ] CIDS/cids-frontend/README.md → CIDS/frontend/apps/cids-frontend/README.md
- [ ] CIDS/cids-frontend/package.json → CIDS/frontend/apps/cids-frontend/package.json
- [ ] CIDS/cids-frontend/package-lock.json → CIDS/frontend/apps/cids-frontend/package-lock.json
- [ ] CIDS/cids-frontend/eslint.config.js → CIDS/frontend/apps/cids-frontend/eslint.config.js
- [ ] CIDS/cids-frontend/vite.config.ts → CIDS/frontend/apps/cids-frontend/vite.config.ts
- [ ] CIDS/cids-frontend/index.html → CIDS/frontend/apps/cids-frontend/index.html
- [ ] CIDS/cids-frontend/tsconfig.json → CIDS/frontend/apps/cids-frontend/tsconfig.json
- [ ] CIDS/cids-frontend/tsconfig.app.json → CIDS/frontend/apps/cids-frontend/tsconfig.app.json
- [ ] CIDS/cids-frontend/tsconfig.node.json → CIDS/frontend/apps/cids-frontend/tsconfig.node.json
- [ ] CIDS/cids-frontend/.env.example (if present) → CIDS/frontend/apps/cids-frontend/.env.example
- [ ] CIDS/cids-frontend/.gitignore → CIDS/frontend/apps/cids-frontend/.gitignore
- [ ] CIDS/cids-frontend/public/** → CIDS/frontend/apps/cids-frontend/public/**
- [ ] CIDS/cids-frontend/src/** → CIDS/frontend/apps/cids-frontend/src/**
- [ ] CIDS/cids-frontend/node_modules/** → CIDS/frontend/apps/cids-frontend/node_modules/**
- [ ] CIDS/cids-frontend/dist/** → CIDS/frontend/apps/cids-frontend/dist/**

## Not included at this time (frontend-facing but attached to backend/test apps)
- [x] CIDS/azure-auth-app/templates/** (Jinja templates for backend service)
- [x] CIDS/azure-auth-app/azure-auth-app/static/** (static assets served by backend)
- [x] CIDS/azure-auth-app/test_apps/discovery_fastapi_app/static/** (test app static page)

## Notes
- [x] Objective is to keep the cids-frontend app self-contained under frontend/apps/cids-frontend.
- [x] No code changes or path updates have been performed yet.

## Required changes after move (per file)
- README.md
  - [ ] Update any paths or references to old location (if any). Current README is template content; likely no changes.
- package.json
  - [ ] No script changes expected; npm run dev/build should work from the app folder.
  - [ ] If any root-level tooling expects package.json at old path, update those scripts/CI jobs accordingly.
- package-lock.json
  - [ ] No changes required; consider fresh install after move if needed.
- eslint.config.js
  - [ ] No path changes expected. globalIgnores(['dist']) remains valid.
- vite.config.ts
  - [ ] Paths to cert.pem and key.pem are relative; keep files alongside vite.config.ts in the new folder.
  - [ ] loadEnv(process.cwd()) remains correct when run from the app folder. If run from repo root, set root option or use fileURLToPath(import.meta.url) to resolve paths.
- index.html
  - [ ] Uses root-relative /src and /vite.svg served by Vite; unchanged when app root is the working directory.
- tsconfig.json
  - [ ] Project references (./tsconfig.app.json, ./tsconfig.node.json) remain correct.
- tsconfig.app.json
  - [ ] tsBuildInfoFile at ./node_modules/.tmp/... stays valid; ensure node_modules moves with the app.
  - [ ] include: ["src"] remains correct.
- tsconfig.node.json
  - [ ] tsBuildInfoFile at ./node_modules/.tmp/... stays valid; ensure node_modules moves with the app.
  - [ ] include: ["vite.config.ts"] remains correct.
- .env.example
  - [ ] Keys remain the same. Update any path-like values if they referenced old location (none currently).
- .gitignore
  - [ ] Keep ignores (node_modules, dist, etc.) scoped to app directory.
- public/**
  - [ ] Asset references continue to work via Vite static handling; no changes.
- src/**
  - [ ] No absolute imports to old repo paths detected. Imports are relative; no changes expected.
- node_modules/**
  - [ ] Moving installed deps may work, but a clean install is safer. If moved, ensure permissions and symlinks remain valid.
- dist/**
  - [ ] Built assets can be moved as-is. Consider rebuilding after move to ensure paths are correct.

