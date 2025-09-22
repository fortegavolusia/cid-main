# FastAPI entrypoint (migrated from azure-auth-app/main.py)
# NOTE: This is a full move; all imports reference backend.* modules.

from fastapi import FastAPI, Request, HTTPException, Response, Header, Body, Query
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse, StreamingResponse, PlainTextResponse
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
import hashlib
import json
import urllib.parse
from dotenv import load_dotenv, dotenv_values
from pathlib import Path
from psycopg2.extras import Json

from services.jwt import JWTManager
from services.refresh_tokens import refresh_token_store
from services.token_activity import token_activity_logger, TokenAction
from services.app_registration import (
    app_store, RegisterAppRequest, UpdateAppRequest,
    AppResponse, AppRegistrationResponse, SetRoleMappingRequest,
    registered_apps, app_role_mappings
)
from services.jwks import JWKSHandler
from services.endpoints import AppEndpointsRegistry, EndpointsUpdate
from services.roles import RolesManager, RolesUpdate, RoleMappingsUpdate
from services.policy import PolicyManager, PolicyDocument
from services.audit import audit_logger, AuditAction
from services.discovery import DiscoveryService
from services.discovery import DiscoveryService as EnhancedDiscoveryService
from services.permission_registry import PermissionRegistry
from services.token_templates import TokenTemplateManager
from services.api_keys import api_key_manager, APIKeyTTL
from background.api_key_rotation import start_rotation_scheduler, rotation_scheduler
from utils.paths import api_templates_path
from libs.logging_config import setup_logging, get_logging_config, update_logging_config as apply_logging_update
from services.log_reader import read_app_logs
from services.database import db_service
from services.discovery_db import DiscoveryDatabase
from api.a2a_endpoints import setup_a2a_endpoints

# Request models
class TokenRequest(BaseModel):
    grant_type: str
    refresh_token: Optional[str] = None

class TokenExchangeRequest(BaseModel):
    code: Optional[str] = None
    redirect_uri: str
    code_verifier: Optional[str] = None
    azure_access_token: Optional[str] = None
    azure_id_token: Optional[str] = None

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
    from middleware.access_log import access_log_middleware
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
    from utils.paths import ensure_dirs
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
    logger.debug(f"validate_api_key_auth called with: {authorization[:30]}...")
    if not authorization.startswith('Bearer cids_ak_'):
        logger.debug(f"API key validation failed: doesn't start with 'Bearer cids_ak_'")
        return False, None, None
    api_key = authorization.replace('Bearer ', '')
    logger.debug(f"Validating API key: {api_key[:20]}...")
    result = api_key_manager.validate_api_key(api_key)
    logger.debug(f"API key manager validation result: {result}")
    if not result:
        logger.debug(f"API key validation failed: api_key_manager returned None")
        return False, None, None
    app_client_id, metadata = result
    audit_logger.log_action(
        action=AuditAction.API_KEY_USED,
        resource_type="api_key",
        resource_id=metadata.key_id,
        user_email=f"{app_client_id}@api-key",  # Add service email
        details={"app_client_id": app_client_id, "key_name": metadata.name}
    )
    metadata_dict = {'sub': f"app:{app_client_id}", 'email': f"{app_client_id}@api-key", 'name': f"API Key: {metadata.name}", 'permissions': metadata.permissions, 'api_key_id': metadata.key_id, 'app_client_id': app_client_id, 'auth_type': 'api_key'}
    return True, app_client_id, metadata_dict



def get_role_permissions_from_db(client_id: str, role_name: str) -> List[str]:
    """Get role permissions directly from database"""
    try:
        import psycopg2
        import json
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '54322'),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cur = conn.cursor()

        # Get permissions from role_permissions table
        cur.execute("""
            SELECT permissions
            FROM cids.role_permissions
            WHERE client_id = %s AND role_name = %s
        """, (client_id, role_name))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if result and result[0]:
            # result[0] is already a list from JSONB
            return result[0] if isinstance(result[0], list) else []
        return []
    except Exception as e:
        logger.error(f"Error getting permissions from DB for {client_id}/{role_name}: {e}")
        return []

def get_role_rls_filters_from_db(client_id: str, role_name: str) -> Dict:
    """Get role RLS filters directly from database"""
    try:
        import psycopg2
        import json
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '54322'),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cur = conn.cursor()

        # First try to get from new RLS filters table (ONLY ACTIVE FILTERS)
        cur.execute("""
            SELECT resource, field_name, filter_condition
            FROM cids.rls_filters
            WHERE client_id = %s
            AND role_name = %s
            AND is_active = true
            ORDER BY priority DESC, resource, field_name
        """, (client_id, role_name))

        rows = cur.fetchall()

        if rows:
            # Build RLS filters structure from new table
            rls_filters = {}
            for resource, field_name, filter_condition in rows:
                # Group by resource
                if resource not in rls_filters:
                    rls_filters[resource] = {}

                # Add filter for this field
                if field_name not in rls_filters[resource]:
                    rls_filters[resource][field_name] = []

                # Add the filter condition
                rls_filters[resource][field_name].append({
                    "filter": filter_condition,
                    "operator": "AND"  # Default operator
                })

            cur.close()
            conn.close()

            logger.info(f"Loaded RLS filters from cids.rls_filters for {client_id}/{role_name}: {rls_filters}")
            return rls_filters

        # Fallback to old role_permissions table if no filters in new table
        cur.execute("""
            SELECT rls_filters
            FROM cids.role_permissions
            WHERE client_id = %s AND role_name = %s
        """, (client_id, role_name))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if result and result[0]:
            # result[0] is already a dict from JSONB
            logger.info(f"Loaded RLS filters from cids.role_permissions (fallback) for {client_id}/{role_name}")
            return result[0] if isinstance(result[0], dict) else {}
        return {}
    except Exception as e:
        logger.error(f"Error getting RLS filters from DB for {client_id}/{role_name}: {e}")
        return {}

def generate_token_with_iam_claims(user_info: dict, client_id: Optional[str] = None,
                                  client_ip: Optional[str] = None, user_agent: Optional[str] = None) -> str:
    """Generate token with IAM claims (legacy-equivalent).
    Populates roles, permissions, and rls_filters exactly like the legacy app.
    Now includes IP and device binding for enhanced security.
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
        # Get apps from database instead of memory
        db_apps = db_service.get_all_registered_apps()
        for app in db_apps:
            app_id = app['client_id']
            try:
                app_roles = app_store.get_user_roles_for_app(app_id, user_groups)
                if app_roles:
                    user_roles[app_id] = app_roles
            except Exception as e:
                logger.warning(f"Error getting roles for app {app_id}: {e}")

    # Compute field-level permissions and RLS filters
    permissions: dict[str, list[str]] = {}
    rls_filters: dict[str, dict[str, dict[str, list[dict]]]] = {}
    if client_id:
        roles_for_app = user_roles.get(client_id, [])
        all_perms = set()
        all_rls: dict[str, dict[str, list[dict]]] = {}
        for role_name in roles_for_app:
            # Get permissions directly from database
            perms_from_db = get_role_permissions_from_db(client_id, role_name)
            for p in perms_from_db:
                all_perms.add(p)
            # Get RLS filters directly from database
            role_rls = get_role_rls_filters_from_db(client_id, role_name)
            # Merge RLS filters correctly - they have structure: {resource: {field: [filters]}}
            for resource, fields in role_rls.items():
                if resource not in all_rls:
                    all_rls[resource] = {}
                for field, filters in fields.items():
                    if field not in all_rls[resource]:
                        all_rls[resource][field] = []
                    all_rls[resource][field].extend(filters)
        if all_perms:
            permissions[client_id] = list(all_perms)
        if all_rls:
            rls_filters[client_id] = all_rls
    else:
        for app_id, roles_list in user_roles.items():
            all_perms = set()
            all_rls: dict[str, dict[str, list[dict]]] = {}
            for role_name in roles_list:
                # Get permissions directly from database
                perms_from_db = get_role_permissions_from_db(app_id, role_name)
                for p in perms_from_db:
                    all_perms.add(p)
                # Get RLS filters directly from database
                role_rls = get_role_rls_filters_from_db(app_id, role_name)
                # Merge RLS filters correctly - they have structure: {resource: {field: [filters]}}
                for resource, fields in role_rls.items():
                    if resource not in all_rls:
                        all_rls[resource] = {}
                    for field, filters in fields.items():
                        if field not in all_rls[resource]:
                            all_rls[resource][field] = []
                        all_rls[resource][field].extend(filters)
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

    # SECURITY: Add IP and device binding for government security
    if client_ip:
        claims['bound_ip'] = client_ip
        logger.info(f"Token bound to IP: {client_ip}")

    if user_agent:
        # Create a simple device fingerprint from user agent
        import hashlib
        device_fingerprint = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
        claims['bound_device'] = device_fingerprint
        claims['device_ua'] = user_agent[:100]  # Store first 100 chars for debugging
        logger.info(f"Token bound to device: {device_fingerprint}")

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
    user_email = claims.get('email', '').strip().lower()  # Convert to lowercase for comparison
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
async def token_endpoint(token_request: TokenRequest, request: Request):
    if token_request.grant_type == "refresh_token":
        if not token_request.refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token required")

        # SECURITY: Hash the refresh token for database lookup
        old_refresh_token_hash = hashlib.sha256(token_request.refresh_token.encode()).hexdigest()

        # Check if refresh token has been revoked in database
        if db_service.is_token_revoked(token_hash=old_refresh_token_hash):
            logger.warning(f"Attempt to use revoked refresh token")
            raise HTTPException(status_code=401, detail="Refresh token has been revoked")

        # Validate and rotate the refresh token
        user_info, new_refresh_token = refresh_token_store.validate_and_rotate(token_request.refresh_token)
        if not user_info:
            # If invalid, revoke it in database for security
            db_service.revoke_token(
                token_id=old_refresh_token_hash,  # Using hash as ID for refresh tokens
                token_hash=old_refresh_token_hash,
                token_type='refresh',
                reason='invalid_token_attempt'
            )
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

        # SECURITY: Capture client IP and User-Agent for token binding on refresh
        client_ip = request.client.host if request.client else None
        forwarded_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if forwarded_ip:
            client_ip = forwarded_ip
        user_agent = request.headers.get('User-Agent', 'Unknown')

        access_token = generate_token_with_iam_claims(user_info, client_ip=client_ip, user_agent=user_agent)
        token_id = str(uuid.uuid4())
        now_utc = datetime.utcnow()
        expires_utc = now_utc + timedelta(minutes=10)

        # SECURITY: Implement refresh token rotation in database
        # 1. Deactivate the old refresh token
        db_service.deactivate_refresh_token(old_refresh_token_hash)
        logger.info(f"Old refresh token deactivated for rotation")

        # 2. Save the new refresh token
        new_refresh_token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
        db_service.save_refresh_token(
            token_hash=new_refresh_token_hash,
            user_email=user_info.get('email'),
            user_id=user_info.get('sub'),
            expires_at=datetime.utcnow() + timedelta(days=30),
            parent_token_hash=old_refresh_token_hash  # Link to previous token for audit trail
        )
        logger.info(f"New refresh token saved for user {user_info.get('email')} (rotation)")

        # 3. Update refresh token usage count
        db_service.update_refresh_token_usage(old_refresh_token_hash)

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
        token_activity_logger.log_activity(token_id=token_id, action=TokenAction.REFRESHED, performed_by=user_info, details={'source': 'refresh_token', 'rotation': True})

        logger.info(f"Token refresh with rotation completed for {user_info.get('email')}")
        return JSONResponse({'access_token': access_token, 'token_type': 'Bearer', 'expires_in': 600, 'refresh_token': new_refresh_token})
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {token_request.grant_type}")

@app.post("/auth/token/exchange")
async def exchange_code_for_token(exchange_request: TokenExchangeRequest, request: Request):
    try:
        tenant_id, client_id, client_secret = ensure_azure_env()
        
        # Check if we received Azure tokens directly (SPA flow)
        if exchange_request.azure_access_token and exchange_request.azure_id_token:
            azure_access_token = exchange_request.azure_access_token
            azure_id_token = exchange_request.azure_id_token
        # Otherwise, exchange code for tokens (traditional flow)
        elif exchange_request.code:
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
            async with httpx.AsyncClient(timeout=10.0) as client:
                token_data = {
                    'grant_type': 'authorization_code',
                    'client_id': client_id,
                    'code': exchange_request.code,
                    'redirect_uri': exchange_request.redirect_uri,
                    'scope': os.getenv('AZURE_SCOPE', 'openid profile email User.Read')
                }
                
                # If code_verifier is provided (PKCE flow), use it instead of client_secret
                if exchange_request.code_verifier:
                    token_data['code_verifier'] = exchange_request.code_verifier
                else:
                    token_data['client_secret'] = client_secret
                
                response = await client.post(token_url, data=token_data)
            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Azure token exchange failed: {error_data}")
                raise HTTPException(status_code=400, detail=error_data.get('error_description', 'Token exchange failed'))
            azure_token_data = response.json()
            azure_access_token = azure_token_data.get('access_token')
            azure_id_token = azure_token_data.get('id_token')
        else:
            raise HTTPException(status_code=400, detail="Either code or Azure tokens must be provided")
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
        # Get apps from database instead of memory
        db_apps = db_service.get_all_registered_apps()
        for app in db_apps:
            client_id = app['client_id']
            user_app_roles = app_store.get_user_roles_for_app(client_id, group_names)
            logger.info(f"Roles for {client_id} with groups {group_names[:3]}: {user_app_roles}")
            for role in user_app_roles:
                if role not in app_roles:
                    app_roles.append(role)
            if user_app_roles:
                all_perms = set()
                all_rls = {}
                for role_name in user_app_roles:
                    # Get permissions directly from database
                    role_perms = get_role_permissions_from_db(client_id, role_name)
                    all_perms.update(role_perms)
                    # Get RLS filters directly from database
                    role_rls = get_role_rls_filters_from_db(client_id, role_name)
                    # Merge RLS filters correctly - they have structure: {resource: {field: [filters]}}
                    for resource, fields in role_rls.items():
                        if resource not in all_rls:
                            all_rls[resource] = {}
                        for field, filters in fields.items():
                            if field not in all_rls[resource]:
                                all_rls[resource][field] = []
                            all_rls[resource][field].extend(filters)
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
        # SECURITY: Capture client IP and User-Agent for token binding
        client_ip = request.client.host if request.client else None
        # Also check for forwarded IP (if behind proxy)
        forwarded_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if forwarded_ip:
            client_ip = forwarded_ip

        user_agent = request.headers.get('User-Agent', 'Unknown')

        # Add IP and device binding to token
        if client_ip:
            internal_token_payload['bound_ip'] = client_ip
            logger.info(f"Token bound to IP: {client_ip} for user {user_email}")

        if user_agent:
            device_fingerprint = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
            internal_token_payload['bound_device'] = device_fingerprint
            internal_token_payload['device_ua'] = user_agent[:100]
            logger.info(f"Token bound to device: {device_fingerprint} for user {user_email}")

        logger.info(f"Token payload before template - roles: {app_roles}")
        # Template will be applied inside jwt_manager.create_token, so don't apply here
        # This avoids double filtering and preserves security claims
        # filtered_payload = token_template_manager.apply_template(internal_token_payload, group_names)
        # logger.info(f"Token payload after template - roles: {filtered_payload.get('roles')}")
        internal_token = jwt_manager.create_token(internal_token_payload)
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
        # Log the login event
        audit_logger.log_action(
            action=AuditAction.USER_LOGIN,
            user_email=user_email,
            user_id=claims.get('sub'),
            resource_type='token',
            resource_id=internal_token_id,
            details={
                'login_method': 'azure_ad',
                'groups': group_names[:5] if group_names else [],  # Log first 5 groups only
                'is_admin': is_admin,
                'token_id': internal_token_id
            }
        )
        
        refresh_token = refresh_token_store.create_refresh_token({
            'user_id': claims.get('sub'),
            'email': user_email,
            'name': claims.get('name'),
            'is_admin': is_admin,
            'azure_access_token': azure_access_token,
            'groups': user_groups,
            'sub': claims.get('sub')
        })

        # SECURITY: Save initial refresh token to database for tracking
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        db_service.save_refresh_token(
            token_hash=refresh_token_hash,
            user_email=user_email,
            user_id=claims.get('sub'),
            expires_at=datetime.utcnow() + timedelta(days=30),
            client_ip=None,  # TODO: Get from request
            user_agent=None,  # TODO: Get from request headers
            parent_token_hash=None  # This is the initial token, no parent
        )
        logger.info(f"Initial refresh token saved to database for user {user_email}")

        token_activity_logger.log_activity(internal_token_id, TokenAction.CREATED, performed_by={'email': user_email, 'sub': claims.get('sub')}, details={'auth_method': 'oauth_code_exchange'})
        
        # Log successful login to activity_log
        db_service.log_activity(
            activity_type='login',
            entity_type='user',
            entity_id=claims.get('sub'),
            entity_name=claims.get('name'),
            user_email=user_email,
            user_id=claims.get('sub'),
            details={
                'auth_method': 'oauth_code_exchange',
                'groups': group_names[:10] if group_names else [],  # Limit groups to avoid too large JSON
                'is_admin': is_admin,
                'token_id': internal_token_id
            },
            status='success',
            session_id=internal_token_id,
            api_endpoint='/auth/token/exchange',
            http_method='POST'
        )
        
        return JSONResponse({'access_token': internal_token, 'refresh_token': refresh_token, 'token_type': 'Bearer', 'expires_in': 1800})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during token exchange")

@app.get("/auth/validate")
async def validate_token(authorization: Optional[str] = Header(None), x_api_key: Optional[str] = Header(None), request: Request = None):
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

    # SECURITY: Check if token has been revoked (check BOTH database and memory)
    token_id = claims.get('jti') or claims.get('token_id')

    # First check database (authoritative source)
    if token_id and db_service.is_token_revoked(token_id=token_id):
        logger.warning(f"Attempt to use revoked token {token_id} (blocked by database)")
        return JSONResponse({'valid': False, 'error': 'Token has been revoked'})

    # Also check memory cache for recent revocations
    if token_id and token_id in issued_tokens:
        token_data = issued_tokens[token_id]
        if token_data.get('revoked', False):
            logger.warning(f"Attempt to use revoked token {token_id} (blocked by memory cache)")
            return JSONResponse({'valid': False, 'error': 'Token has been revoked'})

    # SECURITY: Check if this is a service-to-service call with valid API key
    skip_ip_validation = False
    service_client_id = None

    if x_api_key:
        logger.info(f"X-API-Key header received: {x_api_key[:20]}...")
        # Validate the service API key
        api_key_valid, service_client_id, service_metadata = validate_api_key_auth(f"Bearer {x_api_key}")
        logger.info(f"API key validation result: valid={api_key_valid}, client_id={service_client_id}")
        if api_key_valid:
            # Service authenticated - this is a legitimate proxy request
            skip_ip_validation = True
            logger.info(f"Service {service_client_id} validating token for user {claims.get('email')} - IP validation bypassed")

            # Log this service proxy action for audit
            db_service.log_activity(
                activity_type='service_proxy_validation',
                entity_type='token',
                entity_id=token_id,
                entity_name=f"Token for {claims.get('email', 'unknown')}",
                user_email=claims.get('email'),
                user_id=claims.get('sub'),
                details={
                    'service_id': service_client_id,
                    'service_name': service_metadata.get('name', 'Unknown Service'),
                    'user_email': claims.get('email'),
                    'action': 'allowed'
                }
            )
        else:
            logger.warning(f"Invalid API key provided with token validation request")

    # SECURITY: Verify IP and device binding if present (skip if service authenticated)
    if request and not skip_ip_validation:
        # Get current request IP
        current_ip = request.client.host if request.client else None
        forwarded_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        if forwarded_ip:
            current_ip = forwarded_ip

        # Check IP binding
        bound_ip = claims.get('bound_ip')
        if bound_ip and current_ip and bound_ip != current_ip:
            # Allow Docker internal network communication (172.x.x.x range)
            is_docker_network = (current_ip.startswith('172.') and bound_ip.startswith('172.'))

            if not is_docker_network:
                logger.warning(f"Token bound to IP {bound_ip} but used from {current_ip} - User: {claims.get('email')}")
                db_service.log_activity(
                    activity_type='security.ip_mismatch',
                    entity_type='token',
                    entity_id=token_id,
                    user_email=claims.get('email'),
                    details={
                        'bound_ip': bound_ip,
                        'current_ip': current_ip,
                        'action': 'blocked'
                    }
                )
                return JSONResponse({'valid': False, 'error': 'Token bound to different IP address'})

        # Check device binding
        current_ua = request.headers.get('User-Agent', '')
        if current_ua:
            current_device = hashlib.sha256(current_ua.encode()).hexdigest()[:16]
            bound_device = claims.get('bound_device')
            if bound_device and bound_device != current_device:
                # Allow requests from backend services (uvicorn user agent)
                is_backend_service = 'uvicorn' in current_ua.lower() or 'python' in current_ua.lower()

                if not is_backend_service:
                    logger.warning(f"Token bound to device {bound_device} but used from {current_device} - User: {claims.get('email')}")
                    db_service.log_activity(
                        activity_type='security.device_mismatch',
                        entity_type='token',
                        entity_id=token_id,
                        user_email=claims.get('email'),
                        details={
                            'bound_device': bound_device,
                            'current_device': current_device,
                            'action': 'blocked'
                        }
                    )
                    return JSONResponse({'valid': False, 'error': 'Token bound to different device'})

    # Include service proxy information if applicable
    response = {
        'valid': True,
        'claims': claims,  # Keep for backward compatibility
        # Also include fields directly for consistency
        'sub': claims.get('sub'),
        'email': claims.get('email'),
        'name': claims.get('name'),
        'groups': claims.get('groups', []),
        'permissions': claims.get('permissions', {}),
        'auth_type': 'jwt'
    }
    if service_client_id:
        response['proxy_service'] = service_client_id
        response['proxy_validation'] = True

    return JSONResponse(response)

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
    return JSONResponse({
        'valid': True,
        'sub': claims.get('sub'),
        'email': claims.get('email'),
        'name': claims.get('name'),
        'groups': claims.get('groups', []),
        'permissions': claims.get('permissions', {}),  # Include permissions from token
        'auth_type': 'jwt'
    })

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

@app.post("/auth/logout")
async def logout(authorization: Optional[str] = Header(None), refresh_token: Optional[str] = None):
    """Enhanced logout with token revocation for government security standards"""
    logger.info(f"Logout endpoint called with auth header: {bool(authorization)}")

    if not authorization or not authorization.startswith('Bearer '):
        # Even if no valid token, acknowledge logout
        logger.info("No valid auth header for logout")
        return JSONResponse({"status": "success", "message": "Logged out"})

    token = authorization.replace('Bearer ', '')
    is_valid, claims, error = jwt_manager.validate_token(token)

    logger.info(f"Token validation for logout: valid={is_valid}, error={error}")

    if is_valid:
        # Log the logout action
        user_email = claims.get('email')
        user_id = claims.get('sub')
        token_id = claims.get('jti') or claims.get('token_id')

        # SECURITY: Revoke the access token in BOTH memory and database
        if token_id:
            # Memory revocation (for backward compatibility)
            if token_id in issued_tokens:
                issued_tokens[token_id]['revoked'] = True
                issued_tokens[token_id]['revoked_at'] = datetime.utcnow().isoformat() + 'Z'
                issued_tokens[token_id]['revoked_reason'] = 'user_logout'

            # DATABASE revocation (permanent, survives restarts)
            expires_at = datetime.fromtimestamp(claims.get('exp')) if claims.get('exp') else None
            db_service.revoke_token(
                token_id=token_id,
                token_type='access',
                revoked_by=user_email,
                reason='logout',
                user_email=user_email,
                user_id=user_id,
                ip_address=None,  # TODO: Get from request
                expires_at=expires_at
            )

            # Log token revocation
            token_activity_logger.log_activity(
                token_id=token_id,
                action=TokenAction.REVOKED,
                performed_by={'email': user_email},
                details={'reason': 'logout', 'ip_address': None}
            )
            logger.info(f"Access token {token_id} revoked in database and memory for user {user_email}")

        # SECURITY: Also revoke the refresh token if provided
        if refresh_token:
            # Store revoked refresh tokens (you'll need to implement refresh token tracking)
            logger.info(f"Refresh token revoked on logout for user {user_email}")

        # Log logout activity
        db_service.log_activity(
            activity_type='logout',
            entity_type='user',
            entity_id=user_id,
            entity_name=claims.get('name'),
            user_email=user_email,
            user_id=user_id,
            details={
                'session_end': datetime.utcnow().isoformat(),
                'token_revoked': bool(token_id),
                'refresh_token_revoked': bool(refresh_token)
            }
        )

        logger.info(f"User {user_email} logged out with token revocation")

    return JSONResponse({"status": "success", "message": "Logged out and tokens revoked"})

# ==============================
# Admin: App Registration routes
# ==============================

@app.get("/auth/admin/apps")
async def list_apps(authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get apps from Supabase instead of JSON file
    apps = db_service.get_all_registered_apps()
    
    # Return as plain list of dicts; shapes match AppResponse
    return JSONResponse(apps)

@app.get("/auth/admin/apps/stats")
async def get_apps_stats(authorization: Optional[str] = Header(None)):
    """Get statistics about registered applications from Supabase"""
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get stats from Supabase
    stats = db_service.get_registered_apps_stats()
    
    # Also get counts for other KPIs (these can be expanded later)
    # For now, return placeholder values for tokens and API keys
    return JSONResponse({
        "apps": {
            "total": stats['total'],
            "active": stats['active'],
            "inactive": stats['inactive']
        },
        "tokens": {
            "active": 142  # TODO: Get from token activity
        },
        "api_keys": {
            "total": 28  # TODO: Get from API key store
        }
    })

@app.get("/auth/admin/dashboard/stats")
async def get_dashboard_stats(authorization: Optional[str] = Header(None)):
    """Get comprehensive dashboard statistics from database"""
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get comprehensive stats from database
    stats = db_service.get_dashboard_stats()
    
    return JSONResponse({
        "apps": {
            "total": stats.get('apps_total', 0),
            "active": stats.get('apps_active', 0),
            "discovered": stats.get('apps_discovered', 0)
        },
        "endpoints_total": stats.get('endpoints_total', 0),
        "discovery_endpoints_total": stats.get('discovery_endpoints_total', 0),
        "roles": {
            "total": stats.get('roles_total', 0),
            "active": stats.get('roles_active', 0),
            "inactive": stats.get('roles_inactive', 0)
        },
        "permissions": {
            "total": stats.get('permissions_total', 0),
            "by_role": stats.get('permissions_by_role', [])
        },
        "api_keys": {
            "total": stats.get('api_keys_total', 0),
            "active": stats.get('api_keys_active', 0)
        },
        "a2a_permissions": {
            "total": stats.get('a2a_permissions_total', 0),
            "active": stats.get('a2a_permissions_active', 0),
            "inactive": stats.get('a2a_permissions_inactive', 0)
        },
        "rotation_policies_total": stats.get('rotation_policies_total', 0),
        "rls_filters": {
            "total": stats.get('rls_filters_total', 0),
            "active": stats.get('rls_filters_active', 0),
            "inactive": stats.get('rls_filters_inactive', 0)
        },
        "tokens": {
            "templates": stats.get('token_templates_total', 0)
        },
        "activity": {
            "last_24h": stats.get('activity_last_24h', 0)
        }
    })

@app.get("/auth/admin/apps/{client_id}")
async def get_app_admin(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get app from Supabase
    app_data = db_service.get_app_by_id(client_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="App not found")
    return JSONResponse(app_data)

@app.post("/auth/admin/apps")
async def register_app_admin(request: RegisterAppRequest, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Request client_id from uuid-service
    try:
        async with httpx.AsyncClient() as client:
            uuid_response = await client.post(
                "http://uuid-service-dev:8002/generate",
                json={"type": "app", "count": 1},
                timeout=10.0
            )
            uuid_response.raise_for_status()
            uuid_data = uuid_response.json()
            client_id = uuid_data.get("id")
            
            if not client_id:
                raise HTTPException(status_code=500, detail="Failed to generate client_id from uuid-service")
                
            logging.info(f"Generated client_id from uuid-service: {client_id}")
    except httpx.RequestError as e:
        logging.error(f"Failed to connect to uuid-service: {e}")
        raise HTTPException(status_code=503, detail="UUID service unavailable")
    except Exception as e:
        logging.error(f"Error generating client_id: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate client_id")
    
    # Create app in Supabase with uuid-service generated ID
    app_data = {
        "client_id": client_id,
        "name": request.name,
        "description": request.description,
        "redirect_uris": request.redirect_uris,
        "owner_email": request.owner_email,
        "discovery_endpoint": request.discovery_endpoint,
        "allow_discovery": request.allow_discovery,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    if not db_service.create_app(app_data):
        raise HTTPException(status_code=500, detail="Failed to create app")
    
    # Log app creation
    audit_logger.log_action(
        action=AuditAction.APP_CREATED,
        user_email=claims.get('email') if claims else request.owner_email,
        user_id=claims.get('sub') if claims else None,
        resource_type='app',
        resource_id=client_id,
        details={
            'app_name': request.name,
            'description': request.description,
            'owner_email': request.owner_email,
            'allow_discovery': request.allow_discovery
        }
    )
    
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
    
    # Also log to activity_log for centralized auditing
    db_service.log_activity(
        activity_type='app_registered',
        entity_type='app',
        entity_id=app_data["client_id"],
        entity_name=request.name,
        user_email=claims.get('email', 'admin'),
        user_id=claims.get('sub'),
        details={
            'description': request.description,
            'owner_email': request.owner_email,
            'api_key_created': api_key is not None,
            'allow_discovery': request.allow_discovery
        },
        status='success',
        api_endpoint='/auth/admin/apps',
        http_method='POST'
    )

    # Generate client secret
    import secrets
    client_secret = secrets.token_urlsafe(32)
    
    # Return the registration response
    response_data = {
        "app": app_data,
        "client_secret": client_secret
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
        all_rls: dict[str, dict[str, list[dict]]] = {}
        for role_name in roles_list:
            # Get permissions directly from database
            perms_from_db = get_role_permissions_from_db(app_id, role_name)
            for p in perms_from_db:
                all_perms.add(p)
            # Get RLS filters directly from database
            role_rls = get_role_rls_filters_from_db(app_id, role_name)
            # Merge RLS filters correctly - they have structure: {resource: {field: [filters]}}
            for resource, fields in role_rls.items():
                if resource not in all_rls:
                    all_rls[resource] = {}
                for field, filters in fields.items():
                    if field not in all_rls[resource]:
                        all_rls[resource][field] = []
                    all_rls[resource][field].extend(filters)
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
    
    # Check if app exists
    existing_app = db_service.get_app_by_id(client_id)
    if not existing_app:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Build updates dict
    updates = {}
    if request.name is not None:
        updates['name'] = request.name
    if request.description is not None:
        updates['description'] = request.description
    if request.redirect_uris is not None:
        updates['redirect_uris'] = request.redirect_uris
    if request.is_active is not None:
        updates['is_active'] = request.is_active
    if request.discovery_endpoint is not None:
        updates['discovery_endpoint'] = request.discovery_endpoint
    if request.allow_discovery is not None:
        updates['allow_discovery'] = request.allow_discovery
    
    # Update in Supabase
    if not db_service.update_app(client_id, updates):
        raise HTTPException(status_code=500, detail="Failed to update app")
    
    # Log activity for is_active changes
    if 'is_active' in updates:
        action_desc = 'activated' if updates['is_active'] else 'deactivated'
        audit_logger.log_action(
            action=AuditAction.APP_UPDATED, 
            user_email=claims.get('email'),
            resource_type="app",
            resource_id=client_id,
            details={
                'app_name': existing_app.get('name', 'Unknown'),
                'action': f'app_{action_desc}',
                'new_status': 'active' if updates['is_active'] else 'inactive',
                'previous_status': 'active' if existing_app.get('is_active') else 'inactive'
            }
        )
    
    # Return updated app
    app_data = db_service.get_app_by_id(client_id)
    return JSONResponse(app_data)



@app.delete("/auth/admin/apps/{client_id}")
async def delete_app_admin(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if app exists in Supabase
    app_info = db_service.get_app_by_id(client_id)
    if not app_info:
        raise HTTPException(status_code=404, detail="App not found")
    
    # Delete from Supabase
    if not db_service.delete_app(client_id):
        raise HTTPException(status_code=500, detail="Failed to delete app")

    # Log app deletion
    audit_logger.log_action(
        action=AuditAction.APP_DELETED,
        user_email=claims.get('email') if claims else None,
        user_id=claims.get('sub') if claims else None,
        resource_type='app',
        resource_id=client_id,
        details={
            'app_name': app_info.get('name'),
            'owner_email': app_info.get('owner_email')
        }
    )

    # Clean up related data
    # 1. Revoke all API keys for this app
    api_keys = api_key_manager.list_api_keys(client_id)
    for api_key in api_keys:
        api_key_manager.revoke_api_key(client_id, api_key.key_id)

    # 2. Delete app endpoints
    endpoints_registry.delete_app_endpoints(client_id)

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

# COMMENTED OUT: Old endpoint using JSON files, replaced by database version below
# @app.get("/auth/admin/apps/{caller_id}/a2a-role-mappings")
# async def get_a2a_role_mappings_admin(caller_id: str, authorization: Optional[str] = Header(None)):
#     is_admin, _ = check_admin_access(authorization)
#     if not is_admin:
#         raise HTTPException(status_code=403, detail="Admin access required")
#     if not app_store.get_app(caller_id):
#         raise HTTPException(status_code=404, detail="Caller app not found")
#     return JSONResponse({caller_id: app_store.get_a2a_mappings_for_caller(caller_id)})

class A2ARoleMappingsRequest(BaseModel):
    mappings: Dict[str, List[str]]

# COMMENTED OUT: Old endpoint using JSON files, replaced by database version below
# @app.put("/auth/admin/apps/{caller_id}/a2a-role-mappings")
# async def put_a2a_role_mappings_admin(caller_id: str, request: A2ARoleMappingsRequest, authorization: Optional[str] = Header(None)):
#     is_admin, claims = check_admin_access(authorization)
#     if not is_admin:
#         raise HTTPException(status_code=403, detail="Admin access required")
#     if not app_store.get_app(caller_id):
#         raise HTTPException(status_code=404, detail="Caller app not found")
#     # Validate target apps and roles
#     for target_app_id, roles in (request.mappings or {}).items():
#         if not app_store.get_app(target_app_id):
#             raise HTTPException(status_code=400, detail=f"Unknown target app: {target_app_id}")
#         for role_name in roles or []:
#             role_config = permission_registry.get_role_full_config(target_app_id, role_name)
#             if not role_config['permissions'] and not role_config['rls_filters']:
#                 raise HTTPException(status_code=400, detail=f"Unknown role '{role_name}' for app '{target_app_id}'")
#     result = app_store.upsert_a2a_mappings(caller_id, request.mappings or {})
#     audit_logger.log_action(action=AuditAction.ROLE_MAPPINGS_UPDATED, details={'type': 'a2a', 'caller': caller_id, 'updated_by': claims.get('email')})
#     return JSONResponse({"caller": caller_id, "mappings": result[caller_id]})

@app.post("/auth/admin/apps/{client_id}/role-mappings")
async def set_role_mappings_admin(client_id: str, request: SetRoleMappingRequest, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if app exists in database first
    app_data = db_service.get_app_by_id(client_id)
    app_exists_in_db = app_data is not None
    
    if not app_exists_in_db:
        # Fallback to JSON for legacy apps
        if not app_store.get_app(client_id):
            raise HTTPException(status_code=404, detail="App not found")
    
    # For database apps, we need to ensure they're also in the JSON for now
    # This is a temporary solution until we fully migrate role mappings to database
    if app_exists_in_db and client_id not in registered_apps:
        # Add the app to registered_apps so role mappings can be saved
        registered_apps[client_id] = {
            "client_id": client_id,
            "name": app_data.get('name'),
            "owner_email": app_data.get('owner_email'),
            "created_at": app_data.get('created_at', datetime.now().isoformat()),
            "is_active": app_data.get('is_active', True)
        }
    
    ok = app_store.set_role_mappings(client_id, request.mappings, created_by=claims.get('email', 'admin'))
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to update role mappings")
    return JSONResponse({"message": "Role mappings updated successfully", "mappings": request.mappings})

@app.get("/auth/admin/apps/{client_id}/role-mappings")
async def get_role_mappings_admin(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get app from database
    app_data = db_service.get_app_by_id(client_id)
    if not app_data:
        # Fallback to JSON for legacy apps
        app_data = app_store.get_app(client_id)
        if not app_data:
            raise HTTPException(status_code=404, detail="App not found")
    
    mappings = app_store.get_role_mappings(client_id)
    return JSONResponse({"app_name": app_data.get('name'), "client_id": client_id, "mappings": mappings})

# A2A Permissions Management Endpoints
@app.get("/auth/admin/a2a-permissions")
async def get_a2a_permissions_admin(authorization: Optional[str] = Header(None)):
    """Get all A2A permissions from database"""
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    permissions = db_service.get_all_a2a_permissions()
    return JSONResponse(permissions)

@app.get("/auth/admin/a2a-connections")
async def get_a2a_connections_admin(authorization: Optional[str] = Header(None)):
    """Get A2A connections with app details for visualization"""
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get all A2A permissions
    permissions = db_service.get_all_a2a_permissions()

    # Get all registered apps
    apps = db_service.get_all_registered_apps()
    app_map = {app['client_id']: app for app in apps}

    # Enrich permissions with app details
    connections = []
    for perm in permissions:
        source_app = app_map.get(perm['source_client_id'])
        target_app = app_map.get(perm['target_client_id'])

        if source_app and target_app:
            connections.append({
                'id': perm.get('a2a_id'),
                'source': {
                    'client_id': perm['source_client_id'],
                    'name': source_app.get('name', 'Unknown'),
                    'description': source_app.get('description', '')
                },
                'target': {
                    'client_id': perm['target_client_id'],
                    'name': target_app.get('name', 'Unknown'),
                    'description': target_app.get('description', '')
                },
                'is_active': perm.get('is_active', False),
                'allowed_scopes': perm.get('allowed_scopes', []),
                'allowed_endpoints': perm.get('allowed_endpoints', []),
                'created_at': perm.get('created_at'),
                'updated_at': perm.get('updated_at')
            })

    return JSONResponse({'connections': connections, 'total': len(connections)})

class A2APermissionRequest(BaseModel):
    source_client_id: str
    target_client_id: str
    allowed_scopes: List[str]
    max_token_duration: int = 300
    is_active: bool = True

@app.post("/auth/admin/a2a-permissions")
async def create_a2a_permission_admin(request: A2APermissionRequest, authorization: Optional[str] = Header(None)):
    """Create a new A2A permission"""
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate source and target apps exist
    source_app = db_service.get_app_by_id(request.source_client_id) or app_store.get_app(request.source_client_id)
    if not source_app:
        raise HTTPException(status_code=400, detail=f"Source app {request.source_client_id} not found")

    target_app = db_service.get_app_by_id(request.target_client_id) or app_store.get_app(request.target_client_id)
    if not target_app:
        raise HTTPException(status_code=400, detail=f"Target app {request.target_client_id} not found")

    # Create permission
    permission_id = db_service.create_a2a_permission(
        source_client_id=request.source_client_id,
        target_client_id=request.target_client_id,
        allowed_scopes=request.allowed_scopes,
        max_token_duration=request.max_token_duration,
        is_active=request.is_active,
        created_by=claims.get('email', 'admin')
    )

    audit_logger.log_action(
        action=AuditAction.A2A_PERMISSION_CREATED,
        details={
            'permission_id': permission_id,
            'source': request.source_client_id,
            'target': request.target_client_id,
            'scopes': request.allowed_scopes,
            'created_by': claims.get('email')
        }
    )

    return JSONResponse({"id": permission_id, "message": "A2A permission created successfully"})

@app.put("/auth/admin/a2a-permissions/{permission_id}")
async def update_a2a_permission_admin(permission_id: str, request: A2APermissionRequest, authorization: Optional[str] = Header(None)):
    """Update an existing A2A permission"""
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check permission exists
    existing = db_service.get_a2a_permission_by_id(permission_id)
    if not existing:
        raise HTTPException(status_code=404, detail="A2A permission not found")

    # Update permission
    success = db_service.update_a2a_permission(
        permission_id=permission_id,
        allowed_scopes=request.allowed_scopes,
        max_token_duration=request.max_token_duration,
        is_active=request.is_active,
        updated_by=claims.get('email', 'admin')
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update A2A permission")

    audit_logger.log_action(
        action=AuditAction.A2A_PERMISSION_UPDATED,
        details={
            'permission_id': permission_id,
            'updated_by': claims.get('email')
        }
    )

    return JSONResponse({"message": "A2A permission updated successfully"})

@app.delete("/auth/admin/a2a-permissions/{permission_id}")
async def delete_a2a_permission_admin(permission_id: str, authorization: Optional[str] = Header(None)):
    """Delete an A2A permission"""
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check permission exists
    existing = db_service.get_a2a_permission_by_id(permission_id)
    if not existing:
        raise HTTPException(status_code=404, detail="A2A permission not found")

    # Delete permission
    success = db_service.delete_a2a_permission(permission_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete A2A permission")

    audit_logger.log_action(
        action=AuditAction.A2A_PERMISSION_DELETED,
        details={
            'permission_id': permission_id,
            'deleted_by': claims.get('email')
        }
    )

    return JSONResponse({"message": "A2A permission deleted successfully"})

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
            clean_search = search.replace("'", "")
            fallback_url = f"https://graph.microsoft.com/v1.0/groups?$select=id,displayName,description&$filter=startswith(displayName,'{clean_search}')&$top={min(top, 999)}"
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
    # Check if app exists in database
    db_app = db_service.get_registered_app(client_id)
    if not db_app:
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
    # Check if app exists in database
    db_app = db_service.get_registered_app(client_id)
    if not db_app:
        raise HTTPException(status_code=404, detail="App not found")
    # Get API keys from database
    keys = db_service.get_api_keys_for_app(client_id)
    return JSONResponse(keys if keys else [])

@app.get("/auth/admin/apps/{client_id}/has-active-api-key")
async def check_active_api_key(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if app has any active API keys
    has_active = db_service.has_active_api_key(client_id)
    return JSONResponse({"has_active_key": has_active})

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


@app.get("/auth/admin/apps/{client_id}/a2a-role-mappings")
async def get_a2a_role_mappings(client_id: str, authorization: Optional[str] = Header(None)):
    logger.info(f"A2A role mappings endpoint called for client_id: {client_id}")

    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        logger.warning(f"Non-admin access attempt for a2a-role-mappings: {client_id}")
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if app exists in database
    try:
        db_app = db_service.get_registered_app(client_id)
        logger.info(f"get_registered_app result for {client_id}: {db_app is not None}")

        if not db_app:
            logger.error(f"App not found in database for client_id: {client_id}")
            raise HTTPException(status_code=404, detail="Caller app not found")
    except Exception as e:
        logger.error(f"Error getting app from database: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # For now return empty mappings - can be implemented later
    logger.info(f"Returning empty mappings for client_id: {client_id}")
    return JSONResponse({
        "client_id": client_id,
        "mappings": []
    })

@app.put("/auth/admin/apps/{client_id}/a2a-role-mappings")
async def update_a2a_role_mappings(client_id: str, mappings: Dict = Body(...), authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if app exists in database
    db_app = db_service.get_registered_app(client_id)
    if not db_app:
        raise HTTPException(status_code=404, detail="Caller app not found")

    # For now just return success - can be implemented later
    return JSONResponse({"message": "A2A role mappings updated successfully"})

@app.post("/discovery/endpoints/{client_id}")
async def trigger_discovery(client_id: str, authorization: Optional[str] = Header(None), force: bool = True):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user_email = claims.get('email') if claims else None
    app_data = db_service.get_app_by_id(client_id)
    app_name = app_data.get('name') if app_data else client_id
    
    # Insert activity_log entry with dis_ prefixed ID from UUID service
    try:
        import httpx
        with httpx.Client() as http_client:
            response = http_client.post(
                "http://uuid-service-dev:8002/generate",
                json={
                    "type": "custom",
                    "prefix": "dis",
                    "format": "uuid_v4",
                    "requestor": "discovery_button",
                    "description": f"Discovery button pressed for {app_name}"
                },
                timeout=5.0
            )
            if response.status_code == 200:
                activity_id = response.json().get("id")
                logger.info(f"Generated discovery activity ID: {activity_id}")
                
                # Insert into activity_log table using db_service
                result = db_service.log_activity(
                    activity_id=activity_id,
                    activity_type="discovery_app_process",
                    entity_type="app",
                    entity_id=client_id,
                    entity_name=app_name,
                    user_email=user_email,
                    status="started"
                )
                if result:
                    logger.info(f"Inserted activity_log entry with ID: {activity_id}")
                else:
                    logger.error(f"Failed to insert activity_log entry with ID: {activity_id}")
                    
            else:
                logger.warning(f"Failed to get UUID from service: {response.status_code}")
                
    except Exception as e:
        logger.error(f"Failed to log discovery activity: {e}")
    
    # STEP 2: Execute discovery and save discovery_history
    try:
        # Get discovery endpoint from app data
        discovery_endpoint = app_data.get('discovery_endpoint')
        if not discovery_endpoint:
            raise Exception("No discovery endpoint configured for this app")
        
        logger.info(f"[STEP 2] Starting discovery for {client_id} at {discovery_endpoint}")
        
        # Connect to hr-system and get endpoints
        import httpx
        with httpx.Client() as http_client:
            discovery_response = http_client.get(f"{discovery_endpoint}?version=2.0", timeout=10.0)
            discovery_response.raise_for_status()
            discovery_data = discovery_response.json()
            
        logger.info(f"[STEP 2] Discovery response received: {len(discovery_data.get('endpoints', []))} endpoints")
        
        # Use the SAME dis_ ID from step 1 - NO new ID generation
        logger.info(f"[STEP 2] Using same discovery ID: {activity_id}")
        
        # Insert discovery_history with SAME dis_ ID and auto-increment discovery_version
        if activity_id:
            import json
            
            # Check if there are existing discovery records for this client_id
            existing_versions = db_service.execute_query(
                "SELECT MAX(discovery_version) as max_version FROM cids.discovery_history WHERE client_id = %s",
                (client_id,)
            )
            
            # Determine next version number
            if existing_versions and existing_versions[0]['max_version'] is not None:
                # Convert to int and add 1
                max_version = int(existing_versions[0]['max_version'])
                next_version = max_version + 1
                logger.info(f"[STEP 2] Found existing versions for {client_id}, max: {max_version}, next: {next_version}")
            else:
                next_version = 1
                logger.info(f"[STEP 2] First discovery for {client_id}, version: {next_version}")
            
            history_result = db_service.execute_update("""
                INSERT INTO cids.discovery_history 
                (discovery_id, client_id, discovery_timestamp, discovered_by, endpoints_count, discovery_data, status, discovery_version)
                VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s)
            """, (
                activity_id,  # Use SAME dis_ ID from step 1
                client_id,
                user_email,
                len(discovery_data.get('endpoints', [])),
                json.dumps(discovery_data),  # Convert dict to JSON string
                "completed",  # Set status as completed for this step
                str(next_version)  # Auto-incremented version as string
            ))
            
            logger.info(f"[STEP 2] Saved discovery_history with ID: {activity_id}, version: {next_version}, result: {history_result}")

            # Update registered_apps with discovery information (field_count will be updated at the end)
            update_app_result = db_service.execute_update("""
                UPDATE cids.registered_apps
                SET last_discovery_at = NOW(),
                    discovery_status = 'completed',
                    discovery_version = %s,
                    last_discovery_run_at = NOW(),
                    last_discovery_run_by = %s,
                    discovery_run_count = COALESCE(discovery_run_count, 0) + 1
                WHERE client_id = %s
            """, (
                str(next_version),
                user_email,
                client_id
            ))
            logger.info(f"[STEP 2] Updated registered_apps discovery fields for {client_id}, result: {update_app_result}")

        # STEP 3: Save individual endpoints to discovery_endpoints
        
        # Use the SAME dis_ ID from step 1 - NO new ID generation
        logger.info(f"[STEP 3] Using same discovery ID: {activity_id} for endpoints")
        
        # Process and save each endpoint
        endpoints_saved = 0
        endpoints = discovery_data.get('endpoints', [])
        
        for endpoint in endpoints:
            try:
                # Generate endpoint_id from UUID service with end_ prefix
                try:
                    async with httpx.AsyncClient() as client:
                        uuid_response = await client.post(
                            "http://uuid-service-dev:8002/generate",
                            json={"prefix": "end"}
                        )
                        uuid_response.raise_for_status()
                        endpoint_id = uuid_response.json().get("id")
                        logger.info(f"[STEP 3] Generated endpoint_id: {endpoint_id}")
                except Exception as e:
                    logger.error(f"[STEP 3] Failed to generate endpoint_id: {e}")
                    endpoint_id = None  # Fallback to NULL if UUID service fails
                
                # Extract endpoint data
                method = endpoint.get('method', 'GET')
                path = endpoint.get('path', '')
                operation_id = endpoint.get('operation_id', '')
                description = endpoint.get('description', '')
                resource = endpoint.get('resource', '')
                action = endpoint.get('action', '')
                parameters = endpoint.get('parameters', {})
                response_fields = endpoint.get('response_fields', {})
                
                # Insert endpoint into discovery_endpoints
                endpoint_result = db_service.execute_update("""
                    INSERT INTO cids.discovery_endpoints 
                    (discovery_id, method, path, operation_id, description, resource, action, parameters, response_fields, endpoint_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    activity_id,  # Use SAME dis_ ID from step 1
                    method,
                    path,
                    operation_id,
                    description,
                    resource,
                    action,
                    json.dumps(parameters) if parameters else '{}',
                    json.dumps(response_fields) if response_fields else '{}',
                    endpoint_id
                ))
                
                if endpoint_result:
                    endpoints_saved += 1
                    
            except Exception as e:
                logger.error(f"[STEP 3] Failed to save endpoint {path}: {e}")
        
        logger.info(f"[STEP 3] Saved {endpoints_saved}/{len(endpoints)} endpoints")
        
        # STEP 4: Generate and save permissions to discovered_permissions
        logger.info(f"[STEP 4] Starting permission generation for {len(endpoints)} endpoints")
        
        permissions_saved = 0
        permissions_by_resource = {}  # Group permissions by resource+action
        
        for endpoint in endpoints:
            try:
                resource = endpoint.get('resource', '')
                action = endpoint.get('action', '')
                response_fields = endpoint.get('response_fields', {})
                
                if not resource or not action:
                    continue
                
                # Get fields list from response_fields
                fields = []
                if isinstance(response_fields, dict):
                    # Extract field names from response_fields structure
                    if 'fields' in response_fields:
                        fields = response_fields['fields']
                    elif 'properties' in response_fields:
                        fields = list(response_fields['properties'].keys())
                    else:
                        # If response_fields is a direct field list
                        fields = list(response_fields.keys()) if response_fields else []
                
                # Create key for this resource+action combination
                perm_key = f"{resource}.{action}"
                
                # Aggregate fields for this resource+action
                if perm_key not in permissions_by_resource:
                    permissions_by_resource[perm_key] = {
                        'resource': resource,
                        'action': action,
                        'fields': set()
                    }
                
                # Add fields to the set (avoids duplicates)
                if isinstance(fields, list):
                    permissions_by_resource[perm_key]['fields'].update(fields)
                    
            except Exception as e:
                logger.error(f"[STEP 4] Failed to process permission for {resource}.{action}: {e}")
        
        # Now save aggregated permissions to discovered_permissions
        for perm_key, perm_data in permissions_by_resource.items():
            try:
                # Convert set to list for JSON
                available_fields = list(perm_data['fields'])
                
                # Generate permission_id from UUID service with per_ prefix
                try:
                    async with httpx.AsyncClient() as client:
                        uuid_response = await client.post(
                            "http://uuid-service-dev:8002/generate",
                            json={"prefix": "per"}
                        )
                        uuid_response.raise_for_status()
                        permission_id = uuid_response.json().get("id")
                        logger.info(f"[STEP 4] Generated permission_id: {permission_id}")
                except Exception as e:
                    logger.error(f"[STEP 4] Failed to generate permission_id: {e}")
                    permission_id = None  # Fallback to NULL if UUID service fails
                
                # Insert permission into discovered_permissions
                # Always insert new record for audit trail - each discovery creates new records
                perm_result = db_service.execute_update("""
                    INSERT INTO cids.discovered_permissions 
                    (discovery_id, client_id, resource, action, available_fields, discovered_at, is_active, permission_id)
                    VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s)
                """, (
                    activity_id,  # Use same dis_ ID
                    client_id,
                    perm_data['resource'],
                    perm_data['action'],
                    json.dumps(available_fields) if available_fields else '[]',
                    True,  # Set as active by default
                    permission_id
                ))
                
                if perm_result:
                    permissions_saved += 1
                    logger.info(f"[STEP 4] Saved permission: {perm_key} with {len(available_fields)} fields")
                    
            except Exception as e:
                logger.error(f"[STEP 4] Failed to save permission {perm_key}: {e}")
        
        logger.info(f"[STEP 4] Saved {permissions_saved} permissions from {len(endpoints)} endpoints")
        
        # STEP 5: Process and save field metadata
        logger.info(f"[STEP 5] Starting field metadata extraction for {len(endpoints)} endpoints")
        fields_saved = 0
        
        # Get saved endpoints with their IDs for linking
        endpoint_ids = {}
        try:
            endpoint_result = db_service.execute_query("""
                SELECT endpoint_id, method, path 
                FROM cids.discovery_endpoints 
                WHERE discovery_id = %s
            """, (activity_id,))
            
            for row in endpoint_result:
                key = f"{row['method']}:{row['path']}"
                endpoint_ids[key] = row['endpoint_id']
        except Exception as e:
            logger.error(f"[STEP 5] Failed to retrieve endpoint IDs: {e}")
        
        # Process each endpoint's fields
        for endpoint in endpoints:
            method = endpoint.get('method', 'GET')
            path = endpoint.get('path', '')
            endpoint_key = f"{method}:{path}"
            endpoint_id = endpoint_ids.get(endpoint_key)
            
            if not endpoint_id:
                logger.warning(f"[STEP 5] No endpoint_id found for {endpoint_key}")
                continue
            
            # Process response fields
            response_fields = endpoint.get('response_fields', {})
            if isinstance(response_fields, dict):
                for field_name, field_meta in response_fields.items():
                    if isinstance(field_meta, dict):
                        try:
                            # Generate field_meta_id from UUID service
                            try:
                                async with httpx.AsyncClient() as client:
                                    uuid_response = await client.post(
                                        "http://uuid-service-dev:8002/generate",
                                        json={"prefix": "fld"}
                                    )
                                    uuid_response.raise_for_status()
                                    field_meta_id = uuid_response.json().get("id")
                            except Exception as e:
                                logger.error(f"[STEP 5] Failed to generate field_meta_id: {e}")
                                field_meta_id = None
                            
                            if field_meta_id:
                                # Insert field metadata
                                field_result = db_service.execute_update("""
                                    INSERT INTO cids.field_metadata 
                                    (field_meta_id, endpoint_id, discovery_id, field_name, field_path, 
                                     field_type, field_location, description, is_required, is_sensitive, 
                                     is_pii, is_phi, is_financial, is_read_only, is_write_only,
                                     format, pattern, enum_values, min_length, max_length, 
                                     minimum, maximum)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    field_meta_id,
                                    endpoint_id,
                                    activity_id,
                                    field_name,
                                    field_name,  # field_path - could be nested like "address.street"
                                    field_meta.get('type'),
                                    'response',  # field_location
                                    field_meta.get('description'),
                                    field_meta.get('required', False),
                                    field_meta.get('sensitive', False),
                                    field_meta.get('pii', False),
                                    field_meta.get('phi', False),
                                    field_meta.get('financial', False),
                                    field_meta.get('read_only', False),
                                    field_meta.get('write_only', False),
                                    field_meta.get('format'),
                                    field_meta.get('pattern'),
                                    json.dumps(field_meta.get('enum')) if field_meta.get('enum') else None,
                                    field_meta.get('min_length'),
                                    field_meta.get('max_length'),
                                    field_meta.get('minimum'),
                                    field_meta.get('maximum')
                                ))
                                
                                if field_result:
                                    fields_saved += 1
                        except Exception as e:
                            logger.error(f"[STEP 5] Failed to save field {field_name}: {e}")
            
            # Process request fields
            request_fields = endpoint.get('request_fields', {})
            if isinstance(request_fields, dict):
                for field_name, field_meta in request_fields.items():
                    if isinstance(field_meta, dict):
                        try:
                            # Generate field_meta_id
                            try:
                                async with httpx.AsyncClient() as client:
                                    uuid_response = await client.post(
                                        "http://uuid-service-dev:8002/generate",
                                        json={"prefix": "fld"}
                                    )
                                    uuid_response.raise_for_status()
                                    field_meta_id = uuid_response.json().get("id")
                            except Exception as e:
                                logger.error(f"[STEP 5] Failed to generate field_meta_id: {e}")
                                field_meta_id = None
                            
                            if field_meta_id:
                                # Insert field metadata for request field
                                field_result = db_service.execute_update("""
                                    INSERT INTO cids.field_metadata 
                                    (field_meta_id, endpoint_id, discovery_id, field_name, field_path, 
                                     field_type, field_location, description, is_required, is_sensitive, 
                                     is_pii, is_phi, is_financial, is_read_only, is_write_only,
                                     format, pattern, enum_values, min_length, max_length, 
                                     minimum, maximum)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    field_meta_id,
                                    endpoint_id,
                                    activity_id,
                                    field_name,
                                    field_name,
                                    field_meta.get('type'),
                                    'request',  # field_location
                                    field_meta.get('description'),
                                    field_meta.get('required', False),
                                    field_meta.get('sensitive', False),
                                    field_meta.get('pii', False),
                                    field_meta.get('phi', False),
                                    field_meta.get('financial', False),
                                    field_meta.get('read_only', False),
                                    field_meta.get('write_only', False),
                                    field_meta.get('format'),
                                    field_meta.get('pattern'),
                                    json.dumps(field_meta.get('enum')) if field_meta.get('enum') else None,
                                    field_meta.get('min_length'),
                                    field_meta.get('max_length'),
                                    field_meta.get('minimum'),
                                    field_meta.get('maximum')
                                ))
                                
                                if field_result:
                                    fields_saved += 1
                        except Exception as e:
                            logger.error(f"[STEP 5] Failed to save request field {field_name}: {e}")
            
            # Process parameters
            parameters = endpoint.get('parameters', [])
            if isinstance(parameters, list):
                for param in parameters:
                    if isinstance(param, dict):
                        field_name = param.get('name')
                        if field_name:
                            try:
                                # Generate field_meta_id
                                try:
                                    async with httpx.AsyncClient() as client:
                                        uuid_response = await client.post(
                                            "http://uuid-service-dev:8002/generate",
                                            json={"prefix": "fld"}
                                        )
                                        uuid_response.raise_for_status()
                                        field_meta_id = uuid_response.json().get("id")
                                except Exception as e:
                                    logger.error(f"[STEP 5] Failed to generate field_meta_id: {e}")
                                    field_meta_id = None
                                
                                if field_meta_id:
                                    # Insert parameter metadata
                                    field_result = db_service.execute_update("""
                                        INSERT INTO cids.field_metadata 
                                        (field_meta_id, endpoint_id, discovery_id, field_name, field_path, 
                                         field_type, field_location, description, is_required, is_sensitive, 
                                         pattern, enum_values)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """, (
                                        field_meta_id,
                                        endpoint_id,
                                        activity_id,
                                        field_name,
                                        field_name,
                                        param.get('type'),
                                        'parameter',  # field_location
                                        param.get('description'),
                                        param.get('required', False),
                                        param.get('sensitive', False),
                                        param.get('pattern'),
                                        json.dumps(param.get('enum')) if param.get('enum') else None
                                    ))
                                    
                                    if field_result:
                                        fields_saved += 1
                            except Exception as e:
                                logger.error(f"[STEP 5] Failed to save parameter {field_name}: {e}")
        
        logger.info(f"[STEP 5] Saved {fields_saved} field metadata records")
        
        # Update activity_log to completed status
        if activity_id:
            update_result = db_service.execute_update(
                "UPDATE cids.activity_log SET status = %s, timestamp = NOW() WHERE activity_id = %s",
                ("completed", activity_id)
            )
            logger.info(f"[STEP 5] Updated activity_log status to completed")
        
        # STEP 6: Generate category-based permissions after field_metadata is saved
        logger.info(f"[STEP 6] Starting category permission generation for {client_id}")
        categories_created = 0
        try:
            discovery_db_instance = DiscoveryDatabase()
            categories_created = discovery_db_instance.generate_category_permissions(client_id, activity_id)
            logger.info(f"[STEP 6] Category permissions created: {categories_created}")
        except Exception as e:
            logger.error(f"[STEP 6] Failed to generate category permissions: {e}")
        
        # FINAL STEP: Update field_count in both discovery_history and registered_apps
        logger.info(f"[FINAL] Updating field_count in discovery_history and registered_apps for discovery_id: {activity_id}")
        try:
            # Update field_count in discovery_history
            field_count_result = db_service.execute_update("""
                UPDATE cids.discovery_history
                SET field_count = %s
                WHERE discovery_id = %s
            """, (fields_saved, activity_id))
            logger.info(f"[FINAL] Updated discovery_history field_count to {fields_saved} for discovery_id: {activity_id}")

            # Update field_count in registered_apps
            app_field_count_result = db_service.execute_update("""
                UPDATE cids.registered_apps
                SET field_count = %s
                WHERE client_id = %s
            """, (fields_saved, client_id))
            logger.info(f"[FINAL] Updated registered_apps field_count to {fields_saved} for client_id: {client_id}")

            # Insert completion record in activity_log with the same discovery_id
            activity_log_result = db_service.execute_update("""
                INSERT INTO cids.activity_log
                (activity_id, timestamp, activity_type, entity_type, entity_id, entity_name, user_email, details, status)
                VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s)
            """, (
                activity_id,  # Use the same dis_ ID
                'discovery.completed',
                'discovery',
                client_id,  # entity_id should be the client_id
                f"Discovery for {client_id}",  # entity_name
                user_email,
                json.dumps({
                    'discovery_id': activity_id,
                    'client_id': client_id,
                    'endpoints_saved': endpoints_saved,
                    'permissions_saved': permissions_saved,
                    'fields_saved': fields_saved,
                    'categories_created': categories_created,
                    'version': next_version
                }),
                'completed'
            ))
            logger.info(f"[FINAL] Logged discovery completion to activity_log with ID: {activity_id}")
        except Exception as e:
            logger.error(f"[FINAL] Failed to update field_count or activity_log: {e}")

        # Exit here after all steps
        return JSONResponse({
            "status": "discovery_completed",
            "message": f"Discovery completed - saved {endpoints_saved} endpoints, {permissions_saved} permissions, {fields_saved} field metadata, and {categories_created} category permissions (version {next_version})",
            "discovery_id": activity_id,  # Single ID for entire process
            "discovery_version": next_version,
            "endpoints_found": len(endpoints),
            "endpoints_saved": endpoints_saved,
            "permissions_generated": permissions_saved,
            "fields_metadata_saved": fields_saved,
            "field_count": fields_saved,  # Add field_count to response
            "category_permissions_created": categories_created
        })
        
    except Exception as e:
        logger.error(f"[STEP 2] Discovery failed: {e}")
        
        return JSONResponse({
            "status": "step_2_failed", 
            "message": f"Discovery step 2 failed: {str(e)}",
            "step1_discovery_id": activity_id
        })

@app.get("/discovery/v2/permissions/{client_id}/tree")
async def get_permission_tree(client_id: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    tree = enhanced_discovery.get_permission_tree(client_id)
    return JSONResponse({"app_id": client_id, "permission_tree": tree})

@app.get("/discovery/permissions/{client_id}/categories")
async def get_permissions_by_category(client_id: str, authorization: Optional[str] = Header(None)):
    """Get all discovered permissions grouped by categories (base, pii, phi, financial, sensitive, wildcard)"""
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conn = None
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 54322)),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Fetch all permissions with their categories and available fields
        cursor.execute("""
            SELECT 
                resource,
                action,
                category,
                permission_id,
                available_fields
            FROM cids.discovered_permissions
            WHERE client_id = %s AND is_active = true
            ORDER BY resource, action, 
                CASE category 
                    WHEN 'base' THEN 1
                    WHEN 'pii' THEN 2
                    WHEN 'phi' THEN 3
                    WHEN 'financial' THEN 4
                    WHEN 'sensitive' THEN 5
                    WHEN 'wildcard' THEN 6
                    ELSE 7
                END
        """, (client_id,))
        
        permissions = cursor.fetchall()
        
        # Convert to list of dicts with proper format
        result = []
        for perm in permissions:
            result.append({
                "resource": perm["resource"],
                "action": perm["action"],
                "category": perm["category"],
                "permission_id": perm["permission_id"],
                "available_fields": perm["available_fields"] or []
            })
        
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to fetch category permissions: {e}")
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=str(e))

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

    logger.info(f"=== RECEIVED CREATE ROLE REQUEST ===")
    logger.info(f"  client_id: {client_id}")
    logger.info(f"  role_name: {role_name}")
    logger.info(f"  description: {description}")
    logger.info(f"  description type: {type(description)}")
    logger.info(f"  a2a_only: {a2a_only}")
    logger.info(f"  permissions count: {len(permissions)}")
    
    denied_perms_set = set(denied_permissions) if denied_permissions else set()
    logger.info(f"Creating role {role_name} for {client_id} with {len(permissions)} allowed and {len(denied_perms_set)} denied permissions")
    logger.info(f"Description received: {description}")
    logger.info(f"a2a_only received: {a2a_only}")
    logger.info(f"Denied permissions received: {denied_permissions}")
    # Pasar user_email y user_id desde claims
    user_email = claims.get('email')
    user_id = claims.get('sub')
    valid_perms, valid_denied_perms = permission_registry.create_role_with_rls(
        client_id, role_name, set(permissions), description, rls_filters, denied_perms_set,
        user_email=user_email, user_id=user_id, a2a_only=bool(a2a_only)
    )
    # Persist a2a_only flag in metadata
    try:
        permission_registry.role_metadata.setdefault(client_id, {}).setdefault(role_name, {})['a2a_only'] = bool(a2a_only)
        # NO GUARDAR EN JSON
        # permission_registry._save_registry()
    except Exception:
        logger.exception("Failed to persist a2a_only metadata")
    # No need to log here - permission_registry already logs the activity
    return JSONResponse({"app_id": client_id, "role_name": role_name, "allowed_permissions": list(valid_perms), "denied_permissions": list(valid_denied_perms), "valid_count": len(valid_perms), "denied_count": len(valid_denied_perms), "invalid_count": len(permissions) - len(valid_perms), "rls_filters_saved": len(rls_filters) if rls_filters else 0, "metadata": permission_registry.get_role_metadata(client_id, role_name)})

@app.get("/permissions/{client_id}/roles/{role_name}")
async def get_role_permissions(client_id: str, role_name: str, authorization: Optional[str] = Header(None)):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    role_config = permission_registry.get_role_full_config(client_id, role_name)
    if not role_config['allowed_permissions'] and not role_config['denied_permissions'] and not role_config['rls_filters']:
        raise HTTPException(status_code=404, detail="Role not found")
    return JSONResponse({"app_id": client_id, "role_name": role_name, "allowed_permissions": role_config['allowed_permissions'], "denied_permissions": role_config['denied_permissions'], "rls_filters": role_config['rls_filters'], "metadata": role_config['metadata'], "count": len(role_config['allowed_permissions']), "denied_count": len(role_config['denied_permissions'])})

@app.post("/auth/admin/refresh-cache")
async def refresh_cache(authorization: Optional[str] = Header(None)):
    """Refresh the permission registry cache from database"""
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Reload permission registry from database
        permission_registry._load_registry()
        logger.info("Cache refreshed successfully")
        return JSONResponse({"status": "success", "message": "Cache refreshed from database"})
    except Exception as e:
        logger.error(f"Failed to refresh cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh cache: {str(e)}")

@app.post("/auth/admin/log-app-usage")
async def log_app_usage(
    request: Request,
    body: dict = Body(...),
    authorization: Optional[str] = Header(None)
):
    """Log application usage activity for tracking"""
    is_admin, user_info = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        app_name = body.get('app_name', '')
        client_id = body.get('client_id', '')
        action = body.get('action', f'flw.{app_name.lower()}')
        
        # Get user info from token
        user_email = user_info.get('email', 'unknown') if user_info else 'unknown'
        user_id = user_info.get('sub', 'unknown') if user_info else 'unknown'
        user_name = user_info.get('name', user_email) if user_info else user_email
        
        # Generate activity_id with 'flw' prefix from UUID service
        activity_id = None
        try:
            import httpx
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    "http://uuid-service-dev:8002/generate",
                    json={"prefix": "flw"}
                )
                if response.status_code == 200:
                    activity_id = response.json()["id"]
                    logger.info(f"Generated activity ID from UUID service: {activity_id}")
                else:
                    logger.warning(f"Failed to get UUID from service: {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not get UUID from service: {e}, using fallback")
        
        # Fallback if UUID service fails
        if not activity_id:
            activity_id = f"flw_{uuid.uuid4().hex[:16]}"
            logger.warning(f"UUID service unavailable, using fallback activity_id: {activity_id}")
        
        # Log app usage activity
        success = db_service.log_activity(
            activity_id=activity_id,
            activity_type=action,
            entity_type='application',
            entity_id=client_id,
            entity_name=app_name,
            user_email=user_email,
            user_id=user_id,
            details={
                'application': app_name,
                'client_id': client_id,
                'action': action,
                'source': 'dashboard_access'
            },
            api_endpoint=request.url.path,
            http_method=request.method
        )
        
        if success:
            return JSONResponse({"status": "success", "message": "App usage logged"})
        else:
            raise HTTPException(status_code=500, detail="Failed to log app usage")
            
    except Exception as e:
        logger.error(f"Failed to log app usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log app usage: {str(e)}")

@app.get("/permissions/{client_id}/roles")
async def list_roles(client_id: str, authorization: Optional[str] = Header(None), use_cache: bool = True):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Option to force database read instead of cache
    if not use_cache:
        try:
            # Query database directly
            roles_data = db_service.execute_query("""
                SELECT role_name, description, a2a_only, is_active, created_at
                FROM cids.role_metadata
                WHERE client_id = %s
                ORDER BY role_name
            """, (client_id,))
            
            roles_with_metadata = {}
            if roles_data:
                for role in roles_data:
                    # Get permissions for this role (stored as JSONB)
                    perms_data = db_service.execute_query("""
                        SELECT permissions
                        FROM cids.role_permissions
                        WHERE client_id = %s AND role_name = %s
                    """, (client_id, role['role_name']))
                    
                    permissions = []
                    if perms_data and perms_data[0].get('permissions'):
                        # Los permisos ya vienen como lista en JSONB
                        permissions = perms_data[0]['permissions'] if isinstance(perms_data[0]['permissions'], list) else []
                    
                    roles_with_metadata[role['role_name']] = {
                        "permissions": permissions,
                        "metadata": {
                            "description": role['description'],
                            "a2a_only": role['a2a_only'],
                            "is_active": role['is_active'],
                            "created_at": role['created_at'].isoformat() if role['created_at'] else None
                        }
                    }
            
            logger.info(f"Returning roles for {client_id} from DATABASE")
            return JSONResponse({"app_id": client_id, "roles": roles_with_metadata, "count": len(roles_with_metadata)})
            
        except Exception as e:
            logger.error(f"Failed to query database directly: {e}")
            # Fall back to cache
    
    # Use cache (default behavior)
    app_roles = permission_registry.role_permissions.get(client_id, {})
    app_metadata = permission_registry.role_metadata.get(client_id, {})
    roles_with_metadata = {}
    
    # Include ALL roles regardless of is_active status
    for role_name, perms in app_roles.items():
        meta = app_metadata.get(role_name, {})
        roles_with_metadata[role_name] = {"permissions": list(perms), "metadata": meta}
    
    # Include roles that exist only in metadata (e.g., A2A-only roles with no permissions yet)
    for role_name, meta in app_metadata.items():
        if role_name not in roles_with_metadata:
            roles_with_metadata[role_name] = {"permissions": [], "metadata": meta}
    
    # Log for debugging
    logger.info(f"Returning roles for {client_id} from CACHE: {json.dumps({k: {'metadata': v.get('metadata')} for k, v in roles_with_metadata.items()})}")
    
    return JSONResponse({"app_id": client_id, "roles": roles_with_metadata, "count": len(roles_with_metadata)})

@app.put("/permissions/{client_id}/roles/{role_name}")
async def update_permission_role(client_id: str, role_name: str, authorization: Optional[str] = Header(None), permissions: Optional[List[str]] = Body(None), description: Optional[str] = Body(None), rls_filters: Optional[Dict[str, List[Dict[str, str]]]] = Body(None), a2a_only: Optional[bool] = Body(None), denied_permissions: Optional[List[str]] = Body(None), is_active: Optional[bool] = Body(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    logger.info(f"=== UPDATE ROLE PERMISSIONS REQUEST ===")
    logger.info(f"Update role request for {role_name} in {client_id}, is_active={is_active}")
    logger.info(f"Received permissions: {permissions}")
    logger.info(f"Permissions type: {type(permissions)}")
    logger.info(f"Permissions count: {len(permissions) if permissions else 0}")
    logger.info(f"Received denied_permissions: {denied_permissions}")
    logger.info(f"Received description: {description}")
    logger.info(f"Received rls_filters: {rls_filters}")
    
    # For now, assume role exists if we're just updating is_active
    # This matches the behavior when delete was working
    role_exists = True

    denied_perms_set = set(denied_permissions) if denied_permissions else set()
    logger.info(f"Updating role {role_name} for {client_id}")
    
    # Update permissions if provided
    valid_perms = set()
    valid_denied_perms = set()
    
    if permissions is not None:
        user_email = claims.get('email')
        user_id = claims.get('sub')
        valid_perms, valid_denied_perms = permission_registry.update_role_with_rls(
            client_id, role_name, set(permissions), description, rls_filters, denied_perms_set,
            user_email=user_email, user_id=user_id
        )
    # Optionally update a2a_only flag
    if a2a_only is not None:
        try:
            permission_registry.role_metadata.setdefault(client_id, {}).setdefault(role_name, {})['a2a_only'] = bool(a2a_only)
            # NO GUARDAR EN JSON
            # permission_registry._save_registry()
        except Exception:
            logger.exception("Failed to update a2a_only metadata")
    
    # Handle is_active status change
    if is_active is not None:
        try:
            logger.info(f"Updating is_active status for role {role_name} to {is_active}")
            
            # Use global database connection
            db = db_service
            
            # Get current status
            current_status = True
            if db.cursor:
                db.cursor.execute("""
                    SELECT is_active FROM cids.role_metadata 
                    WHERE client_id = %s AND role_name = %s
                """, (client_id, role_name))
                result = db.cursor.fetchone()
                if result:
                    current_status = result['is_active']
            
            # Update status in database
            if db.cursor:
                # First check if role exists
                db.cursor.execute("""
                    SELECT 1 FROM cids.role_metadata 
                    WHERE client_id = %s AND role_name = %s
                """, (client_id, role_name))
                
                if db.cursor.fetchone():
                    # Role exists, update it
                    logger.info(f"Role exists in DB, executing UPDATE for {role_name}")
                    db.cursor.execute("""
                        UPDATE cids.role_metadata 
                        SET is_active = %s, updated_at = NOW()
                        WHERE client_id = %s AND role_name = %s
                    """, (is_active, client_id, role_name))
                    logger.info(f"UPDATE executed, rows affected: {db.cursor.rowcount}")
                else:
                    # Role doesn't exist in DB - this shouldn't happen for deactivate
                    # Just log a warning and skip
                    logger.warning(f"Attempted to update is_active for non-existent role {role_name} in {client_id}")
                    return JSONResponse({"error": f"Role {role_name} not found"}, status_code=404)
                
                # Log the status change in activity log
                action_type = 'role.activate' if is_active else 'role.deactivate'
                db.cursor.execute("""
                    INSERT INTO cids.activity_log (activity_type, entity_type, entity_id, entity_name, user_email, user_id, details, status, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    action_type,
                    'role',
                    client_id,
                    role_name,
                    claims.get('email', 'unknown'),
                    claims.get('sub', claims.get('oid', 'unknown')),
                    Json({
                        'client_id': client_id,
                        'role_name': role_name,
                        'previous_status': 'active' if current_status else 'inactive',
                        'new_status': 'active' if is_active else 'inactive',
                        'changed_by': claims.get('email', 'unknown')
                    }),
                    'success'
                ))
                
                db.conn.commit()
                logger.info(f"Successfully updated role {role_name} is_active to {is_active}")
                
            # Reload role metadata from database to ensure consistency
            db.cursor.execute("""
                SELECT description, a2a_only, is_active, created_at 
                FROM cids.role_metadata 
                WHERE client_id = %s AND role_name = %s
            """, (client_id, role_name))
            
            updated_role = db.cursor.fetchone()
            if updated_role:
                if client_id not in permission_registry.role_metadata:
                    permission_registry.role_metadata[client_id] = {}
                permission_registry.role_metadata[client_id][role_name] = {
                    'description': updated_role['description'],
                    'a2a_only': updated_role['a2a_only'],
                    'is_active': updated_role['is_active'],
                    'created_at': updated_role['created_at'].isoformat() if updated_role['created_at'] else None
                }
                logger.info(f"Reloaded role metadata from DB: is_active={updated_role['is_active']}")
                
            # Log separate audit for status change
            # Note: We're already logging this in the database directly above, 
            # so we don't need to use audit_logger here to avoid duplicates
        except Exception as e:
            logger.exception(f"Failed to update is_active status: {e}")
    
    # Log general update only if permissions were updated
    if permissions is not None:
        audit_logger.log_action(
            action=AuditAction.ROLE_UPDATED, 
            user_email=claims.get('email'),
            user_id=claims.get('sub', claims.get('oid')),
            resource_type='role',
            resource_id=f"{client_id}:{role_name}",
            details={
                'app_client_id': client_id, 
                'role_name': role_name, 
                'permissions_count': len(valid_perms), 
                'denied_permissions_count': len(valid_denied_perms), 
                'rls_filters_count': len(rls_filters) if rls_filters else 0, 
                'updated_by': claims.get('email'), 
                'a2a_only': a2a_only, 
                'is_active': is_active
            }
        )
    return JSONResponse({"app_id": client_id, "role_name": role_name, "allowed_permissions": list(valid_perms), "denied_permissions": list(valid_denied_perms), "valid_count": len(valid_perms), "denied_count": len(valid_denied_perms), "invalid_count": (len(permissions) - len(valid_perms)) if permissions else 0, "rls_filters_saved": len(rls_filters) if rls_filters else 0, "metadata": permission_registry.get_role_metadata(client_id, role_name)})

@app.delete("/permissions/{client_id}/roles/{role_name}")
async def delete_role(client_id: str, role_name: str, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if role exists in metadata (which includes all roles from DB)
    role_exists = False
    if client_id in permission_registry.role_metadata and role_name in permission_registry.role_metadata[client_id]:
        role_exists = True
    elif client_id in permission_registry.role_permissions and role_name in permission_registry.role_permissions[client_id]:
        role_exists = True
    
    if not role_exists:
        # Try to check directly in database
        from services.database import DatabaseService
        db = DatabaseService()
        if db.cursor:
            db.cursor.execute("""
                SELECT 1 FROM cids.role_metadata 
                WHERE client_id = %s AND role_name = %s
            """, (client_id, role_name))
            if db.cursor.fetchone():
                role_exists = True
    
    if not role_exists:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Use the new delete_role method that handles database deletion
    user_email = claims.get('email', 'unknown')
    user_id = claims.get('sub', claims.get('oid', 'unknown'))
    permission_registry.delete_role(client_id, role_name, user_email, user_id)
    audit_logger.log_action(action=AuditAction.ROLE_DELETED, details={'app_client_id': client_id, 'role_name': role_name, 'deleted_by': user_email, 'user_id': user_id})
    return JSONResponse({"status": "success", "message": f"Role '{role_name}' deleted successfully"})

# ==============================
# Admin: RLS Filters Management
# ==============================

@app.get("/auth/admin/rls-filters/{client_id}/{role_name}")
async def get_rls_filters(client_id: str, role_name: str, authorization: Optional[str] = Header(None)):
    """Get active RLS filters for a role from database"""
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        # Create fresh database connection with RealDictCursor
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # Get connection parameters
        db_host = os.getenv('DB_HOST')
        if db_host:
            connection_params = {
                'host': db_host,
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'postgres'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'postgres')
            }
        else:
            connection_params = {
                'host': 'localhost',
                'port': '54322',
                'database': 'postgres',
                'user': 'postgres',
                'password': 'postgres'
            }

        # Create connection with RealDictCursor for dict-like row access
        conn = psycopg2.connect(**connection_params)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get active RLS filters from database
        cursor.execute("""
            SELECT rls_id, resource, field_name, filter_condition,
                   description, filter_operator, priority, metadata,
                   created_at, updated_at
            FROM cids.rls_filters
            WHERE client_id = %s AND role_name = %s AND is_active = true
            ORDER BY priority, created_at
        """, (client_id, role_name))

        filters = []
        results = cursor.fetchall()

        for row in results:
            filters.append({
                'rls_id': row['rls_id'],
                'resource': row['resource'],
                'field_name': row['field_name'],
                'filter_condition': row['filter_condition'],
                'description': row['description'],
                'filter_operator': row['filter_operator'],
                'priority': row['priority'],
                'metadata': row['metadata'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
            })

        # Close the connection
        cursor.close()
        conn.close()

        logger.info(f"Fetched {len(filters)} RLS filters for {client_id}/{role_name}")

        return JSONResponse({
            'client_id': client_id,
            'role_name': role_name,
            'filters': filters,
            'count': len(filters)
        })
    except Exception as e:
        logger.error(f"Error fetching RLS filters: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/admin/rls-filters/{client_id}/{role_name}")
async def save_rls_filter(
    client_id: str,
    role_name: str,
    resource: str = Body(...),
    field_name: str = Body(...),
    filter_condition: str = Body(...),
    description: Optional[str] = Body(None),
    filter_operator: Optional[str] = Body("AND"),
    priority: Optional[int] = Body(0),
    metadata: Optional[dict] = Body(None),
    authorization: Optional[str] = Header(None)
):
    """Save new RLS filter and deactivate previous versions"""
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    user_email = claims.get('email', 'unknown')
    user_id = claims.get('sub', claims.get('oid', 'unknown'))

    try:
        # Create fresh database connection for transaction
        from services.database import DatabaseService
        db = DatabaseService()
        db.connect()

        # Start transaction
        db.conn.autocommit = False

        try:
            # 1. Deactivate ALL existing active filters for same resource
            # (regardless of field_name to ensure proper versioning)
            db.cursor.execute("""
                UPDATE cids.rls_filters
                SET is_active = false,
                    updated_at = NOW(),
                    updated_by = %s
                WHERE client_id = %s
                  AND role_name = %s
                  AND resource = %s
                  AND is_active = true
            """, (user_email, client_id, role_name, resource))

            deactivated_count = db.cursor.rowcount
            logger.info(f"Deactivated {deactivated_count} existing RLS filters")

            # 2. Insert new active filter
            rls_id = f"rls_{uuid.uuid4().hex[:20]}"

            db.cursor.execute("""
                INSERT INTO cids.rls_filters (
                    rls_id, client_id, role_name, resource, field_name,
                    filter_condition, is_active, description, filter_operator,
                    priority, metadata, created_by, updated_by
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, true, %s, %s,
                    %s, %s, %s, %s
                )
            """, (
                rls_id, client_id, role_name, resource, field_name,
                filter_condition, description, filter_operator,
                priority, json.dumps(metadata) if metadata else '{}',
                user_email, user_email
            ))

            logger.info(f"Created new RLS filter with ID: {rls_id}")

            # 3. Log activity
            db.cursor.execute("""
                INSERT INTO cids.activity_log (
                    activity_type, entity_type, entity_id, entity_name,
                    user_email, user_id, details, status
                ) VALUES (
                    'rls.filter.created', 'rls_filter', %s, %s,
                    %s, %s, %s, 'success'
                )
            """, (
                rls_id, f"{role_name}/{resource}/{field_name}",
                user_email, user_id,
                json.dumps({
                    'client_id': client_id,
                    'role_name': role_name,
                    'resource': resource,
                    'field_name': field_name,
                    'filter_condition': filter_condition,
                    'deactivated_count': deactivated_count
                })
            ))

            # Commit transaction
            db.conn.commit()
            logger.info("RLS filter saved and committed successfully")

            return JSONResponse({
                'status': 'success',
                'rls_id': rls_id,
                'deactivated_count': deactivated_count,
                'message': f'RLS filter created successfully. {deactivated_count} previous filters deactivated.'
            })

        except Exception as e:
            # Rollback on error
            db.conn.rollback()
            logger.error(f"Error saving RLS filter, rolling back: {e}")
            raise
        finally:
            # Restore autocommit and close connection
            db.conn.autocommit = True
            db.disconnect()

    except Exception as e:
        logger.error(f"Error saving RLS filter: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/auth/admin/rls-filters/{rls_id}")
async def delete_rls_filter(rls_id: str, authorization: Optional[str] = Header(None)):
    """Delete (deactivate) an RLS filter"""
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    user_email = claims.get('email', 'unknown')

    try:
        db = db_service
        if not db.cursor:
            db.connect()

        # Deactivate the filter
        db.cursor.execute("""
            UPDATE cids.rls_filters
            SET is_active = false,
                updated_at = NOW(),
                updated_by = %s
            WHERE rls_id = %s
        """, (user_email, rls_id))

        if db.cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="RLS filter not found")

        logger.info(f"Deactivated RLS filter: {rls_id}")

        return JSONResponse({
            'status': 'success',
            'message': 'RLS filter deactivated successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting RLS filter: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    from services.audit import audit_logger, AuditAction
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


@app.get("/auth/admin/logs/activity-count")
async def get_activity_log_count(
    user_email: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """Get total count of activity logs, optionally filtered by user email"""
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        # Connect directly to database
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '54322'),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cur = conn.cursor()

        # Count records in activity_log table where entity_name is not null
        if user_email:
            cur.execute(
                "SELECT COUNT(*) FROM cids.activity_log WHERE user_email = %s AND entity_name IS NOT NULL",
                (user_email,)
            )
        else:
            cur.execute("SELECT COUNT(*) FROM cids.activity_log WHERE entity_name IS NOT NULL")

        count = cur.fetchone()[0]

        cur.close()
        conn.close()

        return {"count": count}

    except Exception as e:
        logger.error(f"Failed to get activity log count: {e}")
        return {"count": 0}


@app.get("/auth/admin/logs/activity-stats")
async def get_activity_stats(authorization: Optional[str] = Header(None)):
    """Get activity statistics from activity_log table for the last 6 months"""
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Connect directly to database
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cursor = conn.cursor()
        
        # Query activity_log table for stats from last 6 months
        query = """
            SELECT activity_type, COUNT(*) as count 
            FROM cids.activity_log 
            WHERE entity_name IS NOT NULL 
              AND timestamp >= NOW() - INTERVAL '6 months'
            GROUP BY activity_type 
            ORDER BY count DESC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Format results for frontend
        stats = []
        if results:
            for row in results:
                stats.append({
                    "type": row[0],
                    "count": int(row[1])
                })
        
        logger.info(f"Activity stats retrieved: {len(stats)} types found")
        return JSONResponse({"items": stats, "count": len(stats)})
    except Exception as e:
        logger.error(f"Failed to get activity stats: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse({"items": [], "count": 0})

@app.get("/auth/admin/logs/token-activity")
async def get_token_activity_logs(authorization: Optional[str] = Header(None), start: Optional[str] = None, end: Optional[str] = None, action: Optional[str] = None, user_email: Optional[str] = None, token_id: Optional[str] = None, limit: int = 100):
    is_admin, _ = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    # Read persisted JSONL files
    from pathlib import Path
    from libs.logging_config import get_logging_config
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
    from services.audit import audit_logger
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
    from libs.logging_config import get_logging_config

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
    from libs.logging_config import get_logging_config

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
    from libs.logging_config import get_logging_config

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
    # Check if app exists in database
    db_app = db_service.get_registered_app(client_id)
    if not db_app:
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
    jwt_manager.template_manager.save_template(template, claims.get('email'))
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

    # Get discovery_id from activity_log
    import psycopg2
    import psycopg2.extras

    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 54322)),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get the latest discovery_id from discovery_history (not activity_log)
        cur.execute("""
            SELECT discovery_id,
                   endpoints_count,
                   discovery_timestamp as last_discovery_at
            FROM cids.discovery_history
            WHERE client_id = %s
            ORDER BY discovery_version DESC
            LIMIT 1
        """, (client_id,))

        discovery_info = cur.fetchone()

        if not discovery_info or not discovery_info.get('discovery_id'):
            conn.close()
            return JSONResponse({
                "endpoints": [],
                "total": 0,
                "last_discovery_at": None,
                "message": "No discovery data found for this app"
            })

        discovery_id = discovery_info['discovery_id']

        # Get endpoints from discovery_endpoints table
        cur.execute("""
            SELECT method, path, resource, action, description,
                   operation_id, parameters, response_fields
            FROM cids.discovery_endpoints
            WHERE discovery_id = %s
            ORDER BY path, method
        """, (discovery_id,))

        endpoints = cur.fetchall()

        # Get generated permissions
        cur.execute("""
            SELECT DISTINCT resource || '.' || action ||
                   CASE
                       WHEN field_name IS NOT NULL AND field_name != ''
                       THEN '.' || field_name
                       ELSE ''
                   END as permission
            FROM cids.discovered_permissions
            WHERE client_id = %s
            ORDER BY permission
        """, (client_id,))

        permissions = [row['permission'] for row in cur.fetchall()]

        conn.close()

        return JSONResponse({
            "endpoints": endpoints,
            "total": len(endpoints),
            "last_discovery_at": discovery_info['last_discovery_at'].isoformat() if discovery_info['last_discovery_at'] else None,
            "permissions_generated": permissions
        })

    except Exception as e:
        logger.error(f"Error getting app endpoints: {str(e)}")
        if 'conn' in locals():
            conn.close()
        raise HTTPException(status_code=500, detail=f"Error retrieving endpoints: {str(e)}")

@app.put("/auth/admin/apps/{client_id}/endpoints")
async def update_app_endpoints_admin(client_id: str, update: EndpointsUpdate, authorization: Optional[str] = Header(None)):
    is_admin, claims = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    # Check if app exists in database
    db_app = db_service.get_registered_app(client_id)
    if not db_app:
        raise HTTPException(status_code=404, detail="App not found")
    result = endpoints_registry.upsert_endpoints(app_client_id=client_id, endpoints=[e.dict() for e in update.endpoints], updated_by=claims.get('email', 'admin'))
    return JSONResponse({"message": "Endpoints updated", **result})


# ===========================
# Employee Photo Endpoints
# ===========================

@app.get("/api/user/photo/{email}")
async def get_user_photo(email: str, authorization: Optional[str] = Header(None)):
    """Get user photo path from database"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 54322)),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cur = conn.cursor()
        
        # Check if photo exists for email
        cur.execute("""
            SELECT photo_path FROM cids.photo_emp 
            WHERE email = %s
        """, (email,))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return JSONResponse({"photo_path": result[0], "has_photo": True})
        else:
            return JSONResponse({"photo_path": None, "has_photo": False})
            
    except Exception as e:
        logger.error(f"Error fetching user photo: {e}")
        return JSONResponse({"photo_path": None, "has_photo": False})


@app.get("/photos/{filename}")
async def serve_photo(filename: str):
    """Serve photo files from the photos directory"""
    import os
    from fastapi.responses import FileResponse
    
    # Sanitize filename to prevent directory traversal
    safe_filename = os.path.basename(filename)
    # Use path relative to backend directory (works in container and local)
    photo_path = os.path.join(os.path.dirname(__file__), "..", "static", "photos", safe_filename)
    photo_path = os.path.abspath(photo_path)
    
    if os.path.exists(photo_path):
        return FileResponse(photo_path, media_type="image/jpeg")
    else:
        raise HTTPException(status_code=404, detail="Photo not found")

# ===========================
# Documentation Endpoints
# ===========================

@app.get("/docs/{doc_name}")
async def get_documentation(doc_name: str):
    """Serve documentation markdown files"""
    # Security: Only allow specific markdown files
    allowed_docs = [
        "CIDS_MANDATORY_SPECIFICATION.md",
        "CIDS_INTEGRATION_GUIDE.md",
        "CID_MIGRATION_REPORT_ES.md",
        "CID_MIGRATION_REPORT_EN.md",
        "PRESENTACION_CAMBIOS.md",
        "CIDS_SECURITY_INTEGRATION_GUIDELINES_v4.md",
        "CIDS_SECURITY_INTEGRATION_GUIDELINES_v3.md",
        "CIDS_SECURITY_INTEGRATION_GUIDELINES.md",
        "SECURITY_COMPLIANCE.md",
        "HYBRID_PERMISSIONS_SYSTEM.md",
        "CLAUDE.md",
        "CHANGES_20250911.md",
        "CAMBIOS_IMPLEMENTADOS_20250910.md",
        "DISCOVERY_FLOW_DOCUMENTATION_ES.md",
        "CID_Visual_Standards_Document.md",
        "MIGRATION_REPORT.md",
        "MIGRATION_NOTES.md",
        "MIGRATION_ISSUES.md",
        "FIX_NOTES_2025-09-08.md",
        "BACKUP_STATUS_20250908.md",
        "BACKUP_SUMMARY_2025-09-09.md",
        "BACKUP_20250910_1533.md",
        "BACKUP_20250911_0800.md",
        "STATUS_20250909_4PM.MD",
        "DISCOVERY_RESUMEN.MD",
        "ARCHITECTURE.md",
        "README.md",
        "TEST-INSTRUCTIONS.md",
        "RESUMEN-USO-LLM.md",
        "README-LLM-APP-CREATION.md",
        "design-proposals.md",
        "arquitectura-comparacion.md"
    ]

    if doc_name not in allowed_docs:
        raise HTTPException(status_code=404, detail="Document not found")

    # Try different paths (updated for Docker container)
    paths_to_try = [
        f"/app/documentation/{doc_name}",  # Main documentation path in Docker
        f"/app/{doc_name}",  # Fallback to app root
        f"/home/dpi/projects/CID/{doc_name}",  # For local development
        f"./{doc_name}"  # Current directory
    ]

    for path in paths_to_try:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return PlainTextResponse(content, media_type="text/markdown")
            except Exception as e:
                logger.error(f"Error reading documentation file {doc_name}: {str(e)}")
                raise HTTPException(status_code=500, detail="Error reading documentation")

    raise HTTPException(status_code=404, detail="Document file not found")

# Initialize A2A endpoints on startup
@app.on_event("startup")
async def startup_event():
    """Initialize A2A endpoints and other startup tasks"""
    await setup_a2a_endpoints(app, db_service, jwt_manager, check_admin_access)
    logger.info("A2A endpoints initialized")

