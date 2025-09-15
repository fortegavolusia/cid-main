"""
A2A (Application-to-Application) endpoints for CIDS
Handles service-to-service authentication and authorization
"""

from fastapi import HTTPException, Header, Body
from fastapi.responses import JSONResponse
from typing import Optional, Dict
from datetime import datetime, timedelta
import json
import uuid
import httpx
import logging

logger = logging.getLogger(__name__)

async def setup_a2a_endpoints(app, db_service, jwt_manager, check_admin_access):
    """Setup A2A endpoints on the FastAPI app"""

    @app.get("/auth/admin/a2a/permissions")
    async def get_a2a_permissions(authorization: Optional[str] = Header(None)):
        """Get all A2A permissions configured in the system"""
        is_admin, _ = check_admin_access(authorization)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        try:
            permissions = db_service.execute_query("""
                SELECT
                    a.a2a_id,
                    a.source_client_id,
                    s.name as source_name,
                    a.target_client_id,
                    t.name as target_name,
                    a.allowed_scopes,
                    a.allowed_endpoints,
                    a.max_token_duration,
                    a.is_active,
                    a.created_at,
                    a.updated_at,
                    a.created_by,
                    a.updated_by
                FROM cids.a2a_permissions a
                JOIN cids.registered_apps s ON a.source_client_id = s.client_id
                JOIN cids.registered_apps t ON a.target_client_id = t.client_id
                ORDER BY a.created_at DESC
            """)

            result = []
            for perm in permissions:
                result.append({
                    "a2a_id": perm['a2a_id'],
                    "source": {
                        "client_id": perm['source_client_id'],
                        "name": perm['source_name']
                    },
                    "target": {
                        "client_id": perm['target_client_id'],
                        "name": perm['target_name']
                    },
                    "allowed_scopes": perm['allowed_scopes'] or [],
                    "allowed_endpoints": perm['allowed_endpoints'] or [],
                    "max_token_duration": perm['max_token_duration'],
                    "is_active": perm['is_active'],
                    "created_at": perm['created_at'].isoformat() if perm['created_at'] else None,
                    "updated_at": perm['updated_at'].isoformat() if perm['updated_at'] else None,
                    "created_by": perm['created_by'],
                    "updated_by": perm['updated_by']
                })

            return JSONResponse({"permissions": result})
        except Exception as e:
            logger.error(f"Failed to get A2A permissions: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve A2A permissions")

    @app.post("/auth/admin/a2a/permissions")
    async def create_a2a_permission(
        request: Dict = Body(...),
        authorization: Optional[str] = Header(None)
    ):
        """Create a new A2A permission between two services"""
        is_admin, claims = check_admin_access(authorization)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        try:
            # Generate a2a_id from UUID service
            a2a_id = None
            try:
                async with httpx.AsyncClient() as client:
                    uuid_response = await client.post(
                        "http://uuid-service-dev:8002/generate",
                        json={"prefix": "a2a", "type": "a2a"}
                    )
                    if uuid_response.status_code == 200:
                        a2a_id = uuid_response.json().get("id")
                        logger.info(f"Generated a2a_id from UUID service: {a2a_id}")
            except Exception as e:
                logger.warning(f"Could not get UUID from service: {e}, using fallback")
                a2a_id = f"a2a_{uuid.uuid4().hex[:16]}"

            # Insert A2A permission
            result = db_service.execute_update("""
                INSERT INTO cids.a2a_permissions
                (a2a_id, source_client_id, target_client_id, allowed_scopes,
                 allowed_endpoints, max_token_duration, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                a2a_id,
                request['source_client_id'],
                request['target_client_id'],
                request.get('allowed_scopes', []),
                request.get('allowed_endpoints', []),
                request.get('max_token_duration', 300),
                request.get('is_active', True),
                claims.get('email', 'admin')
            ))

            # Log to activity_log
            activity_id = f"act_{uuid.uuid4().hex[:16]}"
            db_service.execute_update("""
                INSERT INTO cids.activity_log
                (activity_id, activity_type, entity_type, entity_id, entity_name,
                 user_email, details, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                activity_id,
                'a2a.permission.created',
                'a2a_permission',
                a2a_id,
                f"{request['source_client_id']} -> {request['target_client_id']}",
                claims.get('email', 'admin'),
                json.dumps({
                    'a2a_id': a2a_id,
                    'source': request['source_client_id'],
                    'target': request['target_client_id'],
                    'scopes': request.get('allowed_scopes', [])
                }),
                'success'
            ))

            return JSONResponse({
                "message": "A2A permission created successfully",
                "a2a_id": a2a_id
            })
        except Exception as e:
            logger.error(f"Failed to create A2A permission: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.put("/auth/admin/a2a/permissions/{a2a_id}")
    async def update_a2a_permission(
        a2a_id: str,
        request: Dict = Body(...),
        authorization: Optional[str] = Header(None)
    ):
        """Update an existing A2A permission"""
        is_admin, claims = check_admin_access(authorization)
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        try:
            # Update A2A permission
            result = db_service.execute_update("""
                UPDATE cids.a2a_permissions
                SET allowed_scopes = %s,
                    allowed_endpoints = %s,
                    max_token_duration = %s,
                    is_active = %s,
                    updated_by = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE a2a_id = %s
            """, (
                request.get('allowed_scopes', []),
                request.get('allowed_endpoints', []),
                request.get('max_token_duration', 300),
                request.get('is_active', True),
                claims.get('email', 'admin'),
                a2a_id
            ))

            # Log to activity_log
            activity_id = f"act_{uuid.uuid4().hex[:16]}"
            db_service.execute_update("""
                INSERT INTO cids.activity_log
                (activity_id, activity_type, entity_type, entity_id, entity_name,
                 user_email, details, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                activity_id,
                'a2a.permission.updated',
                'a2a_permission',
                a2a_id,
                a2a_id,
                claims.get('email', 'admin'),
                json.dumps({
                    'a2a_id': a2a_id,
                    'changes': request
                }),
                'success'
            ))

            return JSONResponse({
                "message": "A2A permission updated successfully",
                "a2a_id": a2a_id
            })
        except Exception as e:
            logger.error(f"Failed to update A2A permission: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/auth/service-token")
    async def get_service_token(
        request: Dict = Body(...),
        x_api_key: Optional[str] = Header(None)
    ):
        """Get a service token for A2A communication"""

        # Validate API key
        if not x_api_key or not x_api_key.startswith("cids_ak_"):
            raise HTTPException(status_code=401, detail="Valid API key required")

        # Extract key_id from API key
        key_id = x_api_key.replace("cids_ak_", "")

        # Validate API key and get client_id
        api_key_data = db_service.execute_query("""
            SELECT client_id, is_active
            FROM cids.api_keys
            WHERE key_id = %s AND is_active = true
        """, (key_id,))

        if not api_key_data:
            raise HTTPException(status_code=401, detail="Invalid or inactive API key")

        source_client_id = api_key_data[0]['client_id']
        target_client_id = request.get('target_client_id')

        if not target_client_id:
            raise HTTPException(status_code=400, detail="target_client_id required")

        # Check A2A permission exists
        permission = db_service.execute_query("""
            SELECT a2a_id, allowed_scopes, allowed_endpoints, max_token_duration
            FROM cids.a2a_permissions
            WHERE source_client_id = %s
              AND target_client_id = %s
              AND is_active = true
        """, (source_client_id, target_client_id))

        if not permission:
            raise HTTPException(
                status_code=403,
                detail=f"No A2A permission from {source_client_id} to {target_client_id}"
            )

        # Generate service token
        token_duration = min(
            request.get('duration', 300),
            permission[0]['max_token_duration']
        )

        token_claims = {
            "sub": source_client_id,
            "aud": target_client_id,
            "type": "service_token",
            "a2a_id": permission[0]['a2a_id'],
            "scopes": request.get('requested_scopes', permission[0]['allowed_scopes']),
            "purpose": request.get('purpose', 'service_communication'),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=token_duration)
        }

        # Generate JWT token
        service_token = jwt_manager.create_token(token_claims)

        # Log to activity_log
        activity_id = f"act_{uuid.uuid4().hex[:16]}"
        db_service.execute_update("""
            INSERT INTO cids.activity_log
            (activity_id, activity_type, entity_type, entity_id, entity_name,
             user_email, details, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            activity_id,
            'a2a.token.issued',
            'service_token',
            permission[0]['a2a_id'],
            f"{source_client_id} -> {target_client_id}",
            source_client_id,
            json.dumps({
                'source': source_client_id,
                'target': target_client_id,
                'duration': token_duration,
                'scopes': token_claims['scopes']
            }),
            'success'
        ))

        return JSONResponse({
            "token": service_token,
            "expires_in": token_duration,
            "token_type": "Bearer"
        })

    logger.info("A2A endpoints registered successfully")