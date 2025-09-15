#!/usr/bin/env python3
import psycopg2
from datetime import datetime

# Database connection parameters
conn_params = {
    'host': 'localhost',
    'port': 54322,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres'
}

def insert_photo_record():
    """Insert photo record for FOrtega@volusia.gov"""
    
    email = 'FOrtega@volusia.gov'
    photo_path = 'IMG_5249.JPEG'
    
    try:
        # Connect to database
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        # Check if record already exists
        cur.execute("""
            SELECT id FROM cids.photo_emp WHERE email = %s
        """, (email,))
        
        existing = cur.fetchone()
        
        if existing:
            # Update existing record
            cur.execute("""
                UPDATE cids.photo_emp 
                SET photo_path = %s, updated_at = NOW()
                WHERE email = %s
            """, (photo_path, email))
            print(f"✅ Updated existing photo record for {email}")
        else:
            # Insert new record
            cur.execute("""
                INSERT INTO cids.photo_emp (email, photo_path, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
            """, (email, photo_path))
            print(f"✅ Inserted new photo record for {email}")
        
        # Commit changes
        conn.commit()
        
        # Verify the record
        cur.execute("""
            SELECT email, photo_path, created_at
            FROM cids.photo_emp
            WHERE email = %s
        """, (email,))
        
        result = cur.fetchone()
        if result:
            print(f"\n📋 Record details:")
            print(f"  Email: {result[0]}")
            print(f"  Photo Path: {result[1]}")
            print(f"  Created: {result[2]}")
        
        cur.close()
        conn.close()
        
        print(f"\n✅ Photo record saved successfully!")
        print(f"📸 Photo should be placed at: /home/dpi/projects/CID/photos/{photo_path}")
        
    except psycopg2.Error as e:
        print(f"❌ Error inserting record: {e}")
        if conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    insert_photo_record()