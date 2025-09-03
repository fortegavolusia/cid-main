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

