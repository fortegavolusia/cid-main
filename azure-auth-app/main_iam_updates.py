# IAM Feature Additions for main.py
# Add these imports to the top of main.py:

from jwks_handler import JWKSHandler
from app_endpoints import AppEndpointsRegistry, EndpointsUpdate
from roles_manager import RolesManager, RolesUpdate, RoleMappingsUpdate
from policy_manager import PolicyManager, PolicyDocument
from audit_logger import audit_logger, AuditAction

# Initialize new components (add after jwt_manager initialization)
jwks_handler = JWKSHandler(jwt_manager)
endpoints_registry = AppEndpointsRegistry()
roles_manager = RolesManager()
policy_manager = PolicyManager()

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

# Update token generation to include new claims
def generate_token_with_iam_claims(user_info: dict, client_id: Optional[str] = None) -> str:
    """Generate token with IAM claims"""
    # Get user's roles
    user_groups = user_info.get('groups', [])
    user_roles = roles_manager.get_user_roles(user_groups)
    
    # Build claims
    claims = {
        'iss': 'internal-auth-service',
        'sub': user_info.get('id', ''),
        'aud': [client_id] if client_id else ['internal-services'],
        'email': user_info.get('email', ''),
        'name': user_info.get('name', ''),
        'groups': user_groups,
        'scope': 'openid profile email',
        'roles': user_roles,
        'attrs': {
            'department': extract_department_from_groups(user_groups),
            'tenant': user_info.get('tenant_id')
        },
        'token_version': '2.0'  # New version with IAM claims
    }
    
    # Generate token with 10 minute TTL
    access_token = jwt_manager.generate_token(claims, expires_in=600)
    return access_token

def extract_department_from_groups(groups: List[str]) -> Optional[str]:
    """Extract department from AD groups"""
    # Logic to extract department - customize based on your AD structure
    dept_prefixes = ['IT', 'HR', 'Finance', 'Engineering', 'Sales']
    for group in groups:
        for dept in dept_prefixes:
            if group.startswith(dept):
                return dept
    return None

# OAuth token endpoint for refresh
@app.post("/oauth/token")
async def oauth_token(request: Request, response: Response):
    """OAuth 2.0 token endpoint"""
    try:
        form_data = await request.form()
        grant_type = form_data.get('grant_type')
        
        if grant_type == 'refresh_token':
            refresh_token = form_data.get('refresh_token')
            if not refresh_token:
                raise HTTPException(status_code=400, detail="refresh_token required")
            
            # Validate refresh token
            token_data = refresh_token_store.get_token(refresh_token)
            if not token_data:
                raise HTTPException(status_code=401, detail="Invalid refresh token")
            
            # Generate new access token
            user_info = token_data['user']
            client_id = form_data.get('client_id')
            
            access_token = generate_token_with_iam_claims(user_info, client_id)
            new_refresh_token = refresh_token_store.create_token(
                user_info, token_type="refresh", client_id=client_id
            )
            
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
            
            if not app_store.validate_client_credentials(client_id, client_secret):
                raise HTTPException(status_code=401, detail="Invalid client credentials")
            
            # Generate service token
            app_data = app_store.get_app(client_id)
            claims = {
                'iss': 'internal-auth-service',
                'sub': client_id,
                'aud': ['internal-services'],
                'client_id': client_id,
                'app_name': app_data['name'],
                'token_type': 'service',
                'token_version': '2.0'
            }
            
            access_token = jwt_manager.generate_token(claims, expires_in=3600)
            
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