"""
Enhanced Discovery Service for Field-Level Permissions

This service discovers complete field-level metadata from applications
and generates granular permissions automatically.
"""
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
import httpx
import asyncio
import json
import logging
from pathlib import Path

from discovery_models import (
    DiscoveryResponse, EndpointMetadata, FieldMetadata,
    PermissionMetadata, DiscoveredPermissions,
    generate_permission_key, extract_resource_from_path,
    extract_action_from_method, FieldType
)
import app_registration
from app_registration import save_data, load_data
from jwt_utils import JWTManager

logger = logging.getLogger(__name__)

# Storage paths
PERMISSIONS_FILE = Path("app_data/discovered_permissions.json")
FIELD_METADATA_FILE = Path("app_data/field_metadata.json")


class EnhancedDiscoveryService:
    """Handles field-level discovery and permission generation"""
    
    def __init__(self, jwt_manager: JWTManager):
        self.jwt_manager = jwt_manager
        self.discovery_timeout = 30  # Longer timeout for detailed discovery
        self.permissions_cache: Dict[str, DiscoveredPermissions] = {}
        self._load_permissions()
        
    def _load_permissions(self):
        """Load discovered permissions from storage"""
        try:
            if PERMISSIONS_FILE.exists():
                with open(PERMISSIONS_FILE, 'r') as f:
                    data = json.load(f)
                    for app_id, perm_data in data.items():
                        self.permissions_cache[app_id] = DiscoveredPermissions(**perm_data)
        except Exception as e:
            logger.error(f"Error loading permissions: {e}")
            self.permissions_cache = {}
    
    def _save_permissions(self):
        """Save discovered permissions to storage"""
        try:
            PERMISSIONS_FILE.parent.mkdir(exist_ok=True)
            data = {
                app_id: perms.dict() for app_id, perms in self.permissions_cache.items()
            }
            with open(PERMISSIONS_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving permissions: {e}")
    
    async def discover_with_fields(self, client_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Discover endpoints with complete field metadata
        
        Returns:
            Discovery result with generated permissions
        """
        load_data()
        app = app_registration.registered_apps.get(client_id)
        
        if not app:
            return {
                "status": "error",
                "error": "Application not found"
            }
            
        if not app.get("allow_discovery", False):
            return {
                "status": "error", 
                "error": "Application does not allow discovery"
            }
            
        discovery_endpoint = app.get("discovery_endpoint")
        if not discovery_endpoint:
            return {
                "status": "error",
                "error": "No discovery endpoint configured"
            }
            
        # Check rate limiting
        if not force:
            last_discovery = app.get("last_discovery_at")
            if last_discovery:
                last_time = datetime.fromisoformat(last_discovery)
                if datetime.utcnow() - last_time < timedelta(minutes=5):
                    # Return cached permissions
                    if client_id in self.permissions_cache:
                        cached = self.permissions_cache[client_id]
                        return {
                            "status": "cached",
                            "message": "Using cached discovery data",
                            "permissions_count": cached.total_count,
                            "last_discovery_at": last_discovery
                        }
        
        # Create service token
        service_token = self._create_service_token()
        
        try:
            # Fetch enhanced discovery data
            discovery_json = await self._fetch_enhanced_discovery(discovery_endpoint, service_token)
            
            # Check if this is a v1 response
            if discovery_json.get("version", "1.0") == "1.0":
                logger.warning(f"App {client_id} returned v1 discovery format")
                return {
                    "status": "error",
                    "error": "Application does not support enhanced discovery (v2.0). Only v1 format received.",
                    "discovery_version": "1.0"
                }
            
            # Validate against enhanced schema
            discovery_data = DiscoveryResponse(**discovery_json)
            
            # Generate permissions from discovery
            permissions = self._generate_permissions(client_id, discovery_data)
            
            # Store permissions
            self.permissions_cache[client_id] = permissions
            self._save_permissions()
            
            # Update app status in the global registered_apps
            logger.info(f"Updating discovery status for {client_id}")
            logger.debug(f"Before update - discovery_status: {app_registration.registered_apps[client_id].get('discovery_status')}")
            
            app_registration.registered_apps[client_id]["last_discovery_at"] = datetime.utcnow().isoformat()
            app_registration.registered_apps[client_id]["discovery_status"] = "success"
            app_registration.registered_apps[client_id]["discovery_version"] = discovery_data.version
            
            logger.debug(f"After update - discovery_status: {app_registration.registered_apps[client_id].get('discovery_status')}")
            logger.debug(f"After update - last_discovery_at: {app_registration.registered_apps[client_id].get('last_discovery_at')}")
            
            save_data()
            logger.info(f"Discovery status saved for {client_id}")
            
            # Store field metadata separately for UI
            await self._store_field_metadata(client_id, discovery_data)
            
            return {
                "status": "success",
                "discovery_version": discovery_data.version,
                "endpoints_discovered": len(discovery_data.endpoints or []),
                "services_discovered": len(discovery_data.services or []),
                "permissions_generated": permissions.total_count,
                "sensitive_permissions": permissions.sensitive_count,
                "sample_permissions": list(permissions.permissions.keys())[:10]
            }
            
        except httpx.ConnectError as e:
            logger.error(f"Discovery connection error for {client_id}: {e}")
            app_registration.registered_apps[client_id]["discovery_status"] = "connection_error"
            save_data()
            error_msg = str(e)
            # Check if it's a network connectivity issue
            if "All connection attempts failed" in error_msg:
                return {
                    "status": "error",
                    "error": "Cannot connect to application. Please ensure the application is running and accessible.",
                    "details": error_msg,
                    "discovery_endpoint": discovery_endpoint
                }
            return {
                "status": "error",
                "error": f"Connection error: {error_msg}"
            }
        except httpx.TimeoutException:
            logger.error(f"Discovery timeout for {client_id}")
            app_registration.registered_apps[client_id]["discovery_status"] = "timeout"
            save_data()
            return {
                "status": "error",
                "error": "Discovery endpoint timeout after 30 seconds",
                "discovery_endpoint": discovery_endpoint
            }
        except Exception as e:
            logger.error(f"Discovery error for {client_id}: {e}", exc_info=True)
            app_registration.registered_apps[client_id]["discovery_status"] = "error"
            save_data()
            return {
                "status": "error",
                "error": str(e),
                "discovery_endpoint": discovery_endpoint
            }
    
    def _create_service_token(self) -> str:
        """Create a service token for CIDS to authenticate to apps"""
        claims = {
            'iss': 'internal-auth-service',
            'sub': 'cids-discovery-service',
            'aud': ['discovery-api'],
            'client_id': 'cids-discovery',
            'app_name': 'CIDS Discovery Service',
            'token_type': 'service',
            'permissions': ['discovery.read'],
            'token_version': '2.0'
        }
        return self.jwt_manager.create_token(claims, token_lifetime_minutes=5, token_type='access')
    
    async def _fetch_enhanced_discovery(self, discovery_url: str, token: str) -> Dict:
        """Fetch enhanced discovery data from app"""
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "CIDS-Discovery/2.0",
            "X-Discovery-Version": "2.0"  # Request enhanced format
        }
        
        # Add version parameter to URL if not already present
        if '?' in discovery_url:
            discovery_url += '&version=2.0'
        else:
            discovery_url += '?version=2.0'
        
        logger.info(f"Fetching discovery from: {discovery_url}")
        
        # Try multiple connection attempts with different settings
        errors = []
        
        # Attempt 1: Standard connection with SSL verification disabled
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.discovery_timeout, connect=10.0),
                verify=False,
                follow_redirects=True
            ) as client:
                response = await client.get(discovery_url, headers=headers)
                response.raise_for_status()
                return response.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            errors.append(f"Standard attempt failed: {str(e)}")
            logger.warning(f"Discovery connection attempt 1 failed: {e}")
        except Exception as e:
            errors.append(f"Standard attempt error: {str(e)}")
            logger.warning(f"Discovery attempt 1 error: {e}")
        
        # Attempt 2: Try without version parameter (fallback to v1)
        try:
            # Remove version parameter for compatibility
            base_url = discovery_url.split('?')[0]
            logger.info(f"Trying fallback discovery at: {base_url}")
            
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.discovery_timeout, connect=10.0),
                verify=False,
                follow_redirects=True
            ) as client:
                response = await client.get(base_url, headers=headers)
                response.raise_for_status()
                return response.json()
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            errors.append(f"Fallback attempt failed: {str(e)}")
            logger.warning(f"Discovery connection attempt 2 failed: {e}")
        except Exception as e:
            errors.append(f"Fallback attempt error: {str(e)}")
            logger.warning(f"Discovery attempt 2 error: {e}")
        
        # All attempts failed
        error_msg = "All connection attempts failed"
        if errors:
            error_msg += ": " + "; ".join(errors)
        logger.error(f"Discovery failed for {discovery_url}: {error_msg}")
        raise httpx.ConnectError(error_msg)
    
    def _generate_permissions(self, app_id: str, discovery: DiscoveryResponse) -> DiscoveredPermissions:
        """Generate granular permissions from discovery data"""
        permissions: Dict[str, PermissionMetadata] = {}
        
        # Process endpoints (single-service apps)
        if discovery.endpoints:
            for endpoint in discovery.endpoints:
                self._process_endpoint_permissions(app_id, endpoint, permissions)
        
        # Process services (multi-service apps)
        if discovery.services:
            for service in discovery.services:
                for endpoint in service.endpoints:
                    # Prefix with service name
                    self._process_endpoint_permissions(
                        app_id, endpoint, permissions, 
                        service_prefix=service.name
                    )
        
        # Count sensitive permissions
        sensitive_count = sum(
            1 for p in permissions.values() 
            if p.sensitive or p.pii or p.phi
        )
        
        return DiscoveredPermissions(
            app_id=app_id,
            permissions=permissions,
            total_count=len(permissions),
            sensitive_count=sensitive_count,
            last_discovered=datetime.utcnow(),
            discovery_version=discovery.version
        )
    
    def _process_endpoint_permissions(
        self, 
        app_id: str, 
        endpoint: EndpointMetadata, 
        permissions: Dict[str, PermissionMetadata],
        service_prefix: Optional[str] = None
    ):
        """Extract permissions from a single endpoint"""
        resource = extract_resource_from_path(endpoint.path)
        if service_prefix:
            resource = f"{service_prefix}_{resource}"
        
        # Determine if this is a collection endpoint
        is_collection = not endpoint.path.rstrip('/').endswith('}')
        action = extract_action_from_method(endpoint.method, is_collection)
        
        # Process response fields (for GET endpoints)
        if endpoint.response_fields and endpoint.method == "GET":
            self._process_fields(
                app_id, resource, "read", 
                endpoint.response_fields, 
                endpoint.operation_id,
                permissions
            )
        
        # Process request fields (for POST/PUT/PATCH)
        if endpoint.request_fields and endpoint.method in ["POST", "PUT", "PATCH"]:
            self._process_fields(
                app_id, resource, "write",
                endpoint.request_fields,
                endpoint.operation_id,
                permissions
            )
        
        # Add endpoint-level permission
        endpoint_perm_key = generate_permission_key(app_id, resource, action, "*")
        if endpoint_perm_key not in permissions:
            permissions[endpoint_perm_key] = PermissionMetadata(
                permission_key=endpoint_perm_key,
                resource=resource,
                action=action,
                field_path="*",
                description=f"{action.capitalize()} all fields for {resource}",
                endpoint_id=endpoint.operation_id
            )
    
    def _process_fields(
        self,
        app_id: str,
        resource: str,
        action: str,
        fields: Dict[str, FieldMetadata],
        endpoint_id: str,
        permissions: Dict[str, PermissionMetadata],
        parent_path: str = ""
    ):
        """Recursively process fields to generate permissions"""
        for field_name, field_meta in fields.items():
            field_path = f"{parent_path}.{field_name}" if parent_path else field_name
            perm_key = generate_permission_key(app_id, resource, action, field_path)
            
            # Create permission metadata
            permissions[perm_key] = PermissionMetadata(
                permission_key=perm_key,
                resource=resource,
                action=action,
                field_path=field_path,
                description=field_meta.description or f"{action.capitalize()} {field_path}",
                sensitive=field_meta.sensitive,
                pii=field_meta.pii,
                phi=field_meta.phi,
                endpoint_id=endpoint_id
            )
            
            # Process nested object fields
            if field_meta.type == FieldType.OBJECT and field_meta.fields:
                self._process_fields(
                    app_id, resource, action,
                    field_meta.fields,
                    endpoint_id,
                    permissions,
                    field_path
                )
            
            # Process array item fields
            elif field_meta.type == FieldType.ARRAY and field_meta.items:
                if field_meta.items.type == FieldType.OBJECT and field_meta.items.fields:
                    # Array of objects
                    self._process_fields(
                        app_id, resource, action,
                        field_meta.items.fields,
                        endpoint_id,
                        permissions,
                        f"{field_path}[]"
                    )
    
    async def _store_field_metadata(self, app_id: str, discovery: DiscoveryResponse):
        """Store field metadata for UI consumption"""
        try:
            # Load existing metadata
            metadata = {}
            if FIELD_METADATA_FILE.exists():
                with open(FIELD_METADATA_FILE, 'r') as f:
                    metadata = json.load(f)
            
            # Update with new discovery
            metadata[app_id] = {
                "app_name": discovery.app_name,
                "last_updated": discovery.last_updated.isoformat(),
                "endpoints": discovery.dict()["endpoints"] if discovery.endpoints else [],
                "services": discovery.dict()["services"] if discovery.services else []
            }
            
            # Save
            FIELD_METADATA_FILE.parent.mkdir(exist_ok=True)
            with open(FIELD_METADATA_FILE, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Error storing field metadata: {e}")
    
    def get_app_permissions(self, app_id: str) -> Optional[DiscoveredPermissions]:
        """Get discovered permissions for an app"""
        return self.permissions_cache.get(app_id)
    
    def search_permissions(
        self, 
        app_id: str,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        sensitive_only: bool = False
    ) -> List[PermissionMetadata]:
        """Search for specific permissions"""
        if app_id not in self.permissions_cache:
            return []
        
        perms = self.permissions_cache[app_id].permissions.values()
        
        # Filter by criteria
        if resource:
            perms = [p for p in perms if p.resource == resource]
        if action:
            perms = [p for p in perms if p.action == action]
        if sensitive_only:
            perms = [p for p in perms if p.sensitive or p.pii or p.phi]
        
        return list(perms)
    
    def get_permission_tree(self, app_id: str) -> Dict[str, Any]:
        """Get permissions organized as a tree structure for UI"""
        if app_id not in self.permissions_cache:
            return {}
        
        tree = {}
        perms = self.permissions_cache[app_id].permissions.values()
        
        for perm in perms:
            # Build tree structure: resource -> action -> fields
            if perm.resource not in tree:
                tree[perm.resource] = {}
            
            if perm.action not in tree[perm.resource]:
                tree[perm.resource][perm.action] = {
                    "fields": [],
                    "has_wildcard": False,
                    "sensitive_count": 0
                }
            
            if perm.field_path == "*":
                tree[perm.resource][perm.action]["has_wildcard"] = True
            else:
                field_info = {
                    "path": perm.field_path,
                    "permission_key": perm.permission_key,
                    "description": perm.description,
                    "sensitive": perm.sensitive,
                    "pii": perm.pii,
                    "phi": perm.phi
                }
                tree[perm.resource][perm.action]["fields"].append(field_info)
                
                if perm.sensitive or perm.pii or perm.phi:
                    tree[perm.resource][perm.action]["sensitive_count"] += 1
        
        return tree