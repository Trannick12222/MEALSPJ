#!/usr/bin/env python3
"""
Simple Railway PostgreSQL Database Backup Script
Uses only Python libraries (no external PostgreSQL tools required)
"""

import json
import os
import sys
from datetime import datetime
import zipfile

def install_psycopg2():
    """Install psycopg2 if not available"""
    try:
        import subprocess
        print("Installing psycopg2-binary...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        print("✓ psycopg2-binary installed successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to install psycopg2-binary: {e}")
        return False

def create_backup():
    """Create backup using Python only"""
    
    # Try to import psycopg2, install if needed
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("psycopg2 not found. Attempting to install...")
        if not install_psycopg2():
            print("Cannot proceed without psycopg2. Please install manually:")
            print("pip install psycopg2-binary")
            return False
        
        # Try importing again
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            print("Still cannot import psycopg2. Please install manually.")
            return False
    
    # Database connection details from Railway
    DATABASE_CONFIG = {
        'host': 'centerbeam.proxy.rlwy.net',
        'port': 26191,
        'database': 'railway',
        'user': 'postgres',
        'password': 'qSNUGrxoEFLKrHkscytOjsacoCbByarc'
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'railway_backup_{timestamp}.json'
    
    print(f"Connecting to Railway database...")
    print(f"Host: {DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}")
    print(f"Database: {DATABASE_CONFIG['database']}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=DATABASE_CONFIG['host'],
            port=DATABASE_CONFIG['port'],
            database=DATABASE_CONFIG['database'],
            user=DATABASE_CONFIG['user'],
            password=DATABASE_CONFIG['password'],
            connect_timeout=30
        )
        
        print("✓ Connected successfully!")
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Get database info
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()['version']
        
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()['current_database']
        
        print(f"Database version: {db_version}")
        print(f"Current database: {current_db}")
        
        # Get all tables
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                tableowner
            FROM pg_tables 
            WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
            ORDER BY schemaname, tablename;
        """)
        
        tables_info = cursor.fetchall()
        
        if not tables_info:
            print("No user tables found in database")
            return False
        
        print(f"\nFound {len(tables_info)} tables:")
        for table in tables_info:
            print(f"  - {table['schemaname']}.{table['tablename']}")
        
        # Create backup data structure
        backup_data = {
            'backup_info': {
                'timestamp': datetime.now().isoformat(),
                'database': current_db,
                'host': DATABASE_CONFIG['host'],
                'port': DATABASE_CONFIG['port'],
                'db_version': db_version,
                'backup_type': 'full_data_export'
            },
            'schema': {},
            'data': {}
        }
        
        print(f"\nExporting table data...")
        
        total_rows = 0
        for table_info in tables_info:
            schema = table_info['schemaname']
            table = table_info['tablename']
            full_table_name = f"{schema}.{table}"
            
            try:
                # Get table schema
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position;
                """, (schema, table))
                
                columns = cursor.fetchall()
                backup_data['schema'][full_table_name] = [dict(col) for col in columns]
                
                # Get table data
                cursor.execute(f'SELECT * FROM "{schema}"."{table}"')
                rows = cursor.fetchall()
                
                # Convert rows to JSON-serializable format
                table_data = []
                for row in rows:
                    row_dict = {}
                    for key, value in row.items():
                        # Handle datetime and other non-JSON serializable types
                        if hasattr(value, 'isoformat'):
                            row_dict[key] = value.isoformat()
                        else:
                            row_dict[key] = value
                    table_data.append(row_dict)
                
                backup_data['data'][full_table_name] = table_data
                
                print(f"  ✓ {full_table_name}: {len(rows)} rows")
                total_rows += len(rows)
                
            except Exception as e:
                print(f"  ✗ Error exporting {full_table_name}: {str(e)}")
                continue
        
        cursor.close()
        conn.close()
        
        # Save backup to JSON file
        print(f"\nSaving backup to {backup_filename}...")
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        # Create compressed version
        zip_filename = f'railway_backup_{timestamp}.zip'
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(backup_filename)
        
        # Get file sizes
        json_size = os.path.getsize(backup_filename)
        zip_size = os.path.getsize(zip_filename)
        
        print(f"✓ Backup completed successfully!")
        print(f"\nBackup Summary:")
        print(f"  Tables exported: {len(tables_info)}")
        print(f"  Total rows: {total_rows:,}")
        print(f"  JSON file: {backup_filename} ({json_size:,} bytes, {json_size/1024/1024:.2f} MB)")
        print(f"  ZIP file: {zip_filename} ({zip_size:,} bytes, {zip_size/1024/1024:.2f} MB)")
        print(f"  Compression ratio: {((json_size - zip_size) / json_size * 100):.1f}%")
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"✗ Database connection error: {str(e)}")
        print("\nPossible issues:")
        print("  - Network connectivity problems")
        print("  - Railway database credentials changed")
        print("  - Database server is down")
        return False
        
    except Exception as e:
        print(f"✗ Backup failed: {str(e)}")
        return False

def main():
    """Main function"""
    print("=" * 70)
    print("Railway PostgreSQL Database Backup Tool (Python Only)")
    print("=" * 70)
    
    if create_backup():
        print("\n" + "=" * 70)
        print("✓ Backup process completed successfully!")
        print("=" * 70)
        print("\nBackup files created in current directory.")
        print("Keep these files safe - they contain your complete database!")
        
    else:
        print("\n✗ Backup failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

