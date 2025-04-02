#!/usr/bin/env python3
import os
import sys
import argparse
from dotenv import load_dotenv
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = str(current_dir / "src")
sys.path.append(src_dir)

from database_utils.database_factory import DatabaseFactory


def test_connection(verbose=False):
    """Test the MySQL connection using the configured environment variables."""
    load_dotenv(override=True)
    
    print("Testing MySQL Connection...")
    print(f"Database IP: {os.getenv('DB_IP')}")
    print(f"Database Name: {os.getenv('DB_NAME')}")
    print(f"Database User: {os.getenv('DB_USERNAME')}")
    print(f"Database Type: {os.getenv('DB_TYPE')}")
    
    try:
        # Create a MySQL database manager using the factory
        db_manager = DatabaseFactory.create_database_manager(
            db_mode=os.getenv('DATA_MODE', 'dev'),
            db_id=os.getenv('DB_NAME')
        )
        
        # Test connection by retrieving the database schema
        print("\nAttempting to connect to the database...")
        schema = db_manager.get_db_schema()
        
        # Print the schema to verify connection
        print(f"\nSuccessfully connected to database: {os.getenv('DB_NAME')}")
        
        # Print table count
        table_count = len(schema)
        print(f"Found {table_count} tables in the database.")
        
        if verbose:
            # Print out each table and its columns
            print("\nDatabase Schema:")
            for table, columns in schema.items():
                print(f"  - {table} ({len(columns)} columns)")
                if verbose > 1:  # Extra verbose
                    for column in columns:
                        print(f"    - {column}")
        
        # Test executing a simple query
        print("\nTesting SQL execution...")
        result = db_manager.execute_sql("SELECT 1 as test")
        
        if result["success"]:
            print("SQL execution successful! Database connection works correctly.")
        else:
            print(f"SQL execution failed: {result['error']}")
            return False
        
        return True
    except Exception as e:
        print(f"\nConnection failed: {e}")
        print("\nPlease check your MySQL configuration in .env file.")
        print("Make sure the MySQL server is running and accessible.")
        return False
    finally:
        if 'db_manager' in locals() and db_manager:
            db_manager.disconnect()
            print("\nDatabase connection closed.")

def check_tables_existence():
    """Check if the required MySQL tables for LSH and Vector exist."""
    load_dotenv(override=True)
    
    try:
        # Create a MySQL database manager using the factory
        db_manager = DatabaseFactory.create_database_manager(
            db_mode=os.getenv('DATA_MODE', 'dev'),
            db_id=os.getenv('DB_NAME')
        )
        
        # Get schema and check for required tables
        schema = db_manager.get_db_schema()
        
        # Define required tables
        required_tables = {
            'lsh_signatures': 'LSH signatures table for storing hashes',
            'vector_metadata': 'Vector metadata table for ChromaDB integration'
        }
        
        # Check each required table
        print("\nChecking required tables for MySQL migration:")
        all_tables_exist = True
        
        for table, description in required_tables.items():
            if table in schema:
                print(f"✅ Found {table}: {description}")
            else:
                print(f"❌ Missing {table}: {description}")
                all_tables_exist = False
        
        if all_tables_exist:
            print("\nAll required tables exist. Schema setup is complete.")
        else:
            print("\nSome required tables are missing. Schema needs to be initialized.")
            print("To initialize the schema, run the following command:")
            print("\npython src/database_utils/init_mysql_schema.py")
        
        return all_tables_exist
    except Exception as e:
        print(f"\nError checking tables: {e}")
        return False
    finally:
        if 'db_manager' in locals() and db_manager:
            db_manager.disconnect()

def main():
    parser = argparse.ArgumentParser(description='Test MySQL connection for CHESS+')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Increase output verbosity (use -vv for more detail)')
    parser.add_argument('--init-schema', action='store_true',
                        help='Initialize MySQL schema if tables are missing')
    
    args = parser.parse_args()
    
    # Test basic connection
    connection_successful = test_connection(args.verbose)
    
    if not connection_successful:
        return 1
    
    # Check if required tables exist
    tables_exist = check_tables_existence()
    
    # Optionally initialize schema
    if not tables_exist and args.init_schema:
        print("\nInitializing MySQL schema...")
        try:
            from src.database_utils.init_mysql_schema import initialize_schema
            initialize_schema()
            print("Schema initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize schema: {e}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())