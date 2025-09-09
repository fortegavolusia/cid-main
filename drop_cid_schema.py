#!/usr/bin/env python3
"""
Script to DROP all CID schema and tables in Supabase
"""

import psycopg2
import sys

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': '54322',
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres'
}

try:
    print("🗑️  Connecting to Supabase...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("⚠️  WARNING: This will DROP the entire CID schema and ALL its tables!")
    print("   All data will be permanently deleted.")
    
    response = input("\n   Are you sure you want to continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Operation cancelled.")
        sys.exit(0)
    
    print("\n🧹 Dropping CIDS schema cascade...")
    cursor.execute("DROP SCHEMA IF EXISTS cids CASCADE")
    conn.commit()
    
    print("✅ CIDS schema and all tables have been dropped successfully!")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)