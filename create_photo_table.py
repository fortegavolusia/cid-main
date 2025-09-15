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

def create_photo_emp_table():
    """Create photo_emp table in cids schema"""
    
    create_table_sql = """
    -- Create photo_emp table in cids schema
    CREATE TABLE IF NOT EXISTS cids.photo_emp (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        photo_path VARCHAR(500) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """
    
    create_index_sql = """
    -- Create index on email for faster lookups
    CREATE INDEX IF NOT EXISTS idx_photo_emp_email ON cids.photo_emp(email);
    """
    
    add_comments_sql = """
    -- Add comments to table
    COMMENT ON TABLE cids.photo_emp IS 'Stores employee photo paths by email';
    COMMENT ON COLUMN cids.photo_emp.email IS 'Employee email address';
    COMMENT ON COLUMN cids.photo_emp.photo_path IS 'Relative path to photo file in CID/photos directory';
    """
    
    try:
        # Connect to database
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        # Create table
        cur.execute(create_table_sql)
        print("✅ Table cids.photo_emp created successfully")
        
        # Create index
        cur.execute(create_index_sql)
        print("✅ Index on email created successfully")
        
        # Add comments
        cur.execute(add_comments_sql)
        print("✅ Comments added successfully")
        
        # Commit changes
        conn.commit()
        
        # Verify table was created
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'cids' AND table_name = 'photo_emp'
            ORDER BY ordinal_position;
        """)
        
        columns = cur.fetchall()
        print("\n📋 Table structure:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}{f'({col[2]})' if col[2] else ''}")
        
        cur.close()
        conn.close()
        
        print("\n✅ Table created successfully in Supabase!")
        
    except psycopg2.Error as e:
        print(f"❌ Error creating table: {e}")
        if conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    create_photo_emp_table()