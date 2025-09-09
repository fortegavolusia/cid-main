"""
Database operations for Discovery Service
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor, Json

logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "host": "supabase_db_mi-proyecto-supabase",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "postgres"
}

class DiscoveryDatabase:
    """Handle all database operations for discovery service"""
    
    def __init__(self):
        self.db_config = DB_CONFIG
        
    def get_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(**self.db_config)
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            # Fallback to localhost if container name fails
            try:
                config = self.db_config.copy()
                config["host"] = "localhost"
                config["port"] = 54322
                return psycopg2.connect(**config)
            except Exception as e2:
                logger.error(f"Failed to connect to localhost database: {e2}")
                raise
    
    def save_discovery_history(self, client_id: str, discovery_data: Dict, 
                              discovered_by: str = "system") -> Optional[int]:
        """Save discovery results to database"""
        logger.info(f"[DB] Attempting to save discovery history for {client_id}")
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Insert into discovery_history
            cursor.execute("""
                INSERT INTO cids.discovery_history 
                (client_id, discovery_timestamp, discovery_version, app_name, 
                 app_description, base_url, endpoints_count, discovery_data, 
                 status, discovered_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                client_id,
                datetime.utcnow(),
                discovery_data.get('version', discovery_data.get('discovery_version', '2.0')),
                discovery_data.get('app_name', ''),
                discovery_data.get('description', ''),
                discovery_data.get('base_url', ''),
                len(discovery_data.get('endpoints', [])),
                Json(discovery_data),
                'success',
                discovered_by
            ))
            
            history_id = cursor.fetchone()['id']
            
            # Insert endpoints
            endpoints = discovery_data.get('endpoints', [])
            for endpoint in endpoints:
                cursor.execute("""
                    INSERT INTO cids.discovery_endpoints
                    (history_id, method, path, operation_id, description,
                     resource, action, parameters, response_fields, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    history_id,
                    endpoint.get('method', 'GET'),
                    endpoint.get('path', ''),
                    endpoint.get('operation_id'),
                    endpoint.get('description', ''),
                    endpoint.get('resource'),
                    endpoint.get('action'),
                    Json(endpoint.get('parameters', [])),
                    Json(endpoint.get('response_fields', {})),
                    datetime.utcnow()
                ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Saved discovery history to database for {client_id} with {len(endpoints)} endpoints")
            return history_id
            
        except Exception as e:
            logger.error(f"Error saving discovery history to database: {e}")
            if conn:
                conn.rollback()
            return None
    
    def save_discovered_permissions(self, client_id: str, permissions: Dict) -> bool:
        """Save discovered permissions to database"""
        logger.info(f"[DB] Attempting to save discovered permissions for {client_id}")
        logger.debug(f"[DB] Permissions structure: {list(permissions.keys())[:3] if permissions else 'empty'}")
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Group permissions by resource and action
            grouped_permissions = {}
            
            for perm_key, perm_metadata in permissions.items():
                # Extract resource and action from the permission metadata
                resource = perm_metadata.resource if hasattr(perm_metadata, 'resource') else None
                action = perm_metadata.action if hasattr(perm_metadata, 'action') else None
                field_path = perm_metadata.field_path if hasattr(perm_metadata, 'field_path') else None
                
                if not resource or not action or not field_path:
                    continue
                
                # Create structure if not exists
                if resource not in grouped_permissions:
                    grouped_permissions[resource] = {}
                if action not in grouped_permissions[resource]:
                    grouped_permissions[resource][action] = []
                
                # Create field entry with sensitivity info
                field_entry = {
                    'name': field_path,
                    'allowed': True,
                    'description': perm_metadata.description if hasattr(perm_metadata, 'description') else ''
                }
                
                # Add sensitivity flags
                if hasattr(perm_metadata, 'pii') and perm_metadata.pii:
                    field_entry['is_pii'] = True
                if hasattr(perm_metadata, 'phi') and perm_metadata.phi:
                    field_entry['is_phi'] = True
                if hasattr(perm_metadata, 'sensitive') and perm_metadata.sensitive:
                    field_entry['is_sensitive'] = True
                # Check for financial (might be in different attribute)
                if hasattr(perm_metadata, 'financial') and perm_metadata.financial:
                    field_entry['is_financial'] = True
                    
                grouped_permissions[resource][action].append(field_entry)
            
            # Now save the grouped permissions
            count = 0
            for resource_name, actions in grouped_permissions.items():
                for action_name, fields in actions.items():
                    count += 1
                    
                    # Upsert into discovered_permissions
                    cursor.execute("""
                        INSERT INTO cids.discovered_permissions 
                        (client_id, resource, action, available_fields, discovered_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (client_id, resource, action) 
                        DO UPDATE SET 
                            available_fields = EXCLUDED.available_fields,
                            discovered_at = CURRENT_TIMESTAMP
                    """, (
                        client_id,
                        resource_name,
                        action_name,
                        Json(fields)
                    ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Saved {count} discovered permissions to database for {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving discovered permissions to database: {e}")
            if conn:
                conn.rollback()
            return False
    
    def update_app_discovery_status(self, client_id: str, user_email: str = None) -> bool:
        """Update app's last discovery timestamp"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE cids.registered_apps 
                SET last_discovery_run_at = CURRENT_TIMESTAMP,
                    last_discovery_run_by = %s,
                    discovery_run_count = COALESCE(discovery_run_count, 0) + 1,
                    discovery_status = 'success'
                WHERE client_id = %s
            """, (user_email or 'system', client_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating app discovery status: {e}")
            if conn:
                conn.rollback()
            return False
    
    def log_discovery_activity(self, client_id: str, app_name: str, 
                               user_email: str = None, details: Dict = None,
                               status: str = 'success', error_message: str = None) -> bool:
        """Log discovery activity"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO cids.activity_log 
                (activity_type, entity_type, entity_id, entity_name, 
                 user_email, details, status, error_message, timestamp)
                VALUES ('discovery_run', 'app', %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                client_id,
                app_name,
                user_email or 'system',
                Json(details or {}),
                status,
                error_message
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging discovery activity: {e}")
            if conn:
                conn.rollback()
            return False
    
    def get_latest_discovery(self, client_id: str) -> Optional[Dict]:
        """Get latest discovery data for an app"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM cids.discovery_history 
                WHERE client_id = %s 
                ORDER BY discovery_timestamp DESC 
                LIMIT 1
            """, (client_id,))
            
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Error getting latest discovery: {e}")
            return None
    
    def get_discovered_permissions(self, client_id: str) -> Dict:
        """Get discovered permissions from database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT resource, action, available_fields 
                FROM cids.discovered_permissions 
                WHERE client_id = %s AND is_active = true
            """, (client_id,))
            
            rows = cursor.fetchall()
            
            # Convert to expected format
            permissions = {}
            for row in rows:
                resource = row['resource']
                if resource not in permissions:
                    permissions[resource] = {
                        'actions': {},
                        'description': f"Permissions for {resource}"
                    }
                
                # Convert available_fields back to dict format
                fields = {}
                for field in row['available_fields']:
                    fields[field['name']] = {
                        'allowed': field.get('allowed', True),
                        'sensitivity': field.get('sensitivity', {})
                    }
                
                permissions[resource]['actions'][row['action']] = {
                    'fields': fields
                }
            
            cursor.close()
            conn.close()
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting discovered permissions: {e}")
            return {}

# Create singleton instance
discovery_db = DiscoveryDatabase()