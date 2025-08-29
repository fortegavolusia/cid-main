"""FastAPI Auth Middleware (migrated)"""
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import httpx
from authlib.jose import jwt
import logging
from functools import wraps
import os

logger = logging.getLogger(__name__)

security = HTTPBearer()


class AuthMiddleware:
    def __init__(self, auth_service_url: Optional[str] = None, verify_ssl: Optional[bool] = None):
        self.auth_service_url = (auth_service_url or os.getenv('CIDS_URL') or "http://localhost:8000").rstrip('/')
        self.verify_ssl = verify_ssl if verify_ssl is not None else (os.getenv('CIDS_VERIFY_SSL', 'false').lower() == 'true')
        self.public_keys = None

    async def get_public_keys(self):
        if not self.public_keys:
            async with httpx.AsyncClient(verify=self.verify_ssl) as client:
                response = await client.get(f"{self.auth_service_url}/auth/public-key")
                response.raise_for_status()
                self.public_keys = response.json()
        return self.public_keys

    async def validate_token(self, token: str) -> dict:
        try:
            if token.startswith('cids_ak_'):
                async with httpx.AsyncClient(verify=self.verify_ssl) as client:
                    response = await client.get(f"{self.auth_service_url}/auth/validate", headers={"Authorization": f"Bearer {token}"})
                    if response.status_code != 200:
                        raise HTTPException(status_code=401, detail="Invalid API key")
                    data = response.json()
                    if not data.get('valid'):
                        raise HTTPException(status_code=401, detail="Invalid API key")
                    return {
                        'sub': data.get('sub'),
                        'email': data.get('email'),
                        'name': data.get('name'),
                        'permissions': data.get('permissions', []),
                        'app_client_id': data.get('app_client_id'),
                        'auth_type': 'api_key',
                    }
            jwks = await self.get_public_keys()
            claims = jwt.decode(token, jwks)
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            exp = claims.get('exp')
            if exp and datetime.fromtimestamp(exp, timezone.utc) < now:
                raise HTTPException(status_code=401, detail="Token has expired")
            claims['auth_type'] = 'jwt'
            return claims
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")

    async def __call__(self, request: Request, credentials: HTTPAuthorizationCredentials = None):
        if not credentials:
            raise HTTPException(status_code=401, detail="No authorization provided")
        token = credentials.credentials
        claims = await self.validate_token(token)
        request.state.user = {
            'sub': claims.get('sub'),
            'email': claims.get('email'),
            'name': claims.get('name'),
            'groups': claims.get('groups', []),
        }
        return claims


def require_auth(auth_middleware: AuthMiddleware):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, credentials: HTTPAuthorizationCredentials = security, *args, **kwargs):
            await auth_middleware(request, credentials)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_groups(groups: List[str], auth_middleware: AuthMiddleware):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, credentials: HTTPAuthorizationCredentials = security, *args, **kwargs):
            claims = await auth_middleware(request, credentials)
            user_groups = claims.get('groups', [])
            if not any(group in user_groups for group in groups):
                raise HTTPException(status_code=403, detail=f"User not in required groups: {groups}")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

