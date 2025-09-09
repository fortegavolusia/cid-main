"""
Database service for connecting to Supabase PostgreSQL
"""
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DB_HOST', 'supabase_db_mi-proyecto-supabase'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'postgres'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres')  # Supabase local password
        }
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a SELECT query and return results"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute an INSERT/UPDATE/DELETE query"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update execution failed: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def get_registered_apps_stats(self) -> Dict[str, int]:
        """Get statistics about registered applications"""
        try:
            if not self.conn or self.conn.closed:
                logger.info(f"Connecting to database at {self.connection_params['host']}:{self.connection_params['port']}")
                if not self.connect():
                    logger.error("Failed to connect to database")
                    return {
                        'total': 0,
                        'active': 0,
                        'inactive': 0
                    }
            
            # Get total count
            self.cursor.execute("SELECT COUNT(*) as total FROM cids.registered_apps")
            total = self.cursor.fetchone()['total']
            logger.info(f"Total apps from DB: {total}")
            
            # Get active count
            self.cursor.execute("SELECT COUNT(*) as active FROM cids.registered_apps WHERE is_active = true")
            active = self.cursor.fetchone()['active']
            logger.info(f"Active apps from DB: {active}")
            
            # Get inactive count
            inactive = total - active
            logger.info(f"Inactive apps calculated: {inactive}")
            
            return {
                'total': total,
                'active': active,
                'inactive': inactive
            }
        except Exception as e:
            logger.error(f"Failed to get app stats: {e}")
            logger.error(f"Connection params: host={self.connection_params['host']}, port={self.connection_params['port']}")
            return {
                'total': 0,
                'active': 0,
                'inactive': 0
            }
    
    def get_all_registered_apps(self) -> List[Dict]:
        """Get all registered applications from database"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return []
            
            query = """
                SELECT client_id, name, description, redirect_uris, owner_email,
                       is_active, created_at, updated_at, discovery_endpoint,
                       allow_discovery, last_discovery_at, discovery_status, discovery_version,
                       last_discovery_run_at, last_discovery_run_by, discovery_run_count
                FROM cids.registered_apps
                ORDER BY created_at DESC
            """
            self.cursor.execute(query)
            apps = self.cursor.fetchall()
            
            # Handle JSON fields and datetime conversion
            result = []
            for app in apps:
                # app is already a dict thanks to RealDictCursor
                app_dict = dict(app)  # Make a copy to avoid modifying original
                
                # Debug log
                logger.info(f"App from DB: {app_dict.get('name')} - discovery_endpoint: {app_dict.get('discovery_endpoint')}")
                
                # Convert datetime objects to strings
                if app_dict.get('created_at'):
                    app_dict['created_at'] = app_dict['created_at'].isoformat()
                if app_dict.get('updated_at'):
                    app_dict['updated_at'] = app_dict['updated_at'].isoformat()
                if app_dict.get('last_discovery_at'):
                    app_dict['last_discovery_at'] = app_dict['last_discovery_at'].isoformat()
                if app_dict.get('last_discovery_run_at'):
                    app_dict['last_discovery_run_at'] = app_dict['last_discovery_run_at'].isoformat()
                    
                # Ensure discovery_endpoint is included
                app_dict['discovery_endpoint'] = app_dict.get('discovery_endpoint') or None
                
                result.append(app_dict)
            
            return result
        except Exception as e:
            logger.error(f"Failed to get all apps: {e}")
            return []
    
    def get_app_by_id(self, client_id: str) -> Optional[Dict]:
        """Get a single application by client_id"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return None
            
            query = """
                SELECT client_id, name, description, redirect_uris, owner_email,
                       is_active, created_at, updated_at, discovery_endpoint,
                       allow_discovery, last_discovery_at, discovery_status, discovery_version
                FROM cids.registered_apps
                WHERE client_id = %s
            """
            self.cursor.execute(query, (client_id,))
            app = self.cursor.fetchone()
            
            if app:
                app_dict = dict(app)
                # Convert datetime objects to strings
                if app_dict.get('created_at'):
                    app_dict['created_at'] = app_dict['created_at'].isoformat()
                if app_dict.get('updated_at'):
                    app_dict['updated_at'] = app_dict['updated_at'].isoformat()
                if app_dict.get('last_discovery_at'):
                    app_dict['last_discovery_at'] = app_dict['last_discovery_at'].isoformat()
                if app_dict.get('last_discovery_run_at'):
                    app_dict['last_discovery_run_at'] = app_dict['last_discovery_run_at'].isoformat()
                return app_dict
            
            return None
        except Exception as e:
            logger.error(f"Failed to get app {client_id}: {e}")
            return None
    
    def create_app(self, app_data: Dict) -> bool:
        """Create a new application"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False
            
            query = """
                INSERT INTO cids.registered_apps (
                    client_id, name, description, redirect_uris, owner_email,
                    is_active, created_at, updated_at, discovery_endpoint,
                    allow_discovery
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            from psycopg2.extras import Json
            self.cursor.execute(query, (
                app_data['client_id'],
                app_data['name'],
                app_data['description'],
                Json(app_data.get('redirect_uris', [])),
                app_data['owner_email'],
                app_data.get('is_active', True),
                app_data.get('created_at', datetime.now()),
                app_data.get('updated_at', datetime.now()),
                app_data.get('discovery_endpoint'),
                app_data.get('allow_discovery', False)
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to create app: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def update_app(self, client_id: str, updates: Dict) -> bool:
        """Update an existing application"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            from psycopg2.extras import Json
            for key, value in updates.items():
                if key == 'redirect_uris':
                    set_clauses.append(f"{key} = %s")
                    values.append(Json(value))
                else:
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            # Always update updated_at
            set_clauses.append("updated_at = %s")
            values.append(datetime.now())
            
            values.append(client_id)
            
            query = f"""
                UPDATE cids.registered_apps
                SET {', '.join(set_clauses)}
                WHERE client_id = %s
            """
            
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update app {client_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def delete_app(self, client_id: str) -> bool:
        """Delete an application"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False
            
            query = "DELETE FROM cids.registered_apps WHERE client_id = %s"
            self.cursor.execute(query, (client_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete app {client_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def log_activity(self, activity_type: str, entity_type: str = None, entity_id: str = None,
                    entity_name: str = None, user_email: str = None, user_id: str = None,
                    details: Dict = None, status: str = 'success', error_message: str = None,
                    ip_address: str = None, user_agent: str = None, session_id: str = None,
                    api_endpoint: str = None, http_method: str = None, 
                    response_time_ms: int = None, request_id: str = None) -> bool:
        """Log an activity to the activity_log table for comprehensive auditing"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False
            
            query = """
                INSERT INTO cids.activity_log 
                (activity_type, entity_type, entity_id, entity_name, user_email, user_id,
                 details, status, error_message, ip_address, user_agent, session_id,
                 api_endpoint, http_method, response_time_ms, request_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Convert details dict to JSON
            from psycopg2.extras import Json
            details_json = Json(details) if details else Json({})
            
            self.cursor.execute(query, (
                activity_type, entity_type, entity_id, entity_name, user_email, user_id,
                details_json, status, error_message, ip_address, user_agent, session_id,
                api_endpoint, http_method, response_time_ms, request_id
            ))
            self.conn.commit()
            logger.info(f"Activity logged: {activity_type} for {entity_type or 'system'} {entity_id or ''}")
            return True
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def get_activity_log(self, entity_type: str = None, entity_id: str = None, 
                        limit: int = 100) -> List[Dict]:
        """Get activity log entries"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return []
            
            if entity_type and entity_id:
                query = """
                    SELECT * FROM cids.activity_log 
                    WHERE entity_type = %s AND entity_id = %s
                    ORDER BY created_at DESC LIMIT %s
                """
                self.cursor.execute(query, (entity_type, entity_id, limit))
            elif entity_type:
                query = """
                    SELECT * FROM cids.activity_log 
                    WHERE entity_type = %s
                    ORDER BY created_at DESC LIMIT %s
                """
                self.cursor.execute(query, (entity_type, limit))
            else:
                query = """
                    SELECT * FROM cids.activity_log 
                    ORDER BY created_at DESC LIMIT %s
                """
                self.cursor.execute(query, (limit,))
            
            logs = self.cursor.fetchall()
            result = []
            for log in logs:
                log_dict = dict(log)
                if log_dict.get('timestamp'):
                    log_dict['timestamp'] = log_dict['timestamp'].isoformat()
                result.append(log_dict)
            
            return result
        except Exception as e:
            logger.error(f"Failed to get activity log: {e}")
            return []
    
    def update_discovery_timestamp(self, client_id: str, user_email: str = None) -> bool:
        """Update the last discovery run timestamp for an app"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False
            
            query = """
                UPDATE cids.registered_apps 
                SET last_discovery_run_at = CURRENT_TIMESTAMP,
                    last_discovery_run_by = %s,
                    discovery_run_count = COALESCE(discovery_run_count, 0) + 1,
                    last_discovery_at = CURRENT_TIMESTAMP
                WHERE client_id = %s
            """
            self.cursor.execute(query, (user_email, client_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update discovery timestamp: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    # ========== ROLES METHODS ==========
    def create_role(self, client_id: str, role_name: str, description: str = None, 
                   ad_groups: List[str] = None) -> Optional[int]:
        """Create a new role and return its ID"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return None
            
            from psycopg2.extras import Json
            query = """
                INSERT INTO cids.roles (client_id, role_name, description, ad_groups)
                VALUES (%s, %s, %s, %s)
                RETURNING role_id
            """
            
            self.cursor.execute(query, (
                client_id,
                role_name,
                description,
                Json(ad_groups or [])
            ))
            
            role_id = self.cursor.fetchone()['role_id']
            self.conn.commit()
            logger.info(f"Created role {role_name} for app {client_id} with ID {role_id}")
            return role_id
        except Exception as e:
            logger.error(f"Failed to create role: {e}")
            if self.conn:
                self.conn.rollback()
            return None
    
    def get_role(self, client_id: str, role_name: str) -> Optional[Dict]:
        """Get a specific role by client_id and role_name"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return None
            
            query = """
                SELECT role_id, client_id, role_name, description, ad_groups,
                       created_at, updated_at
                FROM cids.roles
                WHERE client_id = %s AND role_name = %s
            """
            
            self.cursor.execute(query, (client_id, role_name))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Failed to get role: {e}")
            return None
    
    def get_roles_by_client(self, client_id: str) -> List[Dict]:
        """Get all roles for a specific client"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return []
            
            query = """
                SELECT role_id, client_id, role_name, description, ad_groups,
                       created_at, updated_at
                FROM cids.roles
                WHERE client_id = %s
                ORDER BY role_name
            """
            
            self.cursor.execute(query, (client_id,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get roles for client {client_id}: {e}")
            return []
    
    def update_role(self, client_id: str, role_name: str, updates: Dict) -> bool:
        """Update an existing role"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False
            
            from psycopg2.extras import Json
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key == 'ad_groups':
                    set_clauses.append(f"{key} = %s")
                    values.append(Json(value))
                else:
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.extend([client_id, role_name])
            
            query = f"""
                UPDATE cids.roles
                SET {', '.join(set_clauses)}
                WHERE client_id = %s AND role_name = %s
            """
            
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update role: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def delete_role(self, client_id: str, role_name: str) -> bool:
        """Delete a role and its permissions"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False
            
            query = """
                DELETE FROM cids.roles
                WHERE client_id = %s AND role_name = %s
            """
            
            self.cursor.execute(query, (client_id, role_name))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete role: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    # ========== PERMISSIONS METHODS ==========
    def add_permissions(self, role_id: int, permissions: List[Dict]) -> bool:
        """Add permissions to a role"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False
            
            from psycopg2.extras import Json
            for perm in permissions:
                query = """
                    INSERT INTO cids.permissions 
                    (role_id, resource, action, fields, resource_filters)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                self.cursor.execute(query, (
                    role_id,
                    perm.get('resource'),
                    perm.get('action'),
                    Json(perm.get('fields', [])),
                    Json(perm.get('resource_filters', {}))
                ))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to add permissions: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def get_permissions_by_role(self, role_id: int) -> List[Dict]:
        """Get all permissions for a role"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return []
            
            query = """
                SELECT permission_id, resource, action, fields, resource_filters,
                       created_at, updated_at
                FROM cids.permissions
                WHERE role_id = %s
                ORDER BY resource, action
            """
            
            self.cursor.execute(query, (role_id,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get permissions: {e}")
            return []
    
    def clear_permissions(self, role_id: int) -> bool:
        """Clear all permissions for a role"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False
            
            query = "DELETE FROM cids.permissions WHERE role_id = %s"
            self.cursor.execute(query, (role_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to clear permissions: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    # ========== DASHBOARD STATS METHODS ==========
    def get_dashboard_stats(self) -> Dict[str, int]:
        """Get comprehensive statistics for the dashboard"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return {
                        'apps_total': 0,
                        'apps_active': 0,
                        'apps_discovered': 0,
                        'roles_total': 0,
                        'permissions_total': 0,
                        'api_keys_total': 0,
                        'api_keys_active': 0
                    }
            
            stats = {}
            
            # Apps statistics
            self.cursor.execute("SELECT COUNT(*) as total FROM cids.registered_apps")
            stats['apps_total'] = self.cursor.fetchone()['total']
            
            self.cursor.execute("SELECT COUNT(*) as active FROM cids.registered_apps WHERE is_active = true")
            stats['apps_active'] = self.cursor.fetchone()['active']
            
            # Apps with discovery enabled/configured
            self.cursor.execute("""
                SELECT COUNT(*) as discovered 
                FROM cids.registered_apps 
                WHERE discovery_endpoint IS NOT NULL 
                AND allow_discovery = true
            """)
            stats['apps_discovered'] = self.cursor.fetchone()['discovered']
            
            # Roles count (distinct roles across all apps)
            self.cursor.execute("SELECT COUNT(DISTINCT role_name) as total FROM cids.roles")
            stats['roles_total'] = self.cursor.fetchone()['total']
            
            # Permissions count (unique permission combinations)
            self.cursor.execute("""
                SELECT COUNT(DISTINCT CONCAT(resource, '.', action)) as total 
                FROM cids.permissions
            """)
            stats['permissions_total'] = self.cursor.fetchone()['total']
            
            # API Keys statistics
            self.cursor.execute("SELECT COUNT(*) as total FROM cids.api_keys")
            stats['api_keys_total'] = self.cursor.fetchone()['total']
            
            self.cursor.execute("SELECT COUNT(*) as active FROM cids.api_keys WHERE is_active = true")
            stats['api_keys_active'] = self.cursor.fetchone()['active']
            
            # Token templates count
            self.cursor.execute("SELECT COUNT(*) as total FROM cids.token_templates")
            stats['token_templates_total'] = self.cursor.fetchone()['total']
            
            # Audit log entries (last 24 hours)
            self.cursor.execute("""
                SELECT COUNT(*) as recent 
                FROM cids.audit_logs 
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            stats['activity_last_24h'] = self.cursor.fetchone()['recent']
            
            logger.info(f"Dashboard stats retrieved: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            return {
                'apps_total': 0,
                'apps_active': 0,
                'apps_discovered': 0,
                'roles_total': 0,
                'permissions_total': 0,
                'api_keys_total': 0,
                'api_keys_active': 0,
                'token_templates_total': 0,
                'activity_last_24h': 0
            }

# Singleton instance
db_service = DatabaseService()