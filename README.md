## CIDS – Centralized Identity & Discovery Service

CIDS is a centralized authentication and authorization service with discovery-driven permissions. It provides:

- A FastAPI backend issuing JWTs, validating tokens, managing API keys, roles, and policies
- A React (Vite + TypeScript) frontend for administration and self-service token/permission management
- Docs and integration guides for SPAs and web apps

This repository currently contains a migrated backend and a new frontend. Some legacy references in docs may still mention "azure-auth-app" while migration completes.

---

### Repository Structure

- backend/
  - api/ – FastAPI application (entrypoint: backend.api.main:app)
  - services/ – JWT/JWKS, endpoints, discovery, roles, policy, tokens, API keys, auditing
  - background/ – API key rotation scheduler
  - infra/ – data, config, and logs directories used by services
  - utils/ – paths and helpers
  - docs/ – migration plans and notes
- cids-frontend/ – React + Vite + TypeScript admin UI
- docs/ – integration guides
- CLAUDE.md – project overview and detailed notes (internal dev doc)

---

### Prerequisites

- Python 3.10+
- Node 18+ (or 20+ recommended)
- OpenSSL (for local HTTPS dev certificates)

Environment variables (backend):
- AZURE_TENANT_ID – your Azure AD tenant ID
- AZURE_CLIENT_ID – app registration client ID used by CIDS for OAuth code exchange
- AZURE_CLIENT_SECRET – client secret for the above app registration
- ADMIN_EMAILS – comma-separated list of admin emails (optional; defaults to admin@example.com)
- ADMIN_GROUP_IDS – comma-separated Azure AD group IDs treated as admins (optional)
- DEV_CROSS_ORIGIN=true – enable permissive CORS to the local React dev server (optional)
- PERSIST_KEYS=true – persist signing keys to ./keys (optional; default is in-memory)

The backend will also load variables from backend/.env if present.

---

### Backend – Local Development

1) Create and activate a virtual environment

- Linux/macOS
  - python3 -m venv .venv
  - source .venv/bin/activate
- Windows (PowerShell)
  - py -3 -m venv .venv
  - .venv\\Scripts\\Activate.ps1

2) Install dependencies

This repo currently does not include a pyproject or requirements file. Install typical runtime deps:

- pip install fastapi "uvicorn[standard]" pydantic httpx python-dotenv jinja2

3) Set environment

- Create backend/.env with your values, for example:
  - AZURE_TENANT_ID=...
  - AZURE_CLIENT_ID=...
  - AZURE_CLIENT_SECRET=...
  - DEV_CROSS_ORIGIN=true
  - ADMIN_EMAILS=you@example.com

4) Run the API server

- uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

Notes:
- JWKS:            GET /.well-known/jwks.json
- OIDC metadata:   GET /.well-known/openid-configuration
- Public key:      GET /auth/public-key
- Validation:      GET /auth/validate (Bearer token or CIDS API key)
- Whoami:          GET /auth/whoami
- Admin APIs:      Under /auth/admin/* (require admin auth)

Data files (JSON) are written to backend/infra/data/app_data. Audits and logs may be under backend/infra/logs.

---

### Frontend – Local Development (HTTPS)

1) Install dependencies

- cd cids-frontend
- npm install

2) Create local HTTPS certs for Vite (only for development)

- From cids-frontend/, generate or place cert.pem and key.pem. For example (self-signed):
  - openssl req -x509 -nodes -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 \
    -subj "/CN=localhost"

3) Configure API origin (optional but recommended)

- By default, Vite uses VITE_API_ORIGIN or falls back to https://10.1.5.58:8000
- To point to your local backend over HTTP, run with an env var:
  - VITE_API_ORIGIN=http://localhost:8000 npm run dev

4) Start the dev server

- npm run dev
- Open https://localhost:3000 (accept the self-signed cert warning)

The Vite dev server proxies API routes to VITE_API_ORIGIN (see cids-frontend/vite.config.ts).

---

### Integration Guides

- docs/integration/spa-with-cids.md – SPA (React/Vue/Angular) integration
- docs/integration/web-app-with-cids.md – Server-rendered web apps

---

### Production Notes

- Secure key management: run with PERSIST_KEYS=true and store keys securely; rotate regularly
- Configure TLS termination (reverse proxy or run uvicorn with certs) for the backend in production
- Store app registration data and audit logs on persistent volumes (see backend/infra)
- Populate ADMIN_* and other env vars via your secrets manager

---

### Contributing / Next Steps

- Add a pyproject.toml or requirements.txt capturing backend dependencies
- Add linting, tests, and CI workflows
- Consider splitting backend/api/main.py into routers under backend/api/routes/*
- Replace any remaining legacy paths or references noted in backend/docs/azure-auth-app-migration-plan.md

---

### License

TBD

