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
                              discovered_by: str = "system") -> Optional[str]:
        """Save discovery results to database"""
        logger.info(f"[DB] Attempting to save discovery history for {client_id}")
        try:
            # Generate UUID with 'dis' prefix from UUID service
            discovery_id = None
            try:
                import httpx
                with httpx.Client() as http_client:
                    response = http_client.post(
                        "http://uuid-service-dev:8002/generate",
                        json={
                            "type": "custom",
                            "prefix": "dis",
                            "format": "uuid_v4",
                            "requestor": "cids_discovery",
                            "description": f"Discovery for app {client_id}"
                        }
                    )
                    if response.status_code == 200:
                        discovery_id = response.json().get("id")
                        logger.info(f"Generated discovery ID from UUID service: {discovery_id}")
            except Exception as e:
                logger.warning(f"Could not get UUID from service: {e}, using fallback")
                import uuid
                discovery_id = f"dis_{uuid.uuid4().hex[:16]}"
            
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Insert into discovery_history with the generated discovery_id
            cursor.execute("""
                INSERT INTO cids.discovery_history 
                (discovery_id, client_id, discovery_timestamp, discovery_version, app_name, 
                 app_description, base_url, endpoints_count, discovery_data, 
                 status, discovered_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING discovery_id
            """, (
                discovery_id,
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
            
            returned_discovery_id = cursor.fetchone()['discovery_id']
            
            # Insert endpoints with discovery_id reference
            endpoints = discovery_data.get('endpoints', [])
            for endpoint in endpoints:
                cursor.execute("""
                    INSERT INTO cids.discovery_endpoints
                    (discovery_id, method, path, operation_id, description,
                     resource, action, parameters, response_fields, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    discovery_id,
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
            
            # Count fields in response_fields
            field_count = 0
            for endpoint in endpoints:
                response_fields = endpoint.get('response_fields', {})
                if isinstance(response_fields, dict):
                    field_count += len(response_fields)

            # Update registered_apps with discovery information including field_count
            cursor.execute("""
                UPDATE cids.registered_apps
                SET last_discovery_at = %s,
                    discovery_status = %s,
                    discovery_version = %s,
                    last_discovery_run_at = %s,
                    last_discovery_run_by = %s,
                    discovery_run_count = COALESCE(discovery_run_count, 0) + 1,
                    field_count = %s
                WHERE client_id = %s
            """, (
                datetime.utcnow(),
                'success',
                discovery_data.get('version', discovery_data.get('discovery_version', '2.0')),
                datetime.utcnow(),
                discovered_by,
                field_count,
                client_id
            ))

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Saved discovery history to database for {client_id} with discovery_id: {discovery_id} and {len(endpoints)} endpoints")
            logger.info(f"Updated registered_apps discovery fields for {client_id}")
            return discovery_id
            
        except Exception as e:
            logger.error(f"Error saving discovery history to database: {e}")
            if conn:
                conn.rollback()
            return None
    
    def save_discovered_permissions(self, client_id: str, permissions: Dict, discovery_id: str = None) -> bool:
        """Save discovered permissions to database"""
        logger.info(f"[CATEGORY DEBUG] ===== STARTING save_discovered_permissions =====")
        logger.info(f"[DB] Attempting to save discovered permissions for {client_id} with discovery_id: {discovery_id}")
        logger.debug(f"[DB] Permissions structure: {list(permissions.keys())[:3] if permissions else 'empty'}")
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
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
            
            # Now save the grouped permissions with category-based permissions
            count = 0
            for resource_name, actions in grouped_permissions.items():
                for action_name, fields in actions.items():
                    # Get sensitivity flags from field_metadata table for this discovery
                    field_names = [f['name'] for f in fields]
                    logger.info(f"[CATEGORY DEBUG] Processing {resource_name}.{action_name} with fields: {field_names}")
                    
                    if not field_names:
                        logger.warning(f"[CATEGORY DEBUG] No field names found for {resource_name}.{action_name}")
                    
                    placeholders = ','.join(['%s'] * len(field_names)) if field_names else "''"
                    
                    query = f"""
                        SELECT field_name, is_pii, is_phi, is_financial, is_sensitive
                        FROM cids.field_metadata
                        WHERE discovery_id = %s AND field_name IN ({placeholders})
                    """
                    params = [discovery_id] + field_names if field_names else [discovery_id]
                    
                    logger.info(f"[CATEGORY DEBUG] Executing query with discovery_id: {discovery_id}")
                    cursor.execute(query, params)
                    
                    results = cursor.fetchall()
                    logger.info(f"[CATEGORY DEBUG] Found {len(results)} field sensitivities in field_metadata")
                    
                    field_sensitivities = {row['field_name']: row for row in results}
                    
                    # Log what we found
                    for fname, sens in field_sensitivities.items():
                        logger.info(f"[CATEGORY DEBUG] Field '{fname}': pii={sens.get('is_pii')}, phi={sens.get('is_phi')}, financial={sens.get('is_financial')}, sensitive={sens.get('is_sensitive')}")
                    
                    # Update fields with sensitivity info from database
                    for field in fields:
                        if field['name'] in field_sensitivities:
                            sensitivity = field_sensitivities[field['name']]
                            field['is_pii'] = sensitivity.get('is_pii', False)
                            field['is_phi'] = sensitivity.get('is_phi', False)
                            field['is_financial'] = sensitivity.get('is_financial', False)
                            field['is_sensitive'] = sensitivity.get('is_sensitive', False)
                            logger.info(f"[CATEGORY DEBUG] Updated field '{field['name']}' with sensitivity flags")
                        else:
                            logger.warning(f"[CATEGORY DEBUG] Field '{field['name']}' not found in field_metadata")
                    
                    # Determine which categories are needed based on field flags
                    has_pii = any(f.get('is_pii', False) for f in fields)
                    has_phi = any(f.get('is_phi', False) for f in fields)
                    has_financial = any(f.get('is_financial', False) for f in fields)
                    has_sensitive = any(f.get('is_sensitive', False) for f in fields)
                    
                    logger.info(f"[CATEGORY DEBUG] Categories needed - PII: {has_pii}, PHI: {has_phi}, Financial: {has_financial}, Sensitive: {has_sensitive}")
                    
                    # 1. Always create base permission (for non-sensitive fields)
                    import httpx
                    try:
                        base_perm_response = httpx.post(
                            "http://uuid-service-dev:8002/generate",
                            json={"prefix": "per"}
                        )
                        base_perm_id = base_perm_response.json().get("id") if base_perm_response.status_code == 200 else None
                    except:
                        base_perm_id = None
                    
                    count += 1
                    cursor.execute("""
                        INSERT INTO cids.discovered_permissions 
                        (permission_id, discovery_id, client_id, resource, action, category, field_name, description, available_fields, discovered_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (client_id, resource, action, category, field_name) 
                        DO UPDATE SET 
                            permission_id = EXCLUDED.permission_id,
                            discovery_id = EXCLUDED.discovery_id,
                            description = EXCLUDED.description,
                            available_fields = EXCLUDED.available_fields,
                            discovered_at = CURRENT_TIMESTAMP
                    """, (
                        base_perm_id,
                        discovery_id,
                        client_id,
                        resource_name,
                        action_name,
                        'base',
                        f'{action_name.capitalize()} non-sensitive {resource_name} data',
                        Json([f for f in fields if not any([f.get('is_pii'), f.get('is_phi'), f.get('is_financial'), f.get('is_sensitive')])])
                    ))
                    
                    # 2. Create PII category permission if needed
                    if has_pii:
                        count += 1
                        cursor.execute("""
                            INSERT INTO cids.discovered_permissions 
                            (discovery_id, client_id, resource, action, category, description, available_fields, discovered_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (client_id, resource, action, category, field_name) 
                            DO UPDATE SET 
                                discovery_id = EXCLUDED.discovery_id,
                                description = EXCLUDED.description,
                                available_fields = EXCLUDED.available_fields,
                                discovered_at = CURRENT_TIMESTAMP
                        """, (
                            discovery_id,
                            client_id,
                            resource_name,
                            action_name,
                            'pii',
                            f'{action_name.capitalize()} PII {resource_name} data',
                            Json([f for f in fields if f.get('is_pii', False)])
                        ))
                    
                    # 3. Create PHI category permission if needed
                    if has_phi:
                        count += 1
                        cursor.execute("""
                            INSERT INTO cids.discovered_permissions 
                            (discovery_id, client_id, resource, action, category, description, available_fields, discovered_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (client_id, resource, action, category, field_name) 
                            DO UPDATE SET 
                                discovery_id = EXCLUDED.discovery_id,
                                description = EXCLUDED.description,
                                available_fields = EXCLUDED.available_fields,
                                discovered_at = CURRENT_TIMESTAMP
                        """, (
                            discovery_id,
                            client_id,
                            resource_name,
                            action_name,
                            'phi',
                            f'{action_name.capitalize()} PHI {resource_name} data',
                            Json([f for f in fields if f.get('is_phi', False)])
                        ))
                    
                    # 4. Create financial category permission if needed
                    if has_financial:
                        count += 1
                        cursor.execute("""
                            INSERT INTO cids.discovered_permissions 
                            (discovery_id, client_id, resource, action, category, description, available_fields, discovered_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (client_id, resource, action, category, field_name) 
                            DO UPDATE SET 
                                discovery_id = EXCLUDED.discovery_id,
                                description = EXCLUDED.description,
                                available_fields = EXCLUDED.available_fields,
                                discovered_at = CURRENT_TIMESTAMP
                        """, (
                            discovery_id,
                            client_id,
                            resource_name,
                            action_name,
                            'financial',
                            f'{action_name.capitalize()} financial {resource_name} data',
                            Json([f for f in fields if f.get('is_financial', False)])
                        ))
                    
                    # 5. Create sensitive category permission if needed (catch-all for other sensitive data)
                    if has_sensitive:
                        count += 1
                        cursor.execute("""
                            INSERT INTO cids.discovered_permissions 
                            (discovery_id, client_id, resource, action, category, description, available_fields, discovered_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (client_id, resource, action, category, field_name) 
                            DO UPDATE SET 
                                discovery_id = EXCLUDED.discovery_id,
                                description = EXCLUDED.description,
                                available_fields = EXCLUDED.available_fields,
                                discovered_at = CURRENT_TIMESTAMP
                        """, (
                            discovery_id,
                            client_id,
                            resource_name,
                            action_name,
                            'sensitive',
                            f'{action_name.capitalize()} sensitive {resource_name} data',
                            Json([f for f in fields if f.get('is_sensitive', False)])
                        ))
                    
                    # 6. Always create wildcard permission for full access
                    count += 1
                    cursor.execute("""
                        INSERT INTO cids.discovered_permissions 
                        (discovery_id, client_id, resource, action, category, description, available_fields, discovered_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (client_id, resource, action, category, field_name) 
                        DO UPDATE SET 
                            discovery_id = EXCLUDED.discovery_id,
                            description = EXCLUDED.description,
                            available_fields = EXCLUDED.available_fields,
                            discovered_at = CURRENT_TIMESTAMP
                    """, (
                        discovery_id,
                        client_id,
                        resource_name,
                        action_name,
                        'wildcard',
                        f'{action_name.capitalize()} all {resource_name} data (full access)',
                        Json(fields)  # All fields
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
                               status: str = 'success', error_message: str = None,
                               discovery_id: str = None) -> bool:
        """Log discovery activity with dis_ prefix from UUID service"""
        try:
            # Use the provided discovery_id - it should always be provided from save_discovery_history
            activity_id = discovery_id
            if not activity_id:
                logger.warning(f"No discovery_id provided for activity log - this should not happen!")
                # Don't generate a new one, just log without it
                activity_id = None
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Include discovery_id in details
            if activity_id and details:
                details['discovery_id'] = activity_id
            elif activity_id:
                details = {'discovery_id': activity_id}
            
            cursor.execute("""
                INSERT INTO cids.activity_log 
                (activity_id, activity_type, entity_type, entity_id, entity_name, 
                 user_email, details, status, error_message, timestamp)
                VALUES (%s, 'discovery_run', 'app', %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                activity_id,
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
    def generate_category_permissions(self, client_id: str, discovery_id: str) -> int:
        """
        Generate category-based permissions after discovery is complete.
        This runs AFTER field_metadata has been saved.
        
        Process:
        1. Read field_metadata to determine which fields have sensitivity flags
        2. Group by resource/action to determine which categories are needed
        3. Create additional permission entries for each category
        
        Returns: Number of category permissions created
        """
        logger.info(f"[CATEGORY] Starting category permission generation for {client_id} with discovery_id: {discovery_id}")
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Step 1: Get all unique resource/action combinations from discovered_permissions
            cursor.execute("""
                SELECT DISTINCT resource, action 
                FROM cids.discovered_permissions 
                WHERE client_id = %s AND discovery_id = %s
            """, (client_id, discovery_id))
            
            resource_actions = cursor.fetchall()
            logger.info(f"[CATEGORY] Found {len(resource_actions)} resource/action combinations")
            
            categories_created = 0
            
            for ra in resource_actions:
                resource = ra['resource']
                action = ra['action']
                
                # Step 2: Get field sensitivity information from field_metadata
                # Filter by the specific resource and action to get only relevant fields
                cursor.execute("""
                    SELECT DISTINCT
                        fm.field_name,
                        fm.is_pii,
                        fm.is_phi,
                        fm.is_financial,
                        fm.is_sensitive
                    FROM cids.field_metadata fm
                    JOIN cids.discovery_endpoints de ON fm.endpoint_id = de.endpoint_id
                    WHERE fm.discovery_id = %s 
                    AND de.resource = %s
                    AND de.action = %s
                """, (discovery_id, resource, action))
                
                fields = cursor.fetchall()
                logger.info(f"[CATEGORY] Found {len(fields)} fields for {resource}.{action}")
                
                # Step 3: Determine which categories are needed and collect field names
                has_pii = any(f['is_pii'] for f in fields if f['is_pii'])
                has_phi = any(f['is_phi'] for f in fields if f['is_phi'])
                has_financial = any(f['is_financial'] for f in fields if f['is_financial'])
                has_sensitive = any(f['is_sensitive'] for f in fields if f['is_sensitive'])
                
                # Collect field names by category for available_fields
                pii_fields = [f['field_name'] for f in fields if f['is_pii']]
                phi_fields = [f['field_name'] for f in fields if f['is_phi']]
                financial_fields = [f['field_name'] for f in fields if f['is_financial']]
                sensitive_fields = [f['field_name'] for f in fields if f['is_sensitive']]
                all_sensitive_fields = list(set(pii_fields + phi_fields + financial_fields + sensitive_fields))
                
                logger.info(f"[CATEGORY] {resource}.{action} - PII: {has_pii}, PHI: {has_phi}, Financial: {has_financial}, Sensitive: {has_sensitive}")
                
                # Generate permission_id for base permission (always created)
                import httpx
                import json
                
                # Step 4: Create category permissions as needed
                if has_pii:
                    # Generate permission_id for PII category
                    try:
                        pii_perm_response = httpx.post("http://uuid-service-dev:8002/generate", json={"prefix": "per"})
                        pii_perm_id = pii_perm_response.json().get("id") if pii_perm_response.status_code == 200 else None
                    except:
                        pii_perm_id = None
                    
                    cursor.execute("""
                        INSERT INTO cids.discovered_permissions 
                        (permission_id, discovery_id, client_id, resource, action, category, field_name, description, available_fields, discovered_at)
                        VALUES (%s, %s, %s, %s, %s, 'pii', NULL, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (client_id, resource, action, category, field_name) 
                        DO UPDATE SET 
                            permission_id = EXCLUDED.permission_id,
                            discovery_id = EXCLUDED.discovery_id,
                            description = EXCLUDED.description,
                            available_fields = EXCLUDED.available_fields,
                            discovered_at = CURRENT_TIMESTAMP
                    """, (
                        pii_perm_id,
                        discovery_id,
                        client_id,
                        resource,
                        action,
                        f'{action.capitalize()} PII {resource} data',
                        json.dumps(pii_fields)
                    ))
                    categories_created += 1
                    logger.info(f"[CATEGORY] Created PII permission for {resource}.{action}")
                
                if has_phi:
                    # Generate permission_id for PHI category
                    try:
                        phi_perm_response = httpx.post("http://uuid-service-dev:8002/generate", json={"prefix": "per"})
                        phi_perm_id = phi_perm_response.json().get("id") if phi_perm_response.status_code == 200 else None
                    except:
                        phi_perm_id = None
                    
                    cursor.execute("""
                        INSERT INTO cids.discovered_permissions 
                        (permission_id, discovery_id, client_id, resource, action, category, field_name, description, available_fields, discovered_at)
                        VALUES (%s, %s, %s, %s, %s, 'phi', NULL, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (client_id, resource, action, category, field_name) 
                        DO UPDATE SET 
                            permission_id = EXCLUDED.permission_id,
                            discovery_id = EXCLUDED.discovery_id,
                            description = EXCLUDED.description,
                            available_fields = EXCLUDED.available_fields,
                            discovered_at = CURRENT_TIMESTAMP
                    """, (
                        phi_perm_id,
                        discovery_id,
                        client_id,
                        resource,
                        action,
                        f'{action.capitalize()} PHI {resource} data',
                        json.dumps(phi_fields)
                    ))
                    categories_created += 1
                    logger.info(f"[CATEGORY] Created PHI permission for {resource}.{action}")
                
                if has_financial:
                    # Generate permission_id for financial category
                    try:
                        fin_perm_response = httpx.post("http://uuid-service-dev:8002/generate", json={"prefix": "per"})
                        fin_perm_id = fin_perm_response.json().get("id") if fin_perm_response.status_code == 200 else None
                    except:
                        fin_perm_id = None
                    
                    cursor.execute("""
                        INSERT INTO cids.discovered_permissions 
                        (permission_id, discovery_id, client_id, resource, action, category, field_name, description, available_fields, discovered_at)
                        VALUES (%s, %s, %s, %s, %s, 'financial', NULL, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (client_id, resource, action, category, field_name) 
                        DO UPDATE SET 
                            permission_id = EXCLUDED.permission_id,
                            discovery_id = EXCLUDED.discovery_id,
                            description = EXCLUDED.description,
                            available_fields = EXCLUDED.available_fields,
                            discovered_at = CURRENT_TIMESTAMP
                    """, (
                        fin_perm_id,
                        discovery_id,
                        client_id,
                        resource,
                        action,
                        f'{action.capitalize()} financial {resource} data',
                        json.dumps(financial_fields)
                    ))
                    categories_created += 1
                    logger.info(f"[CATEGORY] Created financial permission for {resource}.{action}")
                
                if has_sensitive:
                    # Generate permission_id for sensitive category
                    try:
                        sens_perm_response = httpx.post("http://uuid-service-dev:8002/generate", json={"prefix": "per"})
                        sens_perm_id = sens_perm_response.json().get("id") if sens_perm_response.status_code == 200 else None
                    except:
                        sens_perm_id = None
                    
                    cursor.execute("""
                        INSERT INTO cids.discovered_permissions 
                        (permission_id, discovery_id, client_id, resource, action, category, field_name, description, available_fields, discovered_at)
                        VALUES (%s, %s, %s, %s, %s, 'sensitive', NULL, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (client_id, resource, action, category, field_name) 
                        DO UPDATE SET 
                            permission_id = EXCLUDED.permission_id,
                            discovery_id = EXCLUDED.discovery_id,
                            description = EXCLUDED.description,
                            available_fields = EXCLUDED.available_fields,
                            discovered_at = CURRENT_TIMESTAMP
                    """, (
                        sens_perm_id,
                        discovery_id,
                        client_id,
                        resource,
                        action,
                        f'{action.capitalize()} sensitive {resource} data',
                        json.dumps(sensitive_fields)
                    ))
                    categories_created += 1
                    logger.info(f"[CATEGORY] Created sensitive permission for {resource}.{action}")
                
                # Always create wildcard permission for full access
                try:
                    wild_perm_response = httpx.post("http://uuid-service-dev:8002/generate", json={"prefix": "per"})
                    wild_perm_id = wild_perm_response.json().get("id") if wild_perm_response.status_code == 200 else None
                except:
                    wild_perm_id = None
                
                cursor.execute("""
                    INSERT INTO cids.discovered_permissions 
                    (permission_id, discovery_id, client_id, resource, action, category, field_name, description, available_fields, discovered_at)
                    VALUES (%s, %s, %s, %s, %s, 'wildcard', NULL, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (client_id, resource, action, category, field_name) 
                    DO UPDATE SET 
                        permission_id = EXCLUDED.permission_id,
                        discovery_id = EXCLUDED.discovery_id,
                        description = EXCLUDED.description,
                        available_fields = EXCLUDED.available_fields,
                        discovered_at = CURRENT_TIMESTAMP
                """, (
                    wild_perm_id,
                    discovery_id,
                    client_id,
                    resource,
                    action,
                    f'{action.capitalize()} all {resource} data (full access)',
                    json.dumps(all_sensitive_fields if all_sensitive_fields else ["*"])  # If no sensitive fields, wildcard means all
                ))
                categories_created += 1
                logger.info(f"[CATEGORY] Created wildcard permission for {resource}.{action}")
            
                # Step 4: Field-level permissions removed to avoid constraint conflicts
                # Only creating base, category (pii, phi, financial, sensitive) and wildcard permissions
                logger.info(f"[CATEGORY] Skipping field-level permissions to avoid constraint conflicts")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"[CATEGORY] Successfully created {categories_created} category permissions for {client_id}")
            return categories_created
            
        except Exception as e:
            logger.error(f"[CATEGORY] Error generating category permissions: {e}")
            if conn:
                conn.rollback()
            return 0


discovery_db = DiscoveryDatabase()