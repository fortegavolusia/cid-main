"""
Permission Registry for Field-Level Access Control

This module manages the storage and retrieval of granular permissions
discovered from applications.
"""
from typing import Dict, List, Set, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import json
import logging
from collections import defaultdict

from discovery_models import PermissionMetadata, generate_permission_key

logger = logging.getLogger(__name__)

# Storage paths
PERMISSIONS_DB = Path("app_data/permissions_registry.json")
ROLE_PERMISSIONS_DB = Path("app_data/role_permissions.json")


class PermissionRegistry:
    """Central registry for all discovered permissions"""
    
    def __init__(self):
        self.permissions: Dict[str, Dict[str, PermissionMetadata]] = {}  # app_id -> permission_key -> metadata
        self.role_permissions: Dict[str, Dict[str, Set[str]]] = {}  # app_id -> role_name -> permission_keys
        self._load_registry()
    
    def _load_registry(self):
        """Load permissions from storage"""
        try:
            # Load permissions
            if PERMISSIONS_DB.exists():
                with open(PERMISSIONS_DB, 'r') as f:
                    data = json.load(f)
                    for app_id, perms in data.items():
                        self.permissions[app_id] = {
                            k: PermissionMetadata(**v) for k, v in perms.items()
                        }
            
            # Load role permissions
            if ROLE_PERMISSIONS_DB.exists():
                with open(ROLE_PERMISSIONS_DB, 'r') as f:
                    data = json.load(f)
                    for app_id, roles in data.items():
                        self.role_permissions[app_id] = {
                            role: set(perms) for role, perms in roles.items()
                        }
                        
        except Exception as e:
            logger.error(f"Error loading permission registry: {e}")
            self.permissions = {}
            self.role_permissions = {}
    
    def _save_registry(self):
        """Save permissions to storage"""
        try:
            # Ensure directory exists
            PERMISSIONS_DB.parent.mkdir(exist_ok=True)
            
            # Save permissions
            perm_data = {}
            for app_id, perms in self.permissions.items():
                perm_data[app_id] = {
                    k: v.dict() for k, v in perms.items()
                }
            
            with open(PERMISSIONS_DB, 'w') as f:
                json.dump(perm_data, f, indent=2, default=str)
            
            # Save role permissions
            role_data = {}
            for app_id, roles in self.role_permissions.items():
                role_data[app_id] = {
                    role: list(perms) for role, perms in roles.items()
                }
            
            with open(ROLE_PERMISSIONS_DB, 'w') as f:
                json.dump(role_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving permission registry: {e}")
    
    def register_permissions(self, app_id: str, permissions: Dict[str, PermissionMetadata]):
        """Register discovered permissions for an app"""
        self.permissions[app_id] = permissions
        self._save_registry()
        logger.info(f"Registered {len(permissions)} permissions for app {app_id}")
    
    def get_permission(self, app_id: str, permission_key: str) -> Optional[PermissionMetadata]:
        """Get a specific permission metadata"""
        return self.permissions.get(app_id, {}).get(permission_key)
    
    def get_app_permissions(self, app_id: str) -> Dict[str, PermissionMetadata]:
        """Get all permissions for an app"""
        return self.permissions.get(app_id, {})
    
    def create_role(self, app_id: str, role_name: str, permissions: Set[str]):
        """Create or update a role with specific permissions"""
        if app_id not in self.role_permissions:
            self.role_permissions[app_id] = {}
        
        # Validate permissions exist
        valid_perms = set()
        app_perms = self.permissions.get(app_id, {})
        
        for perm in permissions:
            if perm in app_perms:
                valid_perms.add(perm)
            elif perm.endswith(".*"):
                # Handle wildcard permissions
                prefix = perm[:-2]
                for p in app_perms:
                    if p.startswith(prefix):
                        valid_perms.add(p)
            else:
                logger.warning(f"Permission {perm} not found for app {app_id}")
        
        self.role_permissions[app_id][role_name] = valid_perms
        self._save_registry()
        
        logger.info(f"Created role {role_name} with {len(valid_perms)} permissions for app {app_id}")
        return valid_perms
    
    def get_role_permissions(self, app_id: str, role_name: str) -> Set[str]:
        """Get permissions for a specific role"""
        return self.role_permissions.get(app_id, {}).get(role_name, set())
    
    def get_user_permissions(self, app_id: str, user_roles: List[str]) -> Set[str]:
        """Get all permissions for a user based on their roles"""
        permissions = set()
        app_roles = self.role_permissions.get(app_id, {})
        
        for role in user_roles:
            if role in app_roles:
                permissions.update(app_roles[role])
        
        return permissions
    
    def check_permission(self, app_id: str, user_roles: List[str], permission_key: str) -> bool:
        """Check if user has a specific permission"""
        user_perms = self.get_user_permissions(app_id, user_roles)
        
        # Direct permission check
        if permission_key in user_perms:
            return True
        
        # Check wildcard permissions
        # e.g., users.read.* grants users.read.email
        parts = permission_key.split('.')
        for i in range(len(parts)):
            wildcard = '.'.join(parts[:i+1]) + '.*'
            if wildcard in user_perms:
                return True
        
        return False
    
    def get_permission_hierarchy(self, app_id: str) -> Dict[str, Dict[str, List[str]]]:
        """Get permissions organized by resource and action"""
        hierarchy = defaultdict(lambda: defaultdict(list))
        
        for perm_key, perm_meta in self.permissions.get(app_id, {}).items():
            hierarchy[perm_meta.resource][perm_meta.action].append({
                "field": perm_meta.field_path,
                "key": perm_key,
                "sensitive": perm_meta.sensitive,
                "pii": perm_meta.pii,
                "phi": perm_meta.phi,
                "description": perm_meta.description
            })
        
        return dict(hierarchy)
    
    def search_permissions(
        self,
        app_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        field_contains: Optional[str] = None,
        sensitive_only: bool = False
    ) -> List[Tuple[str, PermissionMetadata]]:
        """Search permissions with filters"""
        results = []
        
        # Determine which apps to search
        apps_to_search = [app_id] if app_id else list(self.permissions.keys())
        
        for aid in apps_to_search:
            for perm_key, perm_meta in self.permissions.get(aid, {}).items():
                # Apply filters
                if resource and perm_meta.resource != resource:
                    continue
                if action and perm_meta.action != action:
                    continue
                if field_contains and field_contains not in perm_meta.field_path:
                    continue
                if sensitive_only and not (perm_meta.sensitive or perm_meta.pii or perm_meta.phi):
                    continue
                
                results.append((aid, perm_meta))
        
        return results
    
    def get_sensitive_permissions(self, app_id: str) -> Dict[str, List[PermissionMetadata]]:
        """Get all sensitive permissions grouped by type"""
        sensitive = {
            "sensitive": [],
            "pii": [],
            "phi": []
        }
        
        for perm in self.permissions.get(app_id, {}).values():
            if perm.sensitive:
                sensitive["sensitive"].append(perm)
            if perm.pii:
                sensitive["pii"].append(perm)
            if perm.phi:
                sensitive["phi"].append(perm)
        
        return sensitive
    
    def export_role_template(self, app_id: str) -> Dict[str, Any]:
        """Export a template for role creation with all available permissions"""
        template = {
            "app_id": app_id,
            "permissions_by_resource": self.get_permission_hierarchy(app_id),
            "sensitive_permissions": self.get_sensitive_permissions(app_id),
            "total_permissions": len(self.permissions.get(app_id, {})),
            "example_roles": {
                "viewer": {
                    "description": "Read-only access to non-sensitive data",
                    "suggested_permissions": [
                        p for p, m in self.permissions.get(app_id, {}).items()
                        if m.action == "read" and not (m.sensitive or m.pii or m.phi)
                    ][:10]  # First 10 as example
                },
                "editor": {
                    "description": "Read and write access to non-sensitive data",
                    "suggested_permissions": [
                        p for p, m in self.permissions.get(app_id, {}).items()
                        if m.action in ["read", "write"] and not (m.sensitive or m.pii or m.phi)
                    ][:10]
                },
                "admin": {
                    "description": "Full access including sensitive data",
                    "suggested_permissions": ["*"]  # Full access
                }
            }
        }
        
        return template