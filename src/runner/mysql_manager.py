import os
import mysql.connector
from threading import Lock
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(override=True)

class MySQLManager:
    """
    A singleton class to manage MySQL database operations.
    This is a simplified version without LSH and vector DB functionality.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls, db_name: Optional[str] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MySQLManager, cls).__new__(cls)
                cls._instance._init(db_name)
            elif db_name and cls._instance.db_name != db_name:
                cls._instance._init(db_name)
            return cls._instance

    def _init(self, db_name: Optional[str] = None):
        """
        Initialize the MySQL connection and database settings.
        
        Args:
            db_name (str, optional): Name of the database to connect to
        """
        self.db_name = db_name
        self.host = os.getenv("DB_IP", "localhost")
        self.user = os.getenv("DB_USERNAME", "root")
        self.password = os.getenv("DB_PASSWORD")
        self.port = int(os.getenv("MYSQL_PORT", "3306"))
        self._connection = None
        self._cursor = None

    def connect(self) -> None:
        """Establish connection to the MySQL database."""
        try:
            self._connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                database=self.db_name
            )
            self._cursor = self._connection.cursor(dictionary=True)
        except mysql.connector.Error as err:
            raise Exception(f"Failed to connect to MySQL: {err}")

    def disconnect(self) -> None:
        """Close the database connection."""
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
        self._cursor = None
        self._connection = None

    def execute_sql(self, query: str, params: tuple = None) -> Dict[str, Any]:
        """
        Execute a SQL query and return the results.
        
        Args:
            query (str): SQL query to execute
            params (tuple, optional): Parameters for the SQL query
            
        Returns:
            Dict[str, Any]: Dictionary containing execution results
        """
        if not self._connection or not self._connection.is_connected():
            self.connect()
            
        try:
            self._cursor.execute(query, params)
            
            if query.strip().upper().startswith(("SELECT", "SHOW", "DESCRIBE")):
                results = self._cursor.fetchall()
                return {
                    "success": True,
                    "results": results,
                    "rowcount": self._cursor.rowcount,
                    "error": None
                }
            else:
                self._connection.commit()
                return {
                    "success": True,
                    "results": None,
                    "rowcount": self._cursor.rowcount,
                    "error": None
                }
                
        except mysql.connector.Error as err:
            return {
                "success": False,
                "results": None,
                "rowcount": 0,
                "error": str(err)
            }

    def get_db_schema(self) -> Dict[str, List[str]]:
        """
        Get the database schema including all tables and their columns.
        
        Returns:
            Dict[str, List[str]]: Dictionary with table names as keys and lists of column names as values
        """
        schema = {}
        if not self._connection or not self._connection.is_connected():
            self.connect()
            
        try:
            self._cursor.execute("SHOW TABLES")
            tables = [table[f"Tables_in_{self.db_name}"] for table in self._cursor.fetchall()]
            
            for table in tables:
                self._cursor.execute(f"DESCRIBE {table}")
                columns = [column["Field"] for column in self._cursor.fetchall()]
                schema[table] = columns
                
            return schema
        except mysql.connector.Error as err:
            raise Exception(f"Failed to get database schema: {err}")

    def get_table_columns(self, table_name: str) -> List[str]:
        """
        Get all columns for a specific table.
        
        Args:
            table_name (str): Name of the table
            
        Returns:
            List[str]: List of column names
        """
        if not self._connection or not self._connection.is_connected():
            self.connect()
            
        try:
            self._cursor.execute(f"DESCRIBE {table_name}")
            return [column["Field"] for column in self._cursor.fetchall()]
        except mysql.connector.Error as err:
            raise Exception(f"Failed to get table columns: {err}")

    def validate_sql_query(self, query: str) -> bool:
        """
        Validate if a SQL query is syntactically correct.
        
        Args:
            query (str): SQL query to validate
            
        Returns:
            bool: True if query is valid, False otherwise
        """
        if not self._connection or not self._connection.is_connected():
            self.connect()
            
        try:
            # Use EXPLAIN to check query syntax
            self._cursor.execute(f"EXPLAIN {query}")
            return True
        except mysql.connector.Error:
            return False