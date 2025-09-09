#!/usr/bin/env python3
"""
Migration script to transfer CID data from JSON files to Supabase PostgreSQL database
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import Json, RealDictCursor
import hashlib
from typing import Dict, List, Any

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),  # Use localhost since we're outside Docker
    'port': os.getenv('DB_PORT', '54322'),  # Use the exposed port
    'database': os.getenv('DB_NAME', 'postgres'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')  # Supabase local default password
}

# JSON data directory
DATA_DIR = Path(__file__).parent / 'backend' / 'infra' / 'data' / 'app_data'

class CIDMigration:
    def __init__(self):
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to the PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            print("✅ Connected to PostgreSQL database")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            sys.exit(1)
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✅ Disconnected from database")
    
    def cleanup_schema(self):
        """Drop all tables in CIDS schema if they exist"""
        print("🧹 Cleaning up existing CIDS schema...")
        try:
            # Drop the entire CIDS schema cascade (this will drop all tables, functions, etc.)
            self.cursor.execute("DROP SCHEMA IF EXISTS cids CASCADE")
            self.conn.commit()
            print("✅ CIDS schema cleaned up successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to cleanup schema: {e}")
            self.conn.rollback()
            return False
    
    def execute_schema(self):
        """Execute the schema SQL file"""
        schema_file = Path(__file__).parent / 'backend' / 'database' / 'schema.sql'
        if not schema_file.exists():
            print(f"❌ Schema file not found: {schema_file}")
            return False
        
        try:
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            # Execute the schema
            self.cursor.execute(schema_sql)
            self.conn.commit()
            print("✅ Database schema created successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to create schema: {e}")
            self.conn.rollback()
            return False
    
    def load_json_file(self, filename: str) -> Dict:
        """Load JSON data from file"""
        file_path = DATA_DIR / filename
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load {filename}: {e}")
            return {}
    
    def migrate_registered_apps(self):
        """Migrate registered_apps.json to database"""
        print("\n📦 Migrating registered apps...")
        apps = self.load_json_file('registered_apps.json')
        
        for client_id, app_data in apps.items():
            try:
                self.cursor.execute("""
                    INSERT INTO cids.registered_apps (
                        client_id, name, description, redirect_uris, owner_email,
                        is_active, created_at, updated_at, discovery_endpoint,
                        allow_discovery, last_discovery_at, discovery_status, discovery_version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (client_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        redirect_uris = EXCLUDED.redirect_uris,
                        owner_email = EXCLUDED.owner_email,
                        is_active = EXCLUDED.is_active,
                        updated_at = EXCLUDED.updated_at,
                        discovery_endpoint = EXCLUDED.discovery_endpoint,
                        allow_discovery = EXCLUDED.allow_discovery,
                        last_discovery_at = EXCLUDED.last_discovery_at,
                        discovery_status = EXCLUDED.discovery_status,
                        discovery_version = EXCLUDED.discovery_version
                """, (
                    client_id,
                    app_data.get('name'),
                    app_data.get('description'),
                    Json(app_data.get('redirect_uris', [])),
                    app_data.get('owner_email'),
                    app_data.get('is_active', True),
                    app_data.get('created_at'),
                    app_data.get('updated_at'),
                    app_data.get('discovery_endpoint'),
                    app_data.get('allow_discovery', True),
                    app_data.get('last_discovery_at'),
                    app_data.get('discovery_status'),
                    app_data.get('discovery_version')
                ))
                print(f"  ✅ Migrated app: {app_data.get('name')}")
            except Exception as e:
                print(f"  ❌ Failed to migrate app {client_id}: {e}")
                self.conn.rollback()
                continue
        
        self.conn.commit()
        print(f"✅ Migrated {len(apps)} registered apps")
    
    def migrate_role_permissions(self):
        """Migrate role_permissions.json to roles and permissions tables"""
        print("\n🔐 Migrating roles and permissions...")
        role_perms = self.load_json_file('role_permissions.json')
        
        for client_id, roles_data in role_perms.items():
            for role_name, role_info in roles_data.items():
                try:
                    # Insert role
                    self.cursor.execute("""
                        INSERT INTO cids.roles (client_id, role_name, description, ad_groups)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (client_id, role_name) DO UPDATE SET
                            description = EXCLUDED.description,
                            ad_groups = EXCLUDED.ad_groups
                        RETURNING role_id
                    """, (
                        client_id,
                        role_name,
                        role_info.get('description', ''),
                        Json(role_info.get('ad_groups', []))
                    ))
                    
                    role_id = self.cursor.fetchone()['role_id']
                    
                    # Insert permissions
                    permissions = role_info.get('permissions', {})
                    for resource, actions in permissions.items():
                        for action, fields_data in actions.items():
                            if isinstance(fields_data, dict):
                                fields = fields_data.get('fields', [])
                                filters = fields_data.get('filters', {})
                            else:
                                fields = fields_data if isinstance(fields_data, list) else []
                                filters = {}
                            
                            self.cursor.execute("""
                                INSERT INTO cids.permissions (
                                    role_id, resource, action, fields, resource_filters
                                ) VALUES (%s, %s, %s, %s, %s)
                            """, (
                                role_id,
                                resource,
                                action,
                                Json(fields),
                                Json(filters)
                            ))
                    
                    print(f"  ✅ Migrated role: {client_id}/{role_name}")
                except Exception as e:
                    print(f"  ❌ Failed to migrate role {client_id}/{role_name}: {e}")
                    self.conn.rollback()
                    continue
        
        self.conn.commit()
        print(f"✅ Migrated roles and permissions")
    
    def migrate_token_templates(self):
        """Migrate token_templates.json to database"""
        print("\n🎫 Migrating token templates...")
        templates = self.load_json_file('token_templates.json')
        
        if isinstance(templates, list):
            template_list = templates
        else:
            template_list = templates.get('templates', [])
        
        for template in template_list:
            try:
                self.cursor.execute("""
                    INSERT INTO cids.token_templates (
                        name, description, claims_structure, ad_groups,
                        is_default, is_enabled, priority, created_at, updated_at, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE SET
                        description = EXCLUDED.description,
                        claims_structure = EXCLUDED.claims_structure,
                        ad_groups = EXCLUDED.ad_groups,
                        is_default = EXCLUDED.is_default,
                        is_enabled = EXCLUDED.is_enabled,
                        priority = EXCLUDED.priority,
                        updated_at = EXCLUDED.updated_at
                """, (
                    template.get('name'),
                    template.get('description', ''),
                    Json(template.get('claims', {})),
                    Json(template.get('ad_groups', [])),
                    template.get('is_default', False),
                    template.get('is_enabled', True),
                    template.get('priority', 0),
                    template.get('created_at', datetime.now().isoformat()),
                    template.get('updated_at', datetime.now().isoformat()),
                    template.get('created_by', 'migration')
                ))
                print(f"  ✅ Migrated template: {template.get('name')}")
            except Exception as e:
                print(f"  ❌ Failed to migrate template {template.get('name')}: {e}")
                self.conn.rollback()
                continue
        
        self.conn.commit()
        print(f"✅ Migrated {len(template_list)} token templates")
    
    def migrate_app_role_mappings(self):
        """Migrate app_role_mappings.json to database"""
        print("\n🔗 Migrating app role mappings...")
        mappings = self.load_json_file('app_role_mappings.json')
        
        count = 0
        for client_id, mappings_list in mappings.items():
            # Handle both old format (dict) and new format (list)
            if isinstance(mappings_list, list):
                # New format: list of mapping objects
                for mapping in mappings_list:
                    ad_group_name = mapping.get('ad_group')
                    role_name = mapping.get('app_role')
                    try:
                        self.cursor.execute("""
                            INSERT INTO cids.app_role_mappings (
                                client_id, ad_group_name, role_name
                            ) VALUES (%s, %s, %s)
                            ON CONFLICT (client_id, ad_group_name) DO UPDATE SET
                                role_name = EXCLUDED.role_name
                        """, (client_id, ad_group_name, role_name))
                        print(f"  ✅ Migrated mapping: {client_id}/{ad_group_name} -> {role_name}")
                        count += 1
                    except Exception as e:
                        print(f"  ❌ Failed to migrate mapping {client_id}/{ad_group_name}: {e}")
                        self.conn.rollback()
                        continue
            elif isinstance(mappings_list, dict):
                # Old format: simple dict mapping
                for ad_group_name, role_name in mappings_list.items():
                    try:
                        self.cursor.execute("""
                            INSERT INTO cids.app_role_mappings (
                                client_id, ad_group_name, role_name
                            ) VALUES (%s, %s, %s)
                            ON CONFLICT (client_id, ad_group_name) DO UPDATE SET
                                role_name = EXCLUDED.role_name
                        """, (client_id, ad_group_name, role_name))
                        print(f"  ✅ Migrated mapping: {client_id}/{ad_group_name} -> {role_name}")
                        count += 1
                    except Exception as e:
                        print(f"  ❌ Failed to migrate mapping {client_id}/{ad_group_name}: {e}")
                        self.conn.rollback()
                        continue
        
        self.conn.commit()
        print(f"✅ Migrated {count} app role mappings")
    
    def migrate_discovered_permissions(self):
        """Migrate discovered_permissions.json to database"""
        print("\n🔍 Migrating discovered permissions...")
        discovered = self.load_json_file('discovered_permissions.json')
        
        for client_id, permissions in discovered.items():
            for permission_key, perm_data in permissions.items():
                # Parse resource and action from key (format: "resource:action")
                if ':' in permission_key:
                    resource, action = permission_key.split(':', 1)
                else:
                    continue
                
                try:
                    self.cursor.execute("""
                        INSERT INTO cids.discovered_permissions (
                            client_id, resource, action, available_fields
                        ) VALUES (%s, %s, %s, %s)
                        ON CONFLICT (client_id, resource, action) DO UPDATE SET
                            available_fields = EXCLUDED.available_fields
                    """, (
                        client_id,
                        resource,
                        action,
                        Json(perm_data.get('fields', []))
                    ))
                    print(f"  ✅ Migrated permission: {client_id}/{permission_key}")
                except Exception as e:
                    print(f"  ❌ Failed to migrate permission {client_id}/{permission_key}: {e}")
                    self.conn.rollback()
                    continue
        
        self.conn.commit()
        print(f"✅ Migrated discovered permissions")
    
    def verify_migration(self):
        """Verify the migration was successful"""
        print("\n🔍 Verifying migration...")
        
        tables = [
            'registered_apps',
            'roles',
            'permissions',
            'token_templates',
            'app_role_mappings',
            'discovered_permissions'
        ]
        
        for table in tables:
            self.cursor.execute(f"SELECT COUNT(*) as count FROM cids.{table}")
            count = self.cursor.fetchone()['count']
            print(f"  📊 {table}: {count} records")
        
        print("✅ Migration verification complete")
    
    def run(self, skip_cleanup=False):
        """Run the complete migration"""
        print("🚀 Starting CID migration to Supabase...")
        print(f"📁 Data directory: {DATA_DIR}")
        
        # Connect to database
        self.connect()
        
        try:
            # Clean up existing schema unless skipped
            if not skip_cleanup:
                if not self.cleanup_schema():
                    print("⚠️  Schema cleanup failed, but continuing...")
            
            # Create schema
            if not self.execute_schema():
                print("❌ Schema creation failed. Aborting migration.")
                return
            
            # Migrate data
            self.migrate_registered_apps()
            self.migrate_role_permissions()
            self.migrate_token_templates()
            self.migrate_app_role_mappings()
            self.migrate_discovered_permissions()
            
            # Verify migration
            self.verify_migration()
            
            print("\n✅ Migration completed successfully!")
            print("\n📌 All tables have been created under the 'cids' schema")
            print("   You can access them using: cids.registered_apps, cids.roles, etc.")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            self.conn.rollback()
        finally:
            self.disconnect()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate CID data from JSON to Supabase')
    parser.add_argument('--skip-cleanup', action='store_true', 
                        help='Skip dropping existing CID schema')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    if not args.skip_cleanup and not args.yes:
        print("\n⚠️  WARNING: This will DROP the entire CIDS schema if it exists!")
        print("   All existing data in the CIDS schema will be lost.")
        response = input("\n   Do you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Migration cancelled.")
            sys.exit(0)
    
    migration = CIDMigration()
    migration.run(skip_cleanup=args.skip_cleanup)