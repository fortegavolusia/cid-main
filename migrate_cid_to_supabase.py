#!/usr/bin/env python3
"""
Migrate all CID JSON data files to Supabase PostgreSQL database
"""

import json
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback

# Directory containing JSON files
DATA_DIR = '/home/dpi/projects/CID/backend/infra/data/app_data'

class CIDMigrator:
    def __init__(self):
        self.container_name = 'supabase_db_mi-proyecto-supabase'
        self.failed_records = []
        self.successful_tables = []
        self.migration_log = []
        
    def execute_sql(self, sql: str) -> tuple[bool, str]:
        """Execute SQL command in Supabase container"""
        try:
            cmd = ['docker', 'exec', self.container_name, 'psql', '-U', 'postgres', '-c', sql]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)
    
    def analyze_json_structure(self, data: Any) -> Dict[str, Any]:
        """Analyze JSON data structure to determine table schema"""
        if isinstance(data, dict):
            # Check if it's a dict of objects (like registered_apps)
            if data and all(isinstance(v, dict) for v in data.values()):
                # Convert to list of records with keys preserved
                records = []
                for key, value in data.items():
                    value['_original_key'] = key
                    records.append(value)
                return {'type': 'dict_of_objects', 'records': records}
            else:
                # Single object
                return {'type': 'single_object', 'records': [data]}
        elif isinstance(data, list):
            return {'type': 'array', 'records': data}
        else:
            return {'type': 'unknown', 'records': []}
    
    def infer_column_type(self, value: Any) -> str:
        """Infer PostgreSQL column type from Python value"""
        if value is None:
            return 'TEXT'
        elif isinstance(value, bool):
            return 'BOOLEAN'
        elif isinstance(value, int):
            # Check if it might be a timestamp
            if len(str(value)) == 10 or len(str(value)) == 13:
                return 'BIGINT'
            return 'INTEGER'
        elif isinstance(value, float):
            return 'NUMERIC'
        elif isinstance(value, (dict, list)):
            return 'JSONB'
        elif isinstance(value, str):
            # Check for datetime patterns
            if 'T' in value and ':' in value:
                return 'TIMESTAMP'
            elif len(value) > 255:
                return 'TEXT'
            else:
                return 'VARCHAR(255)'
        else:
            return 'TEXT'
    
    def create_table_schema(self, table_name: str, records: List[Dict]) -> str:
        """Generate CREATE TABLE statement based on records"""
        if not records:
            return None
            
        # Analyze all records to get all possible columns and their types
        columns = {}
        
        for record in records:
            for key, value in record.items():
                # Clean column name
                col_name = key.replace('-', '_').replace(' ', '_').replace('.', '_').lower()
                
                if col_name not in columns:
                    columns[col_name] = self.infer_column_type(value)
                else:
                    # If we see different types, use JSONB as fallback
                    current_type = columns[col_name]
                    new_type = self.infer_column_type(value)
                    if current_type != new_type and new_type != 'TEXT':
                        if 'JSON' in current_type or 'JSON' in new_type:
                            columns[col_name] = 'JSONB'
                        elif current_type == 'VARCHAR(255)' and new_type == 'TEXT':
                            columns[col_name] = 'TEXT'
                        elif current_type == 'INTEGER' and new_type == 'BIGINT':
                            columns[col_name] = 'BIGINT'
        
        # Build CREATE TABLE statement
        column_defs = []
        
        # Add primary key
        column_defs.append('id SERIAL PRIMARY KEY')
        
        # Add all detected columns
        for col_name, col_type in columns.items():
            column_defs.append(f'{col_name} {col_type}')
        
        # Add metadata columns
        column_defs.append('created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        column_defs.append('updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS cid.{table_name} (
            {', '.join(column_defs)}
        );
        """
        
        return create_sql
    
    def escape_value(self, value: Any) -> str:
        """Escape value for SQL insertion"""
        if value is None:
            return 'NULL'
        elif isinstance(value, bool):
            return 'TRUE' if value else 'FALSE'
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, (dict, list)):
            # Convert to JSON string and escape quotes
            json_str = json.dumps(value, default=str)
            return "'" + json_str.replace("'", "''") + "'::jsonb"
        else:
            # String value - escape single quotes
            str_value = str(value)
            return "'" + str_value.replace("'", "''") + "'"
    
    def insert_records(self, table_name: str, records: List[Dict]) -> Dict:
        """Insert records into table"""
        successful = 0
        failed = 0
        
        for record in records:
            try:
                # Clean and prepare columns and values
                columns = []
                values = []
                
                for key, value in record.items():
                    col_name = key.replace('-', '_').replace(' ', '_').replace('.', '_').lower()
                    columns.append(col_name)
                    values.append(self.escape_value(value))
                
                insert_sql = f"""
                INSERT INTO cid.{table_name} ({', '.join(columns)})
                VALUES ({', '.join(values)});
                """
                
                success, output = self.execute_sql(insert_sql)
                
                if success:
                    successful += 1
                else:
                    failed += 1
                    self.failed_records.append({
                        'table': table_name,
                        'record': record,
                        'error': output
                    })
                    
            except Exception as e:
                failed += 1
                self.failed_records.append({
                    'table': table_name,
                    'record': record,
                    'error': str(e)
                })
        
        return {'successful': successful, 'failed': failed, 'total': len(records)}
    
    def migrate_json_file(self, filename: str) -> bool:
        """Migrate a single JSON file to Supabase"""
        filepath = os.path.join(DATA_DIR, filename)
        table_name = filename.replace('.json', '').replace('-', '_')
        
        print(f"\n{'='*60}")
        print(f"📁 Processing: {filename}")
        print(f"📊 Target table: cid.{table_name}")
        
        try:
            # Read JSON file
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Analyze structure
            structure = self.analyze_json_structure(data)
            records = structure['records']
            
            if not records:
                print(f"⚠️  No records found in {filename}")
                self.migration_log.append({
                    'file': filename,
                    'table': f'cid.{table_name}',
                    'status': 'empty',
                    'records': 0
                })
                return True
            
            print(f"📝 Found {len(records)} records of type: {structure['type']}")
            
            # Create table
            create_sql = self.create_table_schema(table_name, records)
            if create_sql:
                success, output = self.execute_sql(create_sql)
                if success:
                    print(f"✅ Table cid.{table_name} created/verified")
                else:
                    print(f"❌ Failed to create table: {output}")
                    return False
            
            # Insert records
            result = self.insert_records(table_name, records)
            
            # Log results
            self.migration_log.append({
                'file': filename,
                'table': f'cid.{table_name}',
                'status': 'success' if result['failed'] == 0 else 'partial',
                'records': result['total'],
                'successful': result['successful'],
                'failed': result['failed']
            })
            
            print(f"✅ Inserted {result['successful']}/{result['total']} records")
            if result['failed'] > 0:
                print(f"⚠️  Failed to insert {result['failed']} records")
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            traceback.print_exc()
            self.migration_log.append({
                'file': filename,
                'table': f'cid.{table_name}',
                'status': 'error',
                'error': str(e)
            })
            return False
    
    def migrate_all(self):
        """Migrate all JSON files to Supabase"""
        # Get all JSON files
        json_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.json')])
        
        print(f"\n🚀 Starting migration of {len(json_files)} JSON files to Supabase")
        print(f"📂 Source directory: {DATA_DIR}")
        print(f"🎯 Target schema: cid")
        
        # Process each file
        for json_file in json_files:
            self.migrate_json_file(json_file)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print migration summary"""
        print("\n" + "="*60)
        print("📊 MIGRATION SUMMARY")
        print("="*60)
        
        # Group by status
        successful = [m for m in self.migration_log if m.get('status') == 'success']
        partial = [m for m in self.migration_log if m.get('status') == 'partial']
        failed = [m for m in self.migration_log if m.get('status') == 'error']
        empty = [m for m in self.migration_log if m.get('status') == 'empty']
        
        if successful:
            print(f"\n✅ SUCCESSFUL ({len(successful)} files):")
            for m in successful:
                print(f"   • {m['file']}: {m['successful']} records → {m['table']}")
        
        if partial:
            print(f"\n⚠️  PARTIAL SUCCESS ({len(partial)} files):")
            for m in partial:
                print(f"   • {m['file']}: {m['successful']}/{m['records']} records → {m['table']}")
        
        if empty:
            print(f"\n📭 EMPTY FILES ({len(empty)} files):")
            for m in empty:
                print(f"   • {m['file']}")
        
        if failed:
            print(f"\n❌ FAILED ({len(failed)} files):")
            for m in failed:
                print(f"   • {m['file']}: {m.get('error', 'Unknown error')}")
        
        if self.failed_records:
            print(f"\n❌ FAILED RECORDS ({len(self.failed_records)} total):")
            # Show first 5 failures in detail
            for i, fail in enumerate(self.failed_records[:5]):
                print(f"\n   Record #{i+1} in {fail['table']}:")
                print(f"   Error: {fail['error'][:200]}")
            
            if len(self.failed_records) > 5:
                print(f"\n   ... and {len(self.failed_records) - 5} more failed records")
        
        # Summary statistics
        total_files = len(self.migration_log)
        total_records = sum(m.get('records', 0) for m in self.migration_log if 'records' in m)
        total_successful = sum(m.get('successful', 0) for m in self.migration_log if 'successful' in m)
        
        print(f"\n📈 STATISTICS:")
        print(f"   • Total files processed: {total_files}")
        print(f"   • Total records found: {total_records}")
        print(f"   • Total records inserted: {total_successful}")
        print(f"   • Success rate: {(total_successful/total_records*100):.1f}%" if total_records > 0 else "N/A")
        
        # List all created tables
        success, output = self.execute_sql("""
            SELECT table_name, 
                   (SELECT COUNT(*) FROM cid.""" + """||table_name) as row_count
            FROM information_schema.tables 
            WHERE table_schema = 'cid'
            ORDER BY table_name;
        """)
        
        if success:
            print(f"\n📋 TABLES IN CID SCHEMA:")
            print(output)

def main():
    migrator = CIDMigrator()
    migrator.migrate_all()

if __name__ == "__main__":
    main()