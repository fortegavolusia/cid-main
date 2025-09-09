#!/usr/bin/env python3
"""
Test database connection and query
"""
import psycopg2
from psycopg2.extras import RealDictCursor

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': '54322',
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres'
}

try:
    print("🔌 Connecting to Supabase...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    print("✅ Connected successfully!")
    
    print("\n📊 Testing queries:\n")
    
    # Query 1: Total count
    cursor.execute("SELECT COUNT(*) as total FROM cids.registered_apps")
    total = cursor.fetchone()
    print(f"Total apps: {total['total']}")
    
    # Query 2: Active count
    cursor.execute("SELECT COUNT(*) as active FROM cids.registered_apps WHERE is_active = true")
    active = cursor.fetchone()
    print(f"Active apps: {active['active']}")
    
    # Query 3: Inactive count
    cursor.execute("SELECT COUNT(*) as inactive FROM cids.registered_apps WHERE is_active = false")
    inactive = cursor.fetchone()
    print(f"Inactive apps: {inactive['inactive']}")
    
    # Query 4: Show all apps with their status
    print("\n📋 All applications:")
    cursor.execute("SELECT client_id, name, is_active FROM cids.registered_apps ORDER BY created_at")
    apps = cursor.fetchall()
    for app in apps:
        status = "✅" if app['is_active'] else "❌"
        print(f"  {status} {app['name'][:50]}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")