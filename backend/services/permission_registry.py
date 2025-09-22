"""
Permission Registry for Field-Level Access Control (migrated)
"""
from typing import Dict, List, Set, Optional, Tuple, Any
from datetime import datetime
import json
import logging
from collections import defaultdict
import httpx
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor, Json

from schemas.discovery import PermissionMetadata
from utils.paths import data_path

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
        self.db_conn = None
        self.db_cursor = None
        self._connect_db()
        self._load_registry()
    
    def _connect_db(self):
        """Connect to the database"""
        try:
            self.db_conn = psycopg2.connect(
                host='supabase_db_mi-proyecto-supabase',
                port=5432,
                database='postgres',
                user='postgres',
                password='postgres'
            )
            self.db_cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Connected to database for role metadata")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self.db_conn = None
            self.db_cursor = None

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

            # Load role metadata from database
            if self.db_cursor:
                try:
                    self.db_cursor.execute("""
                        SELECT client_id, role_name, description, a2a_only, is_active, created_at
                        FROM cids.role_metadata
                    """)
                    db_roles = self.db_cursor.fetchall()
                    
                    for role in db_roles:
                        if role['client_id'] not in self.role_metadata:
                            self.role_metadata[role['client_id']] = {}
                        self.role_metadata[role['client_id']][role['role_name']] = {
                            'description': role['description'],
                            'a2a_only': role['a2a_only'],
                            'is_active': role.get('is_active', True),
                            'created_at': role['created_at'].isoformat() if role['created_at'] else None
                        }
                        logger.debug(f"Loaded role {role['role_name']} with is_active={role.get('is_active')}")
                    logger.info(f"Loaded {len(db_roles)} roles from database")
                except Exception as e:
                    logger.error(f"Error loading role metadata from database: {e}")
                    # Fallback to JSON file
                    if ROLE_METADATA_DB.exists():
                        with open(ROLE_METADATA_DB, 'r') as f:
                            self.role_metadata = json.load(f)
            elif ROLE_METADATA_DB.exists():
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
        # MIGRADO A BASE DE DATOS - YA NO SE USA JSON
        # try:
        #     PERMISSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
        #
        #     existing_data = {}
        #     if PERMISSIONS_DB.exists():
        #         with open(PERMISSIONS_DB, 'r') as f:
        #             existing_data = json.load(f)
        #
        #     for app_id, perms in self.permissions.items():
        #         if app_id not in existing_data:
        #             existing_data[app_id] = {}
        #         existing_data[app_id]["permissions"] = {k: v.dict() for k, v in perms.items()}
        #
        #     with open(PERMISSIONS_DB, 'w') as f:
        #         json.dump(existing_data, f, indent=2, default=str)
        #
        #     role_data = {}
        #     for app_id, roles in self.role_permissions.items():
        #         role_data[app_id] = {}
        #         for role, perms in roles.items():
        #             denied_perms = self.role_denied_permissions.get(app_id, {}).get(role, set())
        #             role_data[app_id][role] = {
        #                 'allowed_permissions': list(perms),
        #                 'denied_permissions': list(denied_perms),
        #                 'rls_filters': self.role_rls_filters.get(app_id, {}).get(role, {})
        #             }
        #     with open(ROLE_PERMISSIONS_DB, 'w') as f:
        #         json.dump(role_data, f, indent=2)
        #
        #     # Don't save role_metadata to JSON anymore - it's in the database
        #     # with open(ROLE_METADATA_DB, 'w') as f:
        #     #     json.dump(self.role_metadata, f, indent=2, default=str)
        # except Exception as e:
        #     logger.error(f"Error saving permission registry: {e}")
        pass  # Todo está en la base de datos ahora

    def register_permissions(self, app_id: str, permissions: Dict[str, PermissionMetadata]):
        self.permissions[app_id] = permissions
        # NO GUARDAR EN JSON
        # self._save_registry()
        logger.info(f"Registered {len(permissions)} permissions for app {app_id}")

    def get_permission(self, app_id: str, permission_key: str) -> Optional[PermissionMetadata]:
        return self.permissions.get(app_id, {}).get(permission_key)

    def get_app_permissions(self, app_id: str) -> Dict[str, PermissionMetadata]:
        """Get discovered permissions from database"""
        try:
            # Connect to database and get discovered permissions
            self.db_cursor.execute("""
                SELECT permission_id, resource, action, available_fields
                FROM cids.discovered_permissions
                WHERE client_id = %s AND is_active = true
            """, (app_id,))
            
            permissions = {}
            results = self.db_cursor.fetchall()
            
            if results:
                for row in results:
                    # Create PermissionMetadata object for each permission
                    fields = row.get('available_fields', []) if row.get('available_fields') else []
                    if isinstance(fields, str):
                        import json
                        try:
                            fields = json.loads(fields)
                        except:
                            fields = []
                    
                    # For each field, create a permission entry
                    if fields:
                        for field in fields:
                            perm_key = f"{row['resource']}:{row['action']}:{field}"
                            permissions[perm_key] = type('PermissionMetadata', (), {
                                'permission_key': perm_key,
                                'resource': row['resource'],
                                'action': row['action'],
                                'field_path': field,
                                'description': '',
                                'sensitive': False,
                                'pii': False,
                                'phi': False
                            })()
                    else:
                        # No specific fields, use wildcard
                        perm_key = f"{row['resource']}:{row['action']}:*"
                        permissions[perm_key] = type('PermissionMetadata', (), {
                            'permission_key': perm_key,
                            'resource': row['resource'],
                            'action': row['action'],
                            'field_path': '*',
                            'description': row.get('description', ''),
                            'sensitive': row.get('is_sensitive', False),
                            'pii': row.get('is_pii', False),
                            'phi': row.get('is_phi', False)
                        })()
            
            return permissions
        except Exception as e:
            logger.error(f"Error getting app permissions from database: {e}")
            # Fallback to memory if DB fails
            return self.permissions.get(app_id, {})

    async def _get_role_id_from_uuid_service(self) -> str:
        """Get a role ID from UUID service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://uuid-service-dev:8002/generate",
                    json={"prefix": "rol"}
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("id")
                else:
                    logger.error(f"Failed to get role ID from UUID service: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error getting role ID from UUID service: {e}")
            return None
    
    def _delete_role_from_db(self, client_id: str, role_name: str, user_email: str = None, user_id: str = None):
        """Delete role from database"""
        if not self.db_cursor:
            logger.error("No database connection for deleting role")
            return False
        
        try:
            # Get per_id before deletion
            self.db_cursor.execute("""
                SELECT per_id FROM cids.role_permissions 
                WHERE client_id = %s AND role_name = %s
            """, (client_id, role_name))
            result = self.db_cursor.fetchone()
            per_id = result['per_id'] if result else None
            
            # Delete from role_permissions table
            self.db_cursor.execute("""
                DELETE FROM cids.role_permissions 
                WHERE client_id = %s AND role_name = %s
            """, (client_id, role_name))
            
            # Delete from app_role_mappings table
            self.db_cursor.execute("""
                DELETE FROM cids.app_role_mappings
                WHERE client_id = %s AND role_name = %s
            """, (client_id, role_name))

            # Delete from rls_filters table
            self.db_cursor.execute("""
                DELETE FROM cids.rls_filters
                WHERE client_id = %s AND role_name = %s
            """, (client_id, role_name))
            logger.info(f"Deleted RLS filters for role {role_name} from cids.rls_filters")

            # Delete role from role_metadata table
            self.db_cursor.execute("""
                DELETE FROM cids.role_metadata 
                WHERE client_id = %s AND role_name = %s
            """, (client_id, role_name))
            
            # Log activity for permission deletion
            if per_id:
                self.db_cursor.execute("""
                    INSERT INTO cids.activity_log (activity_type, entity_type, entity_id, entity_name, user_email, user_id, details, status, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    'permission.delete',
                    'permission',
                    per_id,
                    f"{client_id}/{role_name}",
                    user_email or 'system',
                    user_id or 'system',
                    Json({
                        'client_id': client_id,
                        'role_name': role_name,
                        'deleted_by': user_email or 'system',
                        'action': 'Permission and role permanently deleted'
                    }),
                    'success'
                ))
            
            self.db_conn.commit()
            logger.info(f"Deleted role {role_name} and permissions from database")
            return True
        except Exception as e:
            logger.error(f"Error deleting role from database: {e}")
            if self.db_conn:
                self.db_conn.rollback()
            return False
    
    async def _get_per_id_from_uuid_service(self) -> str:
        """Get a permission ID from UUID service"""
        try:
            with httpx.Client() as client:
                response = client.post(
                    "http://uuid-service-dev:8002/generate",
                    json={"prefix": "PER"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("id")
                else:
                    logger.error(f"Failed to get per_id from UUID service: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error getting per_id from UUID service: {e}")
            return None

    def _save_role_to_db(self, role_id: str, client_id: str, role_name: str, description: str = None, a2a_only: bool = False, user_email: str = None, user_id: str = None):
        """Save role metadata to database"""
        if not self.db_cursor:
            logger.error("No database connection for saving role metadata")
            return False
        
        try:
            # Check if role already exists
            self.db_cursor.execute("""
                SELECT role_id FROM cids.role_metadata 
                WHERE client_id = %s AND role_name = %s
            """, (client_id, role_name))
            
            existing = self.db_cursor.fetchone()
            
            if existing:
                # Update existing role
                self.db_cursor.execute("""
                    UPDATE cids.role_metadata 
                    SET description = %s, a2a_only = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE client_id = %s AND role_name = %s
                """, (description, a2a_only, client_id, role_name))
                
                # Check if this role has permissions already
                self.db_cursor.execute("""
                    SELECT 1 FROM cids.role_permissions 
                    WHERE client_id = %s AND role_name = %s
                """, (client_id, role_name))
                has_permissions = self.db_cursor.fetchone() is not None
                
                # Generate activity_id for logging
                activity_id = f"log_{role_id.replace('rol_', '')}" if role_id else None
                
                # Log activity - use role.create if this is first time setting permissions
                activity_type = 'role.update' if has_permissions else 'role.create'
                self.db_cursor.execute("""
                    INSERT INTO cids.activity_log (activity_type, entity_type, entity_id, entity_name, 
                                                  user_email, user_id, details, status, activity_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    activity_type,
                    'role', 
                    client_id,  # entity_id es el app client_id
                    role_name,
                    user_email,
                    user_id,
                    Json({'role_id': existing['role_id'] if existing else role_id, 'description': description, 'a2a_only': a2a_only}),
                    'success',
                    activity_id
                ))
            else:
                # Insert new role
                self.db_cursor.execute("""
                    INSERT INTO cids.role_metadata (role_id, client_id, role_name, description, a2a_only)
                    VALUES (%s, %s, %s, %s, %s)
                """, (role_id, client_id, role_name, description, a2a_only))
                
                # Generate activity_id for logging
                activity_id = f"log_{role_id.replace('rol_', '')}" if role_id else None
                
                # Log activity for role creation
                self.db_cursor.execute("""
                    INSERT INTO cids.activity_log (activity_type, entity_type, entity_id, entity_name, 
                                                  user_email, user_id, details, status, activity_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    'role.create',
                    'role',
                    client_id,  # entity_id es el app client_id
                    role_name,
                    user_email,
                    user_id,
                    Json({'role_id': role_id, 'description': description, 'a2a_only': a2a_only}),
                    'success',
                    activity_id
                ))
            
            self.db_conn.commit()
            logger.info(f"Saved role {role_name} to database with ID {role_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving role to database: {e}")
            if self.db_conn:
                self.db_conn.rollback()
            return False

    def create_role_with_rls(self, app_id: str, role_name: str, permissions: Set[str], description: str = None, rls_filters: Dict = None, denied_permissions: Set[str] = None, user_email: str = None, user_id: str = None, a2a_only: bool = False):
        logger.info(f"=== CREATE_ROLE_WITH_RLS CALLED ===")
        logger.info(f"app_id: {app_id}, role_name: {role_name}")
        logger.info(f"permissions received: {permissions}")
        logger.info(f"permissions type: {type(permissions)}")
        
        if app_id not in self.role_permissions:
            self.role_permissions[app_id] = {}
        if app_id not in self.role_denied_permissions:
            self.role_denied_permissions[app_id] = {}
        if app_id not in self.role_metadata:
            self.role_metadata[app_id] = {}
        if app_id not in self.role_rls_filters:
            self.role_rls_filters[app_id] = {}

        # Validate and process allowed permissions with hybrid model support
        valid_perms = set()
        app_perms = self.permissions.get(app_id, {})
        logger.info(f"Available app permissions count: {len(app_perms)}")
        
        for perm in permissions:
            # Handle different permission formats
            # Format 1: resource.action (base)
            # Format 2: resource.action.category (pii, sensitive, financial, phi)
            # Format 3: resource.action.fieldname (field-specific)
            # Format 4: resource:action:field (frontend format)
            
            # Convert frontend format (resource:action:field) to backend format
            if ':' in perm:
                parts = perm.split(':')
                if len(parts) == 2:
                    # resource:action -> resource.action
                    perm = f"{parts[0]}.{parts[1]}"
                elif len(parts) == 3:
                    # resource:action:field -> resource.action.field
                    perm = f"{parts[0]}.{parts[1]}.{parts[2]}"
                logger.info(f"Converted frontend permission format to: {perm}")
            
            logger.info(f"  Checking permission: {perm}")
            
            # Check if permission exists
            if perm in app_perms:
                logger.info(f"    ✓ Found exact match in app_perms")
                valid_perms.add(perm)
            elif perm.endswith(".*"):
                # Wildcard permission
                prefix = perm[:-2]
                logger.info(f"    Checking wildcard with prefix: {prefix}")
                for p in app_perms:
                    if p.startswith(prefix):
                        valid_perms.add(p)
                        logger.info(f"    ✓ Added wildcard match: {p}")
            else:
                # Try to validate as category or field permission
                parts = perm.split('.')
                logger.info(f"    Parts: {parts}")
                if len(parts) >= 2:
                    base_perm = f"{parts[0]}.{parts[1]}"
                    logger.info(f"    Looking for base permission: {base_perm}")
                    if base_perm in app_perms:
                        # Base permission exists, accept the granular version
                        valid_perms.add(perm)
                        logger.info(f"    ✓ Accepting granular permission {perm} based on base {base_perm}")
                    else:
                        # For category-based permissions, we should accept them even if base doesn't exist
                        # because they come from discovered_permissions table
                        if len(parts) == 3 and parts[2] in ['base', 'pii', 'phi', 'financial', 'sensitive', 'wildcard']:
                            logger.info(f"    ✓ Accepting category-based permission: {perm}")
                            valid_perms.add(perm)
                        else:
                            logger.warning(f"    ✗ Permission {perm} not found for app {app_id}")
                else:
                    logger.warning(f"    ✗ Invalid permission format: {perm}")

        # Validate and process denied permissions with hybrid model support
        valid_denied_perms = set()
        if denied_permissions:
            for perm in denied_permissions:
                # Convert frontend format (resource:action:field) to backend format
                if ':' in perm:
                    parts = perm.split(':')
                    if len(parts) == 2:
                        perm = f"{parts[0]}.{parts[1]}"
                    elif len(parts) == 3:
                        perm = f"{parts[0]}.{parts[1]}.{parts[2]}"
                    logger.info(f"Converted denied permission format to: {perm}")
                
                # Check if permission exists
                if perm in app_perms:
                    valid_denied_perms.add(perm)
                elif perm.endswith(".*"):
                    prefix = perm[:-2]
                    for p in app_perms:
                        if p.startswith(prefix):
                            valid_denied_perms.add(p)
                else:
                    # Try to validate as category or field permission
                    parts = perm.split('.')
                    if len(parts) >= 2:
                        base_perm = f"{parts[0]}.{parts[1]}"
                        if base_perm in app_perms:
                            valid_denied_perms.add(perm)
                            logger.info(f"Accepting granular denied permission {perm} based on base {base_perm}")
                        else:
                            logger.warning(f"Denied permission {perm} not found for app {app_id}")
                    else:
                        logger.warning(f"Invalid denied permission format: {perm}")

        self.role_permissions[app_id][role_name] = valid_perms
        self.role_denied_permissions[app_id][role_name] = valid_denied_perms
        self.role_rls_filters[app_id][role_name] = rls_filters or {}

        # Get role_id from UUID service for role_metadata
        role_id = None
        try:
            with httpx.Client() as client:
                response = client.post(
                    "http://uuid-service-dev:8002/generate",
                    json={"prefix": "rol", "type": "role"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    role_id = response.json().get("id")
                    logger.info(f"Got role_id from UUID service: {role_id}")
                else:
                    logger.error(f"Failed to get role_id from UUID service: {response.status_code}")
        except Exception as e:
            logger.error(f"Error getting role_id from UUID service: {e}")
        
        # Get per_id from UUID service for permissions (if needed)
        per_id = None
        if valid_perms or valid_denied_perms or rls_filters:
            try:
                with httpx.Client() as client:
                    response = client.post(
                        "http://uuid-service-dev:8002/generate",
                        json={"prefix": "PER"},
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        per_id = response.json().get("id")
                        logger.info(f"Got per_id from UUID service: {per_id}")
                    else:
                        logger.error(f"Failed to get per_id from UUID service: {response.status_code}")
            except Exception as e:
                logger.error(f"Error getting per_id from UUID service: {e}")
        
        # Save to database with role_id and per_id (generate fallbacks if not available)
        if self.db_cursor:
            # Generate a fallback role_id if UUID service failed
            if not role_id:
                import uuid
                role_id = f"rol_{uuid.uuid4().hex[:16]}"
                logger.warning(f"UUID service unavailable, using fallback role_id: {role_id}")
            
            # Generate a fallback per_id if UUID service failed and we have permissions
            if (valid_perms or valid_denied_perms or rls_filters) and not per_id:
                import uuid
                per_id = f"PER_{uuid.uuid4().hex[:16]}"
                logger.warning(f"UUID service unavailable, using fallback per_id: {per_id}")
            
            try:
                # First check if role name already exists
                self.db_cursor.execute("""
                    SELECT role_id FROM cids.role_metadata 
                    WHERE client_id = %s AND role_name = %s
                """, (app_id, role_name))
                existing_role = self.db_cursor.fetchone()
                
                if existing_role:
                    # Role already exists - we're updating permissions only
                    logger.info(f"Role {role_name} already exists for app {app_id}, updating permissions only")
                    role_id = existing_role['role_id']
                    
                    # Update role metadata if description changed
                    if description is not None:
                        self.db_cursor.execute("""
                            UPDATE cids.role_metadata 
                            SET description = %s, updated_at = NOW()
                            WHERE client_id = %s AND role_name = %s
                        """, (description, app_id, role_name))
                        logger.info(f"Updated role description in role_metadata")
                else:
                    # Insert new role - First always insert into role_metadata
                    logger.info(f"=== INSERTING INTO role_metadata ===")
                    logger.info(f"  role_id: {role_id}")
                    logger.info(f"  client_id: {app_id}")
                    logger.info(f"  role_name: {role_name}")
                    logger.info(f"  description: {description}")
                    logger.info(f"  a2a_only: {a2a_only}")
                    
                    self.db_cursor.execute("""
                        INSERT INTO cids.role_metadata 
                        (role_id, client_id, role_name, description, a2a_only, is_active, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        role_id,
                        app_id,
                        role_name,
                        description,
                        a2a_only,
                        True
                    ))
                    logger.info(f"Inserted role into role_metadata with role_id: {role_id}")
                    
                    # Log activity for role creation
                    self.db_cursor.execute("""
                        INSERT INTO cids.activity_log 
                        (activity_type, entity_type, entity_id, entity_name, user_email, user_id, details, status, timestamp, activity_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                    """, (
                        'role.create',
                        'role',
                        role_id,
                        f"{app_id}/{role_name}",
                        user_email or 'system',
                        user_id or 'system',
                        Json({
                            'client_id': app_id,
                            'role_name': role_name,
                            'description': description,
                            'a2a_only': a2a_only
                        }),
                        'success',
                        role_id  # activity_id = role_id
                    ))
                    logger.info(f"Logged role creation in activity_log")
                
                # Handle permissions - check if they exist first
                if valid_perms or valid_denied_perms or rls_filters:
                    # Check if role_permissions entry exists
                    self.db_cursor.execute("""
                        SELECT per_id FROM cids.role_permissions 
                        WHERE client_id = %s AND role_name = %s
                    """, (app_id, role_name))
                    existing_perms = self.db_cursor.fetchone()
                    
                    if existing_perms:
                        # UPDATE existing permissions
                        logger.info(f"Updating existing permissions for role {role_name}")
                        self.db_cursor.execute("""
                            UPDATE cids.role_permissions 
                            SET permissions = %s, rls_filters = %s, updated_at = NOW()
                            WHERE client_id = %s AND role_name = %s
                        """, (
                            Json(list(valid_perms)),
                            Json(rls_filters or {}),
                            app_id,
                            role_name
                        ))
                        
                        # Delete old permissions and insert new ones
                        logger.info(f"Deleting old permissions from permissions table for role {role_id}")
                        self.db_cursor.execute("""
                            DELETE FROM cids.permissions 
                            WHERE role_id = %s
                        """, (role_id,))
                        
                        # Insert updated individual permissions
                        if valid_perms:
                            logger.info(f"=== BEFORE UPDATING permissions table ===")
                            logger.info(f"Inserting {len(valid_perms)} updated permissions into permissions table")
                            logger.info(f"Valid permissions to update: {valid_perms}")
                            
                            for perm_key in valid_perms:
                                # Parse permission key (format: resource.action or resource.action.field/category)
                                parts = perm_key.split('.')
                                if len(parts) >= 2:
                                    resource = parts[0]
                                    action = parts[1]
                                    
                                    # Check if the third part is a category or a field
                                    category = None
                                    fields = []
                                    if len(parts) > 2:
                                        # Known categories
                                        categories_list = ['base', 'pii', 'phi', 'financial', 'sensitive', 'wildcard']
                                        if parts[2] in categories_list:
                                            category = parts[2]
                                            logger.info(f"  UPDATE: Permission {perm_key} has category: {category}")
                                        else:
                                            fields = parts[2:]
                                            logger.info(f"  UPDATE: Permission {perm_key} has fields: {fields}")
                                    else:
                                        logger.info(f"  UPDATE: Permission {perm_key} is base (no category/fields)")
                                    
                                    # Generate per_id for each permission
                                    import uuid
                                    individual_per_id = f"PER_{uuid.uuid4().hex[:16]}"
                                    
                                    # Get RLS filters for this specific resource if any
                                    resource_filters = {}
                                    if rls_filters and resource in rls_filters:
                                        resource_filters = rls_filters[resource]
                                    
                                    logger.info(f"  === UPDATING permissions (INSERT after DELETE) ===")
                                    logger.info(f"    role_id: {role_id}")
                                    logger.info(f"    resource: {resource}")
                                    logger.info(f"    action: {action}")
                                    logger.info(f"    fields: {fields}")
                                    logger.info(f"    category: {category}")
                                    logger.info(f"    per_id: {individual_per_id}")
                                    
                                    self.db_cursor.execute("""
                                        INSERT INTO cids.permissions 
                                        (role_id, resource, action, fields, resource_filters, per_id, created_at, updated_at)
                                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                                    """, (
                                        role_id,
                                        resource,
                                        action,
                                        Json(fields),
                                        Json(resource_filters),
                                        individual_per_id
                                    ))
                            logger.info(f"=== AFTER UPDATE: Updated {len(valid_perms)} permissions in permissions table ===")
                        
                        # Log activity for update
                        self.db_cursor.execute("""
                            INSERT INTO cids.activity_log 
                            (activity_type, entity_type, entity_id, entity_name, user_email, user_id, details, status, timestamp)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            'permission.update',
                            'permission',
                            existing_perms['per_id'],
                            f"{app_id}/{role_name}",
                            user_email or 'system',
                            user_id or 'system',
                            Json({
                                'client_id': app_id,
                                'role_name': role_name,
                                'allowed_count': len(valid_perms),
                                'denied_count': len(valid_denied_perms),
                                'rls_filter_count': len(rls_filters) if rls_filters else 0
                            }),
                            'success'
                        ))
                    else:
                        # INSERT new permissions
                        logger.info(f"=== BEFORE INSERTING INTO role_permissions table ===")
                        logger.info(f"Inserting new permissions for role {role_name}")
                        logger.info(f"  client_id: {app_id}")
                        logger.info(f"  role_name: {role_name}")
                        logger.info(f"  permissions: {list(valid_perms)}")
                        logger.info(f"  rls_filters: {rls_filters or {}}")
                        logger.info(f"  per_id: {per_id}")
                        
                        self.db_cursor.execute("""
                            INSERT INTO cids.role_permissions 
                            (client_id, role_name, permissions, rls_filters, per_id, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                        """, (
                            app_id,
                            role_name,
                            Json(list(valid_perms)),
                            Json(rls_filters or {}),
                            per_id
                        ))
                        logger.info(f"=== AFTER INSERT into role_permissions ===")

                        # Insert RLS filters into new cids.rls_filters table
                        if rls_filters:
                            logger.info(f"=== INSERTING RLS FILTERS into cids.rls_filters ===")
                            logger.info(f"=== RLS_FILTERS RECEIVED: {json.dumps(rls_filters)} ===")
                            logger.info(f"=== CLIENT_ID: {app_id}, ROLE: {role_name} ===")

                            filter_count = 0
                            for resource, field_filters in rls_filters.items():
                                logger.info(f"  Processing resource: {resource}")
                                logger.info(f"  Field filters for resource: {field_filters}")

                                for field_name, filter_list in field_filters.items():
                                    logger.info(f"    Processing field: {field_name}")
                                    logger.info(f"    Filter list type: {type(filter_list)}")
                                    logger.info(f"    Filter list content: {filter_list}")

                                    for filter_item in filter_list:
                                        # Generate rls_id using UUID
                                        import uuid
                                        rls_id = str(uuid.uuid4())
                                        filter_condition = filter_item.get('filter', '')

                                        filter_count += 1
                                        logger.info(f"    [FILTER {filter_count}] ATTEMPTING INSERT:")
                                        logger.info(f"      rls_id: {rls_id}")
                                        logger.info(f"      client_id: {app_id}")
                                        logger.info(f"      role_name: {role_name}")
                                        logger.info(f"      resource: {resource}")
                                        logger.info(f"      field_name: {field_name}")
                                        logger.info(f"      filter_condition: {filter_condition}")
                                        logger.info(f"      created_by: {user_email or 'system'}")

                                        self.db_cursor.execute("""
                                            INSERT INTO cids.rls_filters
                                            (rls_id, client_id, role_name, resource, field_name,
                                             filter_condition, is_active, created_by, updated_by,
                                             description, filter_operator, priority, metadata)
                                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                            ON CONFLICT (client_id, role_name, resource, field_name) WHERE is_active = true
                                            DO UPDATE SET
                                                filter_condition = EXCLUDED.filter_condition,
                                                updated_by = EXCLUDED.updated_by,
                                                updated_at = NOW()
                                        """, (
                                            rls_id,
                                            app_id,
                                            role_name,
                                            resource,
                                            field_name,
                                            filter_condition,
                                            True,  # is_active
                                            user_email or 'system',
                                            user_email or 'system',
                                            f"RLS filter for {role_name} on {resource}.{field_name}",
                                            filter_item.get('operator', 'AND'),
                                            filter_item.get('priority', 0),
                                            Json(filter_item.get('metadata', {}))
                                        ))

                                        logger.info(f"      [FILTER {filter_count}] INSERT EXECUTED - Rows affected: {self.db_cursor.rowcount}")

                                        # Try to verify the insert
                                        self.db_cursor.execute("""
                                            SELECT COUNT(*) FROM cids.rls_filters
                                            WHERE client_id = %s AND role_name = %s
                                        """, (app_id, role_name))
                                        count_result = self.db_cursor.fetchone()
                                        logger.info(f"      [VERIFICATION] Total RLS filters for this role in DB: {count_result[0] if count_result else 0}")

                            logger.info(f"=== COMPLETED processing {filter_count} RLS filters ===")
                            logger.info(f"=== RLS filters will be committed with main transaction ===")
                        else:
                            logger.info(f"=== NO RLS FILTERS TO INSERT (rls_filters is empty or None) ===")

                        # Also insert individual permissions into permissions table
                        if valid_perms:
                            logger.info(f"=== BEFORE INSERTING INTO permissions table ===")
                            logger.info(f"Inserting {len(valid_perms)} individual permissions into permissions table")
                            logger.info(f"Valid permissions to insert: {valid_perms}")
                            
                            for perm_key in valid_perms:
                                # Parse permission key (format: resource.action or resource.action.field/category)
                                parts = perm_key.split('.')
                                if len(parts) >= 2:
                                    resource = parts[0]
                                    action = parts[1]
                                    
                                    # Check if the third part is a category or a field
                                    category = None
                                    fields = []
                                    if len(parts) > 2:
                                        # Known categories
                                        categories_list = ['base', 'pii', 'phi', 'financial', 'sensitive', 'wildcard']
                                        if parts[2] in categories_list:
                                            category = parts[2]
                                            logger.info(f"  Permission {perm_key} has category: {category}")
                                        else:
                                            fields = parts[2:]
                                            logger.info(f"  Permission {perm_key} has fields: {fields}")
                                    else:
                                        logger.info(f"  Permission {perm_key} is base (no category/fields)")
                                    
                                    # Generate per_id for each permission
                                    import uuid
                                    individual_per_id = f"PER_{uuid.uuid4().hex[:16]}"
                                    
                                    # Get RLS filters for this specific resource if any
                                    resource_filters = {}
                                    if rls_filters and resource in rls_filters:
                                        resource_filters = rls_filters[resource]
                                    
                                    logger.info(f"  === INSERTING INTO permissions ===")
                                    logger.info(f"    role_id: {role_id}")
                                    logger.info(f"    resource: {resource}")
                                    logger.info(f"    action: {action}")
                                    logger.info(f"    fields: {fields}")
                                    logger.info(f"    category: {category}")
                                    logger.info(f"    per_id: {individual_per_id}")
                                    
                                    self.db_cursor.execute("""
                                        INSERT INTO cids.permissions 
                                        (role_id, resource, action, fields, category, resource_filters, per_id, created_at, updated_at)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                                    """, (
                                        role_id,
                                        resource,
                                        action,
                                        Json(fields),
                                        category,  # Now storing category in its own column
                                        Json(resource_filters),
                                        individual_per_id
                                    ))
                            logger.info(f"=== AFTER INSERT: Inserted {len(valid_perms)} permissions into permissions table ===")
                        
                        # Log activity for create with permissions
                        self.db_cursor.execute("""
                            INSERT INTO cids.activity_log 
                            (activity_type, entity_type, entity_id, entity_name, user_email, user_id, details, status, timestamp)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            'permission.create',
                            'permission',
                            per_id,
                            f"{app_id}/{role_name}",
                            user_email or 'system',
                            user_id or 'system',
                            Json({
                                'client_id': app_id,
                                'role_name': role_name,
                                'allowed_count': len(valid_perms),
                                'denied_count': len(valid_denied_perms),
                                'rls_filter_count': len(rls_filters) if rls_filters else 0
                            }),
                            'success'
                        ))
                
                logger.info(f"=== ABOUT TO COMMIT ALL CHANGES TO DATABASE ===")
                self.db_conn.commit()
                logger.info(f"=== SUCCESSFULLY COMMITTED ALL CHANGES ===")

                # Verify RLS filters were actually saved
                if rls_filters:
                    self.db_cursor.execute("""
                        SELECT COUNT(*) FROM cids.rls_filters
                        WHERE client_id = %s AND role_name = %s
                    """, (app_id, role_name))
                    final_count = self.db_cursor.fetchone()
                    logger.info(f"=== FINAL VERIFICATION: {final_count[0] if final_count else 0} RLS filters in DB for {app_id}/{role_name} ===")

                if per_id:
                    logger.info(f"Saved role permissions to database with per_id: {per_id} and role_id: {role_id}")
                else:
                    logger.info(f"Saved role metadata to database with role_id: {role_id}")
            except Exception as e:
                logger.error(f"=== ERROR saving role permissions to database: {e} ===")
                logger.error(f"=== ROLLING BACK TRANSACTION ===")
                if self.db_conn:
                    self.db_conn.rollback()
            finally:
                # Always close cursor after operation
                logger.info(f"=== CLOSING DATABASE CURSOR ===")
                if self.db_cursor:
                    self.db_cursor.close()
                    self.db_cursor = None
                # Reconnect for next operation
                logger.info(f"=== RECONNECTING TO DATABASE FOR NEXT OPERATION ===")
                self._connect_db()
        
        # Update in-memory metadata
        if role_name not in self.role_metadata[app_id]:
            self.role_metadata[app_id][role_name] = {
                'created_at': datetime.now().isoformat(),
                'description': description,
                'a2a_only': a2a_only,
                'is_active': True,
                'per_id': per_id  # Use per_id instead of undefined role_id
            }
        else:
            self.role_metadata[app_id][role_name]['updated_at'] = datetime.now().isoformat()
            if description is not None:
                self.role_metadata[app_id][role_name]['description'] = description
            self.role_metadata[app_id][role_name]['a2a_only'] = a2a_only

        # NO GUARDAR EN JSON - Solo en base de datos
        # self._save_registry()
        logger.info(f"Created/updated role {role_name} with {len(valid_perms)} allowed, {len(valid_denied_perms)} denied permissions and {len(rls_filters) if rls_filters else 0} RLS filters for app {app_id}")
        return valid_perms, valid_denied_perms

    # Legacy alias
    def create_role(self, app_id: str, role_name: str, permissions: Set[str], description: str = None):
        valid_perms, _ = self.create_role_with_rls(app_id, role_name, permissions, description, None)
        return valid_perms

    def update_role_with_rls(self, app_id: str, role_name: str, permissions: Set[str], description: str = None, rls_filters: Dict = None, denied_permissions: Set[str] = None, user_email: str = None, user_id: str = None):
        return self.create_role_with_rls(app_id, role_name, permissions, description, rls_filters, denied_permissions, user_email, user_id)

    def delete_role(self, app_id: str, role_name: str, user_email: str = None, user_id: str = None) -> bool:
        """Delete a role and its permissions"""
        # Delete from database
        self._delete_role_from_db(app_id, role_name, user_email, user_id)
        
        # Delete from memory
        if app_id in self.role_permissions and role_name in self.role_permissions[app_id]:
            del self.role_permissions[app_id][role_name]
        if app_id in self.role_denied_permissions and role_name in self.role_denied_permissions[app_id]:
            del self.role_denied_permissions[app_id][role_name]
        if app_id in self.role_metadata and role_name in self.role_metadata[app_id]:
            del self.role_metadata[app_id][role_name]
        if app_id in self.role_rls_filters and role_name in self.role_rls_filters[app_id]:
            del self.role_rls_filters[app_id][role_name]
        
        # NO GUARDAR EN JSON
        # self._save_registry()
        return True
    
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

