# FastAPI entrypoint (migrated from azure-auth-app/main.py)
# NOTE: This is a full move; all imports reference backend.* modules.

from fastapi import FastAPI, Request, HTTPException, Response, Header, Body
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
from datetime import datetime, timedelta
import secrets
import logging
from typing import Dict, Optional, List
import uuid
import json
import urllib.parse
from dotenv import load_dotenv, dotenv_values
from pathlib import Path

from backend.services.jwt import JWTManager
from backend.services.refresh_tokens import refresh_token_store
from backend.services.token_activity import token_activity_logger, TokenAction
from backend.services.app_registration import (
    app_store, RegisterAppRequest, UpdateAppRequest,
    AppResponse, AppRegistrationResponse, SetRoleMappingRequest,
    registered_apps, app_role_mappings
)
from backend.services.jwks import JWKSHandler
from backend.services.endpoints import AppEndpointsRegistry, EndpointsUpdate
from backend.services.roles import RolesManager, RolesUpdate, RoleMappingsUpdate
from backend.services.policy import PolicyManager, PolicyDocument
from backend.services.audit import audit_logger, AuditAction
from backend.services.discovery import DiscoveryService
from backend.services.discovery import DiscoveryService as EnhancedDiscoveryService
from backend.services.permission_registry import PermissionRegistry
from backend.services.token_templates import TokenTemplateManager
from backend.services.api_keys import api_key_manager, APIKeyTTL
from backend.background.api_key_rotation import start_rotation_scheduler, rotation_scheduler
from backend.utils.paths import api_templates_path
from backend.libs.logging_config import setup_logging, get_logging_config, update_logging_config as apply_logging_update
from backend.services.log_reader import read_app_logs

# Request models
class TokenRequest(BaseModel):
    grant_type: str
    refresh_token: Optional[str] = None

class TokenExchangeRequest(BaseModel):
    code: str
    redirect_uri: str

class RevokeTokenRequest(BaseModel):
    token: str
    token_type_hint: Optional[str] = "refresh_token"

# API Key request models
class CreateAPIKeyRequest(BaseModel):
    name: str
    permissions: List[str]
    ttl_days: Optional[int] = APIKeyTTL.DAYS_90.value
    # Optional A2A token behavior fields
    token_template_name: Optional[str] = None
    app_roles_overrides: Optional[Dict[str, List[str]]] = None
    token_ttl_minutes: Optional[int] = 15
    default_audience: Optional[str] = None
    allowed_audiences: Optional[List[str]] = None

class APIKeyResponse(BaseModel):
    key_id: str
    key_prefix: str
    name: str
    permissions: List[str]
    expires_at: str
    created_at: str
    created_by: str
    is_active: bool
    last_used_at: Optional[str] = None
    usage_count: int = 0

class APIKeyCreationResponse(BaseModel):
    api_key: str  # Only returned on creation
    metadata: APIKeyResponse

# Load environment from backend/.env; if absent, rely on process env only
backend_env = Path(__file__).resolve().parents[1] / '.env'
if backend_env.exists():
    load_dotenv(dotenv_path=str(backend_env), override=False)

# Debug log what we loaded (mask secrets)
_loaded_tenant = os.getenv('AZURE_TENANT_ID')
_loaded_client = os.getenv('AZURE_CLIENT_ID')
_loaded_secret = os.getenv('AZURE_CLIENT_SECRET')
logging.getLogger(__name__).info(
    f"Azure env loaded - TENANT_ID={'set' if _loaded_tenant else 'missing'}, CLIENT_ID={'set' if _loaded_client else 'missing'}, CLIENT_SECRET={'set' if _loaded_secret else 'missing'}"
)

app = FastAPI(title="Centralized Auth Service")

def ensure_azure_env():
    """Return Azure OAuth env vars; no legacy fallbacks."""
    return (
        os.getenv('AZURE_TENANT_ID'),
        os.getenv('AZURE_CLIENT_ID'),
        os.getenv('AZURE_CLIENT_SECRET'),
    )

templates = Jinja2Templates(directory=str(api_templates_path()))

# Dev-only cross-origin support for local React dev server
DEV_CROSS_ORIGIN = os.getenv("DEV_CROSS_ORIGIN", "false").lower() == "true"
SAMESITE_POLICY = "none" if DEV_CROSS_ORIGIN else "lax"

if DEV_CROSS_ORIGIN:
    origins = [
        "http://localhost:3000",
        "http://10.1.5.58:3000",
        "https://localhost:3000",
        "https://10.1.5.58:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

class A2ATokenRequest(BaseModel):
    audience: Optional[str] = None
    template_name: Optional[str] = None


# Access log middleware (enabled by default via config)
try:
    from backend.middleware.access_log import access_log_middleware
    app.middleware("http")(access_log_middleware)
except Exception:
    logging.getLogger(__name__).warning("Access log middleware not loaded")

# Add custom Jinja2 filter for datetime conversion

def datetime_filter(timestamp):
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception:
        return "Invalid timestamp"

templates.env.filters['datetime'] = datetime_filter

# Logging
setup_logging()
logger = logging.getLogger(__name__)

# Ensure infra dirs exist on app import
try:
    from backend.utils.paths import ensure_dirs
    ensure_dirs()
except Exception:
    logger.exception("Failed to ensure backend infra directories exist")

# In-memory stores (as in legacy)
sessions: Dict[str, dict] = {}
issued_tokens: Dict[str, dict] = {}
azure_tokens: Dict[str, dict] = {}

# Initialize services
jwt_manager = JWTManager(key_path="./keys" if os.getenv("PERSIST_KEYS", "false").lower() == "true" else None)
jwks_handler = JWKSHandler(jwt_manager)
endpoints_registry = AppEndpointsRegistry()
roles_manager = RolesManager()
policy_manager = PolicyManager()
discovery_service = DiscoveryService(jwt_manager, endpoints_registry)
enhanced_discovery = EnhancedDiscoveryService(jwt_manager, endpoints_registry)
permission_registry = PermissionRegistry()
token_template_manager = TokenTemplateManager()

# Helper functions copied from legacy main (trimmed to essentials)

def get_session(session_id: str) -> dict:
    return sessions.get(session_id, {})

# Well-known and public key endpoints for local dev and discovery
@app.get('/.well-known/jwks.json')
async def get_jwks():
    return JSONResponse(jwks_handler.get_jwks())

@app.get('/.well-known/openid-configuration')
async def get_openid_configuration(request: Request):
    base_url = str(request.base_url).rstrip('/')
    return JSONResponse(jwks_handler.get_metadata(base_url))

@app.get('/auth/public-key')
async def get_public_key():
    # Provide PEM for quick copy; UI uses this in HomePage
    pem = jwt_manager.public_pem.decode('utf-8') if isinstance(jwt_manager.public_pem, bytes) else (jwt_manager.public_pem or '')
    return PlainTextResponse(pem, media_type='text/plain')


def set_session(session_id: str, data: dict):
    sessions[session_id] = data


def validate_api_key_auth(authorization: str) -> tuple[bool, Optional[str], Optional[dict]]:
    if not authorization.startswith('Bearer cids_ak_'):
        return False, None, None
    api_key = authorization.replace('Bearer ', '')
    result = api_key_manager.validate_api_key(api_key)
    if not result:
        return False, None, None
    app_client_id, metadata = result
    audit_logger.log_action(action=AuditAction.API_KEY_USED, resource_type="api_key", resource_id=metadata.key_id, details={"app_client_id": app_client_id, "key_name": metadata.name})
    metadata_dict = {'sub': f"app:{app_client_id}", 'email': f"{app_client_id}@api-key", 'name': f"API Key: {metadata.name}", 'permissions': metadata.permissions, 'api_key_id': metadata.key_id, 'app_client_id': app_client_id, 'auth_type': 'api_key'}
    return True, app_client_id, metadata_dict



def generate_token_with_iam_claims(user_info: dict, client_id: Optional[str] = None) -> str:
    """Generate token with IAM claims (legacy-equivalent).
    Populates roles, permissions, and rls_filters exactly like the legacy app.
    """
    # Normalize groups to list[str] of display names
    user_groups: list[str] = []
    groups_data = (user_info or {}).get('groups', [])
    if isinstance(groups_data, list):
        for g in groups_data:
            if isinstance(g, dict):
                name = g.get('displayName') or g.get('name') or str(g.get('id') or '')
                if name:
                    user_groups.append(name)
            else:
                user_groups.append(str(g))

    # Aggregate roles from v2 roles manager and v1 app role mappings
    user_roles: dict[str, list[str]] = {}
    try:
        v2_roles = roles_manager.get_user_roles(user_groups)
        if isinstance(v2_roles, dict):
            user_roles.update(v2_roles)
    except Exception as e:
        logger.warning(f"Error getting v2 user roles: {e}")

    if client_id:
        try:
            app_roles = app_store.get_user_roles_for_app(client_id, user_groups)
            if app_roles:
                user_roles[client_id] = app_roles
        except Exception as e:
            logger.warning(f"Error getting app-specific roles for {client_id}: {e}")
    else:
        for app_id in registered_apps.keys():
            try:
                app_roles = app_store.get_user_roles_for_app(app_id, user_groups)
                if app_roles:
                    user_roles[app_id] = app_roles
            except Exception as e:
                logger.warning(f"Error getting roles for app {app_id}: {e}")

    # Compute field-level permissions and RLS filters
    permissions: dict[str, list[str]] = {}
    rls_filters: dict[str, dict[str, list[dict]] ] = {}
    if client_id:
        roles_for_app = user_roles.get(client_id, [])
        all_perms = set()
        all_rls: dict[str, list[dict]] = {}
        for role_name in roles_for_app:
            for p in permission_registry.get_role_permissions(client_id, role_name):
                all_perms.add(p)
            role_rls = permission_registry.get_role_rls_filters(client_id, role_name)
            for field, flist in role_rls.items():
                all_rls.setdefault(field, []).extend(flist)
        if all_perms:
            permissions[client_id] = list(all_perms)
        if all_rls:
            rls_filters[client_id] = all_rls
    else:
        for app_id, roles_list in user_roles.items():
            all_perms = set()
            all_rls: dict[str, list[dict]] = {}
            for role_name in roles_list:
                for p in permission_registry.get_role_permissions(app_id, role_name):
                    all_perms.add(p)
                role_rls = permission_registry.get_role_rls_filters(app_id, role_name)
                for field, flist in role_rls.items():
                    all_rls.setdefault(field, []).extend(flist)
            if all_perms:
                permissions[app_id] = list(all_perms)
            if all_rls:
                rls_filters[app_id] = all_rls

    # Build final claims
    sub = (user_info or {}).get('sub') or (user_info or {}).get('user_id') or (user_info or {}).get('email') or 'unknown-user'
    claims = {
        'iss': 'internal-auth-service',
        'sub': sub,
        'aud': [client_id] if client_id else ['internal-services'],
        'email': (user_info or {}).get('email', ''),
        'name': (user_info or {}).get('name', ''),
        'groups': user_groups,
        'scope': 'openid profile email',
        'roles': user_roles,
        'permissions': permissions,
        'rls_filters': rls_filters,
        'attrs': {
            'tenant': (user_info or {}).get('tenant_id')
        },
        'token_version': '2.0'
    }

    # Include optional fields if provided
    if 'client_id' in (user_info or {}) and not client_id:
        claims['client_id'] = user_info['client_id']
    if 'app_roles' in (user_info or {}):
        claims['app_roles'] = user_info['app_roles']

    # Generate token (10 minutes TTL to match legacy)
    return jwt_manager.create_token(claims, token_lifetime_minutes=10, token_type='access')


def check_admin_access(authorization: Optional[str] = None) -> tuple[bool, Optional[dict]]:
    logger.debug("=== check_admin_access called ===")
    if not authorization or not authorization.startswith('Bearer '):
        return False, None
    if authorization.startswith('Bearer cids_ak_'):
        is_valid, app_client_id, metadata_dict = validate_api_key_auth(authorization)
        if is_valid and 'admin' in metadata_dict.get('permissions', []):
            return True, metadata_dict
        return False, metadata_dict
    token = authorization.replace('Bearer ', '')
    is_valid, claims, error = jwt_manager.validate_token(token)
    if not is_valid:
        return False, None
    for token_id, token_data in issued_tokens.items():
        if token_data['access_token'] == token and token_data.get('revoked', False):
            return False, None
    admin_emails = [e.strip().lower() for e in os.getenv('ADMIN_EMAILS', 'admin@example.com').split(',') if e.strip()]
    admin_group_ids = [g.strip() for g in os.getenv('ADMIN_GROUP_IDS', '').split(',') if g.strip()]
    user_email = claims.get('email', '').strip().lower()
    user_groups = claims.get('groups', [])
    if user_email in admin_emails:
        return True, claims
    for group in user_groups:
        if isinstance(group, dict) and group.get('id') in admin_group_ids:
            return True, claims
    return False, claims

# In-memory relay store for OAuth login flows (CID brokered)
oauth_relays: Dict[str, dict] = {}

@app.get("/auth/login")
async def cids_login(request: Request, client_id: str, app_redirect_uri: str, state: str):
    # Validate app and redirect uri
    app_data = app_store.get_app(client_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="Unknown client_id")
    if not app_data.get('is_active', True):
        raise HTTPException(status_code=400, detail="Application is not active")
    allowed_redirects = app_data.get('redirect_uris') or []
    if app_redirect_uri not in allowed_redirects:
        raise HTTPException(status_code=400, detail="redirect_uri not allowed for this app")

    relay_id = str(uuid.uuid4())
    oauth_relays[relay_id] = {
        'client_id': client_id,
        'app_redirect_uri': app_redirect_uri,
        'state': state,
        'created_at': datetime.utcnow().isoformat() + 'Z'
    }

    tenant_id, azure_client_id, _ = ensure_azure_env()
    if not tenant_id or not azure_client_id:
        raise HTTPException(status_code=500, detail="Azure credentials not configured")
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/auth/callback"

    auth_url = (
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        f"?client_id={urllib.parse.quote(azure_client_id)}"
        f"&response_type=code"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        f"&scope={urllib.parse.quote(os.getenv('AZURE_SCOPE', 'openid profile email User.Read'))}"
        f"&response_mode=query"
        f"&state={urllib.parse.quote(relay_id)}"
    )
    return RedirectResponse(url=auth_url, status_code=302)

@app.get("/auth/callback")
async def cids_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None, error_description: Optional[str] = None):
    if error:
        raise HTTPException(status_code=400, detail=error_description or error)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    relay = oauth_relays.pop(state, None)
    if not relay:
        raise HTTPException(status_code=400, detail="Invalid state (relay not found)")

    # Exchange code for internal token using the same redirect_uri we used to start login
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/auth/callback"
    try:
        token_response: JSONResponse = await exchange_code_for_token(TokenExchangeRequest(code=code, redirect_uri=redirect_uri))  # type: ignore
        # token_response.body is bytes; parse to dict
        payload = json.loads(token_response.body.decode('utf-8'))
        access_token = payload.get('access_token')
        refresh_token = payload.get('refresh_token')
        if not access_token:
            raise HTTPException(status_code=500, detail="No access_token from exchange")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Callback exchange failed: {e}")
        raise HTTPException(status_code=500, detail="Token exchange failed")

    # Redirect back to the app with token in fragment to avoid logs
    params = {
        'access_token': access_token,
        'token_type': 'Bearer',
        'state': relay.get('state', ''),
    }
    if refresh_token:
        params['refresh_token'] = refresh_token
    fragment = urllib.parse.urlencode(params)
    redirect_url = f"{relay['app_redirect_uri']}#{fragment}"
    return RedirectResponse(url=redirect_url, status_code=302)

# ROUTES

@app.post("/auth/token")
async def token_endpoint(token_request: TokenRequest):
    if token_request.grant_type == "refresh_token":
        if not token_request.refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token required")
        user_info, new_refresh_token = refresh_token_store.validate_and_rotate(token_request.refresh_token)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        # Fetch fresh groups if we still have Azure access token stored
        if 'azure_access_token' in user_info:
            azure_access_token = user_info.get('azure_access_token')
            user_groups = []
            group_names = []
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {'Authorization': f'Bearer {azure_access_token}'}
                try:
                    groups_response = await client.get('https://graph.microsoft.com/v1.0/me/memberOf?$select=id,displayName', headers=headers)
                    if groups_response.status_code == 200:
                        groups_data = groups_response.json()
                        for g in groups_data.get('value', []):
                            if isinstance(g, dict):
                                user_groups.append({'id': g.get('id', ''), 'displayName': g.get('displayName', f"Group {g.get('id', '')[:8]}...")})
                                group_names.append(g.get('displayName', ''))
                        user_info['groups'] = user_groups
                except Exception:
                    logger.exception("Refresh: Failed to fetch groups from Graph API")
        access_token = generate_token_with_iam_claims(user_info)
        token_id = str(uuid.uuid4())
        now_utc = datetime.utcnow()
        expires_utc = now_utc + timedelta(minutes=10)
        issued_tokens[token_id] = {
            'id': token_id,
            'access_token': access_token,
            'refresh_token': new_refresh_token,
            'user': user_info,
            'issued_at': now_utc.isoformat() + 'Z',
            'expires_at': expires_utc.isoformat() + 'Z',
            'source': 'refresh_token',
            'parent_refresh_token': token_request.refresh_token
        }
        token_activity_logger.log_activity(token_id=token_id, action=TokenAction.REFRESHED, performed_by=user_info, details={'source': 'refresh_token'})
        return JSONResponse({'access_token': access_token, 'token_type': 'Bearer', 'expires_in': 600, 'refresh_token': new_refresh_token})
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {token_request.grant_type}")

@app.post("/auth/token/exchange")
async def exchange_code_for_token(exchange_request: TokenExchangeRequest):
    try:
        tenant_id, client_id, client_secret = ensure_azure_env()
        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(token_url, data={
                'grant_type': 'authorization_code',
                'client_id': client_id,
                'client_secret': client_secret,
                'code': exchange_request.code,
                'redirect_uri': exchange_request.redirect_uri,
                'scope': os.getenv('AZURE_SCOPE', 'openid profile email User.Read')
            })
        if response.status_code != 200:
            error_data = response.json()
            logger.error(f"Azure token exchange failed: {error_data}")
            raise HTTPException(status_code=400, detail=error_data.get('error_description', 'Token exchange failed'))
        azure_token_data = response.json()
        azure_access_token = azure_token_data.get('access_token')
        azure_id_token = azure_token_data.get('id_token')
        if not azure_access_token:
            raise HTTPException(status_code=400, detail="No access token received from Azure")
        import base64
        parts = azure_id_token.split('.')
        if len(parts) != 3:
            raise HTTPException(status_code=400, detail="Invalid ID token format")
        payload = parts[1]


        payload += '=' * (4 - len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        user_email = claims.get('email') or claims.get('preferred_username')
        admin_emails = os.getenv('ADMIN_EMAILS', '').split(',')
        is_admin = user_email in admin_emails
        user_groups = []
        group_names = []
        if azure_access_token:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {'Authorization': f'Bearer {azure_access_token}'}
                try:
                    groups_response = await client.get('https://graph.microsoft.com/v1.0/me/memberOf?$select=id,displayName', headers=headers)
                    if groups_response.status_code == 200:
                        groups_data = groups_response.json()
                        for g in groups_data.get('value', []):
                            if isinstance(g, dict):
                                user_groups.append({'id': g.get('id', ''), 'displayName': g.get('displayName', f"Group {g.get('id', '')[:8]}...")})
                                group_names.append(g.get('displayName', ''))
                    else:
                        logger.warning(f"Failed to fetch groups from Graph API: {groups_response.status_code}")
                        user_groups = claims.get('groups', [])
                        group_names = user_groups if isinstance(user_groups, list) else []
                except Exception as e:
                    logger.error(f"Failed to fetch groups from Graph API: {e}")
                    user_groups = claims.get('groups', [])
                    group_names = user_groups if isinstance(user_groups, list) else []
        else:
            user_groups = claims.get('groups', [])
            group_names = user_groups if isinstance(user_groups, list) else []
        app_roles = []
        app_permissions = {}
        app_rls_filters = {}
        for client_id in registered_apps.keys():
            user_app_roles = app_store.get_user_roles_for_app(client_id, group_names)
            for role in user_app_roles:
                if role not in app_roles:
                    app_roles.append(role)
            if user_app_roles:
                all_perms = set()
                all_rls = {}
                for role_name in user_app_roles:
                    role_perms = permission_registry.get_role_permissions(client_id, role_name)
                    all_perms.update(role_perms)
                    role_rls = permission_registry.get_role_rls_filters(client_id, role_name)
                    for filter_key, filter_list in role_rls.items():
                        if filter_key not in all_rls:
                            all_rls[filter_key] = []
                        all_rls[filter_key].extend(filter_list)
                if all_perms:
                    app_permissions[client_id] = list(all_perms)
                if all_rls:
                    app_rls_filters[client_id] = all_rls
        internal_token_payload = {
            'sub': claims.get('sub'),
            'email': user_email,
            'name': claims.get('name'),
            'given_name': claims.get('given_name'),
            'family_name': claims.get('family_name'),
            'is_admin': is_admin,
            'groups': user_groups,
            'azure_groups': user_groups,
            'group_names': group_names,
            'roles': app_roles,
            'permissions': app_permissions,
            'rls_filters': app_rls_filters,
            'preferred_username': claims.get('preferred_username'),
            'token_type': 'internal',
            'token_version': '2.0'
        }
        filtered_payload = token_template_manager.apply_template(internal_token_payload, group_names)
        internal_token = jwt_manager.create_token(filtered_payload)
        internal_token_id = str(uuid.uuid4())
        issued_tokens[internal_token_id] = {
            'id': internal_token_id,
            'access_token': internal_token,
            'user': {'name': claims.get('name', ''), 'email': user_email},
            'subject': claims.get('sub'),
            'issued_at': datetime.utcnow().isoformat() + 'Z',
            'expires_at': (datetime.utcnow() + timedelta(seconds=1800)).isoformat() + 'Z',
            'source': 'oauth_exchange',
            'revoked': False
        }
        azure_token_id = str(uuid.uuid4())
        azure_tokens[azure_token_id] = {
            'id': azure_token_id,
            'id_token': azure_id_token,
            'access_token': azure_access_token,
            'user': {'name': claims.get('name', ''), 'email': user_email},
            'subject': claims.get('sub'),
            'issued_at': datetime.utcnow().isoformat() + 'Z',
            'expires_at': (datetime.utcnow() + timedelta(seconds=3600)).isoformat() + 'Z',
            'issuer': claims.get('iss', 'https://login.microsoftonline.com'),
            'audience': claims.get('aud', '')
        }
        refresh_token = refresh_token_store.create_refresh_token({
            'user_id': claims.get('sub'),
            'email': user_email,
            'name': claims.get('name'),
            'is_admin': is_admin,
            'azure_access_token': azure_access_token,
            'groups': user_groups,
            'sub': claims.get('sub')
        })
        token_activity_logger.log_activity(internal_token_id, TokenAction.CREATED, performed_by={'email': user_email, 'sub': claims.get('sub')}, details={'auth_method': 'oauth_code_exchange'})
        return JSONResponse({'access_token': internal_token, 'refresh_token': refresh_token, 'token_type': 'Bearer', 'expires_in': 1800})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during token exchange")

@app.get("/auth/validate")
async def validate_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    if authorization.startswith('Bearer cids_ak_'):
        is_valid, app_client_id, metadata_dict = validate_api_key_auth(authorization)
        if is_valid:
            return JSONResponse({'valid': True, 'sub': metadata_dict.get('sub'), 'email': metadata_dict.get('email'), 'name': metadata_dict.get('name'), 'permissions': metadata_dict.get('permissions', []), 'app_client_id': app_client_id, 'auth_type': 'api_key'})
        else:
            raise HTTPException(status_code=401, detail="Invalid API key")
    token = authorization.replace('Bearer ', '')
    is_valid, claims, error = jwt_manager.validate_token(token)
    if not is_valid:
        return JSONResponse({'valid': False, 'error': error or 'Invalid token'})
    client_id = None
    return JSONResponse({'valid': True, 'claims': claims})

@app.get("/auth/my-token")
async def get_my_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.replace('Bearer ', '')
    is_valid, claims, error = jwt_manager.validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail=error or "Invalid token")
    token_info = None
    for token_id, token_data in issued_tokens.items():
        if token_data.get('access_token') == token:
            token_info = {
                'token_id': token_id,
                'issued_at': token_data.get('issued_at'),
                'expires_at': token_data.get('expires_at'),
                'source': token_data.get('source')
            }
            break
    return JSONResponse({'valid': True, 'claims': claims, 'token_info': token_info, 'token_preview': token[:20] + '...' if len(token) > 20 else token})


    if not is_valid:
        raise HTTPException(status_code=401, detail=error or "Invalid token")
    token_id_found = None
    for token_id, token_data in issued_tokens.items():
        if token_data['access_token'] == token:
            token_id_found = token_id
            if token_data.get('revoked', False):
                raise HTTPException(status_code=401, detail="Token has been revoked")
            break
    if token_id_found:
        token_activity_logger.log_activity(token_id=token_id_found, action=TokenAction.VALIDATED, details={'endpoint': '/auth/validate'})
    return JSONResponse({'valid': True, 'sub': claims.get('sub'), 'email': claims.get('email'), 'name': claims.get('name'), 'groups': claims.get('groups', []), 'auth_type': 'jwt'})

@app.post("/auth/validate")
async def validate_token_endpoint(request: Request):
    data = await request.json()
    token = data.get('token')
    if not token:
        return JSONResponse({'valid': False, 'error': 'No token provided'}, status_code=400)
    is_valid, claims, error = jwt_manager.validate_token(token)
    if not is_valid:
        return JSONResponse({'valid': False, 'error': error or 'Invalid token'})
    client_id = data.get('client_id')
    if client_id:
        app_data = app_store.get_app(client_id)
        if not app_data:
            return JSONResponse({'valid': False, 'error': 'Invalid client_id'})
        if not app_data.get('is_active'):
            return JSONResponse({'valid': False, 'error': 'Application is not active'})
    return JSONResponse({'valid': True, 'claims': claims})

@app.get("/auth/whoami")
async def whoami(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.replace('Bearer ', '')
    is_valid, claims, error = jwt_manager.validate_token(token)
    if not is_valid:
        raise HTTPException(status_code=401, detail=error or "Invalid token")
    admin_emails_raw = os.getenv('ADMIN_EMAILS', 'admin@example.com').split(',')
    admin_emails = [email.strip().lower() for email in admin_emails_raw if email.strip()]
    admin_group_ids_raw = os.getenv('ADMIN_GROUP_IDS', '').split(',')
    admin_group_ids = [group_id.strip() for group_id in admin_group_ids_raw if group_id.strip()]
    user_email = claims.get('email', '').strip().lower()
    user_groups = claims.get('groups', [])
    is_admin = user_email in admin_emails
    for group in user_groups:
        if isinstance(group, dict) and group.get('id') in admin_group_ids:
            is_admin = True
            break
    return JSONResponse({'email': claims.get('email'), 'name': claims.get('name'), 'sub': claims.get('sub'), 'groups': claims.get('groups', []), 'is_admin': is_admin, 'admin_config': {'admin_emails': admin_emails, 'admin_emails_raw': admin_emails_raw, 'admin_group_ids': admin_group_ids} if is_admin else None})

# ==============================
# Admin: App Registration routes
# ==============================

@app.get("/auth/admin/apps")
async def list_apps(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    apps = app_store.list_apps()
    # Return as plain list of dicts; shapes match AppResponse
    return JSONResponse(apps)

@app.get("/auth/admin/apps/{client_id}")
async def get_app_admin(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    app_data = app_store.get_app(client_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="App not found")
    return JSONResponse(app_data)

@app.post("/auth/admin/apps")
async def register_app_admin(request: RegisterAppRequest, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    app_data = app_store.register_app(request)
    api_key = None
    api_key_metadata = None
    if request.create_api_key:
        try:
            key_name = request.api_key_name or f"Initial API Key for {request.name}"
            permissions = request.api_key_permissions or ["admin"]
            new_key, metadata = api_key_manager.create_api_key(
                app_client_id=app_data["client_id"],
                name=key_name,
                permissions=permissions,
                created_by=claims.get('email', 'admin'),
                ttl_days=90
            )
            api_key = new_key
            api_key_metadata = metadata.to_dict()

        except Exception:
            logger.exception("Failed to create initial API key")

    # Log the registration
    audit_logger.log_action(
        action=AuditAction.APP_REGISTERED,
        details={
            'app_name': request.name,
            'client_id': app_data["client_id"],
            'registered_by': claims.get('email', 'admin'),
            'api_key_created': api_key is not None
        }
    )

    # Return the registration response
    response_data = {
        "app": app_data
    }

    if api_key:
        response_data["api_key"] = api_key
        response_data["api_key_metadata"] = api_key_metadata

    return JSONResponse(response_data)

@app.post("/auth/token/a2a")
async def a2a_token_exchange(request: A2ATokenRequest = Body(None), authorization: Optional[str] = Header(None)):
    # Validate API key from Authorization header
    if not authorization or not authorization.startswith('Bearer cids_ak_'):
        raise HTTPException(status_code=401, detail="API key required in Authorization header")
    is_valid, app_client_id, _ = validate_api_key_auth(authorization)
    if not is_valid or not app_client_id:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Build service identity for the app
    app_info = registered_apps.get(app_client_id)
    app_name = app_info.get('name') if app_info else app_client_id

    # Fetch per-key metadata (validate again to get metadata and update usage)
    api_key = authorization.replace('Bearer ', '')
    key_lookup = api_key_manager.validate_api_key(api_key)
    key_metadata = key_lookup[1] if key_lookup else None

    # Construct a minimal user_info for service token
    user_info = {
        'sub': f'app:{app_client_id}',
        'email': f'{app_client_id}@apps.cids',
        'name': f'{app_name} (service)',
        'groups': [],
        'token_version': '2.0'
    }

    # Build roles for all apps using permission_registry and any app_roles_overrides from the key
    user_roles: dict[str, list[str]] = {}
    roles_source = "none"
    if key_metadata and key_metadata.app_roles_overrides:
        for aid, roles in (key_metadata.app_roles_overrides or {}).items():
            if roles:
                user_roles[aid] = list(set(roles))
        roles_source = "overrides"
    if not user_roles:
        # Fallback to A2A mappings for this caller app id
        try:
            mapped = app_store.get_a2a_mappings_for_caller(app_client_id)
            for aid, roles in (mapped or {}).items():
                if roles:
                    user_roles[aid] = list(set(roles))
            if user_roles:
                roles_source = "a2a_mappings"
        except Exception:
            logger.exception("Error loading A2A role mappings")

    # Compute permissions and rls_filters
    permissions: dict[str, list[str]] = {}
    rls_filters: dict[str, dict[str, list[dict]]] = {}
    for app_id, roles_list in user_roles.items():
        all_perms = set()
        all_rls: dict[str, list[dict]] = {}
        for role_name in roles_list:
            for p in permission_registry.get_role_permissions(app_id, role_name):
                all_perms.add(p)
            role_rls = permission_registry.get_role_rls_filters(app_id, role_name)
            for field, flist in role_rls.items():
                all_rls.setdefault(field, []).extend(flist)
        if all_perms:
            permissions[app_id] = list(all_perms)
        if all_rls:
            rls_filters[app_id] = all_rls

    # Assemble claims and apply template if specified on request or key
    claims = {
        'sub': user_info['sub'],
        'email': user_info['email'],
        'name': user_info['name'],
        'groups': user_info['groups'],
        'roles': user_roles,
        'permissions': permissions,
        'rls_filters': rls_filters,
        'attrs': { 'app_client_id': app_client_id, 'app_name': app_name },
        'token_version': user_info['token_version'],
        'aud': ['internal-services']
    }

    template_name = (request.template_name if request else None) or (key_metadata.token_template_name if key_metadata else None)
    if template_name:
        try:
            tmpls = token_template_manager.get_all_templates()
            chosen = next((t for t in tmpls if t.get('name') == template_name and t.get('enabled', True)), None)
            if chosen:
                template_claims = {c['key']: c for c in chosen.get('claims', [])}
                filtered = {}
                required = ['iss','sub','aud','exp','iat','nbf','jti','token_type','token_version']
                for key in template_claims.keys():
                    if key in claims:
                        filtered[key] = claims[key]
                for key in required:
                    if key not in filtered and key in claims:
                        filtered[key] = claims[key]
                claims = filtered
        except Exception:
            logger.exception("Failed to apply named template; proceeding with default")

    ttl_minutes = (key_metadata.token_ttl_minutes if key_metadata and key_metadata.token_ttl_minutes else 15)
    access_token = jwt_manager.create_token(claims, token_lifetime_minutes=ttl_minutes, token_type='service')

    token_id = str(uuid.uuid4())
    now_utc = datetime.utcnow()
    expires_utc = now_utc + timedelta(minutes=ttl_minutes)
    issued_tokens[token_id] = {
        'id': token_id,
        'access_token': access_token,
        'user': {'name': user_info['name'], 'email': user_info['email']},
        'issued_at': now_utc.isoformat() + 'Z',
        'roles_source': roles_source,
        'expires_at': expires_utc.isoformat() + 'Z',
        'source': 'api_key_a2a',
        'app_client_id': app_client_id,
        'api_key_id': key_metadata.key_id if key_metadata else None
    }
    token_activity_logger.log_activity(token_id, TokenAction.CREATED, performed_by={'email': user_info['email'], 'sub': user_info['sub']}, details={'auth_method': 'api_key_a2a'})

    return JSONResponse({'access_token': access_token, 'token_type': 'Bearer', 'expires_in': ttl_minutes * 60, 'token_id': token_id})

@app.put("/auth/admin/apps/{client_id}")
async def update_app_admin(client_id: str, request: UpdateAppRequest, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    app_data = app_store.update_app(client_id, request)
    if not app_data:
        raise HTTPException(status_code=404, detail="App not found")
    return JSONResponse(app_data)



@app.delete("/auth/admin/apps/{client_id}")
async def delete_app_admin(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if app exists before deletion
    if not app_store.get_app(client_id):
        raise HTTPException(status_code=404, detail="App not found")

    # Clean up related data
    # 1. Revoke all API keys for this app
    api_keys = api_key_manager.list_api_keys(client_id)
    for api_key in api_keys:
        api_key_manager.revoke_api_key(client_id, api_key.key_id)

    # 2. Delete app endpoints
    endpoints_registry.delete_app_endpoints(client_id)

    # 3. Delete the app itself (includes secrets, role mappings, a2a mappings)
    app_store.delete_app(client_id)

    return JSONResponse({"message": "App has been permanently deleted"})

# ==============================
# Admin: Role Mappings & Azure Groups
# ==============================

@app.get("/auth/admin/a2a-role-mappings")
async def get_all_a2a_role_mappings_admin(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return JSONResponse(app_store.get_a2a_mappings())

@app.get("/auth/admin/apps/{caller_id}/a2a-role-mappings")
async def get_a2a_role_mappings_admin(caller_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not app_store.get_app(caller_id):
        raise HTTPException(status_code=404, detail="Caller app not found")
    return JSONResponse({caller_id: app_store.get_a2a_mappings_for_caller(caller_id)})

class A2ARoleMappingsRequest(BaseModel):
    mappings: Dict[str, List[str]]

@app.put("/auth/admin/apps/{caller_id}/a2a-role-mappings")
async def put_a2a_role_mappings_admin(caller_id: str, request: A2ARoleMappingsRequest, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not app_store.get_app(caller_id):
        raise HTTPException(status_code=404, detail="Caller app not found")
    # Validate target apps and roles
    for target_app_id, roles in (request.mappings or {}).items():
        if not app_store.get_app(target_app_id):
            raise HTTPException(status_code=400, detail=f"Unknown target app: {target_app_id}")
        for role_name in roles or []:
            role_config = permission_registry.get_role_full_config(target_app_id, role_name)
            if not role_config['permissions'] and not role_config['rls_filters']:
                raise HTTPException(status_code=400, detail=f"Unknown role '{role_name}' for app '{target_app_id}'")
    result = app_store.upsert_a2a_mappings(caller_id, request.mappings or {})
    audit_logger.log_action(action=AuditAction.ROLE_MAPPINGS_UPDATED, details={'type': 'a2a', 'caller': caller_id, 'updated_by': claims.get('email')})
    return JSONResponse({"caller": caller_id, "mappings": result[caller_id]})

@app.post("/auth/admin/apps/{client_id}/role-mappings")
async def set_role_mappings_admin(client_id: str, request: SetRoleMappingRequest, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not app_store.get_app(client_id):
        raise HTTPException(status_code=404, detail="App not found")
    ok = app_store.set_role_mappings(client_id, request.mappings, created_by=claims.get('email', 'admin'))
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to update role mappings")
    return JSONResponse({"message": "Role mappings updated successfully", "mappings": request.mappings})

@app.get("/auth/admin/apps/{client_id}/role-mappings")
async def get_role_mappings_admin(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    app_data = app_store.get_app(client_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="App not found")
    mappings = app_store.get_role_mappings(client_id)
    return JSONResponse({"app_name": app_data.get('name'), "client_id": client_id, "mappings": mappings})

@app.get("/auth/admin/azure-groups")
async def get_azure_groups_admin(authorization: Optional[str] = Header(None), search: Optional[str] = None, top: int = 100):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    tenant_id, client_id, client_secret = ensure_azure_env()
    if not tenant_id or not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Azure credentials not configured")
    # Prefer application token for tenant-wide group listing
    app_token = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                data={
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'scope': 'https://graph.microsoft.com/.default'
                }
            )
        if token_resp.status_code == 200:
            app_token = token_resp.json().get('access_token')
        else:
            logger.warning(f"Graph app token fetch failed: {token_resp.status_code} {token_resp.text}")
    except Exception:
        logger.exception("Error fetching Graph app token")

    # Fallback to last delegated token
    delegated_token = None
    if not app_token and azure_tokens:
        try:
            latest = max(azure_tokens.values(), key=lambda t: t.get('issued_at', ''))
            delegated_token = latest.get('access_token')
        except Exception:
            delegated_token = None

    access_token = app_token or delegated_token
    if not access_token:
        raise HTTPException(status_code=400, detail="No Azure access token available; login first or configure app permissions")

    headers = {'Authorization': f'Bearer {access_token}'}
    # Use $search contains when a search term is provided
    if search:
        headers['ConsistencyLevel'] = 'eventual'
        query_url = f"https://graph.microsoft.com/v1.0/groups?$search=\"displayName:{search}\"&$select=id,displayName,description&$top={min(top, 999)}"
    else:
        query_url = f"https://graph.microsoft.com/v1.0/groups?$select=id,displayName,description&$top={min(top, 999)}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(query_url, headers=headers)
        if resp.status_code != 200 and search:
            # Fallback to startswith if $search not allowed
            fallback_url = f"https://graph.microsoft.com/v1.0/groups?$select=id,displayName,description&$filter=startswith(displayName,'{search.replace("'", "")}')&$top={min(top, 999)}"
            resp = await client.get(fallback_url, headers={'Authorization': f'Bearer {access_token}'})
        if resp.status_code != 200:
            logger.error(f"Azure groups fetch failed: {resp.status_code} {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch Azure groups (check Graph permissions)")
        data = resp.json()
        values = data.get('value', [])
        groups = [{"id": g.get('id', ''), "displayName": g.get('displayName', ''), "description": g.get('description', '')} for g in values][:top]
        return JSONResponse({"groups": groups})



# Note: whoami route is already defined earlier; remove stray stub header
# ==============================
# Admin: API Keys
# ==============================

@app.post("/auth/admin/apps/{client_id}/api-keys")
async def create_api_key_admin(client_id: str, request: CreateAPIKeyRequest, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not app_store.get_app(client_id):
        raise HTTPException(status_code=404, detail="App not found")
    api_key, metadata = api_key_manager.create_api_key(
        app_client_id=client_id,
        name=request.name,
        permissions=request.permissions,
        created_by=claims.get('email', 'admin'),
        ttl_days=request.ttl_days,
        token_template_name=request.token_template_name,
        app_roles_overrides=request.app_roles_overrides,
        token_ttl_minutes=request.token_ttl_minutes,
        default_audience=request.default_audience,
        allowed_audiences=request.allowed_audiences,
    )
    return JSONResponse({
        "api_key": api_key,
        "metadata": {
            "key_id": metadata.key_id,
            "key_prefix": metadata.key_prefix,
            "name": metadata.name,
            "permissions": metadata.permissions,
            "expires_at": metadata.expires_at,
            "created_at": metadata.created_at,
            "created_by": metadata.created_by,
            "is_active": metadata.is_active,
            "last_used_at": metadata.last_used_at,
            "usage_count": metadata.usage_count,
            # A2A fields
            "token_template_name": metadata.token_template_name,
            "app_roles_overrides": metadata.app_roles_overrides,
            "token_ttl_minutes": metadata.token_ttl_minutes,
            "default_audience": metadata.default_audience,
            "allowed_audiences": metadata.allowed_audiences,
        }
    })

@app.get("/auth/admin/apps/{client_id}/api-keys")
async def list_api_keys_admin(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not app_store.get_app(client_id):
        raise HTTPException(status_code=404, detail="App not found")
    keys = api_key_manager.list_api_keys(client_id)
    return JSONResponse([{
        "key_id": k.key_id,
        "key_prefix": k.key_prefix,
        "name": k.name,
        "permissions": k.permissions,
        "expires_at": k.expires_at,
        "created_at": k.created_at,
        "created_by": k.created_by,
        "is_active": k.is_active,
        "last_used_at": k.last_used_at,
        "usage_count": k.usage_count,
        # A2A fields
        "token_template_name": k.token_template_name,
        "app_roles_overrides": k.app_roles_overrides,
        "token_ttl_minutes": k.token_ttl_minutes,
        "default_audience": k.default_audience,
        "allowed_audiences": k.allowed_audiences,
    } for k in keys])

@app.delete("/auth/admin/apps/{client_id}/api-keys/{key_id}")
async def revoke_api_key_admin(client_id: str, key_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not api_key_manager.revoke_api_key(client_id, key_id):
        raise HTTPException(status_code=404, detail="Key not found")
    return JSONResponse({"message": "API key revoked successfully"})

@app.post("/auth/admin/apps/{client_id}/api-keys/{key_id}/rotate")
async def rotate_api_key_admin(client_id: str, key_id: str, authorization: Optional[str] = Header(None), grace_period_hours: int = 24):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    result = api_key_manager.rotate_api_key(client_id, key_id, created_by=claims.get('email', 'admin'), grace_period_hours=grace_period_hours)
    if not result:
        raise HTTPException(status_code=404, detail="Key not found")
    new_key, metadata = result
    return JSONResponse({
        "api_key": new_key,
        "metadata": {
            "key_id": metadata.key_id,
            "key_prefix": metadata.key_prefix,
            "name": metadata.name,
            "permissions": metadata.permissions,
            "expires_at": metadata.expires_at,
            "created_at": metadata.created_at,
            "created_by": metadata.created_by,
            "is_active": metadata.is_active,
            "last_used_at": metadata.last_used_at,
            "usage_count": metadata.usage_count,
        }
    })


@app.post("/discovery/endpoints/{client_id}")
async def trigger_discovery(client_id: str, authorization: Optional[str] = Header(None), force: bool = True):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    audit_logger.log_action(action=AuditAction.DISCOVERY_TRIGGERED, details={'app_client_id': client_id, 'triggered_by': claims.get('email') if claims else None, 'force': force})
    try:
        result = await enhanced_discovery.discover_with_fields(client_id, force)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Discovery execution error for {client_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

@app.get("/discovery/v2/permissions/{client_id}/tree")
async def get_permission_tree(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    tree = enhanced_discovery.get_permission_tree(client_id)
    return JSONResponse({"app_id": client_id, "permission_tree": tree})

# Enhanced Discovery Endpoints

@app.post("/discovery/batch")
async def batch_discovery(client_ids: List[str] = Body(...), force: bool = Body(True), authorization: Optional[str] = Header(None)):
    """Run discovery on multiple apps simultaneously"""
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    audit_logger.log_action(
        action=AuditAction.DISCOVERY_TRIGGERED,
        details={
            'batch_discovery': True,
            'app_client_ids': client_ids,
            'triggered_by': claims.get('email') if claims else None,
            'force': force
        }
    )

    try:
        result = await enhanced_discovery.batch_discover(client_ids, force)
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Batch discovery error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch discovery failed: {str(e)}")






# ==============================
# Permissions: roles CRUD (for Admin UI)
# ==============================

@app.post("/permissions/{client_id}/roles")
async def create_permission_role(client_id: str, authorization: Optional[str] = Header(None), role_name: str = Body(...), permissions: List[str] = Body(...), description: Optional[str] = Body(None), rls_filters: Optional[Dict[str, List[Dict[str, str]]]] = Body(None), a2a_only: Optional[bool] = Body(False), denied_permissions: Optional[List[str]] = Body(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    denied_perms_set = set(denied_permissions) if denied_permissions else set()
    logger.info(f"Creating role {role_name} for {client_id} with {len(permissions)} allowed and {len(denied_perms_set)} denied permissions")
    logger.info(f"Denied permissions received: {denied_permissions}")
    valid_perms, valid_denied_perms = permission_registry.create_role_with_rls(client_id, role_name, set(permissions), description, rls_filters, denied_perms_set)
    # Persist a2a_only flag in metadata
    try:
        permission_registry.role_metadata.setdefault(client_id, {}).setdefault(role_name, {})['a2a_only'] = bool(a2a_only)
        permission_registry._save_registry()
    except Exception:
        logger.exception("Failed to persist a2a_only metadata")
    audit_logger.log_action(action=AuditAction.ROLE_CREATED, details={'app_client_id': client_id, 'role_name': role_name, 'permissions_count': len(valid_perms), 'denied_permissions_count': len(valid_denied_perms), 'rls_filters_count': len(rls_filters) if rls_filters else 0, 'created_by': claims.get('email'), 'a2a_only': bool(a2a_only)})
    return JSONResponse({"app_id": client_id, "role_name": role_name, "permissions": list(valid_perms), "denied_permissions": list(valid_denied_perms), "valid_count": len(valid_perms), "denied_count": len(valid_denied_perms), "invalid_count": len(permissions) - len(valid_perms), "rls_filters_saved": len(rls_filters) if rls_filters else 0, "metadata": permission_registry.get_role_metadata(client_id, role_name)})

@app.get("/permissions/{client_id}/roles/{role_name}")
async def get_role_permissions(client_id: str, role_name: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    role_config = permission_registry.get_role_full_config(client_id, role_name)
    if not role_config['permissions'] and not role_config['denied_permissions'] and not role_config['rls_filters']:
        raise HTTPException(status_code=404, detail="Role not found")
    return JSONResponse({"app_id": client_id, "role_name": role_name, "permissions": role_config['permissions'], "denied_permissions": role_config['denied_permissions'], "rls_filters": role_config['rls_filters'], "metadata": role_config['metadata'], "count": len(role_config['permissions']), "denied_count": len(role_config['denied_permissions'])})

@app.get("/permissions/{client_id}/roles")
async def list_roles(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    app_roles = permission_registry.role_permissions.get(client_id, {})
    app_metadata = permission_registry.role_metadata.get(client_id, {})
    roles_with_metadata = {role_name: {"permissions": list(perms), "metadata": app_metadata.get(role_name, {})} for role_name, perms in app_roles.items()}
    # Include roles that exist only in metadata (e.g., A2A-only roles with no permissions yet)
    for role_name, meta in app_metadata.items():
        if role_name not in roles_with_metadata:
            roles_with_metadata[role_name] = {"permissions": [], "metadata": meta}
    return JSONResponse({"app_id": client_id, "roles": roles_with_metadata, "count": len(roles_with_metadata)})

@app.put("/permissions/{client_id}/roles/{role_name}")
async def update_permission_role(client_id: str, role_name: str, authorization: Optional[str] = Header(None), permissions: List[str] = Body(...), description: Optional[str] = Body(None), rls_filters: Optional[Dict[str, List[Dict[str, str]]]] = Body(None), a2a_only: Optional[bool] = Body(None), denied_permissions: Optional[List[str]] = Body(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if client_id not in permission_registry.role_permissions or role_name not in permission_registry.role_permissions[client_id]:
        raise HTTPException(status_code=404, detail="Role not found")

    denied_perms_set = set(denied_permissions) if denied_permissions else set()
    logger.info(f"Updating role {role_name} for {client_id} with {len(permissions)} allowed and {len(denied_perms_set)} denied permissions")
    logger.info(f"Denied permissions received: {denied_permissions}")
    valid_perms, valid_denied_perms = permission_registry.update_role_with_rls(client_id, role_name, set(permissions), description, rls_filters, denied_perms_set)
    # Optionally update a2a_only flag
    if a2a_only is not None:
        try:
            permission_registry.role_metadata.setdefault(client_id, {}).setdefault(role_name, {})['a2a_only'] = bool(a2a_only)
            permission_registry._save_registry()
        except Exception:
            logger.exception("Failed to update a2a_only metadata")
    audit_logger.log_action(action=AuditAction.ROLE_UPDATED, details={'app_client_id': client_id, 'role_name': role_name, 'permissions_count': len(valid_perms), 'denied_permissions_count': len(valid_denied_perms), 'rls_filters_count': len(rls_filters) if rls_filters else 0, 'updated_by': claims.get('email'), 'a2a_only': a2a_only})
    return JSONResponse({"app_id": client_id, "role_name": role_name, "permissions": list(valid_perms), "denied_permissions": list(valid_denied_perms), "valid_count": len(valid_perms), "denied_count": len(valid_denied_perms), "invalid_count": len(permissions) - len(valid_perms), "rls_filters_saved": len(rls_filters) if rls_filters else 0, "metadata": permission_registry.get_role_metadata(client_id, role_name)})

@app.delete("/permissions/{client_id}/roles/{role_name}")
async def delete_role(client_id: str, role_name: str, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if client_id not in permission_registry.role_permissions or role_name not in permission_registry.role_permissions[client_id]:
        raise HTTPException(status_code=404, detail="Role not found")
    del permission_registry.role_permissions[client_id][role_name]
    if client_id in permission_registry.role_metadata and role_name in permission_registry.role_metadata[client_id]:
        del permission_registry.role_metadata[client_id][role_name]
    if client_id in permission_registry.role_rls_filters and role_name in permission_registry.role_rls_filters[client_id]:
        del permission_registry.role_rls_filters[client_id][role_name]
    permission_registry._save_registry()
    audit_logger.log_action(action=AuditAction.ROLE_DELETED, details={'app_client_id': client_id, 'role_name': role_name, 'deleted_by': claims.get('email')})
    return JSONResponse({"status": "success", "message": f"Role '{role_name}' deleted successfully"})

# ==============================
# Admin: Tokens & Activities
# ==============================

@app.get("/auth/admin/tokens")
async def get_all_tokens(authorization: Optional[str] = Header(None), include_revoked: bool = True):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    tokens_list = []
    for token_id, token_data in issued_tokens.items():
        if not include_revoked and token_data.get('revoked', False):
            continue
        tokens_list.append({
            'id': token_id,
            'user': token_data.get('user'),
            'issued_at': token_data.get('issued_at'),
            'expires_at': token_data.get('expires_at'),
            'source': token_data.get('source'),
            'revoked': token_data.get('revoked', False)
        })
    return JSONResponse({'total': len(tokens_list), 'tokens': tokens_list})

@app.delete("/auth/admin/tokens/{token_id}")
async def revoke_token_by_id(token_id: str, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if token_id not in issued_tokens:
        raise HTTPException(status_code=404, detail="Token not found")
    token_data = issued_tokens[token_id]
    token_data['revoked'] = True
    token_data['revoked_at'] = datetime.utcnow().isoformat() + 'Z'
    token_activity_logger.log_activity(token_id=token_id, action=TokenAction.REVOKED, performed_by={'email': claims.get('email')}, details={'reason': 'admin_revoked'})
    return JSONResponse({'status': 'success', 'message': 'Token revoked successfully', 'token_id': token_id})

@app.get("/auth/admin/tokens/{token_id}/activities")
async def get_token_activities(token_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    activities = token_activity_logger.get_token_activities(token_id)
    token_data = issued_tokens.get(token_id)
    return JSONResponse({'token_id': token_id, 'token_data': token_data, 'activities': activities, 'activity_count': len(activities)})

# Azure tokens
@app.get("/auth/admin/azure-tokens")
async def get_all_azure_tokens(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    tokens_list = []
    for token_id, token_data in azure_tokens.items():
        tokens_list.append({
            'id': token_id,
            'user': token_data.get('user'),
            'issued_at': token_data.get('issued_at'),
            'expires_at': token_data.get('expires_at'),
            'issuer': token_data.get('issuer'),
            'audience': token_data.get('audience'),
        })
    return JSONResponse({'total': len(tokens_list), 'tokens': tokens_list})

@app.delete("/auth/admin/azure-tokens/{token_id}")
async def remove_azure_token(token_id: str, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if token_id not in azure_tokens:
        raise HTTPException(status_code=404, detail="Token not found")
    del azure_tokens[token_id]
    return JSONResponse({'status': 'success', 'message': 'Token removed from local storage', 'token_id': token_id})

@app.get("/auth/admin/azure-tokens/{token_id}/activities")
async def get_azure_token_activities(token_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    activities = token_activity_logger.get_token_activities(token_id)
    token_data = azure_tokens.get(token_id)
    return JSONResponse({'token_id': token_id, 'token_data': token_data, 'activities': activities, 'activity_count': len(activities)})

@app.get("/auth/admin/azure-tokens/cleanup")
async def cleanup_expired_azure_tokens(authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    current_time = datetime.utcnow()
    expired_tokens = []
    for token_id, token_data in list(azure_tokens.items()):
        try:
            exp = datetime.fromisoformat(token_data['expires_at'].replace('Z',''))
            if current_time > exp:
                expired_tokens.append(token_id)
                del azure_tokens[token_id]
        except Exception:
            continue
    return JSONResponse({'status': 'success', 'expired_token_ids': expired_tokens, 'cleaned_at': current_time.isoformat() + 'Z'})

# Start rotation scheduler
# ==============================
# Admin: Rotation policies and manual check
# ==============================
# Admin: Logging configuration & readers
# ==============================

@app.get("/auth/debug/admin-check")
async def admin_check(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    return JSONResponse({"is_admin": is_admin})


@app.get("/auth/admin/logging/config")
async def get_logging_configuration(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return JSONResponse(get_logging_config())


class LoggingConfigUpdate(BaseModel):
    app: Optional[dict] = None
    audit: Optional[dict] = None
    token_activity: Optional[dict] = None
    access: Optional[dict] = None
    privacy: Optional[dict] = None


@app.put("/auth/admin/logging/config")
async def update_logging_configuration(request: LoggingConfigUpdate, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    patch = {k: v for k, v in request.dict(exclude_none=True).items()}
    updated = apply_logging_update(patch)
    audit_logger.log_action(action=AuditAction.POLICY_UPDATED, user_email=claims.get('email'), resource_type="logging", resource_id="config", details={"updated_keys": list(patch.keys())})
    return JSONResponse(updated)


@app.get("/auth/admin/logs/app")
async def get_app_logs(authorization: Optional[str] = Header(None), start: Optional[str] = None, end: Optional[str] = None, level: Optional[str] = None, logger_prefix: Optional[str] = None, q: Optional[str] = None, limit: int = 100):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    levels = [s.strip() for s in (level or "").split(",") if s.strip()]
    items = read_app_logs(start=start, end=end, level=levels or None, logger_prefix=logger_prefix, q=q, limit=limit)
    return JSONResponse({"items": items, "count": len(items)})



@app.get("/auth/admin/logs/audit")
async def get_audit_logs(authorization: Optional[str] = Header(None), start: Optional[str] = None, end: Optional[str] = None, action: Optional[str] = None, user_email: Optional[str] = None, resource_id: Optional[str] = None, limit: int = 100):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    # Reuse existing audit reader utility
    from backend.services.audit import audit_logger, AuditAction
    # audit_logger.query_audit_logs supports start/end datetime objects
    from datetime import datetime

    def parse_ts(s: Optional[str]):
        if not s:
            return None
        try:
            if s.endswith('Z'):
                s = s[:-1]
            # Try with microseconds then without
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(s, fmt)
                except Exception:
                    continue
        except Exception:
            return None

    start_dt = parse_ts(start)
    end_dt = parse_ts(end)
    action_enum = AuditAction(action) if action in [a.value for a in AuditAction] else None
    items = audit_logger.query_audit_logs(start_date=start_dt, end_date=end_dt, action=action_enum, user_email=user_email, resource_id=resource_id, limit=limit)
    return JSONResponse({"items": items, "count": len(items)})


@app.get("/auth/admin/logs/token-activity")
async def get_token_activity_logs(authorization: Optional[str] = Header(None), start: Optional[str] = None, end: Optional[str] = None, action: Optional[str] = None, user_email: Optional[str] = None, token_id: Optional[str] = None, limit: int = 100):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    # Read persisted JSONL files
    from pathlib import Path
    from backend.libs.logging_config import get_logging_config
    import json

    cfg = get_logging_config()
    dir_path = Path(cfg.get("token_activity", {}).get("path"))
    items = []

    def parse_ts(v: str):
        try:
            from datetime import datetime
            if v.endswith('Z') and '.' not in v:
                return datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ")
            return datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ")
        except Exception:
            return None

    start_dt = parse_ts(start) if start else None
    end_dt = parse_ts(end) if end else None

    if dir_path.exists():
        for p in sorted(dir_path.glob('token_activity_*.jsonl'), reverse=True):
            try:
                with p.open('r') as fh:
                    for line in fh:
                        if not line.strip():
                            continue
                        obj = json.loads(line)
                        ts = parse_ts(obj.get('timestamp', ''))
                        if start_dt and (not ts or ts < start_dt):
                            continue
                        if end_dt and (not ts or ts > end_dt):
                            continue
                        if action and obj.get('action') != action:
                            continue
                        if user_email and (obj.get('performed_by', {}) or {}).get('email') != user_email:
                            continue
                        if token_id and obj.get('token_id') != token_id:
                            continue
                        items.append(obj)
            except Exception:
                continue
    items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return JSONResponse({"items": items[: max(1, min(limit, 1000))], "count": min(len(items), max(1, min(limit, 1000)))})

# ===============
# Export endpoints
# ===============

@app.get("/auth/admin/logs/app/export")
async def export_app_logs(authorization: Optional[str] = Header(None), format: str = "ndjson", limit: int = 50000):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    items = read_app_logs(limit=min(max(1, limit), 50000))

    if format == "csv":
        import csv
        from io import StringIO
        buf = StringIO()
        if items:
            keys = sorted({k for item in items for k in item.keys()})
            writer = csv.DictWriter(buf, fieldnames=keys)
            writer.writeheader()
            for it in items:
                writer.writerow(it)
        content = buf.getvalue()
        return Response(content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=app_logs.csv"})
    else:
        # ndjson
        content = "\n".join(json.dumps(it) for it in items)
        return Response(content + ("\n" if content else ""), media_type="application/x-ndjson", headers={"Content-Disposition": "attachment; filename=app_logs.ndjson"})


@app.get("/auth/admin/logs/audit/export")
async def export_audit_logs(authorization: Optional[str] = Header(None), format: str = "ndjson", limit: int = 50000):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    from backend.services.audit import audit_logger
    items = audit_logger.query_audit_logs(limit=min(max(1, limit), 50000))
    if format == "csv":
        import csv
        from io import StringIO
        buf = StringIO()
        if items:
            keys = sorted({k for item in items for k in item.keys()})
            writer = csv.DictWriter(buf, fieldnames=keys)
            writer.writeheader()
            for it in items:
                writer.writerow(it)
        return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit_logs.csv"})
    else:
        content = "\n".join(json.dumps(it) for it in items)
        return Response(content + ("\n" if content else ""), media_type="application/x-ndjson", headers={"Content-Disposition": "attachment; filename=audit_logs.ndjson"})


@app.get("/auth/admin/logs/token-activity/export")
async def export_token_activity_logs(authorization: Optional[str] = Header(None), format: str = "ndjson", limit: int = 50000):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    # Reuse reader
    data = await get_token_activity_logs(authorization=authorization, limit=min(max(1, limit), 50000))
    items = data.body if hasattr(data, 'body') else None
    if hasattr(data, 'body'):
        import json as _json
        body = _json.loads(data.body)
        items = body.get('items', [])
    else:
        items = []
    if format == "csv":
        import csv
        from io import StringIO
        buf = StringIO()
        if items:
            keys = sorted({k for item in items for k in item.keys()})
            writer = csv.DictWriter(buf, fieldnames=keys)
            writer.writeheader()
            for it in items:
                writer.writerow(it)
        return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=token_activity.csv"})
    else:
        content = "\n".join(json.dumps(it) for it in items)
        return Response(content + ("\n" if content else ""), media_type="application/x-ndjson", headers={"Content-Disposition": "attachment; filename=token_activity.ndjson"})


# ===============
# SSE live tails
# ===============

async def _sse_event_stream_app():
    import asyncio
    from pathlib import Path
    from backend.libs.logging_config import get_logging_config

    cfg = get_logging_config()
    path = Path(cfg.get("app", {}).get("file", {}).get("path", ""))
    if not path.exists():
        # yield a comment to keep connection open
        yield f": no log file yet\n\n"
    last_size = 0
    while True:
        try:
            if path.exists():
                size = path.stat().st_size
                if size > last_size:
                    with path.open('r') as fh:
                        fh.seek(last_size)
                        for line in fh:
                            if line.strip():
                                yield f"data: {line.strip()}\n\n"
                    last_size = size
        except Exception:
            pass
        await asyncio.sleep(1)


@app.get("/auth/admin/logs/app/stream")
async def stream_app_logs(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return StreamingResponse(_sse_event_stream_app(), media_type="text/event-stream")


async def _sse_event_stream_audit():
    import asyncio
    from pathlib import Path
    from backend.libs.logging_config import get_logging_config

    cfg = get_logging_config()
    dir_path = Path(cfg.get("audit", {}).get("path", ""))
    last_file = None
    last_size = 0
    while True:
        try:
            files = sorted(dir_path.glob('audit_*.jsonl')) if dir_path.exists() else []
            current = files[-1] if files else None
            if current is None:
                yield f": no audit log file yet\n\n"
                await asyncio.sleep(2)
                continue
            if last_file != current:
                last_file = current
                last_size = 0
            size = current.stat().st_size
            if size > last_size:
                with current.open('r') as fh:
                    fh.seek(last_size)
                    for line in fh:
                        if line.strip():
                            yield f"data: {line.strip()}\n\n"
                last_size = size
        except Exception:
            pass
        await asyncio.sleep(1)


@app.get("/auth/admin/logs/audit/stream")
async def stream_audit_logs(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return StreamingResponse(_sse_event_stream_audit(), media_type="text/event-stream")


async def _sse_event_stream_token_activity():
    import asyncio
    from pathlib import Path
    from backend.libs.logging_config import get_logging_config

    cfg = get_logging_config()
    dir_path = Path(cfg.get("token_activity", {}).get("path", ""))
    last_file = None
    last_size = 0
    while True:
        try:
            files = sorted(dir_path.glob('token_activity_*.jsonl')) if dir_path.exists() else []
            current = files[-1] if files else None
            if current is None:
                yield f": no token activity log file yet\n\n"
                await asyncio.sleep(2)
                continue
            if last_file != current:
                last_file = current
                last_size = 0
            size = current.stat().st_size
            if size > last_size:
                with current.open('r') as fh:
                    fh.seek(last_size)
                    for line in fh:
                        if line.strip():
                            yield f"data: {line.strip()}\n\n"
                last_size = size
        except Exception:
            pass
        await asyncio.sleep(1)


@app.get("/auth/admin/logs/token-activity/stream")
async def stream_token_activity_logs(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return StreamingResponse(_sse_event_stream_token_activity(), media_type="text/event-stream")


async def get_app_logs(authorization: Optional[str] = Header(None), start: Optional[str] = None, end: Optional[str] = None, level: Optional[str] = None, logger_prefix: Optional[str] = None, q: Optional[str] = None, limit: int = 100):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    levels = [s.strip() for s in (level or "").split(",") if s.strip()]
    items = read_app_logs(start=start, end=end, level=levels or None, logger_prefix=logger_prefix, q=q, limit=limit)
    return JSONResponse({"items": items, "count": len(items)})

# ==============================

@app.post("/auth/admin/rotation/check")
async def manual_rotation_check_endpoint(authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    result = await rotation_scheduler.check_and_rotate_keys()
    cleaned = await rotation_scheduler.cleanup_expired_keys()
    audit_logger.log_action(action=AuditAction.API_KEY_ROTATED, user_email=claims.get('email'), resource_type="rotation_check", details={"manual_trigger": True, "rotated_count": result, "cleaned_count": cleaned})
    return JSONResponse({"rotated_keys": result, "cleaned_keys": cleaned, "triggered_by": claims.get('email'), "timestamp": datetime.utcnow().isoformat()})

@app.get("/auth/admin/rotation/policies")
async def get_rotation_policies_endpoint(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return JSONResponse(rotation_scheduler.rotation_policies)

@app.put("/auth/admin/apps/{client_id}/rotation-policy")
async def set_app_rotation_policy_endpoint(client_id: str, days_before_expiry: int = 7, grace_period_hours: int = 24, auto_rotate: bool = True, notify_webhook: Optional[str] = None, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not app_store.get_app(client_id):
        raise HTTPException(status_code=404, detail="App not found")
    rotation_scheduler.set_app_rotation_policy(app_client_id=client_id, days_before_expiry=days_before_expiry, grace_period_hours=grace_period_hours, auto_rotate=auto_rotate, notify_webhook=notify_webhook)
    return JSONResponse({"message": "Rotation policy updated", "app_client_id": client_id, "policy": {"days_before_expiry": days_before_expiry, "grace_period_hours": grace_period_hours, "auto_rotate": auto_rotate, "notify_webhook": notify_webhook}})

start_rotation_scheduler(app, check_interval_hours=6)
# ==============================
# Admin: Token Templates
# ==============================

@app.get("/auth/admin/token-templates")
async def get_token_templates(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    templates = jwt_manager.template_manager.get_all_templates()
    return JSONResponse({"templates": templates})

@app.get("/auth/admin/token-templates/{template_name}")
async def get_token_template(template_name: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    template = jwt_manager.template_manager.get_template(template_name)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return JSONResponse(template)

@app.post("/auth/admin/token-templates")
async def create_token_template(template: Dict = Body(...), authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if 'name' not in template:
        raise HTTPException(status_code=400, detail="Template must include 'name'")
    jwt_manager.template_manager.save_template(template)
    audit_logger.log_action(action=AuditAction.TOKEN_TEMPLATE_UPDATED, user_email=claims.get('email'), resource_type="token_template", details={"template_name": template['name'], "action": "save"})
    return JSONResponse({"message": "Template saved successfully", "template_name": template['name']})

@app.delete("/auth/admin/token-templates/{template_name}")
async def delete_token_template(template_name: str, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    ok = jwt_manager.template_manager.delete_template(template_name)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
    audit_logger.log_action(action=AuditAction.TOKEN_TEMPLATE_DELETED, user_email=claims.get('email'), resource_type="token_template", details={"template_name": template_name, "action": "delete"})
    return JSONResponse({"message": "Template deleted successfully"})

@app.post("/auth/admin/token-templates/import")
async def import_token_templates(templates: List[Dict] = Body(...), authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    imported = 0
    failed = 0
    for t in templates:
        try:
            if 'name' in t:
                jwt_manager.template_manager.save_template(t)
                imported += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    audit_logger.log_action(action=AuditAction.TOKEN_TEMPLATES_IMPORTED, user_email=claims.get('email'), resource_type="token_template", details={"imported": imported, "failed": failed})
    return JSONResponse({"message": f"Import completed. {imported} templates imported, {failed} failed.", "imported": imported, "failed": failed})


# ==============================
# Admin: App Endpoints
# ==============================

@app.get("/auth/admin/apps/{client_id}/endpoints")
async def get_app_endpoints_admin(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    endpoints = endpoints_registry.get_app_endpoints(client_id)
    if not endpoints:
        raise HTTPException(status_code=404, detail="No endpoints found for app")
    return JSONResponse({"source": "registry", "endpoints": endpoints})

@app.put("/auth/admin/apps/{client_id}/endpoints")
async def update_app_endpoints_admin(client_id: str, update: EndpointsUpdate, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    if not app_store.get_app(client_id):
        raise HTTPException(status_code=404, detail="App not found")
    result = endpoints_registry.upsert_endpoints(app_client_id=client_id, endpoints=[e.dict() for e in update.endpoints], updated_by=claims.get('email', 'admin'))
    return JSONResponse({"message": "Endpoints updated", **result})

