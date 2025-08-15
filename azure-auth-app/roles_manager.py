"""Roles and mappings management for CIDS"""
from typing import Dict, List, Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Role(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    permissions: Optional[List[str]] = []

class RolesUpdate(BaseModel):
    roles: List[Role]

class RoleMapping(BaseModel):
    azure_group: str
    app_client_id: str
    role: str
    tenant_id: Optional[str] = None  # For tenant-specific mappings

class RoleMappingsUpdate(BaseModel):
    mappings: List[RoleMapping]

class RolesManager:
    """Manages roles and Azure AD group mappings"""
    
    def __init__(self, data_dir: str = "app_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.roles_file = self.data_dir / "app_roles.json"
        self.mappings_file = self.data_dir / "role_mappings_v2.json"
        self.roles: Dict[str, Dict] = self._load_roles()
        self.mappings: List[Dict] = self._load_mappings()
    
    def _load_roles(self) -> Dict[str, Dict]:
        """Load roles from persistent storage"""
        if self.roles_file.exists():
            try:
                with open(self.roles_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading roles: {e}")
                return {}
        return {}
    
    def _load_mappings(self) -> List[Dict]:
        """Load role mappings from persistent storage"""
        if self.mappings_file.exists():
            try:
                with open(self.mappings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading mappings: {e}")
                return []
        return []
    
    def _save_roles(self):
        """Save roles to persistent storage"""
        with open(self.roles_file, 'w') as f:
            json.dump(self.roles, f, indent=2)
    
    def _save_mappings(self):
        """Save mappings to persistent storage"""
        with open(self.mappings_file, 'w') as f:
            json.dump(self.mappings, f, indent=2)
    
    def upsert_app_roles(self, app_client_id: str, update: RolesUpdate, updated_by: str) -> Dict:
        """Update roles for an app"""
        # Validate role names are unique within the app
        role_names = set()
        for role in update.roles:
            if role.name in role_names:
                raise ValueError(f"Duplicate role name: {role.name}")
            role_names.add(role.name)
        
        # Store roles
        self.roles[app_client_id] = {
            'roles': [role.dict() for role in update.roles],
            'updated_at': datetime.utcnow().isoformat(),
            'updated_by': updated_by
        }
        
        self._save_roles()
        
        return {
            'app_client_id': app_client_id,
            'roles_count': len(update.roles),
            'updated_at': self.roles[app_client_id]['updated_at']
        }
    
    def get_app_roles(self, app_client_id: str) -> Optional[Dict]:
        """Get roles for a specific app"""
        return self.roles.get(app_client_id)
    
    def upsert_role_mappings(self, update: RoleMappingsUpdate, updated_by: str) -> Dict:
        """Update role mappings"""
        # Validate that referenced apps and roles exist
        for mapping in update.mappings:
            if mapping.app_client_id not in self.roles:
                raise ValueError(f"App {mapping.app_client_id} not found")
            
            app_roles = [r['name'] for r in self.roles[mapping.app_client_id]['roles']]
            if mapping.role not in app_roles:
                raise ValueError(
                    f"Role {mapping.role} not found in app {mapping.app_client_id}"
                )
        
        # Clear existing mappings and add new ones
        self.mappings = []
        for mapping in update.mappings:
            self.mappings.append({
                **mapping.dict(),
                'created_at': datetime.utcnow().isoformat(),
                'created_by': updated_by
            })
        
        self._save_mappings()
        
        return {
            'mappings_count': len(self.mappings),
            'updated_at': datetime.utcnow().isoformat()
        }
    
    def get_user_roles(self, user_groups: List[str], tenant_id: Optional[str] = None) -> Dict[str, List[str]]:
        """Get roles for a user based on their Azure AD groups"""
        user_roles = {}
        
        for mapping in self.mappings:
            # Check if user has the required Azure AD group
            if mapping['azure_group'] not in user_groups:
                continue
            
            # Check tenant match if specified
            if mapping.get('tenant_id') and mapping['tenant_id'] != tenant_id:
                continue
            
            # Add role to user's roles for this app
            app_id = mapping['app_client_id']
            if app_id not in user_roles:
                user_roles[app_id] = []
            
            if mapping['role'] not in user_roles[app_id]:
                user_roles[app_id].append(mapping['role'])
        
        return user_roles
    
    def get_all_mappings(self) -> List[Dict]:
        """Get all role mappings"""
        return self.mappings
    
    def get_role_permissions(self, app_client_id: str, role_name: str) -> List[str]:
        """Get permissions for a specific role"""
        app_roles = self.roles.get(app_client_id, {}).get('roles', [])
        for role in app_roles:
            if role['name'] == role_name:
                return role.get('permissions', [])
        return []