from typing import Optional

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .cids_auth import CIDSClient

app = FastAPI(title="CID Test App – FastAPI")

# Dev CORS for local frontend on 3100
origins = [
    "http://localhost:3100",
    "http://127.0.0.1:3100",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


async def get_identity(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.split(" ", 1)[1]
    cids = CIDSClient()
    return await cids.validate(token)


@app.get("/")
async def root():
    return {"status": "ok", "service": "cid-test-app"}


@app.get("/secure/ping")
async def secure_ping(identity = Depends(get_identity)):
    return {"message": "pong", "identity": identity}


@app.get("/secure/admin")
async def secure_admin(identity = Depends(get_identity)):
    # Demo protection: require admin permission (for app-to-app case, it's a permission string)
    perms = set(identity.get("permissions", [])) if isinstance(identity, dict) else set()
    if "admin" not in perms:
        raise HTTPException(status_code=403, detail="Admin permission required")
    return {"message": "admin ok", "identity": identity}


@app.get("/whoami")
async def whoami(identity = Depends(get_identity)):
    return JSONResponse(identity)


@app.get("/discovery")
async def discovery_endpoint():
    """
    CID Discovery endpoint - returns metadata about this app's endpoints and fields
    """
    return {
        "app_id": "sample-test-app",
        "app_name": "CID Sample Test App",
        "version": "2.0",
        "description": "A sample FastAPI application for testing CID integration",
        "endpoints": [
            {
                "path": "/",
                "method": "GET",
                "operation_id": "root",
                "description": "Health check endpoint",
                "response_fields": {
                    "status": {
                        "type": "string",
                        "description": "Service status",
                        "sensitive": False,
                        "pii": False,
                        "phi": False
                    },
                    "service": {
                        "type": "string",
                        "description": "Service name",
                        "sensitive": False,
                        "pii": False,
                        "phi": False
                    }
                }
            },
            {
                "path": "/secure/ping",
                "method": "GET",
                "operation_id": "secure_ping",
                "description": "Authenticated ping endpoint that returns user identity",
                "response_fields": {
                    "message": {
                        "type": "string",
                        "description": "Response message",
                        "sensitive": False,
                        "pii": False,
                        "phi": False
                    },
                    "identity": {
                        "type": "object",
                        "description": "Complete user identity information from CID",
                        "sensitive": True,
                        "pii": True,
                        "phi": False
                    },
                    "identity.email": {
                        "type": "string",
                        "description": "User email address",
                        "sensitive": False,
                        "pii": True,
                        "phi": False
                    },
                    "identity.name": {
                        "type": "string",
                        "description": "User full name",
                        "sensitive": False,
                        "pii": True,
                        "phi": False
                    },
                    "identity.sub": {
                        "type": "string",
                        "description": "User subject identifier",
                        "sensitive": False,
                        "pii": True,
                        "phi": False
                    },
                    "identity.permissions": {
                        "type": "array",
                        "description": "User permissions list",
                        "sensitive": True,
                        "pii": False,
                        "phi": False
                    }
                }
            },
            {
                "path": "/secure/admin",
                "method": "GET",
                "operation_id": "secure_admin",
                "description": "Admin-only endpoint requiring admin permission",
                "required_roles": ["admin"],
                "response_fields": {
                    "message": {
                        "type": "string",
                        "description": "Admin confirmation message",
                        "sensitive": False,
                        "pii": False,
                        "phi": False
                    },
                    "identity": {
                        "type": "object",
                        "description": "Admin user identity information",
                        "sensitive": True,
                        "pii": True,
                        "phi": False
                    },
                    "identity.email": {
                        "type": "string",
                        "description": "Admin user email",
                        "sensitive": False,
                        "pii": True,
                        "phi": False
                    },
                    "identity.permissions": {
                        "type": "array",
                        "description": "Admin permissions (includes admin)",
                        "sensitive": True,
                        "pii": False,
                        "phi": False
                    }
                }
            },
            {
                "path": "/whoami",
                "method": "GET",
                "operation_id": "whoami",
                "description": "Returns the authenticated user's identity information",
                "response_fields": {
                    "auth_type": {
                        "type": "string",
                        "description": "Authentication method used (jwt or api_key)",
                        "sensitive": False,
                        "pii": False,
                        "phi": False
                    },
                    "email": {
                        "type": "string",
                        "description": "User email address",
                        "sensitive": False,
                        "pii": True,
                        "phi": False
                    },
                    "name": {
                        "type": "string",
                        "description": "User display name",
                        "sensitive": False,
                        "pii": True,
                        "phi": False
                    },
                    "sub": {
                        "type": "string",
                        "description": "User subject identifier",
                        "sensitive": False,
                        "pii": True,
                        "phi": False
                    },
                    "app_client_id": {
                        "type": "string",
                        "description": "Client ID of the calling application",
                        "sensitive": False,
                        "pii": False,
                        "phi": False
                    },
                    "permissions": {
                        "type": "array",
                        "description": "List of user permissions",
                        "sensitive": True,
                        "pii": False,
                        "phi": False
                    },
                    "valid": {
                        "type": "boolean",
                        "description": "Token validation status",
                        "sensitive": False,
                        "pii": False,
                        "phi": False
                    }
                }
            }
        ]
    }

