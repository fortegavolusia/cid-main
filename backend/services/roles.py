"""Roles and mappings management for CIDS (migrated to database)"""
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json
import logging

from utils.paths import data_path
from services.database import db_service

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
    tenant_id: Optional[str] = None


class RoleMappingsUpdate(BaseModel):
    mappings: List[RoleMapping]


class RolesManager:
    def __init__(self):
        # Keep legacy file paths for backward compatibility during transition
        self.roles_file = data_path("app_roles.json")
        self.mappings_file = data_path("role_mappings_v2.json")
        # Database service will be used for all operations
        self.db = db_service
        
    def _load_roles(self) -> Dict[str, Dict]:
        """Legacy method - kept for compatibility but uses database"""
        logger.info("Loading roles from database")
        return {}
    
    def _load_mappings(self) -> List[Dict]:
        """Legacy method - kept for compatibility but uses database"""
        logger.info("Loading mappings from database")
        return []
    
    def _save_roles(self):
        """Legacy method - operations are now directly saved to database"""
        pass
    
    def _save_mappings(self):
        """Legacy method - operations are now directly saved to database"""
        pass

    def upsert_app_roles(self, app_client_id: str, update: RolesUpdate, updated_by: str) -> Dict:
        """Update or insert roles for an application using database"""
        role_names = set()
        for role in update.roles:
            if role.name in role_names:
                raise ValueError(f"Duplicate role name: {role.name}")
            role_names.add(role.name)
        
        try:
            # Get existing roles for this app
            existing_roles = self.db.get_roles_by_client(app_client_id)
            existing_role_names = {r['role_name'] for r in existing_roles}
            
            # Process each role in the update
            for role in update.roles:
                if role.name in existing_role_names:
                    # Update existing role
                    self.db.update_role(
                        app_client_id, 
                        role.name,
                        {'description': role.description}
                    )
                else:
                    # Create new role
                    role_id = self.db.create_role(
                        app_client_id,
                        role.name,
                        role.description
                    )
                    
                    # Add permissions if any
                    if role.permissions:
                        permissions_data = []
                        for perm in role.permissions:
                            # Parse permission string (format: resource.action.field)
                            parts = perm.split('.')
                            if len(parts) >= 2:
                                resource = parts[0]
                                action = parts[1]
                                fields = parts[2:] if len(parts) > 2 else []
                                permissions_data.append({
                                    'resource': resource,
                                    'action': action,
                                    'fields': fields,
                                    'resource_filters': {}
                                })
                        
                        if permissions_data and role_id:
                            self.db.add_permissions(role_id, permissions_data)
            
            # Delete roles that are not in the update
            new_role_names = {role.name for role in update.roles}
            for existing_role in existing_roles:
                if existing_role['role_name'] not in new_role_names:
                    self.db.delete_role(app_client_id, existing_role['role_name'])
            
            return {
                'app_client_id': app_client_id,
                'roles_count': len(update.roles),
                'updated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to upsert roles: {e}")
            raise

    def get_app_roles(self, app_client_id: str) -> Optional[Dict]:
        """Get roles for an application from database"""
        try:
            roles = self.db.get_roles_by_client(app_client_id)
            if not roles:
                return None
            
            # Format response to match expected structure
            roles_data = []
            for role in roles:
                # Get permissions for this role
                permissions = self.db.get_permissions_by_role(role['role_id'])
                
                # Format permissions as strings
                perm_strings = []
                for perm in permissions:
                    base = f"{perm['resource']}.{perm['action']}"
                    if perm.get('fields'):
                        for field in perm['fields']:
                            perm_strings.append(f"{base}.{field}")
                    else:
                        perm_strings.append(base)
                
                roles_data.append({
                    'name': role['role_name'],
                    'description': role.get('description', ''),
                    'permissions': perm_strings
                })
            
            return {
                'roles': roles_data,
                'updated_at': max(r['updated_at'].isoformat() if r.get('updated_at') else datetime.utcnow().isoformat() 
                                for r in roles) if roles else datetime.utcnow().isoformat(),
                'updated_by': 'system'  # We don't track this in DB yet
            }
        except Exception as e:
            logger.error(f"Failed to get app roles: {e}")
            return None

    def upsert_role_mappings(self, update: RoleMappingsUpdate, updated_by: str) -> Dict:
        """Update role mappings in database"""
        try:
            # Validate all mappings first
            for mapping in update.mappings:
                # Check if app exists
                app = self.db.get_app_by_id(mapping.app_client_id)
                if not app:
                    raise ValueError(f"App {mapping.app_client_id} not found")
                
                # Check if role exists
                role = self.db.get_role(mapping.app_client_id, mapping.role)
                if not role:
                    raise ValueError(f"Role {mapping.role} not found in app {mapping.app_client_id}")
            
            # Update role mappings by updating the ad_groups field in roles table
            for mapping in update.mappings:
                role = self.db.get_role(mapping.app_client_id, mapping.role)
                if role:
                    current_groups = role.get('ad_groups', [])
                    if mapping.azure_group not in current_groups:
                        current_groups.append(mapping.azure_group)
                        self.db.update_role(
                            mapping.app_client_id,
                            mapping.role,
                            {'ad_groups': current_groups}
                        )
            
            return {
                'mappings_count': len(update.mappings),
                'updated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to upsert role mappings: {e}")
            raise

    def get_user_roles(self, user_groups: List[str], tenant_id: Optional[str] = None) -> Dict[str, List[str]]:
        """Get roles for a user based on their AD groups from database"""
        user_roles: Dict[str, List[str]] = {}
        
        try:
            # Get all apps
            apps = self.db.get_all_registered_apps()
            
            for app in apps:
                app_id = app['client_id']
                # Get roles for this app
                roles = self.db.get_roles_by_client(app_id)
                
                for role in roles:
                    # Check if user's AD groups match this role's ad_groups
                    role_groups = role.get('ad_groups', [])
                    if any(group in user_groups for group in role_groups):
                        if app_id not in user_roles:
                            user_roles[app_id] = []
                        if role['role_name'] not in user_roles[app_id]:
                            user_roles[app_id].append(role['role_name'])
            
            return user_roles
        except Exception as e:
            logger.error(f"Failed to get user roles: {e}")
            return {}

    def get_all_mappings(self) -> List[Dict]:
        """Get all role mappings from database"""
        try:
            mappings = []
            apps = self.db.get_all_registered_apps()
            
            for app in apps:
                roles = self.db.get_roles_by_client(app['client_id'])
                for role in roles:
                    for ad_group in role.get('ad_groups', []):
                        mappings.append({
                            'app_client_id': app['client_id'],
                            'azure_group': ad_group,
                            'role': role['role_name'],
                            'created_at': role.get('created_at', datetime.utcnow()).isoformat(),
                            'created_by': 'system'
                        })
            
            return mappings
        except Exception as e:
            logger.error(f"Failed to get all mappings: {e}")
            return []

    def get_role_permissions(self, app_client_id: str, role_name: str) -> List[str]:
        """Get permissions for a specific role from database"""
        try:
            role = self.db.get_role(app_client_id, role_name)
            if not role:
                return []
            
            permissions = self.db.get_permissions_by_role(role['role_id'])
            
            # Format permissions as strings
            perm_strings = []
            for perm in permissions:
                base = f"{perm['resource']}.{perm['action']}"
                if perm.get('fields'):
                    for field in perm['fields']:
                        perm_strings.append(f"{base}.{field}")
                else:
                    perm_strings.append(base)
            
            return perm_strings
        except Exception as e:
            logger.error(f"Failed to get role permissions: {e}")
            return []

