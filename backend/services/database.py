"""
Database service for connecting to Supabase PostgreSQL
"""
import os
import json
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any, Optional, Tuple, Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        # Always check environment variables fresh
        db_host = os.getenv('DB_HOST')
        
        # If DB_HOST is explicitly set, use it (we're in Docker)
        if db_host:
            self.connection_params = {
                'host': db_host,
                'port': os.getenv('DB_PORT', '5432'),
                'database': os.getenv('DB_NAME', 'postgres'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'postgres')
            }
        else:
            # Local development (not in Docker)
            self.connection_params = {
                'host': 'localhost',
                'port': '54322',
                'database': 'postgres',
                'user': 'postgres',
                'password': 'postgres'
            }
        
        logger.info(f"Database config: host={self.connection_params['host']}, port={self.connection_params['port']}")
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            # Re-check environment variables at connection time
            db_host = os.getenv('DB_HOST')
            if db_host:
                self.connection_params = {
                    'host': db_host,
                    'port': os.getenv('DB_PORT', '5432'),
                    'database': os.getenv('DB_NAME', 'postgres'),
                    'user': os.getenv('DB_USER', 'postgres'),
                    'password': os.getenv('DB_PASSWORD', 'postgres')
                }
            logger.info(f"Connecting to database at {self.connection_params['host']}:{self.connection_params['port']}")
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
            results = self.cursor.fetchall()
            
            # Close connection after query to avoid connection leaks
            self.disconnect()
            
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            # Ensure connection is closed on error
            self.disconnect()
            return []
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute an INSERT/UPDATE/DELETE query"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            self.cursor.execute(query, params)
            self.conn.commit()
            
            # Close connection after update to avoid connection leaks
            self.disconnect()
            
            return True
        except Exception as e:
            logger.error(f"Update execution failed: {e}")
            if self.conn:
                self.conn.rollback()
            # Ensure connection is closed on error
            self.disconnect()
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
                SELECT 
                    ra.client_id, ra.name, ra.description, ra.redirect_uris, ra.owner_email,
                    ra.is_active, ra.created_at, ra.updated_at, ra.discovery_endpoint,
                    ra.allow_discovery, ra.last_discovery_at, ra.discovery_status, ra.discovery_version,
                    ra.last_discovery_run_at, ra.last_discovery_run_by, ra.discovery_run_count,
                    -- Get latest discovery version and endpoints count from discovery_history
                    dh.latest_version, dh.latest_endpoints_count, dh.latest_permissions_count, dh.latest_sensitive_fields_count,
                    dh.latest_discovery_timestamp, dh.latest_discovery_id
                FROM cids.registered_apps ra
                LEFT JOIN (
                    SELECT client_id, 
                           MAX(discovery_version::int) as latest_version,
                           (SELECT endpoints_count 
                            FROM cids.discovery_history dh2 
                            WHERE dh2.client_id = dh.client_id 
                              AND dh2.discovery_version::int = MAX(dh.discovery_version::int)
                            LIMIT 1) as latest_endpoints_count,
                           (SELECT COUNT(DISTINCT CONCAT(resource, '.', action))
                            FROM cids.discovered_permissions dp
                            WHERE dp.client_id = dh.client_id 
                              AND dp.discovery_id = (
                                  SELECT discovery_id 
                                  FROM cids.discovery_history dh3
                                  WHERE dh3.client_id = dh.client_id
                                    AND dh3.discovery_version::int = MAX(dh.discovery_version::int)
                                  LIMIT 1
                              )) as latest_permissions_count,
                           (SELECT COUNT(DISTINCT field_name)
                            FROM cids.field_metadata fm
                            WHERE fm.discovery_id = (
                                  SELECT discovery_id
                                  FROM cids.discovery_history dh4
                                  WHERE dh4.client_id = dh.client_id
                                    AND dh4.discovery_version::int = MAX(dh.discovery_version::int)
                                  LIMIT 1
                              )) as latest_sensitive_fields_count,
                           (SELECT discovery_timestamp 
                            FROM cids.discovery_history dh5
                            WHERE dh5.client_id = dh.client_id 
                              AND dh5.discovery_version::int = MAX(dh.discovery_version::int)
                            LIMIT 1) as latest_discovery_timestamp,
                           (SELECT discovery_id 
                            FROM cids.discovery_history dh6
                            WHERE dh6.client_id = dh.client_id 
                              AND dh6.discovery_version::int = MAX(dh.discovery_version::int)
                            LIMIT 1) as latest_discovery_id
                    FROM cids.discovery_history dh
                    GROUP BY client_id
                ) dh ON ra.client_id = dh.client_id
                ORDER BY ra.created_at DESC
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
                if app_dict.get('latest_discovery_timestamp'):
                    app_dict['latest_discovery_timestamp'] = app_dict['latest_discovery_timestamp'].isoformat()
                    
                # Ensure discovery_endpoint is included
                app_dict['discovery_endpoint'] = app_dict.get('discovery_endpoint') or None
                
                # Add active roles count for this app
                app_dict['active_roles_count'] = self.get_active_roles_count_by_app(app_dict['client_id'])
                
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
                if app_dict.get('latest_discovery_timestamp'):
                    app_dict['latest_discovery_timestamp'] = app_dict['latest_discovery_timestamp'].isoformat()
                return app_dict
            
            return None
        except Exception as e:
            logger.error(f"Failed to get app {client_id}: {e}")
            return None

    def get_registered_app(self, client_id: str) -> Optional[Dict]:
        """Get a registered app by client_id (alias for get_app_by_id)"""
        return self.get_app_by_id(client_id)

    def has_active_api_key(self, client_id: str) -> bool:
        """Check if an app has any active API keys"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False

            query = """
                SELECT COUNT(*) as count
                FROM cids.api_keys
                WHERE client_id = %s AND is_active = true
            """
            self.cursor.execute(query, (client_id,))
            result = self.cursor.fetchone()

            return result['count'] > 0 if result else False

        except Exception as e:
            logger.error(f"Failed to check active API keys: {e}")
            return False

    def get_api_keys_for_app(self, client_id: str) -> List[Dict]:
        """Get all API keys for a specific app"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return []

            query = """
                SELECT key_id, client_id, name, key_hash,
                       created_at, expires_at, last_used_at, is_active, created_by, log_id,
                       usage_count, last_rotated_at, rotation_scheduled_at, rotation_grace_end,
                       token_template_name, app_roles_overrides, token_ttl_minutes,
                       default_audience, allowed_audiences
                FROM cids.api_keys
                WHERE client_id = %s
                ORDER BY created_at DESC
            """
            self.cursor.execute(query, (client_id,))
            keys = self.cursor.fetchall()

            result = []
            for key in keys:
                key_dict = dict(key)
                # Convert datetime objects to strings
                if key_dict.get('created_at'):
                    key_dict['created_at'] = key_dict['created_at'].isoformat()
                if key_dict.get('expires_at'):
                    key_dict['expires_at'] = key_dict['expires_at'].isoformat()
                if key_dict.get('last_used_at'):
                    key_dict['last_used_at'] = key_dict['last_used_at'].isoformat()
                # Add key prefix (first 12 chars of key_id)
                key_dict['key_prefix'] = f"cids_ak_{key_dict['key_id'][:8]}..."
                result.append(key_dict)

            return result
        except Exception as e:
            logger.error(f"Failed to get API keys for app {client_id}: {e}")
            return []

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
    
    def log_activity(self, activity_id: str = None, activity_type: str = None, entity_type: str = None, entity_id: str = None,
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
                (activity_id, activity_type, entity_type, entity_id, entity_name, user_email, user_id,
                 details, status, error_message, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Convert details dict to JSON
            from psycopg2.extras import Json
            details_json = Json(details) if details else Json({})
            
            # Add extra fields to details if provided
            if session_id or api_endpoint or http_method or response_time_ms or request_id:
                extra_details = details or {}
                if session_id:
                    extra_details['session_id'] = session_id
                if api_endpoint:
                    extra_details['api_endpoint'] = api_endpoint
                if http_method:
                    extra_details['http_method'] = http_method
                if response_time_ms:
                    extra_details['response_time_ms'] = response_time_ms
                if request_id:
                    extra_details['request_id'] = request_id
                details_json = Json(extra_details)
            
            # Set autocommit to ensure transaction is committed immediately
            old_autocommit = self.conn.autocommit
            self.conn.autocommit = True
            
            self.cursor.execute(query, (
                activity_id, activity_type, entity_type, entity_id, entity_name, user_email, user_id,
                details_json, status, error_message, ip_address, user_agent
            ))
            
            # Restore original autocommit setting
            self.conn.autocommit = old_autocommit
            logger.info(f"Activity logged: {activity_type} for {entity_type or 'system'} {entity_id or ''} with ID {activity_id}")
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
    
    # ========== ROLES METHODS (DEPRECATED - TABLE NO LONGER EXISTS) ==========
    def create_role(self, client_id: str, role_name: str, description: str = None, 
                   ad_groups: List[str] = None) -> Optional[int]:
        """Create a new role and return its ID - DEPRECATED: Table no longer exists"""
        logger.warning("create_role called but cids.roles table no longer exists")
        return None
    
    def get_role(self, client_id: str, role_name: str) -> Optional[Dict]:
        """Get a specific role by client_id and role_name - DEPRECATED: Table no longer exists"""
        logger.warning("get_role called but cids.roles table no longer exists")
        return None
    
    def get_roles_by_client(self, client_id: str) -> List[Dict]:
        """Get all roles for a specific client from role_metadata table"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return []
            
            self.cursor.execute("""
                SELECT role_id, role_name, description, is_active, created_at, updated_at
                FROM cids.role_metadata
                WHERE client_id = %s AND is_active = true
                ORDER BY role_name
            """, (client_id,))
            
            roles = self.cursor.fetchall()
            self.disconnect()
            return roles if roles else []
        except Exception as e:
            logger.error(f"Error getting roles for client {client_id}: {e}")
            return []
    
    def update_role(self, client_id: str, role_name: str, updates: Dict) -> bool:
        """Update an existing role - DEPRECATED: Table no longer exists"""
        logger.warning("update_role called but cids.roles table no longer exists")
        return False
    
    def delete_role(self, client_id: str, role_name: str) -> bool:
        """Delete a role and its permissions - DEPRECATED: Table no longer exists"""
        logger.warning("delete_role called but cids.roles table no longer exists")
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
    def get_active_roles_count_by_app(self, client_id: str) -> int:
        """Get count of active roles for a specific app"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return 0
            
            query = """
                SELECT COUNT(*) as count 
                FROM cids.role_metadata 
                WHERE client_id = %s AND is_active = true
            """
            
            self.cursor.execute(query, (client_id,))
            result = self.cursor.fetchone()
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"Failed to get active roles count for app {client_id}: {e}")
            return 0
    
    def get_dashboard_stats(self) -> Dict[str, int]:
        """Get comprehensive statistics for the dashboard"""
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return {
                        'apps_total': 0,
                        'apps_active': 0,
                        'apps_discovered': 0,
                        'endpoints_total': 0,
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
            
            # Apps discovered (apps that have been discovered - last_discovery_at is not null)
            self.cursor.execute("""
                SELECT COUNT(*) as discovered 
                FROM cids.registered_apps 
                WHERE last_discovery_at IS NOT NULL
            """)
            stats['apps_discovered'] = self.cursor.fetchone()['discovered']
            
            # Endpoints count from discovery_endpoints table (actual discovered endpoints)
            self.cursor.execute("""
                SELECT COUNT(*) as total
                FROM cids.discovery_endpoints
            """)
            stats['discovery_endpoints_total'] = self.cursor.fetchone()['total']

            # Apps with discovery enabled (for backward compatibility)
            self.cursor.execute("""
                SELECT COUNT(*) as total
                FROM cids.registered_apps
                WHERE allow_discovery = true
                AND discovery_endpoint IS NOT NULL
            """)
            stats['endpoints_total'] = self.cursor.fetchone()['total']
            
            # Roles count from role_metadata table
            self.cursor.execute("SELECT COUNT(*) as total FROM cids.role_metadata")
            stats['roles_total'] = self.cursor.fetchone()['total']
            
            # Active roles count
            self.cursor.execute("SELECT COUNT(*) as active FROM cids.role_metadata WHERE is_active = true")
            stats['roles_active'] = self.cursor.fetchone()['active']
            
            # Inactive roles count
            stats['roles_inactive'] = stats['roles_total'] - stats['roles_active']
            
            # Permissions count (unique permission combinations)
            self.cursor.execute("""
                SELECT COUNT(DISTINCT CONCAT(resource, '.', action)) as total 
                FROM cids.permissions
            """)
            stats['permissions_total'] = self.cursor.fetchone()['total']
            
            # Permissions by role
            self.cursor.execute("""
                SELECT 
                    rm.role_name,
                    COUNT(p.permission_id) as permission_count
                FROM cids.role_metadata rm
                LEFT JOIN cids.permissions p ON rm.role_id = p.role_id
                WHERE rm.is_active = true
                GROUP BY rm.role_name, rm.role_id
                ORDER BY permission_count DESC, rm.role_name
            """)
            permissions_by_role = self.cursor.fetchall()
            stats['permissions_by_role'] = [
                {'role_name': row['role_name'], 'count': row['permission_count']} 
                for row in permissions_by_role
            ]
            
            # API Keys statistics
            self.cursor.execute("SELECT COUNT(*) as total FROM cids.api_keys")
            stats['api_keys_total'] = self.cursor.fetchone()['total']
            
            self.cursor.execute("SELECT COUNT(*) as active FROM cids.api_keys WHERE is_active = true")
            stats['api_keys_active'] = self.cursor.fetchone()['active']
            
            # Token templates count
            self.cursor.execute("SELECT COUNT(*) as total FROM cids.token_templates")
            stats['token_templates_total'] = self.cursor.fetchone()['total']
            
            # Rotation policies count
            self.cursor.execute("SELECT COUNT(*) as total FROM cids.rotation_policies WHERE app_client_id != 'default'")
            stats['rotation_policies_total'] = self.cursor.fetchone()['total']

            # A2A Permissions statistics
            self.cursor.execute("SELECT COUNT(*) as total FROM cids.a2a_permissions")
            stats['a2a_permissions_total'] = self.cursor.fetchone()['total']

            self.cursor.execute("SELECT COUNT(*) as active FROM cids.a2a_permissions WHERE is_active = true")
            stats['a2a_permissions_active'] = self.cursor.fetchone()['active']

            stats['a2a_permissions_inactive'] = stats['a2a_permissions_total'] - stats['a2a_permissions_active']

            # RLS Filters statistics
            self.cursor.execute("SELECT COUNT(*) as total FROM cids.rls_filters")
            stats['rls_filters_total'] = self.cursor.fetchone()['total']

            self.cursor.execute("SELECT COUNT(*) as active FROM cids.rls_filters WHERE is_active = true")
            stats['rls_filters_active'] = self.cursor.fetchone()['active']

            stats['rls_filters_inactive'] = stats['rls_filters_total'] - stats['rls_filters_active']

            # Audit log entries (last 24 hours)
            self.cursor.execute("""
                SELECT COUNT(*) as recent 
                FROM cids.activity_log 
                WHERE timestamp > NOW() - INTERVAL '24 hours'
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
                'endpoints_total': 0,
                'roles_total': 0,
                'permissions_total': 0,
                'api_keys_total': 0,
                'api_keys_active': 0,
                'token_templates_total': 0,
                'activity_last_24h': 0
            }

    def get_token_templates(self) -> List[Dict]:
        """Get all token templates from database"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            self.cursor.execute("""
                SELECT template_id, name, description, claims_structure, 
                       ad_groups, is_default, is_enabled, priority,
                       created_at, updated_at, created_by
                FROM cids.token_templates
                ORDER BY priority DESC, name
            """)
            
            templates = []
            for row in self.cursor.fetchall():
                template = {
                    'template_id': row['template_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'claims': row['claims_structure'] if row['claims_structure'] else [],
                    'adGroups': row['ad_groups'] if row['ad_groups'] else [],
                    'isDefault': row['is_default'],
                    'enabled': row['is_enabled'],
                    'priority': row['priority'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                    'created_by': row['created_by']
                }
                templates.append(template)
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get token templates: {e}")
            return []
    
    def save_token_template(self, template: Dict, user_email: str = None) -> bool:
        """Save or update a token template"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            # Check if template exists
            template_id = template.get('template_id')
            if template_id:
                # Update existing
                self.cursor.execute("""
                    UPDATE cids.token_templates 
                    SET name = %s, description = %s, claims_structure = %s,
                        ad_groups = %s, is_default = %s, is_enabled = %s,
                        priority = %s, updated_at = NOW()
                    WHERE template_id = %s
                """, (
                    template.get('name'),
                    template.get('description'),
                    json.dumps(template.get('claims', [])),
                    json.dumps(template.get('adGroups', [])),
                    template.get('isDefault', False),
                    template.get('enabled', True),
                    template.get('priority', 0),
                    template_id
                ))
            else:
                # Insert new
                self.cursor.execute("""
                    INSERT INTO cids.token_templates 
                    (name, description, claims_structure, ad_groups, 
                     is_default, is_enabled, priority, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    template.get('name'),
                    template.get('description'),
                    json.dumps(template.get('claims', [])),
                    json.dumps(template.get('adGroups', [])),
                    template.get('isDefault', False),
                    template.get('enabled', True),
                    template.get('priority', 0),
                    user_email or 'system'
                ))
            
            self.conn.commit()

            # Log template update to activity_log for audit trail
            action = "template_updated" if template_id else "template_created"
            self.cursor.execute("""
                INSERT INTO cids.activity_log
                (user_email, action, resource_type, resource_id, details, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_email or 'system',
                action,
                'token_template',
                template.get('name'),
                json.dumps({
                    'template_name': template.get('name'),
                    'claims_count': len(template.get('claims', [])),
                    'has_custom_claims': any(
                        'custom_' in str(claim.get('id', ''))
                        for claim in template.get('claims', [])
                    ),
                    'ad_groups': template.get('adGroups', []),
                    'priority': template.get('priority', 0),
                    'enabled': template.get('enabled', True)
                }),
                '127.0.0.1'  # System operation
            ))
            self.conn.commit()

            logger.info(f"Token template '{template.get('name')}' saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save token template: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def delete_token_template(self, template_id: int) -> bool:
        """Delete a token template"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            self.cursor.execute("""
                DELETE FROM cids.token_templates 
                WHERE template_id = %s
            """, (template_id,))
            
            self.conn.commit()
            logger.info(f"Token template {template_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete token template: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def get_rotation_policies(self) -> List[Dict]:
        """Get all rotation policies"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            self.cursor.execute("""
                SELECT app_client_id, days_before_expiry, grace_period_hours, 
                       auto_rotate, notify_webhook
                FROM cids.rotation_policies
                ORDER BY app_client_id
            """)
            
            return self.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Failed to get rotation policies: {e}")
            return []
    
    def get_rotation_policy(self, app_client_id: str) -> Dict:
        """Get rotation policy for an app, falls back to default"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            # Try to get app-specific policy
            self.cursor.execute("""
                SELECT days_before_expiry, grace_period_hours, auto_rotate, notify_webhook
                FROM cids.rotation_policies
                WHERE app_client_id = %s
            """, (app_client_id,))
            
            result = self.cursor.fetchone()
            if result:
                return dict(result)
            
            # Fall back to default policy
            self.cursor.execute("""
                SELECT days_before_expiry, grace_period_hours, auto_rotate, notify_webhook
                FROM cids.rotation_policies
                WHERE app_client_id = 'default'
            """)
            
            result = self.cursor.fetchone()
            if result:
                return dict(result)
            
            # Return hardcoded default if no default in DB
            return {
                'days_before_expiry': 7,
                'grace_period_hours': 24,
                'auto_rotate': True,
                'notify_webhook': None
            }
            
        except Exception as e:
            logger.error(f"Failed to get rotation policy: {e}")
            return {
                'days_before_expiry': 7,
                'grace_period_hours': 24,
                'auto_rotate': True,
                'notify_webhook': None
            }
    
    def save_rotation_policy(self, app_client_id: str, days_before_expiry: int = 7, 
                           grace_period_hours: int = 24, auto_rotate: bool = True, 
                           notify_webhook: str = None) -> bool:
        """Save or update rotation policy for an app"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            self.cursor.execute("""
                INSERT INTO cids.rotation_policies 
                (app_client_id, days_before_expiry, grace_period_hours, auto_rotate, notify_webhook)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (app_client_id) 
                DO UPDATE SET 
                    days_before_expiry = EXCLUDED.days_before_expiry,
                    grace_period_hours = EXCLUDED.grace_period_hours,
                    auto_rotate = EXCLUDED.auto_rotate,
                    notify_webhook = EXCLUDED.notify_webhook,
                    updated_at = CURRENT_TIMESTAMP
            """, (app_client_id, days_before_expiry, grace_period_hours, auto_rotate, notify_webhook))
            
            self.conn.commit()
            logger.info(f"Rotation policy for {app_client_id} saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save rotation policy: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    # ========== TOKEN REVOCATION METHODS (GOVERNMENT SECURITY) ==========
    def revoke_token(self, token_id: str, token_type: str = 'access',
                    revoked_by: str = None, reason: str = 'logout',
                    user_email: str = None, user_id: str = None,
                    ip_address: str = None, expires_at: datetime = None,
                    token_hash: str = None) -> bool:
        """Store a revoked token in the database for permanent blacklisting"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute("""
                INSERT INTO cids.revoked_tokens
                (token_id, token_type, revoked_by, revoked_reason, user_email,
                 user_id, ip_address, expires_at, token_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (token_id) DO NOTHING
            """, (token_id, token_type, revoked_by, reason, user_email,
                  user_id, ip_address, expires_at, token_hash))

            self.conn.commit()
            logger.info(f"Token {token_id} revoked in database (reason: {reason})")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def is_token_revoked(self, token_id: str = None, token_hash: str = None) -> bool:
        """Check if a token has been revoked"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            if token_id:
                self.cursor.execute("""
                    SELECT 1 FROM cids.revoked_tokens
                    WHERE token_id = %s LIMIT 1
                """, (token_id,))
            elif token_hash:
                self.cursor.execute("""
                    SELECT 1 FROM cids.revoked_tokens
                    WHERE token_hash = %s LIMIT 1
                """, (token_hash,))
            else:
                return False

            result = self.cursor.fetchone()
            return result is not None

        except Exception as e:
            logger.error(f"Error checking token revocation: {e}")
            # In case of error, assume not revoked (fail open for availability)
            # But log the error for security monitoring
            return False

    def save_refresh_token(self, token_hash: str, user_email: str, user_id: str,
                          expires_at: datetime, client_ip: str = None,
                          user_agent: str = None, device_fingerprint: str = None,
                          parent_token_hash: str = None) -> bool:
        """Save refresh token info for tracking and rotation"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute("""
                INSERT INTO cids.refresh_tokens
                (token_hash, user_email, user_id, expires_at, client_ip,
                 user_agent, device_fingerprint, parent_token_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (token_hash) DO NOTHING
            """, (token_hash, user_email, user_id, expires_at, client_ip,
                  user_agent, device_fingerprint, parent_token_hash))

            self.conn.commit()
            logger.info(f"Refresh token saved for user {user_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to save refresh token: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def update_refresh_token_usage(self, token_hash: str) -> bool:
        """Update refresh token usage statistics"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute("""
                UPDATE cids.refresh_tokens
                SET last_used_at = CURRENT_TIMESTAMP,
                    use_count = use_count + 1
                WHERE token_hash = %s
            """, (token_hash,))

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to update refresh token usage: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def deactivate_refresh_token(self, token_hash: str) -> bool:
        """Deactivate a refresh token (for rotation)"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute("""
                UPDATE cids.refresh_tokens
                SET is_active = false
                WHERE token_hash = %s
            """, (token_hash,))

            # Also revoke it in the revoked_tokens table
            # For refresh tokens, use the hash as the token_id since we don't have a separate token_id
            self.cursor.execute("""
                INSERT INTO cids.revoked_tokens
                (token_id, token_hash, token_type, revoked_reason)
                VALUES (%s, %s, 'refresh', 'rotation')
                ON CONFLICT (token_id) DO NOTHING
            """, (token_hash, token_hash))

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to deactivate refresh token: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def cleanup_expired_tokens(self) -> int:
        """Clean up expired revoked tokens older than 7 days"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute("SELECT cids.cleanup_expired_revoked_tokens()")
            result = self.cursor.fetchone()
            self.conn.commit()

            deleted_count = result[0] if result else 0
            logger.info(f"Cleaned up {deleted_count} expired revoked tokens")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {e}")
            if self.conn:
                self.conn.rollback()
            return 0

    def validate_api_key_in_db(self, key_id: str, api_key: str) -> Union[bool, Tuple[str, str]]:
        """Validate an API key against the database
        Returns: False if invalid, or (client_id, name) tuple if valid
        """
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            import hashlib
            # Hash the provided API key
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()

            # Check if the API key exists and is active
            self.cursor.execute("""
                SELECT ak.client_id, ak.name, ak.is_active, ak.expires_at
                FROM cids.api_keys ak
                WHERE ak.key_hash = %s
                  AND ak.is_active = true
                  AND (ak.expires_at IS NULL OR ak.expires_at > CURRENT_TIMESTAMP)
            """, (key_hash,))

            result = self.cursor.fetchone()

            if result:
                # Handle both tuple and dict-like result formats
                if isinstance(result, (tuple, list)):
                    client_id, name = result[0], result[1]
                else:
                    # Handle dict-like format
                    client_id, name = result['client_id'], result['name']

                # Update last used timestamp and usage count
                self.cursor.execute("""
                    UPDATE cids.api_keys
                    SET last_used_at = CURRENT_TIMESTAMP,
                        usage_count = COALESCE(usage_count, 0) + 1
                    WHERE key_hash = %s
                """, (key_hash,))
                self.conn.commit()

                logger.info(f"API key validated successfully for app: {client_id}, updated last_used_at and usage_count")
                return (client_id, name)  # Return client_id and name
            else:
                logger.warning(f"API key validation failed - key not found or inactive")
                return False

        except Exception as e:
            import traceback
            logger.error(f"Failed to validate API key in database: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            if self.conn:
                self.conn.rollback()
            return False

    def create_api_key(self, app_id: str, key_id: str, key_hash: str, name: str,
                      permissions: List[str] = None, expires_at: str = None,
                      created_by: str = None, token_template_name: str = None,
                      app_roles_overrides: Dict = None, token_ttl_minutes: int = None,
                      default_audience: str = None, allowed_audiences: List[str] = None) -> bool:
        """Create a new API key in the database"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            # Generate log_id from UUID service
            import httpx
            log_id = None
            try:
                with httpx.Client(timeout=5.0) as client:
                    response = client.post(
                        "http://uuid-service-dev:8002/generate",
                        json={"type": "api_key", "prefix": "apk"}
                    )
                    if response.status_code == 200:
                        uuid_data = response.json()
                        log_id = uuid_data.get("id")
                        logger.info(f"Generated log_id from UUID service: {log_id}")
            except Exception as e:
                logger.warning(f"Failed to get UUID for log_id: {e}, using fallback")
                # Fallback to simple ID
                log_id = f"apk_{uuid.uuid4().hex[:12]}"

            # First, deactivate all existing API keys for this client_id
            self.cursor.execute("""
                UPDATE cids.api_keys
                SET is_active = FALSE
                WHERE client_id = %s AND is_active = TRUE
            """, (app_id,))  # app_id is actually the client_id

            deactivated_count = self.cursor.rowcount
            if deactivated_count > 0:
                logger.info(f"Deactivated {deactivated_count} existing API keys for client {app_id}")

            # Insert the new API key (using client_id directly, not app_id FK)
            from psycopg2.extras import Json
            self.cursor.execute("""
                INSERT INTO cids.api_keys (
                    client_id, key_id, key_hash, name,
                    expires_at, created_by, is_active,
                    log_id, token_template_name, app_roles_overrides,
                    token_ttl_minutes, default_audience, allowed_audiences
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                app_id,  # This is actually the client_id
                key_id, key_hash, name,
                expires_at, created_by, True,
                log_id, token_template_name,
                Json(app_roles_overrides) if app_roles_overrides else None,
                token_ttl_minutes, default_audience,
                Json(allowed_audiences) if allowed_audiences else None
            ))

            # Log to activity_log
            self.cursor.execute("""
                INSERT INTO cids.activity_log (
                    activity_id, activity_type, user_email, user_id,
                    entity_type, entity_id, entity_name, details
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                log_id,  # Use same log_id as activity_id
                'api_key.created',
                created_by,
                None,  # user_id
                'api_key',
                key_id,
                name,  # entity_name
                json.dumps({
                    'app_id': app_id,
                    'key_name': name,
                    'expires_at': expires_at,
                    'permissions': permissions
                })
            ))

            self.conn.commit()
            logger.info(f"API key created successfully for app {app_id}: {name} with log_id: {log_id}")
            return True

        except Exception as e:
            import traceback
            logger.error(f"Failed to create API key in database: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            if self.conn:
                self.conn.rollback()
            return False

    # A2A Permissions Management
    def get_all_a2a_permissions(self) -> List[Dict[str, Any]]:
        """Get all A2A permissions"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute("""
                SELECT
                    a2a_id as id,
                    source_client_id,
                    target_client_id,
                    allowed_scopes,
                    max_token_duration,
                    is_active,
                    created_at::text,
                    updated_at::text,
                    created_by,
                    updated_by
                FROM cids.a2a_permissions
                ORDER BY created_at DESC
            """)

            results = self.cursor.fetchall()
            return [dict(r) for r in results] if results else []

        except Exception as e:
            logger.error(f"Failed to get A2A permissions: {e}")
            return []

    def get_a2a_permission_by_id(self, permission_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific A2A permission by ID"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute("""
                SELECT
                    a2a_id as id,
                    source_client_id,
                    target_client_id,
                    allowed_scopes,
                    max_token_duration,
                    is_active,
                    created_at::text,
                    updated_at::text,
                    created_by,
                    updated_by
                FROM cids.a2a_permissions
                WHERE a2a_id = %s
            """, (permission_id,))

            result = self.cursor.fetchone()
            return dict(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get A2A permission {permission_id}: {e}")
            return None

    def create_a2a_permission(self, source_client_id: str, target_client_id: str,
                            allowed_scopes: List[str], max_token_duration: int = 300,
                            is_active: bool = True, created_by: str = 'admin') -> Optional[str]:
        """Create a new A2A permission"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            import uuid
            permission_id = str(uuid.uuid4())

            self.cursor.execute("""
                INSERT INTO cids.a2a_permissions
                (a2a_id, source_client_id, target_client_id, allowed_scopes,
                 max_token_duration, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING a2a_id
            """, (permission_id, source_client_id, target_client_id,
                  allowed_scopes, max_token_duration, is_active, created_by))

            self.conn.commit()
            result = self.cursor.fetchone()
            return result['a2a_id'] if result else None

        except Exception as e:
            logger.error(f"Failed to create A2A permission: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    def update_a2a_permission(self, permission_id: str, allowed_scopes: List[str],
                            max_token_duration: int, is_active: bool,
                            updated_by: str = 'admin') -> bool:
        """Update an existing A2A permission"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute("""
                UPDATE cids.a2a_permissions
                SET allowed_scopes = %s,
                    max_token_duration = %s,
                    is_active = %s,
                    updated_by = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE a2a_id = %s
            """, (allowed_scopes, max_token_duration, is_active,
                  updated_by, permission_id))

            self.conn.commit()
            return self.cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to update A2A permission {permission_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def delete_a2a_permission(self, permission_id: str) -> bool:
        """Delete an A2A permission"""
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            self.cursor.execute("""
                DELETE FROM cids.a2a_permissions
                WHERE a2a_id = %s
            """, (permission_id,))

            self.conn.commit()
            return self.cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to delete A2A permission {permission_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

# Singleton instance
db_service = DatabaseService()