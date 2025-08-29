"""
Consolidated Enhanced Discovery Service (unversioned)
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx
import asyncio
import json
import logging

from backend.schemas.discovery import (
    DiscoveryResponse, EndpointMetadata, FieldMetadata,
    PermissionMetadata, DiscoveredPermissions,
    generate_permission_key, extract_resource_from_path,
    extract_action_from_method, FieldType
)
from backend.utils.paths import data_path
from backend.services.jwt import JWTManager
from backend.services.endpoints import AppEndpointsRegistry
from backend.services.permission_registry import PermissionRegistry
from backend.services.app_registration import registered_apps, save_data

logger = logging.getLogger(__name__)

PERMISSIONS_FILE = data_path("discovered_permissions.json")
FIELD_METADATA_FILE = data_path("field_metadata.json")


class DiscoveryService:
    """Handles field-level discovery and permission generation"""

    def __init__(self, jwt_manager: JWTManager, endpoints_registry: Optional[AppEndpointsRegistry] = None, permission_registry: Optional[PermissionRegistry] = None):
        self.jwt_manager = jwt_manager
        self.endpoints_registry = endpoints_registry
        self.permission_registry = permission_registry or PermissionRegistry()
        self.discovery_timeout = 30
        self.permissions_cache: Dict[str, DiscoveredPermissions] = {}
        self._load_permissions()

    def _load_permissions(self):
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
        try:
            PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {app_id: perms.dict() for app_id, perms in self.permissions_cache.items()}
            with open(PERMISSIONS_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving permissions: {e}")

    async def discover_with_fields(self, client_id: str, force: bool = False) -> Dict[str, Any]:
        """Discover endpoints with complete field metadata for a registered app (v2 format)."""
        # Load app config
        app = registered_apps.get(client_id)
        if not app:
            return {"status": "error", "error": "Application not found"}
        if not app.get("allow_discovery", False):
            return {"status": "error", "error": "Application does not allow discovery"}
        discovery_endpoint = app.get("discovery_endpoint")
        if not discovery_endpoint:
            return {"status": "error", "error": "No discovery endpoint configured"}

        # Rate limit caching window
        if not force and client_id in self.permissions_cache:
            cached = self.permissions_cache[client_id]
            last = app.get("last_discovery_at") or cached.last_discovered.isoformat()
            return {
                "status": "cached",
                "message": "Using cached discovery data",
                "permissions_count": cached.total_count,
                "last_discovery_at": last
            }

        service_token = self._create_service_token()
        try:
            discovery_json = await self._fetch_enhanced_discovery(discovery_endpoint, service_token)
            # Validate against schema (v2 format only)
            discovery_data = DiscoveryResponse(**discovery_json)

            # Generate permissions
            permissions = self._generate_permissions(client_id, discovery_data)
            self.permissions_cache[client_id] = permissions
            # Also register with central permission registry for UI queries
            try:
                self.permission_registry.register_permissions(client_id, permissions.permissions)
            except Exception:
                logger.exception("Failed to register permissions in registry")
            self._save_permissions()

            # Update app discovery status
            app["last_discovery_at"] = datetime.utcnow().isoformat()
            app["discovery_status"] = "success"
            app["discovery_version"] = discovery_data.discovery_version if hasattr(discovery_data, 'discovery_version') else "2.0"
            save_data()

            # Store field metadata separately for UI
            await self._store_field_metadata(client_id, discovery_data)

            # Store endpoints if registry available
            endpoints_stored = 0
            if self.endpoints_registry and discovery_data.endpoints:
                endpoints_stored = await self._store_endpoints(client_id, discovery_data)

            return {
                "status": "success",
                "endpoints_discovered": len(discovery_data.endpoints or []),
                "endpoints_stored": endpoints_stored,
                "services_discovered": len(discovery_data.services or []),
                "permissions_generated": permissions.total_count,
                "sensitive_permissions": permissions.sensitive_count,
                "sample_permissions": list(permissions.permissions.keys())[:10]
            }
        except httpx.ConnectError as e:
            error_msg = str(e)
            app["discovery_status"] = "connection_error"
            save_data()
            return {"status": "error", "error": f"Connection error: {error_msg}", "discovery_endpoint": discovery_endpoint}
        except httpx.TimeoutException:
            app["discovery_status"] = "timeout"
            save_data()
            return {"status": "error", "error": "Discovery endpoint timeout after 30 seconds", "discovery_endpoint": discovery_endpoint}
        except Exception as e:
            app["discovery_status"] = "error"
            save_data()
            return {"status": "error", "error": str(e), "discovery_endpoint": discovery_endpoint}

    def _create_service_token(self) -> str:
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
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "CIDS-Discovery/2.0",
            "X-Discovery-Version": "2.0"
        }
        url = discovery_url if '?' in discovery_url else f"{discovery_url}?version=2.0"
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.discovery_timeout, connect=10.0), verify=False, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    def _generate_permissions(self, app_id: str, discovery: DiscoveryResponse) -> DiscoveredPermissions:
        permissions: Dict[str, PermissionMetadata] = {}
        if discovery.endpoints:
            for endpoint in discovery.endpoints:
                self._process_endpoint_permissions(app_id, endpoint, permissions)
        if discovery.services:
            for service in discovery.services:
                for endpoint in service.endpoints:
                    self._process_endpoint_permissions(app_id, endpoint, permissions, service_prefix=service.name)
        sensitive_count = sum(1 for p in permissions.values() if p.sensitive or p.pii or p.phi)
        return DiscoveredPermissions(
            app_id=app_id,
            permissions=permissions,
            total_count=len(permissions),
            sensitive_count=sensitive_count,
            last_discovered=datetime.utcnow(),
            discovery_version="2.0",
        )

    def _process_endpoint_permissions(self, app_id: str, endpoint: EndpointMetadata, permissions: Dict[str, PermissionMetadata], service_prefix: Optional[str] = None):
        resource = extract_resource_from_path(endpoint.path)
        if service_prefix:
            resource = f"{service_prefix}_{resource}"
        is_collection = not endpoint.path.rstrip('/').endswith('}')
        action = extract_action_from_method(endpoint.method, is_collection)
        if endpoint.response_fields and endpoint.method == "GET":
            self._process_fields(app_id, resource, "read", endpoint.response_fields, endpoint.operation_id, permissions)
        if endpoint.request_fields and endpoint.method in ["POST", "PUT", "PATCH"]:
            self._process_fields(app_id, resource, "write", endpoint.request_fields, endpoint.operation_id, permissions)
        endpoint_perm_key = generate_permission_key(app_id, resource, action, "*")
        if endpoint_perm_key not in permissions:
            permissions[endpoint_perm_key] = PermissionMetadata(
                permission_key=endpoint_perm_key,
                resource=resource,
                action=action,
                field_path="*",
                description=f"{action.capitalize()} all fields for {resource}",
                endpoint_id=endpoint.operation_id,
            )

    def _process_fields(self, app_id: str, resource: str, action: str, fields: Dict[str, FieldMetadata], endpoint_id: str, permissions: Dict[str, PermissionMetadata], parent_path: str = ""):
        for field_name, field_meta in fields.items():
            field_path = f"{parent_path}.{field_name}" if parent_path else field_name
            perm_key = generate_permission_key(app_id, resource, action, field_path)
            permissions[perm_key] = PermissionMetadata(
                permission_key=perm_key,
                resource=resource,
                action=action,
                field_path=field_path,
                description=field_meta.description or f"{action.capitalize()} {field_path}",
                sensitive=field_meta.sensitive,
                pii=field_meta.pii,
                phi=field_meta.phi,
                endpoint_id=endpoint_id,
            )
            if field_meta.type == FieldType.OBJECT and field_meta.fields:
                self._process_fields(app_id, resource, action, field_meta.fields, endpoint_id, permissions, field_path)
            elif field_meta.type == FieldType.ARRAY and field_meta.items:
                if field_meta.items.type == FieldType.OBJECT and field_meta.items.fields:
                    self._process_fields(app_id, resource, action, field_meta.items.fields, endpoint_id, permissions, f"{field_path}[]")

    async def _store_field_metadata(self, app_id: str, discovery: DiscoveryResponse):
        try:
            metadata = {}
            if FIELD_METADATA_FILE.exists():
                with open(FIELD_METADATA_FILE, 'r') as f:
                    metadata = json.load(f)
            metadata[app_id] = {
                "app_name": discovery.app_name,
                "last_updated": discovery.last_updated.isoformat(),
                "endpoints": discovery.dict().get("endpoints", []),
                "services": discovery.dict().get("services", []),
            }
            FIELD_METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FIELD_METADATA_FILE, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error storing field metadata: {e}")

    # Exposed helper methods for UI/administration
    def get_app_permissions(self, app_id: str) -> Optional[DiscoveredPermissions]:
        return self.permissions_cache.get(app_id)

    def search_permissions(self, app_id: Optional[str] = None, resource: Optional[str] = None, action: Optional[str] = None, sensitive_only: bool = False):
        """Return a list of PermissionMetadata objects (legacy-compatible)."""
        # permission_registry.search_permissions returns List[Tuple[app_id, PermissionMetadata]]
        results = self.permission_registry.search_permissions(app_id, resource, action, None, sensitive_only)
        return [perm for (_aid, perm) in results]

    def get_permission_tree(self, app_id: str):
        """Return legacy tree shape: resource -> action -> {fields: [], has_wildcard: bool, sensitive_count: int}"""
        tree: Dict[str, Dict[str, Dict[str, Any]]] = {}
        perms = self.permission_registry.get_app_permissions(app_id).values()
        for perm in perms:
            res = perm.resource
            act = perm.action
            if res not in tree:
                tree[res] = {}
            if act not in tree[res]:
                tree[res][act] = {"fields": [], "has_wildcard": False, "sensitive_count": 0}
            if perm.field_path == "*":
                tree[res][act]["has_wildcard"] = True
            else:
                field_info = {
                    "path": perm.field_path,
                    "permission_key": perm.permission_key,
                    "description": perm.description,
                    "sensitive": getattr(perm, "sensitive", False),
                    "pii": getattr(perm, "pii", False),
                    "phi": getattr(perm, "phi", False),
                }
                tree[res][act]["fields"].append(field_info)
                if field_info["sensitive"] or field_info["pii"] or field_info["phi"]:
                    tree[res][act]["sensitive_count"] += 1
        return tree

    async def _store_endpoints(self, client_id: str, discovery_data: DiscoveryResponse) -> int:
        if not self.endpoints_registry:
            return 0
        stored = 0
        endpoints_to_store = []
        if discovery_data.endpoints:
            for endpoint in discovery_data.endpoints:
                endpoints_to_store.append({
                    "method": endpoint.method,
                    "path": endpoint.path,
                    "description": endpoint.description,
                    "discovered": True,
                    "discovered_at": datetime.utcnow().isoformat(),
                    "required_permissions": getattr(endpoint, 'required_permissions', []),
                    "required_roles": getattr(endpoint, 'required_roles', []),
                    "tags": getattr(endpoint, 'tags', []),
                })
        try:
            if endpoints_to_store:
                self.endpoints_registry.upsert_endpoints(client_id, endpoints_to_store)
                stored = len(endpoints_to_store)
        except Exception:
            pass
        return stored

