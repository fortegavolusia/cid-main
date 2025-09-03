import os
from typing import Optional, Dict, Any

import httpx
from fastapi import HTTPException


class CIDSClient:
    def __init__(self, base_url: Optional[str] = None, verify_ssl: Optional[bool] = None):
        self.base_url = (base_url or os.getenv("CID_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        if verify_ssl is None:
            env = os.getenv("CID_VERIFY_SSL")
            verify_ssl = False if (env is not None and env.lower() in ("0", "false", "no")) else True
        self.verify_ssl = verify_ssl

    async def validate(self, token: str) -> Dict[str, Any]:
        if not token:
            raise HTTPException(status_code=401, detail="No token provided")

        try:
            async with httpx.AsyncClient(verify=self.verify_ssl, timeout=10.0) as client:
                if token.startswith("cids_ak_"):
                    # API Key validation must go via GET /auth/validate with Authorization header
                    resp = await client.get(
                        f"{self.base_url}/auth/validate",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if resp.status_code != 200:
                        raise HTTPException(status_code=401, detail="Invalid API key")
                    data = resp.json()
                    if not data.get("valid"):
                        raise HTTPException(status_code=401, detail="Invalid API key")
                    # Normalize to a claims-like shape
                    return {
                        "auth_type": "api_key",
                        "app_client_id": data.get("app_client_id"),
                        "email": data.get("email"),
                        "name": data.get("name"),
                        "permissions": data.get("permissions", []),
                        "sub": data.get("sub"),
                        "valid": True,
                    }
                else:
                    # JWT validation: POST /auth/validate with token in body
                    resp = await client.post(
                        f"{self.base_url}/auth/validate",
                        json={"token": token},
                    )
                    if resp.status_code != 200:
                        raise HTTPException(status_code=401, detail="Invalid token")
                    data = resp.json()
                    if not data.get("valid"):
                        raise HTTPException(status_code=401, detail=data.get("error") or "Invalid token")
                    return {"auth_type": "jwt", **data}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Token validation error: {e}")

