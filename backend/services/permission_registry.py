"""
Permission Registry for Field-Level Access Control (migrated)
"""
from typing import Dict, List, Set, Optional, Tuple, Any
from datetime import datetime
import json
import logging
from collections import defaultdict

from backend.schemas.discovery import PermissionMetadata
from backend.utils.paths import data_path

logger = logging.getLogger(__name__)

# Storage paths
PERMISSIONS_DB = data_path("discovered_permissions.json")
ROLE_PERMISSIONS_DB = data_path("role_permissions.json")
ROLE_METADATA_DB = data_path("role_metadata.json")


class PermissionRegistry:
    """Central registry for all discovered permissions"""

    def __init__(self):
        self.permissions: Dict[str, Dict[str, PermissionMetadata]] = {}
        self.role_permissions: Dict[str, Dict[str, Set[str]]] = {}
        self.role_denied_permissions: Dict[str, Dict[str, Set[str]]] = {}
        self.role_metadata: Dict[str, Dict[str, Dict]] = {}
        self.role_rls_filters: Dict[str, Dict[str, Dict]] = {}
        self._load_registry()

    def _load_registry(self):
        """Load permissions from storage"""
        try:
            if PERMISSIONS_DB.exists():
                with open(PERMISSIONS_DB, 'r') as f:
                    data = json.load(f)
                    for app_id, app_data in data.items():
                        perms = app_data["permissions"] if isinstance(app_data, dict) and "permissions" in app_data else app_data
                        self.permissions[app_id] = {k: PermissionMetadata(**v) for k, v in perms.items()}

            if ROLE_PERMISSIONS_DB.exists():
                with open(ROLE_PERMISSIONS_DB, 'r') as f:
                    data = json.load(f)
                    for app_id, roles in data.items():
                        self.role_permissions[app_id] = {}
                        self.role_denied_permissions[app_id] = {}
                        self.role_rls_filters[app_id] = {}
                        for role, role_data in roles.items():
                            if isinstance(role_data, dict):
                                self.role_permissions[app_id][role] = set(role_data.get('allowed_permissions', []))
                                self.role_denied_permissions[app_id][role] = set(role_data.get('denied_permissions', []))
                                self.role_rls_filters[app_id][role] = role_data.get('rls_filters', {})
                            else:
                                logger.warning(f"Role {role} in app {app_id} has invalid format, initializing as empty")
                                self.role_permissions[app_id][role] = set()
                                self.role_denied_permissions[app_id][role] = set()
                                self.role_rls_filters[app_id][role] = {}

            if ROLE_METADATA_DB.exists():
                with open(ROLE_METADATA_DB, 'r') as f:
                    self.role_metadata = json.load(f)
            else:
                self.role_metadata = {}
        except Exception as e:
            logger.error(f"Error loading permission registry: {e}")
            self.permissions = {}
            self.role_permissions = {}
            self.role_denied_permissions = {}
            self.role_metadata = {}

    def _save_registry(self):
        """Save permissions to storage"""
        try:
            PERMISSIONS_DB.parent.mkdir(parents=True, exist_ok=True)

            existing_data = {}
            if PERMISSIONS_DB.exists():
                with open(PERMISSIONS_DB, 'r') as f:
                    existing_data = json.load(f)

            for app_id, perms in self.permissions.items():
                if app_id not in existing_data:
                    existing_data[app_id] = {}
                existing_data[app_id]["permissions"] = {k: v.dict() for k, v in perms.items()}

            with open(PERMISSIONS_DB, 'w') as f:
                json.dump(existing_data, f, indent=2, default=str)

            role_data = {}
            for app_id, roles in self.role_permissions.items():
                role_data[app_id] = {}
                for role, perms in roles.items():
                    denied_perms = self.role_denied_permissions.get(app_id, {}).get(role, set())
                    role_data[app_id][role] = {
                        'allowed_permissions': list(perms),
                        'denied_permissions': list(denied_perms),
                        'rls_filters': self.role_rls_filters.get(app_id, {}).get(role, {})
                    }
            with open(ROLE_PERMISSIONS_DB, 'w') as f:
                json.dump(role_data, f, indent=2)

            with open(ROLE_METADATA_DB, 'w') as f:
                json.dump(self.role_metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving permission registry: {e}")

    def register_permissions(self, app_id: str, permissions: Dict[str, PermissionMetadata]):
        self.permissions[app_id] = permissions
        self._save_registry()
        logger.info(f"Registered {len(permissions)} permissions for app {app_id}")

    def get_permission(self, app_id: str, permission_key: str) -> Optional[PermissionMetadata]:
        return self.permissions.get(app_id, {}).get(permission_key)

    def get_app_permissions(self, app_id: str) -> Dict[str, PermissionMetadata]:
        return self.permissions.get(app_id, {})

    def create_role_with_rls(self, app_id: str, role_name: str, permissions: Set[str], description: str = None, rls_filters: Dict = None, denied_permissions: Set[str] = None):
        if app_id not in self.role_permissions:
            self.role_permissions[app_id] = {}
        if app_id not in self.role_denied_permissions:
            self.role_denied_permissions[app_id] = {}
        if app_id not in self.role_metadata:
            self.role_metadata[app_id] = {}
        if app_id not in self.role_rls_filters:
            self.role_rls_filters[app_id] = {}

        # Validate and process allowed permissions
        valid_perms = set()
        app_perms = self.permissions.get(app_id, {})
        for perm in permissions:
            if perm in app_perms:
                valid_perms.add(perm)
            elif perm.endswith(".*"):
                prefix = perm[:-2]
                for p in app_perms:
                    if p.startswith(prefix):
                        valid_perms.add(p)
            else:
                logger.warning(f"Permission {perm} not found for app {app_id}")

        # Validate and process denied permissions
        valid_denied_perms = set()
        if denied_permissions:
            for perm in denied_permissions:
                if perm in app_perms:
                    valid_denied_perms.add(perm)
                elif perm.endswith(".*"):
                    prefix = perm[:-2]
                    for p in app_perms:
                        if p.startswith(prefix):
                            valid_denied_perms.add(p)
                else:
                    logger.warning(f"Denied permission {perm} not found for app {app_id}")

        self.role_permissions[app_id][role_name] = valid_perms
        self.role_denied_permissions[app_id][role_name] = valid_denied_perms
        self.role_rls_filters[app_id][role_name] = rls_filters or {}

        if role_name not in self.role_metadata[app_id]:
            self.role_metadata[app_id][role_name] = {
                'created_at': datetime.now().isoformat(),
                'description': description
            }
        else:
            self.role_metadata[app_id][role_name]['updated_at'] = datetime.now().isoformat()
            if description is not None:
                self.role_metadata[app_id][role_name]['description'] = description

        self._save_registry()
        logger.info(f"Created/updated role {role_name} with {len(valid_perms)} allowed, {len(valid_denied_perms)} denied permissions and {len(rls_filters) if rls_filters else 0} RLS filters for app {app_id}")
        return valid_perms, valid_denied_perms

    # Legacy alias
    def create_role(self, app_id: str, role_name: str, permissions: Set[str], description: str = None):
        valid_perms, _ = self.create_role_with_rls(app_id, role_name, permissions, description, None)
        return valid_perms

    def update_role_with_rls(self, app_id: str, role_name: str, permissions: Set[str], description: str = None, rls_filters: Dict = None, denied_permissions: Set[str] = None):
        return self.create_role_with_rls(app_id, role_name, permissions, description, rls_filters, denied_permissions)

    def get_role_permissions(self, app_id: str, role_name: str) -> Set[str]:
        return self.role_permissions.get(app_id, {}).get(role_name, set())

    def get_role_denied_permissions(self, app_id: str, role_name: str) -> Set[str]:
        return self.role_denied_permissions.get(app_id, {}).get(role_name, set())

    def get_role_rls_filters(self, app_id: str, role_name: str) -> Dict:
        return self.role_rls_filters.get(app_id, {}).get(role_name, {})

    def get_role_full_config(self, app_id: str, role_name: str) -> Dict:
        return {
            'allowed_permissions': list(self.get_role_permissions(app_id, role_name)),
            'denied_permissions': list(self.get_role_denied_permissions(app_id, role_name)),
            'rls_filters': self.get_role_rls_filters(app_id, role_name),
            'metadata': self.get_role_metadata(app_id, role_name)
        }

    def get_role_metadata(self, app_id: str, role_name: str) -> Dict:
        return self.role_metadata.get(app_id, {}).get(role_name, {})

    def get_user_permissions(self, app_id: str, user_roles: List[str]) -> Set[str]:
        permissions = set()
        app_roles = self.role_permissions.get(app_id, {})
        for role in user_roles:
            if role in app_roles:
                permissions.update(app_roles[role])
        return permissions

    def check_permission(self, app_id: str, user_roles: List[str], permission_key: str) -> bool:
        user_perms = self.get_user_permissions(app_id, user_roles)
        if permission_key in user_perms:
            return True
        parts = permission_key.split('.')
        for i in range(len(parts)):
            wildcard = '.'.join(parts[:i+1]) + '.*'
            if wildcard in user_perms:
                return True
        return False

    def get_permission_hierarchy(self, app_id: str) -> Dict[str, Dict[str, List[str]]]:
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
        results = []
        apps_to_search = [app_id] if app_id else list(self.permissions.keys())
        for aid in apps_to_search:
            for perm_key, perm_meta in self.permissions.get(aid, {}).items():
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
        sensitive = {"sensitive": [], "pii": [], "phi": []}
        for perm in self.permissions.get(app_id, {}).values():
            if perm.sensitive:
                sensitive["sensitive"].append(perm)
            if perm.pii:
                sensitive["pii"].append(perm)
            if perm.phi:
                sensitive["phi"].append(perm)
        return sensitive

    def export_role_template(self, app_id: str) -> Dict[str, Any]:
        return {
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
                    ][:10]
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
                    "suggested_permissions": ["*"]
                }
            }
        }

