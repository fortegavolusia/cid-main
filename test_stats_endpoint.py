#!/usr/bin/env python3
"""
Test the database service directly
"""
import sys
import os
sys.path.insert(0, '/home/dpi/projects/CID/backend')

from services.database import db_service

print("Testing database service...")
print("Connection params:", {
    'host': db_service.connection_params['host'],
    'port': db_service.connection_params['port'],
    'database': db_service.connection_params['database'],
    'user': db_service.connection_params['user']
})

stats = db_service.get_registered_apps_stats()
print("\nStats result:", stats)

# Also test direct connection
import psycopg2
from psycopg2.extras import RealDictCursor

print("\n--- Testing direct connection ---")
for host in ['localhost', 'supabase_db_mi-proyecto-supabase']:
    for port in ['54322', '5432']:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database='postgres',
                user='postgres',
                password='postgres'
            )
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT COUNT(*) as total FROM cids.registered_apps")
            result = cursor.fetchone()
            print(f"✅ {host}:{port} - Total apps: {result['total']}")
            conn.close()
        except Exception as e:
            print(f"❌ {host}:{port} - {str(e)[:50]}")