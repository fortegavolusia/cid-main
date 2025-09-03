# FastAPI Test Backend (CID sample app)

A minimal FastAPI service that trusts CID for auth:
- Accepts user JWTs (Authorization: Bearer <token>)
- Accepts CIDS API keys (Authorization: Bearer cids_ak_...)
- Validates both against the running CID instance via /auth/validate

## Run

- export CID_BASE_URL=http://127.0.0.1:8000
- uvicorn app.main:app --port 8091 --reload

## Endpoints

- GET /              -> health
- GET /secure/ping   -> requires valid token or API key (returns identity)
- GET /secure/admin  -> requires 'admin' permission
- GET /whoami        -> returns the identity object

