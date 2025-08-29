"""
CIDS Auth Library for Microservices (migrated)
"""
from typing import Dict, List, Any, Optional, Set, Union, Callable
from functools import wraps
import requests
import jwt
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class CIDSAuthError(Exception):
    pass


class CIDSPermissionDenied(CIDSAuthError):
    pass


class CIDSTokenError(CIDSAuthError):
    pass


class CIDSAuth:
    def __init__(self, cids_url: str, client_id: str, client_secret: Optional[str] = None, verify_ssl: bool = True, cache_public_key: bool = True):
        self.cids_url = cids_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl
        self._public_key = None
        self._public_key_cached_at = None
        self.cache_public_key = cache_public_key
        self.cache_duration = 3600

    def _get_public_key(self) -> str:
        if self.cache_public_key and self._public_key:
            if (datetime.utcnow().timestamp() - self._public_key_cached_at) < self.cache_duration:
                return self._public_key
        try:
            response = requests.get(f"{self.cids_url}/auth/public-key", verify=self.verify_ssl, timeout=10)
            response.raise_for_status()
            key_data = response.json()
            public_key = key_data.get('public_key')
            if not public_key:
                raise CIDSAuthError("No public key returned from CIDS")
            if self.cache_public_key:
                self._public_key = public_key
                self._public_key_cached_at = datetime.utcnow().timestamp()
            return public_key
        except requests.RequestException as e:
            raise CIDSAuthError(f"Failed to fetch public key from CIDS: {e}")

    def validate_token(self, token: str) -> Dict[str, Any]:
        if not token:
            raise CIDSTokenError("No token provided")
        if token.startswith('Bearer '):
            token = token[7:]
        try:
            public_key = self._get_public_key()
            claims = jwt.decode(token, public_key, algorithms=['RS256'], audience=[self.client_id, 'internal-services'])
            all_permissions = claims.get('permissions', {})
            app_permissions = all_permissions.get(self.client_id, [])
            return {
                'sub': claims.get('sub'),
                'email': claims.get('email'),
                'name': claims.get('name'),
                'groups': claims.get('groups', []),
                'roles': claims.get('roles', {}).get(self.client_id, []),
                'permissions': app_permissions,
                'claims': claims
            }
        except jwt.ExpiredSignatureError:
            raise CIDSTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise CIDSTokenError(f"Invalid token: {e}")
        except Exception as e:
            raise CIDSTokenError(f"Token validation failed: {e}")

    def check_permission(self, user_info: Dict[str, Any], permission: str) -> bool:
        user_permissions = set(user_info.get('permissions', []))
        if permission in user_permissions:
            return True
        parts = permission.split('.')
        for i in range(len(parts)):
            wildcard = '.'.join(parts[:i+1]) + '.*'
            if wildcard in user_permissions:
                return True
        if '*' in user_permissions:
            return True
        return False

    def require_permission(self, permission: str):
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                user_info = kwargs.get('user_info')
                if not user_info:
                    raise CIDSPermissionDenied("No user information provided")
                if not self.check_permission(user_info, permission):
                    raise CIDSPermissionDenied(f"Permission '{permission}' required")
                return await func(*args, **kwargs)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                user_info = kwargs.get('user_info')
                if not user_info:
                    raise CIDSPermissionDenied("No user information provided")
                if not self.check_permission(user_info, permission):
                    raise CIDSPermissionDenied(f"Permission '{permission}' required")
                return func(*args, **kwargs)

            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return decorator

    def filter_fields(self, data: Union[Dict, List[Dict]], user_permissions: List[str], resource: str, action: str = "read") -> Union[Dict, List[Dict]]:
        if isinstance(data, list):
            return [self._filter_single_object(obj, user_permissions, resource, action) for obj in data]
        else:
            return self._filter_single_object(data, user_permissions, resource, action)

    def _filter_single_object(self, obj: Dict[str, Any], user_permissions: List[str], resource: str, action: str) -> Dict[str, Any]:
        if not isinstance(obj, dict):
            return obj
        permission_set = set(user_permissions)
        if f"{self.client_id}.{resource}.{action}.*" in permission_set or "*" in permission_set:
            return obj
        filtered = {}
        for field_name, field_value in obj.items():
            permission_key = f"{self.client_id}.{resource}.{action}.{field_name}"
            if self._has_field_permission(permission_key, permission_set):
                if isinstance(field_value, dict):
                    filtered[field_name] = self._filter_single_object(field_value, user_permissions, f"{resource}_{field_name}", action)
                elif isinstance(field_value, list) and field_value and isinstance(field_value[0], dict):
                    filtered[field_name] = [self._filter_single_object(item, user_permissions, f"{resource}_{field_name}", action) for item in field_value]
                else:
                    filtered[field_name] = field_value
        return filtered

    def _has_field_permission(self, permission_key: str, permission_set: Set[str]) -> bool:
        if permission_key in permission_set:
            return True
        parts = permission_key.split('.')
        for i in range(len(parts) - 1):
            wildcard = '.'.join(parts[:i+1]) + '.*'
            if wildcard in permission_set:
                return True
        return False

    async def get_current_user(self, authorization: Optional[str] = None) -> Dict[str, Any]:
        if not authorization:
            raise CIDSTokenError("No authorization header")
        return self.validate_token(authorization)

    def require_auth(self, f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, g
            token = request.headers.get('Authorization')
            if not token:
                return {"error": "No authorization header"}, 401
            try:
                user_info = self.validate_token(token)
                g.user_info = user_info
                return f(*args, **kwargs)
            except CIDSTokenError as e:
                return {"error": str(e)}, 401
        return decorated_function


def from_env() -> CIDSAuth:
    cids_url = os.getenv('CIDS_URL')
    if not cids_url:
        raise ValueError("CIDS_URL environment variable not set")
    client_id = os.getenv('CIDS_CLIENT_ID')
    if not client_id:
        raise ValueError("CIDS_CLIENT_ID environment variable not set")
    client_secret = os.getenv('CIDS_CLIENT_SECRET')
    verify_ssl = os.getenv('CIDS_VERIFY_SSL', 'true').lower() == 'true'
    return CIDSAuth(cids_url=cids_url, client_id=client_id, client_secret=client_secret, verify_ssl=verify_ssl)

