## CIDS cleanup and restructuring plan (non‑breaking)

### Goals
- Reduce clutter and ambiguity without changing runtime or business behavior
- Standardize structure for backend, frontend, test apps, scripts, docs, and infra
- Remove committed build artifacts and vendor folders; keep lockfiles
- Prepare for CI/CD, better local dev experience, and future modularization

### Current state (observed)
- Backend: CIDS/azure-auth-app (FastAPI/Flask-like services, scripts, static, test apps inside)
- Frontend: CIDS/cids-frontend (React + Vite + TS)
- BFF: CIDS/bff-service (currently empty)
- Test/example apps: scattered (e.g., azure-auth-app/test_apps/... and CIDS/test-app)
- Misc: SQL, README/docs, logs, certs/keys, node_modules committed

### Target top-level layout
- apps/
  - backend/
    - azure-auth-app/  (existing backend app, 1:1 move)
    - bff-service/     (keep or archive; see decision below)
  - frontend/
    - cids-frontend/   (existing React app, 1:1 move)
- test-apps/
  - discovery_fastapi_app/ (move from azure-auth-app/test_apps/discovery_fastapi_app)
  - other example apps currently under azure-auth-app and CIDS/test-app
- packages/
  - py/cids-common/        (future: shared Python models/utils; do not create yet)
  - ts/cids-ui/            (future: shared UI components; do not create yet)
- infra/
  - docker/ (Dockerfiles if/when we add them)
  - compose/ (docker-compose.yml + envs)
  - k8s/ (manifests, if used later)
- scripts/ (utility bash/python scripts; non-product code)
- docs/ (all md docs consolidated; architecture, guides, specs)
- .github/workflows/ (CI for lint/test/build; added in a later phase)

Note: The first wave focuses on moving folders, removing vendor/build artifacts from git, and consolidating docs. Code internals remain unchanged.

### Housekeeping standards
- Git hygiene
  - Add .gitignore rules for node_modules, dist/build, .venv, __pycache__, .pytest_cache, .DS_Store, .env*, coverage*, .mypy_cache
  - Remove committed node_modules and other build artifacts from history (working tree first); keep package-lock.json and requirements*.txt
- Environments
  - Keep env.example templates; move sensitive pem/keys out of repo or into a secrets/ folder with .gitignore
  - Do not change how apps read env yet
- Python
  - Keep current requirements*.txt; later consider requirements/ (base, dev, test)
  - Formatting/lint later: black, isort, flake8/ruff, mypy
- Node/Frontend
  - Ensure package-lock.json is kept; npm ci reproducibility
  - Formatting/lint later: eslint + prettier

### Non-breaking migration plan (phased)
- Phase 0: Prep (no functional changes)
  1) Create new top-level directories: apps/{backend,frontend}, test-apps, docs, infra/{docker,compose}, scripts
  2) Introduce .gitignore updates (as above) without deleting anything yet
  3) Move markdown docs to docs/ (update relative links only within docs; application code untouched)

- Phase 1: Vendor/build artifacts cleanup
  1) Git-remove committed node_modules under CIDS/azure-auth-app and CIDS/cids-frontend: git rm -r --cached …; keep lockfiles; add ignore rules
  2) Remove committed logs and transient files (e.g., server.log, cids_server.log, simple_test_report*.json) from git and add ignore rules
  3) Move cert/key files to secrets/ with .gitignore; keep copies locally for dev

- Phase 2: Directory moves (preserve behavior)
  1) Move CIDS/azure-auth-app → apps/backend/azure-auth-app (git mv)
  2) Move CIDS/cids-frontend → apps/frontend/cids-frontend (git mv)
  3) Move test apps:
     - apps/backend/azure-auth-app/test_apps/discovery_fastapi_app → test-apps/discovery_fastapi_app
     - CIDS/test-app → test-apps/sqlite_demo (or similar)
  4) Misc files: postgres_rls_example.sql → docs/examples/sql/postgres_rls_example.sql
  5) Do not modify import paths or code in this phase. Validate by running existing start commands from the new working directories (see Verification).

- Phase 3: Scripts and entry points (minimal)
  1) Add thin run scripts in scripts/ that cd into the correct app folder and invoke the current commands (avoids code changes). Examples:
     - scripts/dev-backend.sh: cd apps/backend/azure-auth-app && <existing run cmd>
     - scripts/dev-frontend.sh: cd apps/frontend/cids-frontend && npm run dev
  2) Keep package.json and python entry points unchanged

- Phase 4: CI scaffolding (optional, non-breaking)
  1) Add .github/workflows/ci.yml that runs lint/test/build for both apps using matrices
  2) No publishing/deploy; only checks

### Verification after each phase
- Backend
  - From apps/backend/azure-auth-app: run the discovery FastAPI app at http://localhost:5001/discovery/endpoints (unchanged per current workflow)
  - Run any existing Python tests: pytest -q (if present)
- Frontend
  - From apps/frontend/cids-frontend: npm ci && npm run build && npm run dev to ensure dev server works
- General
  - Spot-check docs links by opening docs/markdown files and confirming relative links resolve in GitHub UI

### Decisions to make (before Phase 2)
- bff-service
  - If unused, archive to docs/decisions/ARCHIVE_BFF.md and remove folder
  - If planned, leave as apps/backend/bff-service (empty placeholder with README)
- Secrets handling
  - Keep local-only secrets in secrets/ (gitignored) vs. move to a proper secret manager later
- Test-apps naming
  - Choose final names (e.g., discovery_fastapi_app, sqlite_demo) and a README per app describing purpose and run steps

### Future (post-restructure; optional)
- Shared libraries
  - Extract common Python code to packages/py/cids-common (editable install via pip)
  - Extract shared UI components to packages/ts/cids-ui (npm workspace) if duplication exists
- Tooling
  - Pre-commit hooks for black/isort/ruff/eslint/prettier
  - Type checking: mypy for Python, strict TS config for frontend
- Infra
  - docker-compose for local dev: backend, frontend, and any dependencies (postgres/mock auth)
  - Parameterize ports and envs via .env files

### Acceptance criteria
- No change to runtime behavior or external interfaces
- All existing start scripts/commands still work via thin wrappers in scripts/
- Frontend builds and serves; backend discovery endpoints work unchanged
- Repo is navigable: apps/, test-apps/, docs/, infra/, scripts/ are clear and self-explanatory
- No vendor/build artifacts or logs committed to git; lockfiles retained

### Quick checklist
- [ ] Create directories: apps/, test-apps/, docs/, infra/{docker,compose}, scripts/
- [ ] Add .gitignore and remove committed artifacts (keep lockfiles)
- [ ] Move docs to docs/
- [ ] Move azure-auth-app and cids-frontend under apps/
- [ ] Move test apps under test-apps/
- [ ] Add scripts/dev-*.sh wrappers
- [ ] Validate backend endpoints and frontend dev server
- [ ] Decide fate of bff-service
- [ ] Open small follow-up tasks for CI and tooling