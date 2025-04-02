#!/usr/bin/env python3
"""
MySQL Schema Initialization for CHESS+

This script initializes the required MySQL schema for CHESS+
by creating the necessary tables for LSH signatures and vector metadata.
"""

import os
import sys
import pymysql
from pathlib import Path
from dotenv import load_dotenv


def initialize_schema():
    """Initialize MySQL schema with required tables."""
    # Load environment variables
    load_dotenv(override=True)
    
    # Get MySQL connection parameters from environment
    host = os.getenv("DB_IP", "localhost")
    user = os.getenv("DB_USERNAME", "root")
    password = os.getenv("DB_PASSWORD", "")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    db_name = os.getenv("DB_NAME")
    
    if not db_name:
        raise ValueError("DB_NAME environment variable is not set")
    
    # Connect to MySQL
    connection = None
    try:
        print(f"Connecting to MySQL at {host}:{port}...")
        # First connect without specifying a database to check if it exists
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # Check if database exists, create if it doesn't
        cursor.execute(f"SHOW DATABASES LIKE '{db_name}'")
        database_exists = cursor.fetchone() is not None
        
        if not database_exists:
            print(f"Creating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
            connection.commit()
            print(f"Database '{db_name}' created successfully")
        else:
            print(f"Database '{db_name}' already exists")
        
        # Close the initial connection
        cursor.close()
        connection.close()
        
        # Connect to the specific database
        print(f"Connecting to database '{db_name}'...")
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            database=db_name,
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        # Read and execute the schema SQL file
        schema_file = Path(__file__).parent / "mysql_schema.sql"
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
        print(f"Executing schema from {schema_file}...")
        schema_sql = schema_file.read_text()
        
        # Split and execute statements
        for statement in schema_sql.split(';'):
            statement = statement.strip()
            if statement:  # Skip empty statements
                cursor.execute(statement)
        
        connection.commit()
        print("Schema initialized successfully")
        
        # Verify tables were created
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        print(f"Tables in database: {', '.join(tables)}")
        
        # Check for required tables
        required_tables = ['lsh_signatures', 'vector_metadata']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"WARNING: Some required tables are missing: {', '.join(missing_tables)}")
        else:
            print("All required tables are present")
        
        return True
    
    except Exception as e:
        print(f"Error initializing schema: {e}")
        return False
    
    finally:
        if connection:
            connection.close()


def main():
    """Main function to run from command line."""
    try:
        result = initialize_schema()
        return 0 if result else 1
    except Exception as e:
        print(f"Initialization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())