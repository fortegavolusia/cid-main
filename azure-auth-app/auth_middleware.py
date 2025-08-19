"""
FastAPI middleware for protecting endpoints with auth service tokens
"""
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import httpx
from authlib.jose import jwt
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Security scheme for OpenAPI docs
security = HTTPBearer()

class AuthMiddleware:
    """Middleware for validating tokens from the centralized auth service"""
    
    def __init__(self, auth_service_url: str = "https://10.1.5.58:8000", verify_ssl: bool = False):
        self.auth_service_url = auth_service_url
        self.verify_ssl = verify_ssl
        self.public_keys = None
        
    async def get_public_keys(self):
        """Fetch and cache public keys from auth service"""
        if not self.public_keys:
            async with httpx.AsyncClient(verify=self.verify_ssl) as client:
                response = await client.get(f"{self.auth_service_url}/auth/public-key")
                response.raise_for_status()
                self.public_keys = response.json()
        return self.public_keys
    
    async def validate_token(self, token: str) -> dict:
        """Validate token (JWT or API key) and return claims"""
        try:
            # Check if this is an API key
            if token.startswith('cids_ak_'):
                # Validate API key with auth service
                async with httpx.AsyncClient(verify=self.verify_ssl) as client:
                    response = await client.get(
                        f"{self.auth_service_url}/auth/validate",
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    if response.status_code != 200:
                        raise HTTPException(status_code=401, detail="Invalid API key")
                    
                    data = response.json()
                    if not data.get('valid'):
                        raise HTTPException(status_code=401, detail="Invalid API key")
                    
                    # Return claims-like structure for API key
                    return {
                        'sub': data.get('sub'),
                        'email': data.get('email'),
                        'name': data.get('name'),
                        'permissions': data.get('permissions', []),
                        'app_client_id': data.get('app_client_id'),
                        'auth_type': 'api_key'
                    }
            
            # Regular JWT validation
            # Get public keys
            jwks = await self.get_public_keys()
            
            # Decode and validate
            claims = jwt.decode(token, jwks)
            
            # Check expiration
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
        """Validate request token"""
        if not credentials:
            raise HTTPException(status_code=401, detail="No authorization provided")
        
        token = credentials.credentials
        claims = await self.validate_token(token)
        
        # Add user info to request state
        request.state.user = {
            'sub': claims.get('sub'),
            'email': claims.get('email'),
            'name': claims.get('name'),
            'groups': claims.get('groups', [])
        }
        
        return claims


def require_auth(auth_middleware: AuthMiddleware):
    """Decorator to require authentication for an endpoint"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, credentials: HTTPAuthorizationCredentials = security, *args, **kwargs):
            await auth_middleware(request, credentials)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_groups(groups: List[str], auth_middleware: AuthMiddleware):
    """Decorator to require specific groups for an endpoint"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, credentials: HTTPAuthorizationCredentials = security, *args, **kwargs):
            claims = await auth_middleware(request, credentials)
            
            user_groups = claims.get('groups', [])
            if not any(group in user_groups for group in groups):
                raise HTTPException(
                    status_code=403, 
                    detail=f"User not in required groups: {groups}"
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# Example usage in a FastAPI app:
"""
from fastapi import FastAPI, Request
from auth_middleware import AuthMiddleware, require_auth, require_groups

app = FastAPI()
auth = AuthMiddleware()

@app.get("/protected")
@require_auth(auth)
async def protected_endpoint(request: Request):
    user = request.state.user
    return {"message": f"Hello {user['name']}!", "groups": user['groups']}

@app.get("/admin")
@require_groups(["admin-group-id"], auth)
async def admin_endpoint(request: Request):
    return {"message": "Admin access granted"}
"""