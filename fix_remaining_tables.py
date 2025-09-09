#!/usr/bin/env python3
"""
Fix and migrate the remaining problematic JSON files
"""

import json
import os
import subprocess
import re

DATA_DIR = '/home/dpi/projects/CID/backend/infra/data/app_data'

def execute_sql(sql: str) -> tuple[bool, str]:
    """Execute SQL in Supabase"""
    try:
        cmd = ['docker', 'exec', 'supabase_db_mi-proyecto-supabase', 'psql', '-U', 'postgres', '-c', sql]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return False, str(e)

def clean_column_name(name: str) -> str:
    """Clean column name to be SQL-safe"""
    # Remove or replace problematic characters
    name = name.replace('-', '_').replace(' ', '_').replace('.', '_').replace('*', 'all')
    # Remove non-alphanumeric characters except underscore
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    # Ensure it doesn't start with a number
    if name and name[0].isdigit():
        name = 'col_' + name
    return name.lower()

def escape_value(value):
    """Escape value for SQL"""
    if value is None:
        return 'NULL'
    elif isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, (dict, list)):
        json_str = json.dumps(value, default=str)
        return "'" + json_str.replace("'", "''") + "'::jsonb"
    else:
        str_value = str(value)
        return "'" + str_value.replace("'", "''") + "'"

def fix_app_api_keys():
    """Fix app_api_keys table"""
    print("\n📁 Fixing app_api_keys.json")
    
    with open(f"{DATA_DIR}/app_api_keys.json", 'r') as f:
        data = json.load(f)
    
    # Store as JSONB since the keys are dynamic
    create_sql = """
    CREATE TABLE IF NOT EXISTS cid.app_api_keys (
        id SERIAL PRIMARY KEY,
        client_id VARCHAR(255),
        api_keys JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    success, msg = execute_sql(create_sql)
    if success:
        print("✅ Table created")
    else:
        print(f"❌ Failed to create table: {msg}")
        return
    
    # Insert each app's API keys
    for client_id, api_keys in data.items():
        insert_sql = f"""
        INSERT INTO cid.app_api_keys (client_id, api_keys)
        VALUES ({escape_value(client_id)}, {escape_value(api_keys)});
        """
        success, msg = execute_sql(insert_sql)
        if success:
            print(f"✅ Inserted API keys for {client_id}")
        else:
            print(f"❌ Failed to insert {client_id}: {msg}")

def fix_app_endpoints():
    """Fix app_endpoints table"""
    print("\n📁 Fixing app_endpoints.json")
    
    with open(f"{DATA_DIR}/app_endpoints.json", 'r') as f:
        data = json.load(f)
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS cid.app_endpoints (
        id SERIAL PRIMARY KEY,
        client_id VARCHAR(255),
        endpoints JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    success, msg = execute_sql(create_sql)
    if success:
        print("✅ Table created")
    else:
        print(f"❌ Failed to create table: {msg}")
        return
    
    for client_id, endpoints in data.items():
        insert_sql = f"""
        INSERT INTO cid.app_endpoints (client_id, endpoints)
        VALUES ({escape_value(client_id)}, {escape_value(endpoints)});
        """
        success, msg = execute_sql(insert_sql)
        if success:
            print(f"✅ Inserted endpoints for {client_id}")
        else:
            print(f"❌ Failed to insert {client_id}: {msg}")

def fix_permissions_registry():
    """Fix permissions_registry table"""
    print("\n📁 Fixing permissions_registry.json")
    
    with open(f"{DATA_DIR}/permissions_registry.json", 'r') as f:
        data = json.load(f)
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS cid.permissions_registry (
        id SERIAL PRIMARY KEY,
        client_id VARCHAR(255),
        permissions JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    success, msg = execute_sql(create_sql)
    if success:
        print("✅ Table created")
    else:
        print(f"❌ Failed to create table: {msg}")
        return
    
    for client_id, permissions in data.items():
        insert_sql = f"""
        INSERT INTO cid.permissions_registry (client_id, permissions)
        VALUES ({escape_value(client_id)}, {escape_value(permissions)});
        """
        success, msg = execute_sql(insert_sql)
        if success:
            print(f"✅ Inserted permissions for {client_id}")
        else:
            print(f"❌ Failed to insert {client_id}: {msg}")

def fix_registered_apps():
    """Fix registered_apps table"""
    print("\n📁 Fixing registered_apps.json")
    
    with open(f"{DATA_DIR}/registered_apps.json", 'r') as f:
        data = json.load(f)
    
    # Get first record to analyze structure
    sample = next(iter(data.values()))
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS cid.registered_apps (
        id SERIAL PRIMARY KEY,
        client_id VARCHAR(255) UNIQUE,
        name VARCHAR(255),
        description TEXT,
        redirect_uris JSONB,
        owner VARCHAR(255),
        api_key_required BOOLEAN,
        discovery_endpoint VARCHAR(500),
        created_date TIMESTAMP,
        last_discovered TIMESTAMP,
        role_mappings JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    success, msg = execute_sql(create_sql)
    if success:
        print("✅ Table created")
    else:
        print(f"❌ Failed to create table: {msg}")
        return
    
    for client_id, app_data in data.items():
        # Parse timestamps
        created_date = app_data.get('created_at', app_data.get('created'))
        if created_date and isinstance(created_date, str):
            created_date = f"'{created_date}'"
        else:
            created_date = 'NULL'
        
        last_discovered = app_data.get('last_discovered')
        if last_discovered and isinstance(last_discovered, str):
            last_discovered = f"'{last_discovered}'"
        else:
            last_discovered = 'NULL'
        
        insert_sql = f"""
        INSERT INTO cid.registered_apps (
            client_id, name, description, redirect_uris, owner, 
            api_key_required, discovery_endpoint, created_date, 
            last_discovered, role_mappings
        )
        VALUES (
            {escape_value(client_id)},
            {escape_value(app_data.get('name'))},
            {escape_value(app_data.get('description'))},
            {escape_value(app_data.get('redirect_uris', []))},
            {escape_value(app_data.get('owner'))},
            {escape_value(app_data.get('api_key_required', False))},
            {escape_value(app_data.get('discovery_endpoint'))},
            {created_date},
            {last_discovered},
            {escape_value(app_data.get('role_mappings', {}))}
        );
        """
        
        success, msg = execute_sql(insert_sql)
        if success:
            print(f"✅ Inserted app: {app_data.get('name', client_id)}")
        else:
            print(f"❌ Failed to insert {client_id}: {msg}")

def fix_token_templates():
    """Fix token_templates table"""
    print("\n📁 Fixing token_templates.json")
    
    with open(f"{DATA_DIR}/token_templates.json", 'r') as f:
        data = json.load(f)
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS cid.token_templates (
        id SERIAL PRIMARY KEY,
        template_data JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    success, msg = execute_sql(create_sql)
    if success:
        print("✅ Table created")
    else:
        print(f"❌ Failed to create table: {msg}")
        return
    
    # Insert the entire JSON as one record
    insert_sql = f"""
    INSERT INTO cid.token_templates (template_data)
    VALUES ({escape_value(data)});
    """
    
    success, msg = execute_sql(insert_sql)
    if success:
        print("✅ Inserted token templates")
    else:
        print(f"❌ Failed to insert: {msg}")

def verify_migration():
    """Verify all tables and show summary"""
    print("\n" + "="*60)
    print("📊 FINAL MIGRATION STATUS")
    print("="*60)
    
    # Get all tables in CID schema with row counts
    sql = """
    SELECT 
        t.table_name,
        (SELECT COUNT(*) FROM cid.||t.table_name) as row_count
    FROM information_schema.tables t
    WHERE t.table_schema = 'cid'
    ORDER BY t.table_name;
    """
    
    # We need a different approach for row counts
    tables_sql = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'cid'
    ORDER BY table_name;
    """
    
    success, output = execute_sql(tables_sql)
    
    if success:
        print("\n📋 TABLES IN CID SCHEMA:")
        # Parse table names from output
        lines = output.strip().split('\n')
        
        for line in lines[2:-1]:  # Skip header and footer
            table_name = line.strip()
            if table_name and not table_name.startswith('-'):
                # Get row count for this table
                count_sql = f"SELECT COUNT(*) FROM cid.{table_name};"
                success, count_output = execute_sql(count_sql)
                if success:
                    count_lines = count_output.strip().split('\n')
                    for count_line in count_lines:
                        if count_line.strip().isdigit():
                            count = count_line.strip()
                            print(f"   ✅ cid.{table_name}: {count} records")
                            break

def main():
    print("🔧 Fixing remaining CID tables")
    
    # Fix each problematic table
    fix_app_api_keys()
    fix_app_endpoints()
    fix_permissions_registry()
    fix_registered_apps()
    fix_token_templates()
    
    # Verify migration
    verify_migration()
    
    print("\n✅ Migration fixes completed!")

if __name__ == "__main__":
    main()