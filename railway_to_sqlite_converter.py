#!/usr/bin/env python3
"""
Railway PostgreSQL to SQLite Converter
Converts data from Railway PostgreSQL database to local SQLite database
"""

import os
import sys
import json
import sqlite3
import psycopg2
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('conversion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RailwayToSQLiteConverter:
    def __init__(self):
        # Railway PostgreSQL connection details
        self.pg_config = {
            'host': 'centerbeam.proxy.rlwy.net',
            'port': 26191,
            'database': 'railway',
            'user': 'postgres',
            'password': 'qSNUGrxoEFLKrHkscytOjsacoCbByarc'
        }
        
        self.sqlite_db = 'site.db'
        self.backup_file = f'railway_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
    def connect_postgresql(self):
        """Connect to Railway PostgreSQL database"""
        try:
            conn = psycopg2.connect(**self.pg_config)
            logger.info("Successfully connected to Railway PostgreSQL")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return None
    
    def get_table_list(self, pg_conn):
        """Get list of all tables in the database"""
        cursor = pg_conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
        return tables
    
    def get_table_schema(self, pg_conn, table_name):
        """Get table schema information"""
        cursor = pg_conn.cursor()
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = %s 
            ORDER BY ordinal_position;
        """, (table_name,))
        
        schema = cursor.fetchall()
        cursor.close()
        return schema
    
    def postgresql_to_sqlite_type(self, pg_type, max_length=None):
        """Convert PostgreSQL data type to SQLite equivalent"""
        type_mapping = {
            'integer': 'INTEGER',
            'bigint': 'INTEGER',
            'smallint': 'INTEGER',
            'serial': 'INTEGER',
            'bigserial': 'INTEGER',
            'boolean': 'BOOLEAN',
            'character varying': 'TEXT',
            'varchar': 'TEXT',
            'text': 'TEXT',
            'char': 'TEXT',
            'character': 'TEXT',
            'date': 'DATE',
            'timestamp without time zone': 'DATETIME',
            'timestamp with time zone': 'DATETIME',
            'time': 'TIME',
            'numeric': 'REAL',
            'decimal': 'REAL',
            'real': 'REAL',
            'double precision': 'REAL',
            'money': 'REAL',
            'json': 'TEXT',
            'jsonb': 'TEXT',
            'uuid': 'TEXT'
        }
        
        return type_mapping.get(pg_type, 'TEXT')
    
    def create_sqlite_table(self, sqlite_conn, table_name, schema):
        """Create SQLite table based on PostgreSQL schema"""
        cursor = sqlite_conn.cursor()
        
        # Drop table if exists
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Build CREATE TABLE statement
        columns = []
        for col_name, data_type, is_nullable, default, max_length in schema:
            sqlite_type = self.postgresql_to_sqlite_type(data_type, max_length)
            
            col_def = f"{col_name} {sqlite_type}"
            
            if is_nullable == 'NO':
                col_def += " NOT NULL"
            
            if default is not None and not default.startswith('nextval('):
                if 'CURRENT_TIMESTAMP' in default.upper():
                    col_def += " DEFAULT CURRENT_TIMESTAMP"
                elif default.lower() in ['true', 'false']:
                    col_def += f" DEFAULT {1 if default.lower() == 'true' else 0}"
                elif default.startswith("'") and default.endswith("'"):
                    col_def += f" DEFAULT {default}"
                else:
                    try:
                        # Try to parse as number
                        float(default)
                        col_def += f" DEFAULT {default}"
                    except ValueError:
                        col_def += f" DEFAULT '{default}'"
            
            columns.append(col_def)
        
        create_sql = f"CREATE TABLE {table_name} ({', '.join(columns)})"
        logger.info(f"Creating table {table_name}: {create_sql}")
        
        cursor.execute(create_sql)
        sqlite_conn.commit()
        cursor.close()
    
    def copy_table_data(self, pg_conn, sqlite_conn, table_name):
        """Copy data from PostgreSQL table to SQLite table"""
        pg_cursor = pg_conn.cursor()
        sqlite_cursor = sqlite_conn.cursor()
        
        # Get column names
        pg_cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
        columns = [desc[0] for desc in pg_cursor.description]
        
        # Fetch all data
        pg_cursor.execute(f"SELECT * FROM {table_name}")
        rows = pg_cursor.fetchall()
        
        if not rows:
            logger.info(f"Table {table_name} is empty")
            pg_cursor.close()
            sqlite_cursor.close()
            return
        
        # Insert data into SQLite
        placeholders = ','.join(['?' for _ in columns])
        insert_sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
        
        # Convert data types for SQLite compatibility
        converted_rows = []
        for row in rows:
            converted_row = []
            for value in row:
                if value is None:
                    converted_row.append(None)
                elif isinstance(value, bool):
                    converted_row.append(1 if value else 0)
                elif hasattr(value, 'isoformat'):  # datetime objects
                    converted_row.append(value.isoformat())
                elif hasattr(value, '__class__') and 'decimal' in str(type(value)).lower():
                    # Handle decimal.Decimal objects
                    converted_row.append(float(value))
                else:
                    converted_row.append(value)
            converted_rows.append(tuple(converted_row))
        
        sqlite_cursor.executemany(insert_sql, converted_rows)
        sqlite_conn.commit()
        
        logger.info(f"Copied {len(converted_rows)} rows to table {table_name}")
        
        pg_cursor.close()
        sqlite_cursor.close()
    
    def backup_to_json(self, pg_conn, tables):
        """Create JSON backup of all data"""
        backup_data = {}
        
        for table_name in tables:
            cursor = pg_conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name}")
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch all rows
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            table_data = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    if hasattr(value, 'isoformat'):  # datetime objects
                        row_dict[columns[i]] = value.isoformat()
                    elif isinstance(value, bool):
                        row_dict[columns[i]] = value
                    elif hasattr(value, '__class__') and 'decimal' in str(type(value)).lower():
                        # Handle decimal.Decimal objects
                        row_dict[columns[i]] = float(value)
                    else:
                        row_dict[columns[i]] = value
                table_data.append(row_dict)
            
            backup_data[table_name] = {
                'columns': columns,
                'data': table_data
            }
            
            cursor.close()
            logger.info(f"Backed up {len(table_data)} rows from table {table_name}")
        
        # Save to JSON file
        with open(self.backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Backup saved to {self.backup_file}")
        return backup_data
    
    def convert(self):
        """Main conversion process"""
        logger.info("Starting Railway PostgreSQL to SQLite conversion")
        
        # Connect to PostgreSQL
        pg_conn = self.connect_postgresql()
        if not pg_conn:
            logger.error("Cannot proceed without PostgreSQL connection")
            return False
        
        try:
            # Get table list
            tables = self.get_table_list(pg_conn)
            if not tables:
                logger.warning("No tables found in the database")
                return False
            
            # Create JSON backup first
            logger.info("Creating JSON backup...")
            backup_data = self.backup_to_json(pg_conn, tables)
            
            # Connect to SQLite
            sqlite_conn = sqlite3.connect(self.sqlite_db)
            logger.info(f"Connected to SQLite database: {self.sqlite_db}")
            
            # Process each table
            for table_name in tables:
                logger.info(f"Processing table: {table_name}")
                
                # Get schema
                schema = self.get_table_schema(pg_conn, table_name)
                
                # Create SQLite table
                self.create_sqlite_table(sqlite_conn, table_name, schema)
                
                # Copy data
                self.copy_table_data(pg_conn, sqlite_conn, table_name)
            
            # Close connections
            sqlite_conn.close()
            pg_conn.close()
            
            logger.info("Conversion completed successfully!")
            logger.info(f"SQLite database: {self.sqlite_db}")
            logger.info(f"JSON backup: {self.backup_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            if 'sqlite_conn' in locals():
                sqlite_conn.close()
            if 'pg_conn' in locals():
                pg_conn.close()
            return False

def main():
    """Main function"""
    print("Railway PostgreSQL to SQLite Converter")
    print("=" * 50)
    
    converter = RailwayToSQLiteConverter()
    success = converter.convert()
    
    if success:
        print("\n✅ Conversion completed successfully!")
        print(f"📁 SQLite database: {converter.sqlite_db}")
        print(f"📄 JSON backup: {converter.backup_file}")
    else:
        print("\n❌ Conversion failed. Check the logs for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

