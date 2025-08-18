"""
CIDS Auth Library for Microservices

This library provides authentication and field-level authorization for CIDS-compliant applications.
It handles token validation and field filtering based on permissions.
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
    """Base exception for CIDS auth errors"""
    pass


class CIDSPermissionDenied(CIDSAuthError):
    """Raised when user lacks required permissions"""
    pass


class CIDSTokenError(CIDSAuthError):
    """Raised when token validation fails"""
    pass


class CIDSAuth:
    """
    CIDS Authentication and Authorization Client
    
    Example:
        auth = CIDSAuth(
            cids_url="https://cids.example.com",
            client_id="app_123",
            client_secret="secret",
            verify_ssl=True
        )
        
        # In your request handler:
        user_info = auth.validate_token(token)
        filtered_data = auth.filter_response(data, user_info['permissions'])
    """
    
    def __init__(
        self,
        cids_url: str,
        client_id: str,
        client_secret: Optional[str] = None,
        verify_ssl: bool = True,
        cache_public_key: bool = True
    ):
        self.cids_url = cids_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl
        self._public_key = None
        self._public_key_cached_at = None
        self.cache_public_key = cache_public_key
        self.cache_duration = 3600  # 1 hour
        
    def _get_public_key(self) -> str:
        """Get CIDS public key for token verification"""
        # Check cache
        if self.cache_public_key and self._public_key:
            if (datetime.utcnow().timestamp() - self._public_key_cached_at) < self.cache_duration:
                return self._public_key
        
        # Fetch from CIDS
        try:
            response = requests.get(
                f"{self.cids_url}/auth/public-key",
                verify=self.verify_ssl,
                timeout=10
            )
            response.raise_for_status()
            
            key_data = response.json()
            public_key = key_data.get('public_key')
            
            if not public_key:
                raise CIDSAuthError("No public key returned from CIDS")
            
            # Cache the key
            if self.cache_public_key:
                self._public_key = public_key
                self._public_key_cached_at = datetime.utcnow().timestamp()
            
            return public_key
            
        except requests.RequestException as e:
            raise CIDSAuthError(f"Failed to fetch public key from CIDS: {e}")
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a CIDS token and return user information
        
        Args:
            token: JWT token from Authorization header
            
        Returns:
            Dict containing user info and permissions
            
        Raises:
            CIDSTokenError: If token is invalid
        """
        if not token:
            raise CIDSTokenError("No token provided")
        
        # Remove Bearer prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        try:
            # Get public key
            public_key = self._get_public_key()
            
            # Decode and verify token
            claims = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=[self.client_id, 'internal-services']
            )
            
            # Extract permissions for this app
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
        """
        Check if user has a specific permission
        
        Args:
            user_info: User info from validate_token
            permission: Permission key (e.g., "users.read.email")
            
        Returns:
            True if user has permission
        """
        user_permissions = set(user_info.get('permissions', []))
        
        # Direct permission check
        if permission in user_permissions:
            return True
        
        # Check wildcard permissions
        # e.g., users.read.* grants users.read.email
        parts = permission.split('.')
        for i in range(len(parts)):
            wildcard = '.'.join(parts[:i+1]) + '.*'
            if wildcard in user_permissions:
                return True
        
        # Check full wildcard
        if '*' in user_permissions:
            return True
        
        return False
    
    def require_permission(self, permission: str):
        """
        Decorator to require specific permission for a route
        
        Example:
            @app.get("/users/{user_id}/salary")
            @auth.require_permission("users.read.salary")
            async def get_user_salary(user_id: str, user_info: dict = Depends(auth.get_current_user)):
                # Handler code
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Look for user_info in kwargs
                user_info = kwargs.get('user_info')
                if not user_info:
                    raise CIDSPermissionDenied("No user information provided")
                
                if not self.check_permission(user_info, permission):
                    raise CIDSPermissionDenied(f"Permission '{permission}' required")
                
                return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Look for user_info in kwargs
                user_info = kwargs.get('user_info')
                if not user_info:
                    raise CIDSPermissionDenied("No user information provided")
                
                if not self.check_permission(user_info, permission):
                    raise CIDSPermissionDenied(f"Permission '{permission}' required")
                
                return func(*args, **kwargs)
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    def filter_fields(
        self,
        data: Union[Dict, List[Dict]],
        user_permissions: List[str],
        resource: str,
        action: str = "read"
    ) -> Union[Dict, List[Dict]]:
        """
        Filter response fields based on user permissions
        
        Args:
            data: Response data (dict or list of dicts)
            user_permissions: User's permissions
            resource: Resource name (e.g., "users")
            action: Action type (e.g., "read")
            
        Returns:
            Filtered data with only permitted fields
        """
        if isinstance(data, list):
            return [self._filter_single_object(obj, user_permissions, resource, action) for obj in data]
        else:
            return self._filter_single_object(data, user_permissions, resource, action)
    
    def _filter_single_object(
        self,
        obj: Dict[str, Any],
        user_permissions: List[str],
        resource: str,
        action: str
    ) -> Dict[str, Any]:
        """Filter a single object based on permissions"""
        if not isinstance(obj, dict):
            return obj
        
        permission_set = set(user_permissions)
        filtered = {}
        
        # Check for wildcard permissions
        if f"{self.client_id}.{resource}.{action}.*" in permission_set or "*" in permission_set:
            return obj  # User has access to all fields
        
        # Filter each field
        for field_name, field_value in obj.items():
            permission_key = f"{self.client_id}.{resource}.{action}.{field_name}"
            
            if self._has_field_permission(permission_key, permission_set):
                # Handle nested objects
                if isinstance(field_value, dict):
                    filtered[field_name] = self._filter_single_object(
                        field_value,
                        user_permissions,
                        f"{resource}_{field_name}",
                        action
                    )
                elif isinstance(field_value, list) and field_value and isinstance(field_value[0], dict):
                    filtered[field_name] = [
                        self._filter_single_object(item, user_permissions, f"{resource}_{field_name}", action)
                        for item in field_value
                    ]
                else:
                    filtered[field_name] = field_value
        
        return filtered
    
    def _has_field_permission(self, permission_key: str, permission_set: Set[str]) -> bool:
        """Check if user has permission for a specific field"""
        # Direct permission
        if permission_key in permission_set:
            return True
        
        # Check wildcards
        parts = permission_key.split('.')
        for i in range(len(parts) - 1):
            wildcard = '.'.join(parts[:i+1]) + '.*'
            if wildcard in permission_set:
                return True
        
        return False
    
    # FastAPI dependency
    async def get_current_user(self, authorization: Optional[str] = None) -> Dict[str, Any]:
        """
        FastAPI dependency to get current user from token
        
        Example:
            from fastapi import Depends, Header
            
            @app.get("/profile")
            async def get_profile(
                user_info: dict = Depends(auth.get_current_user),
                authorization: Optional[str] = Header(None)
            ):
                return {"email": user_info["email"]}
        """
        if not authorization:
            raise CIDSTokenError("No authorization header")
        
        return self.validate_token(authorization)
    
    # Flask decorator
    def require_auth(self, f: Callable) -> Callable:
        """
        Flask decorator to require authentication
        
        Example:
            @app.route('/profile')
            @auth.require_auth
            def get_profile():
                user_info = g.user_info
                return jsonify({"email": user_info["email"]})
        """
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


# Convenience function for environment-based configuration
def from_env() -> CIDSAuth:
    """
    Create CIDSAuth instance from environment variables
    
    Required environment variables:
        - CIDS_URL: URL of CIDS service
        - CIDS_CLIENT_ID: Your app's client ID
        - CIDS_CLIENT_SECRET: Your app's client secret (optional)
    """
    cids_url = os.getenv('CIDS_URL')
    if not cids_url:
        raise ValueError("CIDS_URL environment variable not set")
    
    client_id = os.getenv('CIDS_CLIENT_ID')
    if not client_id:
        raise ValueError("CIDS_CLIENT_ID environment variable not set")
    
    client_secret = os.getenv('CIDS_CLIENT_SECRET')
    verify_ssl = os.getenv('CIDS_VERIFY_SSL', 'true').lower() == 'true'
    
    return CIDSAuth(
        cids_url=cids_url,
        client_id=client_id,
        client_secret=client_secret,
        verify_ssl=verify_ssl
    )