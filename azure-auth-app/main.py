from fastapi import FastAPI, Request, HTTPException, Response, Header
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from authlib.jose import jwt
import os
import httpx
from dotenv import load_dotenv
from datetime import datetime, timedelta
import secrets
import logging
from typing import Dict, Optional, List
import uuid
import json
import urllib.parse
from jwt_utils import JWTManager
from refresh_token_store import refresh_token_store
from pydantic import BaseModel
from token_activity_logger import token_activity_logger, TokenAction
from app_registration import (
    app_store, RegisterAppRequest, UpdateAppRequest, 
    AppResponse, AppRegistrationResponse, SetRoleMappingRequest,
    registered_apps, app_role_mappings
)
from jwks_handler import JWKSHandler
from app_endpoints import AppEndpointsRegistry, EndpointsUpdate
from roles_manager import RolesManager, RolesUpdate, RoleMappingsUpdate
from policy_manager import PolicyManager, PolicyDocument
from audit_logger import audit_logger, AuditAction

load_dotenv()

# Request models
class TokenRequest(BaseModel):
    grant_type: str
    refresh_token: Optional[str] = None
    
class RevokeTokenRequest(BaseModel):
    token: str
    token_type_hint: Optional[str] = "refresh_token"

app = FastAPI(title="Centralized Auth Service")
templates = Jinja2Templates(directory="templates")

# Add custom Jinja2 filter for datetime conversion
def datetime_filter(timestamp):
    """Convert Unix timestamp to readable datetime"""
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return "Invalid timestamp"

templates.env.filters['datetime'] = datetime_filter

# Configure logging at module level with DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# In-memory session storage (will be replaced with Redis in production)
sessions: Dict[str, dict] = {}

# In-memory token storage for admin tracking (will be replaced with Redis/DB in production)
issued_tokens: Dict[str, dict] = {}

# In-memory Azure token storage for admin tracking (will be replaced with Redis/DB in production)
azure_tokens: Dict[str, dict] = {}

# Initialize JWT manager (in production, specify key_path for persistent storage)
jwt_manager = JWTManager(key_path="./keys" if os.getenv("PERSIST_KEYS", "false").lower() == "true" else None)

# Initialize IAM components
jwks_handler = JWKSHandler(jwt_manager)
endpoints_registry = AppEndpointsRegistry()
roles_manager = RolesManager()
policy_manager = PolicyManager()

def get_session(session_id: str) -> dict:
    return sessions.get(session_id, {})

def set_session(session_id: str, data: dict):
    sessions[session_id] = data

def check_admin_access(authorization: Optional[str] = None) -> tuple[bool, Optional[dict]]:
    """Check if the provided token has admin access"""
    logger.debug(f"=== check_admin_access called ===")
    logger.debug(f"Authorization parameter: {authorization[:50] + '...' if authorization and len(authorization) > 50 else authorization}")
    
    if not authorization or not authorization.startswith('Bearer '):
        logger.debug(f"No authorization header or invalid format. Header: '{authorization}'")
        return False, None
    
    token = authorization.replace('Bearer ', '')
    logger.debug(f"Extracted token: {token[:20] + '...' if len(token) > 20 else token}")
    
    is_valid, claims, error = jwt_manager.validate_token(token)
    logger.debug(f"JWT validation result: is_valid={is_valid}, error={error}")
    
    if not is_valid:
        logger.debug(f"Invalid token: {error}")
        return False, None
    
    # Check if token has been revoked
    for token_id, token_data in issued_tokens.items():
        if token_data['access_token'] == token and token_data.get('revoked', False):
            logger.debug(f"Token has been revoked")
            return False, None
    
    # Check for admin group or email
    admin_emails_raw = os.getenv('ADMIN_EMAILS', 'admin@example.com').split(',')
    # Trim whitespace and convert to lowercase for case-insensitive comparison
    admin_emails = [email.strip().lower() for email in admin_emails_raw if email.strip()]
    
    admin_group_ids_raw = os.getenv('ADMIN_GROUP_IDS', '').split(',')
    admin_group_ids = [group_id.strip() for group_id in admin_group_ids_raw if group_id.strip()]
    
    user_email = claims.get('email', '').strip().lower()
    user_groups = claims.get('groups', [])
    
    logger.info(f"Admin access check - User email: '{user_email}'")
    logger.info(f"Admin access check - Admin emails: {admin_emails}")
    logger.info(f"Admin access check - User groups: {[g.get('id') if isinstance(g, dict) else str(g) for g in user_groups]}")
    logger.info(f"Admin access check - Admin group IDs: {admin_group_ids}")
    
    # Check if user is admin by email
    if user_email in admin_emails:
        logger.info(f"User '{user_email}' has admin access via email")
        return True, claims
    
    # Check if user is in admin group
    for group in user_groups:
        if isinstance(group, dict) and group.get('id') in admin_group_ids:
            logger.info(f"User '{user_email}' has admin access via group {group.get('id')}")
            return True, claims
    
    logger.info(f"User '{user_email}' does NOT have admin access")
    return False, claims

async def get_azure_signing_keys():
    """Fetch the signing keys from Azure AD"""
    discovery_url = os.getenv('AZURE_DISCOVERY_URL').replace('{tenant_id}', os.getenv('AZURE_TENANT_ID'))
    async with httpx.AsyncClient() as client:
        discovery_response = await client.get(discovery_url)
        discovery_data = discovery_response.json()
        jwks_uri = discovery_data['jwks_uri']
        
        jwks_response = await client.get(jwks_uri)
        return jwks_response.json()


@app.get("/auth/login")
async def auth_login(request: Request, response: Response, return_url: Optional[str] = None, client_id: Optional[str] = None, app_redirect_uri: Optional[str] = None, state: Optional[str] = None):
    """Initiate Azure AD OAuth flow"""
    # Azure redirect URI - NEVER change this, it's configured in Azure AD
    azure_redirect_uri = os.getenv('REDIRECT_URI', 'https://10.1.5.58:8000/auth/callback')
    
    # Create session
    session_id = str(uuid.uuid4())
    oauth_state = state or secrets.token_urlsafe(32)
    
    # Validate client_id and app_redirect_uri if provided (for app-specific flows)
    if client_id:
        app_data = app_store.get_app(client_id)
        if not app_data:
            raise HTTPException(status_code=400, detail="Invalid client_id")
        if not app_data.get('is_active'):
            raise HTTPException(status_code=400, detail="Application is not active")
        
        # Validate app_redirect_uri if provided
        if app_redirect_uri:
            if not app_store.validate_redirect_uri(client_id, app_redirect_uri):
                raise HTTPException(status_code=400, detail="Invalid redirect_uri for this client")
        
        # Store app-specific data in session
        session_data = {
            'oauth_state': oauth_state,
            'return_url': return_url or '/',
            'client_id': client_id,
            'app_redirect_uri': app_redirect_uri,  # Where to redirect AFTER auth
            'app_state': state  # App's state parameter for CSRF
        }
    else:
        # Standard flow without app registration
        session_data = {
            'oauth_state': oauth_state,
            'return_url': return_url or '/'
        }
    
    set_session(session_id, session_data)
    
    # Construct authorization URL - ALWAYS use Azure redirect URI
    authorize_url = (
        f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}/oauth2/v2.0/authorize"
        f"?client_id={os.getenv('AZURE_CLIENT_ID')}"
        f"&response_type=code"
        f"&redirect_uri={azure_redirect_uri}"
        f"&scope={os.getenv('AZURE_SCOPE', 'openid profile email groups')}"
        f"&state={oauth_state}"
        f"&nonce={secrets.token_urlsafe(16)}"
    )
    
    # Set session cookie
    response = RedirectResponse(url=authorize_url)
    response.set_cookie(key="auth_session_id", value=session_id, httponly=True, samesite="lax", secure=True)
    return response

@app.get("/auth/callback")
async def auth_callback(request: Request, response: Response):
    """Handle Azure AD callback and issue internal token"""
    try:
        # Get session
        session_id = request.cookies.get('auth_session_id')
        if not session_id:
            raise HTTPException(status_code=400, detail="No session found")
        
        session_data = get_session(session_id)
        
        # Get code and state from query params
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        
        # Verify state
        stored_state = session_data.get('oauth_state')
        if not stored_state or stored_state != state:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Exchange code for token
        redirect_uri = os.getenv('REDIRECT_URI', 'https://10.1.5.58:8000/auth/callback')
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}/oauth2/v2.0/token",
                data={
                    'client_id': os.getenv('AZURE_CLIENT_ID'),
                    'client_secret': os.getenv('AZURE_CLIENT_SECRET'),
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code'
                }
            )
            
            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Token exchange failed: {token_response.text}")
            
            token_data = token_response.json()
        
        id_token_data = token_data.get('id_token')
        access_token = token_data.get('access_token')
        
        # Get signing keys and validate token
        jwks = await get_azure_signing_keys()
        
        # Decode and validate ID token
        claims = jwt.decode(
            id_token_data,
            jwks,
            claims_options={
                "aud": {"essential": True, "value": os.getenv('AZURE_CLIENT_ID')},
                "iss": {"essential": True, "value": f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}/v2.0"}
            }
        )
        
        # Extract user information
        user_info = {
            'name': claims.get('name', 'Unknown'),
            'email': claims.get('email', claims.get('preferred_username', 'Unknown')),
            'sub': claims.get('sub'),
            'groups': []
        }
        
        # Store Azure tokens for admin tracking
        azure_token_id = str(uuid.uuid4())
        azure_issued_at = datetime.utcnow()
        
        # Extract Azure token expiry from claims
        azure_expires_at = datetime.fromtimestamp(claims.get('exp', 0))
        
        logger.info(f"Storing Azure tokens for user: {user_info['email']}")
        
        azure_token_info = {
            'id': azure_token_id,
            'id_token': id_token_data,
            'access_token': access_token,
            'user': {
                'name': user_info['name'],
                'email': user_info['email']
            },
            'issued_at': azure_issued_at.isoformat() + 'Z',
            'expires_at': azure_expires_at.isoformat() + 'Z',
            'subject': user_info['sub'],
            'issuer': claims.get('iss', 'Unknown'),
            'audience': claims.get('aud', 'Unknown'),
            'claims': claims
        }
        
        # Store Azure token
        azure_tokens[azure_token_id] = azure_token_info
        logger.info(f"Azure token stored successfully. Current azure_tokens count: {len(azure_tokens)}")
        
        # Log Azure token creation activity
        token_activity_logger.log_activity(
            token_id=azure_token_id,
            action=TokenAction.CREATED,
            performed_by=user_info,
            details={
                'token_type': 'azure_token',
                'issuer': claims.get('iss', 'Unknown'),
                'audience': claims.get('aud', 'Unknown')
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        # Get groups from Microsoft Graph if we have access token
        if access_token:
            async with httpx.AsyncClient() as client:
                headers = {'Authorization': f'Bearer {access_token}'}
                try:
                    groups_response = await client.get(
                        'https://graph.microsoft.com/v1.0/me/memberOf?$select=id,displayName',
                        headers=headers
                    )
                    if groups_response.status_code == 200:
                        groups_data = groups_response.json()
                        logger.debug(f"Groups data from Microsoft Graph: {json.dumps(groups_data, indent=2)}")
                        
                        # Process groups, handling both dict and other formats
                        processed_groups = []
                        for g in groups_data.get('value', []):
                            if isinstance(g, dict):
                                processed_groups.append({
                                    'id': g.get('id', ''),
                                    'displayName': g.get('displayName', f"Group {g.get('id', '')[:8]}...")
                                })
                            else:
                                logger.warning(f"Unexpected group format: {type(g)} - {g}")
                                
                        user_info['groups'] = processed_groups
                except Exception as e:
                    logger.error(f"Failed to fetch groups: {e}")
        
        # Create our internal tokens with IAM claims
        access_token = generate_token_with_iam_claims(user_info)
        refresh_token = refresh_token_store.create_refresh_token(user_info, lifetime_days=30)
        
        # Store tokens in issued_tokens for admin tracking
        token_id = str(uuid.uuid4())
        now_utc = datetime.utcnow()
        expires_utc = now_utc + timedelta(minutes=10)  # 10 minutes for IAM tokens
        
        # Debug logging
        logger.debug(f"Token timestamp debug:")
        logger.debug(f"  now_utc: {now_utc}")
        logger.debug(f"  now_utc.isoformat(): {now_utc.isoformat()}")
        logger.debug(f"  expires_utc: {expires_utc}")
        logger.debug(f"  expires_utc.isoformat(): {expires_utc.isoformat()}")
        
        issued_tokens[token_id] = {
            'id': token_id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_info,
            'issued_at': now_utc.isoformat() + 'Z',  # Explicitly add Z for UTC
            'expires_at': expires_utc.isoformat() + 'Z',  # Explicitly add Z for UTC
            'source': 'azure_callback',
            'session_id': session_id
        }
        
        # Log token creation activity
        token_activity_logger.log_activity(
            token_id=token_id,
            action=TokenAction.CREATED,
            performed_by=user_info,
            details={
                'source': 'azure_callback',
                'session_id': session_id
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        # Store tokens in session
        session_data['internal_token'] = access_token  # Keep backward compatibility
        session_data['access_token'] = access_token
        session_data['refresh_token'] = refresh_token
        session_data['azure_id_token'] = id_token_data  # Store Azure token for comparison
        session_data['azure_claims'] = claims  # Store Azure claims
        session_data['user'] = user_info
        session_data['token_id'] = token_id  # Store reference to issued_tokens
        set_session(session_id, session_data)
        
        logger.info(f"User authenticated: {user_info['name']}")
        
        # Check if this is an app-specific flow
        if session_data.get('client_id'):
            # Add app-specific roles to the token
            client_id = session_data['client_id']
            # Extract group names handling both dict and string formats
            groups_raw = user_info.get('groups', [])
            user_groups = []
            for g in groups_raw:
                if isinstance(g, dict):
                    user_groups.append(g.get('displayName', ''))
                else:
                    user_groups.append(str(g))
            app_roles = app_store.get_user_roles_for_app(client_id, user_groups)
            
            # Recreate token with app-specific claims
            token_claims = user_info.copy()
            token_claims['client_id'] = client_id
            token_claims['app_roles'] = app_roles
            
            access_token = generate_token_with_iam_claims(token_claims, client_id)
            
            # Update stored token
            issued_tokens[token_id]['access_token'] = access_token
            session_data['access_token'] = access_token
            
            # Redirect back to app with token
            app_redirect_uri = session_data.get('app_redirect_uri')
            app_state = session_data.get('app_state')
            
            if app_redirect_uri:
                # Build redirect URL with token and state
                redirect_params = {
                    'access_token': access_token,
                    'state': app_state
                }
                redirect_url = f"{app_redirect_uri}?{urllib.parse.urlencode(redirect_params)}"
                return RedirectResponse(url=redirect_url, status_code=303)
        
        # Standard flow - redirect to home page
        response = RedirectResponse(url='/', status_code=303)
        response.set_cookie(key="auth_session_id", value=session_id, httponly=True, samesite="lax", secure=True)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Authentication error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

@app.post("/auth/token")
async def token_endpoint(token_request: TokenRequest):
    """
    OAuth2 Token Endpoint
    
    Supports:
    - grant_type=refresh_token: Exchange refresh token for new access token
    """
    if token_request.grant_type == "refresh_token":
        if not token_request.refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token required")
        
        # Validate and rotate refresh token
        user_info, new_refresh_token = refresh_token_store.validate_and_rotate(token_request.refresh_token)
        
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Create new access token with IAM claims
        access_token = generate_token_with_iam_claims(user_info)
        
        # Store tokens in issued_tokens for admin tracking
        token_id = str(uuid.uuid4())
        now_utc = datetime.utcnow()
        expires_utc = now_utc + timedelta(minutes=10)  # 10 minutes for IAM tokens
        
        # Debug logging
        logger.debug(f"Refresh token timestamp debug:")
        logger.debug(f"  now_utc: {now_utc}")
        logger.debug(f"  now_utc.isoformat(): {now_utc.isoformat()}")
        logger.debug(f"  expires_utc: {expires_utc}")
        logger.debug(f"  expires_utc.isoformat(): {expires_utc.isoformat()}")
        
        issued_tokens[token_id] = {
            'id': token_id,
            'access_token': access_token,
            'refresh_token': new_refresh_token,
            'user': user_info,
            'issued_at': now_utc.isoformat() + 'Z',  # Explicitly add Z for UTC
            'expires_at': expires_utc.isoformat() + 'Z',  # Explicitly add Z for UTC
            'source': 'refresh_token',
            'parent_refresh_token': token_request.refresh_token
        }
        
        # Log token refresh activity
        token_activity_logger.log_activity(
            token_id=token_id,
            action=TokenAction.REFRESHED,
            performed_by=user_info,
            details={
                'source': 'refresh_token',
                'parent_refresh_token': token_request.refresh_token[:20] + '...' if len(token_request.refresh_token) > 20 else token_request.refresh_token
            }
        )
        
        return JSONResponse({
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': 600,  # 10 minutes
            'refresh_token': new_refresh_token
        })
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {token_request.grant_type}")

# OAuth token endpoint for refresh with httpOnly cookies
@app.post("/oauth/token")
async def oauth_token(request: Request, response: Response):
    """OAuth 2.0 token endpoint with httpOnly refresh token support"""
    try:
        form_data = await request.form()
        grant_type = form_data.get('grant_type')
        
        if grant_type == 'refresh_token':
            refresh_token = form_data.get('refresh_token')
            if not refresh_token:
                raise HTTPException(status_code=400, detail="refresh_token required")
            
            # Validate and rotate refresh token
            user_info, new_refresh_token = refresh_token_store.validate_and_rotate(refresh_token)
            
            if not user_info:
                raise HTTPException(status_code=401, detail="Invalid refresh token")
            
            # Generate new access token
            client_id = form_data.get('client_id')
            access_token = generate_token_with_iam_claims(user_info, client_id)
            
            # Set httpOnly cookie for refresh token
            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=7*24*60*60  # 7 days
            )
            
            return JSONResponse({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 600,  # 10 minutes
                "refresh_token": new_refresh_token
            })
            
        elif grant_type == 'client_credentials':
            # For service-to-service auth
            client_id = form_data.get('client_id')
            client_secret = form_data.get('client_secret')
            
            # Validate client credentials
            app_data = app_store.get_app(client_id)
            if not app_data:
                raise HTTPException(status_code=401, detail="Invalid client credentials")
            
            # Check if the secret matches
            stored_secret = app_store.app_secrets.get(client_id)
            if not stored_secret or stored_secret != client_secret:
                raise HTTPException(status_code=401, detail="Invalid client credentials")
            
            # Generate service token
            claims = {
                'iss': 'internal-auth-service',
                'sub': client_id,
                'aud': ['internal-services'],
                'client_id': client_id,
                'app_name': app_data['name'],
                'token_type': 'service',
                'token_version': '2.0'
            }
            
            access_token = jwt_manager.create_token(claims, token_lifetime_minutes=60, token_type='service')
            
            return JSONResponse({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600
            })
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported grant_type")
            
    except Exception as e:
        logger.error(f"Token endpoint error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/token/session")
async def get_session_token(request: Request):
    """Get current token from session (backward compatibility)"""
    session_id = request.cookies.get('auth_session_id')
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_data = get_session(session_id)
    access_token = session_data.get('access_token') or session_data.get('internal_token')
    refresh_token = session_data.get('refresh_token')
    
    if not access_token:
        raise HTTPException(status_code=401, detail="No valid token found")
    
    response = {
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 1800
    }
    
    if refresh_token:
        response['refresh_token'] = refresh_token
    
    return JSONResponse(response)

@app.get("/auth/validate")
async def validate_token(authorization: Optional[str] = Header(None)):
    """Validate an internal JWT token"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace('Bearer ', '')
    
    is_valid, claims, error = jwt_manager.validate_token(token)
    
    if not is_valid:
        raise HTTPException(status_code=401, detail=error or "Invalid token")
    
    # Check if token has been revoked and find token_id
    token_id_found = None
    for token_id, token_data in issued_tokens.items():
        if token_data['access_token'] == token:
            token_id_found = token_id
            if token_data.get('revoked', False):
                raise HTTPException(status_code=401, detail="Token has been revoked")
            break
    
    # Log validation activity if we found the token
    if token_id_found:
        token_activity_logger.log_activity(
            token_id=token_id_found,
            action=TokenAction.VALIDATED,
            details={
                'endpoint': '/auth/validate'
            }
        )
    
    return JSONResponse({
        'valid': True,
        'sub': claims.get('sub'),
        'email': claims.get('email'),
        'name': claims.get('name'),
        'groups': claims.get('groups', [])
    })

@app.get("/auth/public-key")
async def get_public_key():
    """Get the public key for token validation in JWKS format"""
    return JSONResponse(jwt_manager.get_public_key_jwks())

@app.post("/auth/introspect")
async def introspect_token(token: str):
    """
    Introspect a token (RFC 7662)
    
    This endpoint allows services to validate tokens and get detailed information
    """
    return JSONResponse(jwt_manager.introspect_token(token))

@app.post("/auth/revoke")
async def revoke_token(revoke_request: RevokeTokenRequest):
    """
    Revoke a token (RFC 7009)
    
    Supports revoking refresh tokens
    """
    if revoke_request.token_type_hint == "refresh_token":
        success = refresh_token_store.revoke_token(revoke_request.token)
        if success:
            logger.info("Refresh token revoked successfully")
        return Response(status_code=200)  # Always return 200 per RFC
    else:
        # For now, we don't support revoking access tokens
        # In production, you'd maintain a blacklist
        return Response(status_code=200)

@app.get("/auth/logout")
async def auth_logout(request: Request, response: Response):
    """Logout and clear session"""
    session_id = request.cookies.get('auth_session_id')
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response = RedirectResponse(url='/')
    response.delete_cookie(key="auth_session_id")
    return response

@app.get("/auth/admin/tokens")
async def get_all_tokens(authorization: Optional[str] = Header(None), include_revoked: bool = True):
    """View all issued tokens (admin only)"""
    logger.debug(f"=== /auth/admin/tokens endpoint called ===")
    logger.debug(f"Authorization header received: {authorization[:50] + '...' if authorization and len(authorization) > 50 else authorization}")
    
    is_admin, claims = check_admin_access(authorization)
    logger.debug(f"Admin check result: is_admin={is_admin}, claims={claims}")
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Return all tokens with sensitive data redacted
    tokens_list = []
    for token_id, token_data in issued_tokens.items():
        # Skip revoked tokens if not requested
        if not include_revoked and token_data.get('revoked', False):
            continue
            
        tokens_list.append({
            'id': token_data['id'],
            'user': {
                'name': token_data['user'].get('name'),
                'email': token_data['user'].get('email')
            },
            'issued_at': token_data['issued_at'],
            'expires_at': token_data['expires_at'],
            'source': token_data['source'],
            'session_id': token_data.get('session_id'),
            'access_token': token_data['access_token'],  # Include full token for admin viewing
            'access_token_preview': token_data['access_token'][:20] + '...' if len(token_data['access_token']) > 20 else token_data['access_token'],
            'revoked': token_data.get('revoked', False),
            'revoked_at': token_data.get('revoked_at'),
            'revoked_by': token_data.get('revoked_by')
        })
    
    return JSONResponse({
        'total': len(tokens_list),
        'tokens': tokens_list,
        'admin_user': claims.get('email')
    })

@app.delete("/auth/admin/tokens/{token_id}")
async def revoke_token_by_id(token_id: str, authorization: Optional[str] = Header(None)):
    """Revoke a specific token by ID (admin only)"""
    logger.debug(f"=== /auth/admin/tokens/{token_id} DELETE endpoint called ===")
    logger.debug(f"Authorization header received: {authorization[:50] + '...' if authorization and len(authorization) > 50 else authorization}")
    
    is_admin, claims = check_admin_access(authorization)
    logger.debug(f"Admin check result: is_admin={is_admin}, claims={claims}")
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if token exists
    if token_id not in issued_tokens:
        raise HTTPException(status_code=404, detail="Token not found")
    
    token_data = issued_tokens[token_id]
    
    # Check if already revoked
    if token_data.get('revoked', False):
        raise HTTPException(status_code=400, detail="Token is already revoked")
    
    # Mark token as revoked
    token_data['revoked'] = True
    token_data['revoked_at'] = datetime.utcnow().isoformat() + 'Z'
    token_data['revoked_by'] = claims.get('email')
    
    # Log revocation activity
    token_activity_logger.log_activity(
        token_id=token_id,
        action=TokenAction.REVOKED,
        performed_by={
            'email': claims.get('email'),
            'name': claims.get('name')
        },
        details={
            'revoked_at': token_data['revoked_at'],
            'token_user': token_data.get('user', {}).get('email')
        }
    )
    
    # Also revoke the associated refresh token if it exists
    if 'refresh_token' in token_data:
        refresh_token_store.revoke_token(token_data['refresh_token'])
    
    logger.info(f"Token {token_id} revoked by {claims.get('email')}")
    
    return JSONResponse({
        'status': 'success',
        'message': f'Token {token_id} has been revoked',
        'revoked_by': claims.get('email'),
        'revoked_at': token_data['revoked_at']
    })


@app.get("/auth/admin/tokens/{token_id}/activities")
async def get_token_activities(token_id: str, authorization: Optional[str] = Header(None)):
    """Get activity log for a specific token (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if token exists
    if token_id not in issued_tokens:
        raise HTTPException(status_code=404, detail="Token not found")
    
    # Get token activities
    activities = token_activity_logger.get_token_activities(token_id)
    
    # Also log that admin viewed the activities
    token_activity_logger.log_activity(
        token_id=token_id,
        action=TokenAction.ADMIN_VIEW,
        performed_by={
            'email': claims.get('email'),
            'name': claims.get('name')
        },
        details={
            'viewed': 'token_activities'
        }
    )
    
    return JSONResponse({
        'token_id': token_id,
        'token_info': {
            'user': issued_tokens[token_id].get('user'),
            'issued_at': issued_tokens[token_id].get('issued_at'),
            'expires_at': issued_tokens[token_id].get('expires_at'),
            'source': issued_tokens[token_id].get('source'),
            'revoked': issued_tokens[token_id].get('revoked', False)
        },
        'activities': activities,
        'activity_count': len(activities)
    })

@app.get("/auth/admin/azure-tokens")
async def get_all_azure_tokens(authorization: Optional[str] = Header(None)):
    """View all Azure-issued tokens (admin only)"""
    logger.debug(f"=== /auth/admin/azure-tokens endpoint called ===")
    logger.debug(f"Authorization header received: {authorization[:50] + '...' if authorization and len(authorization) > 50 else authorization}")
    
    is_admin, claims = check_admin_access(authorization)
    logger.debug(f"Admin check result: is_admin={is_admin}, claims={claims}")
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Return all Azure tokens with sensitive data handling
    tokens_list = []
    for token_id, token_data in azure_tokens.items():
        # Mask sensitive parts of the tokens for display
        id_token_masked = token_data['id_token'][:20] + '...' + token_data['id_token'][-20:] if token_data.get('id_token') else 'N/A'
        access_token_masked = token_data['access_token'][:20] + '...' + token_data['access_token'][-20:] if token_data.get('access_token') else 'N/A'
        
        tokens_list.append({
            'id': token_data['id'],
            'user': {
                'name': token_data['user'].get('name'),
                'email': token_data['user'].get('email')
            },
            'issued_at': token_data['issued_at'],
            'expires_at': token_data['expires_at'],
            'subject': token_data['subject'],
            'issuer': token_data['issuer'],
            'audience': token_data['audience'],
            'id_token_preview': id_token_masked,
            'access_token_preview': access_token_masked,
            'full_id_token': token_data.get('id_token', ''),
            'full_access_token': token_data.get('access_token', '')
        })
    
    return JSONResponse({
        'total': len(tokens_list),
        'tokens': tokens_list,
        'admin_user': claims.get('email')
    })

@app.delete("/auth/admin/azure-tokens/{token_id}")
async def remove_azure_token(token_id: str, authorization: Optional[str] = Header(None)):
    """Remove a specific Azure token from storage (admin only)
    Note: This only removes it from our storage, not from Azure AD."""
    logger.debug(f"=== /auth/admin/azure-tokens/{token_id} DELETE endpoint called ===")
    
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if token exists
    if token_id not in azure_tokens:
        raise HTTPException(status_code=404, detail="Azure token not found")
    
    # Remove token from storage
    token_info = azure_tokens.pop(token_id)
    
    # Log Azure token removal activity
    token_activity_logger.log_activity(
        token_id=token_id,
        action=TokenAction.REVOKED,
        performed_by={
            'email': claims.get('email'),
            'name': claims.get('name')
        },
        details={
            'token_type': 'azure_token',
            'action': 'removed_from_storage',
            'token_user': token_info.get('user', {}).get('email')
        }
    )
    
    logger.info(f"Azure token {token_id} removed by {claims.get('email')}")
    
    return JSONResponse({
        'status': 'success',
        'message': 'Azure token removed from storage successfully',
        'token_id': token_id,
        'removed_by': claims.get('email'),
        'removed_at': datetime.utcnow().isoformat() + 'Z',
        'note': 'Token removed from local storage only. Azure AD tokens remain valid until expiry.'
    })

@app.get("/auth/admin/azure-tokens/cleanup")
async def cleanup_expired_azure_tokens(authorization: Optional[str] = Header(None)):
    """Clean up expired Azure tokens from storage (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    expired_tokens = []
    current_time = datetime.utcnow()
    
    # Find expired tokens
    for token_id, token_info in list(azure_tokens.items()):
        expires_at = datetime.fromisoformat(token_info['expires_at'].rstrip('Z'))
        if expires_at < current_time:
            expired_tokens.append(token_id)
            del azure_tokens[token_id]
    
    logger.info(f"Cleaned up {len(expired_tokens)} expired Azure tokens by {claims.get('email')}")
    
    return JSONResponse({
        'status': 'success',
        'message': f'Cleaned up {len(expired_tokens)} expired Azure tokens',
        'expired_token_ids': expired_tokens,
        'cleaned_by': claims.get('email'),
        'cleaned_at': current_time.isoformat() + 'Z'
    })

@app.get("/auth/admin/azure-tokens/{token_id}/activities")
async def get_azure_token_activities(token_id: str, authorization: Optional[str] = Header(None)):
    """Get activity log for a specific Azure token (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if token exists
    if token_id not in azure_tokens:
        raise HTTPException(status_code=404, detail="Azure token not found")
    
    # Get token activities
    activities = token_activity_logger.get_token_activities(token_id)
    
    # Also log that admin viewed the activities
    token_activity_logger.log_activity(
        token_id=token_id,
        action=TokenAction.ADMIN_VIEW,
        performed_by={
            'email': claims.get('email'),
            'name': claims.get('name')
        },
        details={
            'viewed': 'azure_token_activities',
            'token_type': 'azure_token'
        }
    )
    
    return JSONResponse({
        'token_id': token_id,
        'token_info': {
            'user': azure_tokens[token_id].get('user'),
            'issued_at': azure_tokens[token_id].get('issued_at'),
            'expires_at': azure_tokens[token_id].get('expires_at'),
            'issuer': azure_tokens[token_id].get('issuer'),
            'audience': azure_tokens[token_id].get('audience')
        },
        'activities': activities,
        'activity_count': len(activities)
    })

# ============================================
# App Registration Endpoints
# ============================================

@app.post("/auth/admin/apps", response_model=AppRegistrationResponse)
async def register_app(request: RegisterAppRequest, authorization: Optional[str] = Header(None)):
    """Register a new application (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Register the app
    app_data, client_secret = app_store.register_app(request)
    
    # Log the registration
    logger.info(f"App '{request.name}' registered by {claims.get('email')}")
    
    return AppRegistrationResponse(
        app=AppResponse(**app_data),
        client_secret=client_secret
    )

@app.get("/auth/admin/apps", response_model=List[AppResponse])
async def list_apps(authorization: Optional[str] = Header(None)):
    """List all registered applications (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    apps = app_store.list_apps()
    return [AppResponse(**app) for app in apps]

@app.get("/auth/admin/apps/{client_id}", response_model=AppResponse)
async def get_app(client_id: str, authorization: Optional[str] = Header(None)):
    """Get details of a specific app (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    app = app_store.get_app(client_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    return AppResponse(**app)

@app.put("/auth/admin/apps/{client_id}", response_model=AppResponse)
async def update_app(client_id: str, request: UpdateAppRequest, authorization: Optional[str] = Header(None)):
    """Update app details (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    app = app_store.update_app(client_id, request)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    logger.info(f"App '{client_id}' updated by {claims.get('email')}")
    
    return AppResponse(**app)

@app.post("/auth/admin/apps/{client_id}/rotate-secret")
async def rotate_app_secret(client_id: str, authorization: Optional[str] = Header(None)):
    """Rotate client secret for an app (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    new_secret = app_store.rotate_client_secret(client_id)
    if not new_secret:
        raise HTTPException(status_code=404, detail="App not found")
    
    logger.info(f"Client secret rotated for app '{client_id}' by {claims.get('email')}")
    
    return JSONResponse({
        "client_id": client_id,
        "client_secret": new_secret,
        "message": "Client secret has been rotated. Please update your application configuration."
    })

@app.delete("/auth/admin/apps/{client_id}")
async def delete_app(client_id: str, authorization: Optional[str] = Header(None)):
    """Delete (deactivate) an app (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not app_store.delete_app(client_id):
        raise HTTPException(status_code=404, detail="App not found")
    
    logger.info(f"App '{client_id}' deleted by {claims.get('email')}")
    
    return JSONResponse({"message": "App has been deactivated"})

# Role Mapping Endpoints

@app.post("/auth/admin/apps/{client_id}/role-mappings")
async def set_role_mappings(
    client_id: str, 
    request: SetRoleMappingRequest, 
    authorization: Optional[str] = Header(None)
):
    """Set AD group to app role mappings (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not app_store.set_role_mappings(client_id, request.mappings, claims.get('email')):
        raise HTTPException(status_code=404, detail="App not found")
    
    logger.info(f"Role mappings set for app '{client_id}' by {claims.get('email')}")
    
    return JSONResponse({
        "message": "Role mappings updated successfully",
        "mappings": request.mappings
    })

@app.get("/auth/admin/apps/{client_id}/role-mappings")
async def get_role_mappings(client_id: str, authorization: Optional[str] = Header(None)):
    """Get role mappings for an app (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    app = app_store.get_app(client_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    mappings = app_store.get_role_mappings(client_id)
    
    return JSONResponse({
        "client_id": client_id,
        "app_name": app.get('name'),
        "mappings": mappings
    })

# Admin UI for app management
@app.get("/auth/admin/apps-ui")
async def apps_admin_ui(request: Request):
    """Admin UI for managing registered apps"""
    # Check if user is authenticated via session
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/auth/login?return_url=/auth/admin/apps-ui")
    
    session_data = get_session(session_id)
    if not session_data or 'access_token' not in session_data:
        return RedirectResponse(url="/auth/login?return_url=/auth/admin/apps-ui")
    
    # Check admin access
    is_admin, claims = check_admin_access(f"Bearer {session_data['access_token']}")
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return templates.TemplateResponse("apps_admin.html", {"request": request})

@app.get("/debug/app-storage")
async def debug_app_storage(authorization: Optional[str] = Header(None)):
    """Debug endpoint to view app registrations (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return JSONResponse({
        'registered_apps_count': len(registered_apps),
        'apps': [
            {
                'client_id': app['client_id'],
                'name': app['name'],
                'is_active': app['is_active'],
                'created_at': app['created_at']
            }
            for app in registered_apps.values()
        ],
        'app_role_mappings_count': len(app_role_mappings),
        'note': 'Apps are stored in memory and reset on server restart'
    })

@app.get("/debug/token-storage")
async def debug_token_storage(authorization: Optional[str] = Header(None)):
    """Debug endpoint to view token storage (admin only)"""
    is_admin, claims = check_admin_access(authorization)
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Add timezone debug info
    now_utc = datetime.utcnow()
    now_local = datetime.now()
    
    return JSONResponse({
        'issued_tokens_count': len(issued_tokens),
        'sessions_count': len(sessions),
        'refresh_tokens_count': len(refresh_token_store.tokens),
        'storage_details': {
            'issued_tokens_ids': list(issued_tokens.keys()),
            'session_ids': list(sessions.keys()),
            'refresh_token_count_by_user': {}
        },
        'timezone_debug': {
            'server_utc_time': now_utc.isoformat(),
            'server_local_time': now_local.isoformat(),
            'server_timezone_offset': str(now_local - now_utc),
            'sample_token': next(iter(issued_tokens.values()), None) if issued_tokens else None
        }
    })

@app.get("/auth/my-token")
async def get_my_token(authorization: Optional[str] = Header(None)):
    """View your own token information"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace('Bearer ', '')
    is_valid, claims, error = jwt_manager.validate_token(token)
    
    if not is_valid:
        raise HTTPException(status_code=401, detail=error or "Invalid token")
    
    # Find this token in issued_tokens
    token_info = None
    for token_id, token_data in issued_tokens.items():
        if token_data['access_token'] == token:
            token_info = {
                'token_id': token_id,
                'issued_at': token_data['issued_at'],
                'expires_at': token_data['expires_at'],
                'source': token_data['source']
            }
            break
    
    return JSONResponse({
        'valid': True,
        'claims': claims,
        'token_info': token_info,
        'token_preview': token[:20] + '...' if len(token) > 20 else token
    })

@app.post("/auth/validate")
async def validate_token_endpoint(request: Request):
    """Validate a token sent in the request body"""
    try:
        data = await request.json()
        token = data.get('token')
        
        if not token:
            return JSONResponse({'valid': False, 'error': 'No token provided'}, status_code=400)
        
        is_valid, claims, error = jwt_manager.validate_token(token)
        
        if not is_valid:
            return JSONResponse({'valid': False, 'error': error or 'Invalid token'})
        
        # Check if this is for a specific client app
        client_id = data.get('client_id')
        if client_id:
            # Verify the client exists and is active
            app_data = app_store.get_app(client_id)
            if not app_data:
                return JSONResponse({'valid': False, 'error': 'Invalid client_id'})
            if not app_data.get('is_active'):
                return JSONResponse({'valid': False, 'error': 'Application is not active'})
            
            # Add app-specific roles to claims
            role_mappings = app_store.get_role_mappings(client_id)
            app_roles = []
            user_groups = claims.get('groups', [])
            
            for mapping in role_mappings:
                if mapping['ad_group'] in user_groups:
                    app_roles.append(mapping['app_role'])
            
            claims['app_roles'] = app_roles
            claims['client_id'] = client_id
        
        return JSONResponse({
            'valid': True,
            'claims': claims
        })
        
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return JSONResponse({'valid': False, 'error': str(e)}, status_code=400)

@app.get("/auth/debug/admin-check")
async def debug_admin_check(authorization: Optional[str] = Header(None)):
    """Debug endpoint to test admin access check"""
    is_admin, claims = check_admin_access(authorization)
    
    # Get the raw config for debugging
    admin_emails_raw = os.getenv('ADMIN_EMAILS', 'admin@example.com').split(',')
    admin_emails = [email.strip().lower() for email in admin_emails_raw if email.strip()]
    
    admin_group_ids_raw = os.getenv('ADMIN_GROUP_IDS', '').split(',')
    admin_group_ids = [group_id.strip() for group_id in admin_group_ids_raw if group_id.strip()]
    
    user_email = claims.get('email', '').strip().lower() if claims else None
    
    return JSONResponse({
        'is_admin': is_admin,
        'user_email': claims.get('email') if claims else None,
        'user_email_normalized': user_email,
        'user_groups': claims.get('groups', []) if claims else [],
        'admin_config': {
            'ADMIN_EMAILS_env': os.getenv('ADMIN_EMAILS'),
            'admin_emails_raw': admin_emails_raw,
            'admin_emails_normalized': admin_emails,
            'ADMIN_GROUP_IDS_env': os.getenv('ADMIN_GROUP_IDS'),
            'admin_group_ids': admin_group_ids
        },
        'claims': claims
    })

@app.get("/debug/timestamps")
async def debug_timestamps():
    """Debug endpoint to show server timestamps and timezone info"""
    import time
    import platform
    
    now_utc = datetime.utcnow()
    now_local = datetime.now()
    
    # Get a sample token if any exist
    sample_token = None
    if issued_tokens:
        sample_token_data = next(iter(issued_tokens.values()))
        sample_token = {
            'issued_at': sample_token_data['issued_at'],
            'expires_at': sample_token_data['expires_at'],
            'user': sample_token_data['user']['email']
        }
    
    return JSONResponse({
        'server_info': {
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'timezone_name': time.tzname,
            'timezone_offset_seconds': time.timezone,
            'dst_offset_seconds': time.altzone,
            'is_dst': time.daylight
        },
        'current_timestamps': {
            'utc_now': now_utc.isoformat() + 'Z',
            'local_now': now_local.isoformat(),
            'utc_timestamp': now_utc.timestamp(),
            'local_timestamp': now_local.timestamp(),
            'offset_hours': (now_local - now_utc).total_seconds() / 3600
        },
        'sample_token': sample_token,
        'timestamp_examples': {
            'correct_utc_format': datetime.utcnow().isoformat() + 'Z',
            'without_z': datetime.utcnow().isoformat(),
            'with_timezone': datetime.now().astimezone().isoformat()
        }
    })

# JWKS and metadata endpoints
@app.get("/.well-known/jwks.json")
async def get_jwks():
    """Get JSON Web Key Set"""
    return JSONResponse(jwks_handler.get_jwks())

@app.get("/.well-known/cids-config")
async def get_cids_config(request: Request):
    """Get CIDS configuration metadata"""
    base_url = str(request.base_url).rstrip('/')
    return JSONResponse(jwks_handler.get_metadata(base_url))

# App endpoints registry
@app.put("/apps/{client_id}/endpoints")
async def update_app_endpoints(
    client_id: str,
    update: EndpointsUpdate,
    authorization: Optional[str] = Header(None)
):
    """Update endpoints for an app"""
    # Check admin access
    is_admin, user_info = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Verify app exists
    app_data = app_store.get_app(client_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="App not found")
    
    try:
        result = endpoints_registry.upsert_endpoints(
            client_id, update, user_info.get('email', 'unknown')
        )
        
        # Audit log
        audit_logger.log_action(
            AuditAction.ENDPOINTS_UPDATED,
            user_email=user_info.get('email'),
            resource_type="app_endpoints",
            resource_id=client_id,
            details={"endpoints_count": result['endpoints_count']}
        )
        
        return JSONResponse(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/apps/{client_id}/endpoints")
async def get_app_endpoints(client_id: str):
    """Get endpoints for an app"""
    endpoints = endpoints_registry.get_app_endpoints(client_id)
    if not endpoints:
        raise HTTPException(status_code=404, detail="No endpoints found for app")
    return JSONResponse(endpoints)

# Roles and mappings
@app.put("/apps/{client_id}/roles")
async def update_app_roles(
    client_id: str,
    update: RolesUpdate,
    authorization: Optional[str] = Header(None)
):
    """Update roles for an app"""
    is_admin, user_info = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Verify app exists
    app_data = app_store.get_app(client_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="App not found")
    
    try:
        result = roles_manager.upsert_app_roles(
            client_id, update, user_info.get('email', 'unknown')
        )
        
        # Audit log
        audit_logger.log_action(
            AuditAction.ROLES_UPDATED,
            user_email=user_info.get('email'),
            resource_type="app_roles",
            resource_id=client_id,
            details={"roles_count": result['roles_count']}
        )
        
        return JSONResponse(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/apps/{client_id}/roles")
async def get_app_roles(client_id: str):
    """Get roles for an app"""
    roles = roles_manager.get_app_roles(client_id)
    if not roles:
        raise HTTPException(status_code=404, detail="No roles found for app")
    return JSONResponse(roles)

@app.put("/role-mappings")
async def update_role_mappings(
    update: RoleMappingsUpdate,
    authorization: Optional[str] = Header(None)
):
    """Update Azure AD group to role mappings"""
    is_admin, user_info = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        result = roles_manager.upsert_role_mappings(
            update, user_info.get('email', 'unknown')
        )
        
        # Audit log
        audit_logger.log_action(
            AuditAction.ROLE_MAPPINGS_UPDATED,
            user_email=user_info.get('email'),
            resource_type="role_mappings",
            details={"mappings_count": result['mappings_count']}
        )
        
        return JSONResponse(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/role-mappings")
async def get_role_mappings():
    """Get all role mappings"""
    return JSONResponse({"mappings": roles_manager.get_all_mappings()})

# Policy management
@app.put("/policy/{client_id}")
async def update_app_policy(
    client_id: str,
    policy: PolicyDocument,
    authorization: Optional[str] = Header(None)
):
    """Create or update policy for an app"""
    is_admin, user_info = check_admin_access(authorization)
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Verify app exists
    app_data = app_store.get_app(client_id)
    if not app_data:
        raise HTTPException(status_code=404, detail="App not found")
    
    try:
        result = policy_manager.upsert_policy(
            client_id, policy, user_info.get('email', 'unknown')
        )
        
        # Audit log
        audit_logger.log_action(
            AuditAction.POLICY_UPDATED,
            user_email=user_info.get('email'),
            resource_type="policy",
            resource_id=client_id,
            details={
                "version": result['version'],
                "permissions_count": result['permissions_count']
            }
        )
        
        return JSONResponse(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/policy/{client_id}")
async def get_app_policy(client_id: str, version: Optional[str] = None):
    """Get policy for an app"""
    if version:
        policy = policy_manager.get_policy_version(client_id, version)
    else:
        policy = policy_manager.get_active_policy(client_id)
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return JSONResponse(policy)

# Effective identity endpoint
@app.get("/iam/me")
async def get_effective_identity(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None)
):
    """Get effective identity with computed permissions"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace('Bearer ', '')
    is_valid, claims, error = jwt_manager.validate_token(token)
    
    if not is_valid:
        raise HTTPException(status_code=401, detail=error or "Invalid token")
    
    # Get user's roles across all apps
    user_groups = claims.get('groups', [])
    user_roles = roles_manager.get_user_roles(user_groups, x_tenant_id)
    
    # Compute effective permissions for each app
    effective_perms = {}
    for app_id, roles in user_roles.items():
        perms = set()
        for role in roles:
            perms.update(policy_manager.compute_effective_permissions(
                app_id, roles, claims.get('attrs', {})
            ))
        effective_perms[app_id] = list(perms)
    
    # Build response
    response = {
        "sub": claims.get('sub'),
        "email": claims.get('email'),
        "name": claims.get('name'),
        "aud": claims.get('aud', ['internal-services']),
        "scope": claims.get('scope', 'openid profile email'),
        "roles": user_roles,
        "effective_permissions": effective_perms,
        "attrs": {
            "department": claims.get('attrs', {}).get('department'),
            "tenant": x_tenant_id,
            "groups": user_groups[:10]  # Limit for response size
        },
        "token_info": {
            "iss": claims.get('iss'),
            "iat": claims.get('iat'),
            "exp": claims.get('exp'),
            "ver": claims.get('token_version', '1.0')
        }
    }
    
    return JSONResponse(response)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "cids-auth",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.get("/auth/whoami")
async def whoami(authorization: Optional[str] = Header(None)):
    """Get current authenticated user's information"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace('Bearer ', '')
    is_valid, claims, error = jwt_manager.validate_token(token)
    
    if not is_valid:
        raise HTTPException(status_code=401, detail=error or "Invalid token")
    
    # Check if user is admin (using same logic as check_admin_access)
    admin_emails_raw = os.getenv('ADMIN_EMAILS', 'admin@example.com').split(',')
    admin_emails = [email.strip().lower() for email in admin_emails_raw if email.strip()]
    
    admin_group_ids_raw = os.getenv('ADMIN_GROUP_IDS', '').split(',')
    admin_group_ids = [group_id.strip() for group_id in admin_group_ids_raw if group_id.strip()]
    
    user_email = claims.get('email', '').strip().lower()
    user_groups = claims.get('groups', [])
    
    is_admin = user_email in admin_emails
    
    # Check if user is in admin group
    for group in user_groups:
        if isinstance(group, dict) and group.get('id') in admin_group_ids:
            is_admin = True
            break
    
    return JSONResponse({
        'email': claims.get('email'),
        'name': claims.get('name'),
        'sub': claims.get('sub'),
        'groups': claims.get('groups', []),
        'is_admin': is_admin,
        'admin_config': {
            'admin_emails': admin_emails,
            'admin_emails_raw': admin_emails_raw,  # Show raw config for debugging
            'admin_group_ids': admin_group_ids
        } if is_admin else None
    })

# Helper functions for IAM token generation
def generate_token_with_iam_claims(user_info: dict, client_id: Optional[str] = None) -> str:
    """Generate token with IAM claims"""
    # Get user's roles
    user_groups = []
    groups_data = user_info.get('groups', [])
    
    # Handle both dict and string group formats
    if isinstance(groups_data, list):
        for group in groups_data:
            if isinstance(group, dict):
                # Extract displayName from dict
                display_name = group.get('displayName', '')
                if display_name:
                    user_groups.append(display_name)
            elif isinstance(group, str):
                # Already a string, just use it
                user_groups.append(group)
            else:
                # Convert whatever it is to string
                user_groups.append(str(group))
    else:
        logger.warning(f"Unexpected groups data type: {type(groups_data)}")
    
    # Get roles from the roles manager
    try:
        user_roles = roles_manager.get_user_roles(user_groups)
    except Exception as e:
        logger.warning(f"Error getting user roles: {e}")
        user_roles = {}
    
    # Build claims from scratch to avoid any dict/string confusion
    claims = {
        'iss': 'internal-auth-service',
        'sub': user_info.get('sub', user_info.get('id', '')),
        'aud': [client_id] if client_id else ['internal-services'],
        'email': user_info.get('email', ''),
        'name': user_info.get('name', ''),
        'groups': user_groups,  # This is now a clean list of strings
        'scope': 'openid profile email',
        'roles': user_roles,
        'attrs': {
            'tenant': user_info.get('tenant_id')
        },
        'token_version': '2.0'  # New version with IAM claims
    }
    
    # Add any app-specific claims if provided
    if 'client_id' in user_info and not client_id:
        claims['client_id'] = user_info['client_id']
    if 'app_roles' in user_info:
        claims['app_roles'] = user_info['app_roles']
    
    # Generate token with 10 minute TTL
    access_token = jwt_manager.create_token(claims, token_lifetime_minutes=10, token_type='access')
    return access_token


@app.get("/", response_class=HTMLResponse)
async def test_page(request: Request):
    """Test page to demonstrate auth service functionality"""
    session_id = request.cookies.get('auth_session_id')
    session_data = None
    internal_token = None
    token_claims = None
    azure_token = None
    azure_claims = None
    
    if session_id:
        session_data = get_session(session_id)
        # Try both possible keys for the token
        internal_token = session_data.get('access_token') or session_data.get('internal_token')
        azure_token = session_data.get('azure_id_token')
        azure_claims = session_data.get('azure_claims')
        
        if internal_token:
            try:
                # Decode token to show claims
                _, token_claims, _ = jwt_manager.validate_token(internal_token)
            except Exception as e:
                logger.debug(f"Error decoding token for display: {e}")
                pass
    
    return templates.TemplateResponse("auth_test.html", {
        "request": request,
        "session_id": session_id,
        "session_data": session_data,
        "internal_token": internal_token,
        "token_claims": token_claims,
        "azure_token": azure_token,
        "azure_claims": azure_claims
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, ssl_keyfile="key.pem", ssl_certfile="cert.pem", reload=True)