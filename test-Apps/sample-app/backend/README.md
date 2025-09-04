# FastAPI Test Backend (CID sample app)

A minimal FastAPI service that trusts CID for auth:
- Accepts user JWTs (Authorization: Bearer <token>)
- Accepts CIDS API keys (Authorization: Bearer cids_ak_...)
- Validates both against the running CID instance via /auth/validate

## Run

- export CID_BASE_URL=http://127.0.0.1:8000
- uvicorn app.main:app --port 8091 --reload

## Endpoints

- GET /              -> health check
- GET /secure/ping   -> requires valid token or API key (returns identity)
- GET /secure/admin  -> requires 'admin' permission
- GET /whoami        -> returns the identity object
- GET /discovery     -> CID discovery endpoint (returns app metadata for field-level permissions)

## CID Integration

This app now supports CID's enhanced discovery process:

1. **Authentication**: Uses CIDSClient to validate JWT tokens and API keys
2. **Authorization**: Checks permissions (e.g., 'admin' permission for /secure/admin)
3. **Discovery**: Provides /discovery endpoint for CID to discover endpoints and fields

### Discovery Endpoint

The `/discovery` endpoint returns detailed metadata about all endpoints including:
- Field-level information with PII/PHI/sensitive markers
- Authentication requirements
- Permission requirements
- Nested field structures for complex objects

This enables CID to generate granular field-level permissions for role-based access control.

