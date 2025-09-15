#!/usr/bin/env python3
import psycopg2
from psycopg2 import sql

# Database connection parameters
conn_params = {
    'host': 'localhost',
    'port': 54322,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres'
}

try:
    # Connect to database
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    
    print("=== Checking dependencies on cids.roles table ===\n")
    
    # Check foreign key constraints referencing roles table
    cursor.execute("""
        SELECT 
            conname AS constraint_name,
            conrelid::regclass AS table_name,
            a.attname AS column_name
        FROM pg_constraint c
        JOIN pg_attribute a ON a.attnum = ANY(c.conkey) AND a.attrelid = c.conrelid
        WHERE confrelid = 'cids.roles'::regclass
        ORDER BY conrelid::regclass;
    """)
    
    dependencies = cursor.fetchall()
    
    if dependencies:
        print("Found the following tables with foreign keys to cids.roles:")
        for dep in dependencies:
            print(f"  - Table: {dep[1]}, Constraint: {dep[0]}, Column: {dep[2]}")
        
        print("\n=== Solution to drop the roles table ===\n")
        print("Option 1: Drop dependent tables first (CASCADE)")
        print("  DROP TABLE cids.roles CASCADE;")
        print("  WARNING: This will also drop all dependent tables!\n")
        
        print("Option 2: Drop only the foreign key constraints:")
        seen_constraints = set()
        for dep in dependencies:
            if dep[0] not in seen_constraints:
                print(f"  ALTER TABLE {dep[1]} DROP CONSTRAINT {dep[0]};")
                seen_constraints.add(dep[0])
        print("  DROP TABLE cids.roles;")
        print("\nOption 3: Backup data, then drop with CASCADE and recreate:")
        print("  -- First backup the data")
        print("  pg_dump -h localhost -p 54322 -U postgres -t cids.roles postgres > roles_backup.sql")
        print("  -- Then drop with cascade")
        print("  DROP TABLE cids.roles CASCADE;")
        
    else:
        print("No foreign key dependencies found on cids.roles table.")
        print("\nYou should be able to drop it with:")
        print("  DROP TABLE cids.roles;")
    
    # Check if there are any views depending on the table
    cursor.execute("""
        SELECT DISTINCT 
            dependent_ns.nspname AS dependent_schema,
            dependent_view.relname AS dependent_view
        FROM pg_depend 
        JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid 
        JOIN pg_class AS dependent_view ON pg_rewrite.ev_class = dependent_view.oid 
        JOIN pg_class AS source_table ON pg_depend.refobjid = source_table.oid 
        JOIN pg_namespace dependent_ns ON dependent_view.relnamespace = dependent_ns.oid
        JOIN pg_namespace source_ns ON source_table.relnamespace = source_ns.oid
        WHERE 
            source_ns.nspname = 'cids' 
            AND source_table.relname = 'roles'
            AND pg_depend.deptype = 'n';
    """)
    
    views = cursor.fetchall()
    if views:
        print("\n=== Views depending on cids.roles ===")
        for view in views:
            print(f"  - {view[0]}.{view[1]}")
    
    # Check current data in roles table
    cursor.execute("SELECT COUNT(*) FROM cids.roles;")
    count = cursor.fetchone()[0]
    print(f"\n=== Current status ===")
    print(f"Number of records in cids.roles: {count}")
    
    if count > 0:
        cursor.execute("""
            SELECT client_id, role_name 
            FROM cids.roles 
            LIMIT 5;
        """)
        sample = cursor.fetchall()
        print("\nSample records:")
        for row in sample:
            print(f"  - Client: {row[0]}, Role: {row[1]}")
    
    cursor.close()
    conn.close()
    
except psycopg2.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"Error: {e}")