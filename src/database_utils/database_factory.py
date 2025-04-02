import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from database_utils.database_interface import DatabaseInterface
from src.runner.sqlite_manager import SQLiteDatabaseManager
from src.runner.mysql_manager import MySQLDatabaseManager

load_dotenv(override=True)

class DatabaseFactory:
    """
    Factory class to create the appropriate database manager based on configuration.
    """
    
    @staticmethod
    def get_database_manager(config: Dict[str, Any]) -> DatabaseInterface:
        """
        Create and return the appropriate database manager instance based on config.
        
        Args:
            config (Dict[str, Any]): Configuration dictionary with database settings
            
        Returns:
            DatabaseInterface: An instance of a class implementing the DatabaseInterface
        """
        try:
            db_type = config.get('database', {}).get('type', 'sqlite').lower()
            
            if db_type == "mysql":
                # Get MySQL settings from config
                mysql_settings = config.get('database', {}).get('mysql_settings', {})
                db_name = mysql_settings.get('database')
                db_id = mysql_settings.get('db_id')
                
                if not db_name:
                    raise ValueError("MySQL database name not provided in config")
                
                return MySQLDatabaseManager(db_name=db_name, db_id=db_id)
            else:
                # Default to SQLite
                sqlite_settings = config.get('database', {}).get('sqlite_settings', {})
                db_mode = sqlite_settings.get('mode')
                db_id = sqlite_settings.get('id')
                
                if not db_mode or not db_id:
                    raise ValueError("SQLite mode and id must be provided in config")
                    
                return SQLiteDatabaseManager(db_mode=db_mode, db_id=db_id)
        except Exception as e:
            raise ValueError(f"Failed to create database manager: {e}")
    
    @staticmethod
    def create_database_manager(db_mode: Optional[str] = None, db_id: Optional[str] = None) -> DatabaseInterface:
        """
        Create and return the appropriate database manager instance using environment variables.
        Legacy method for backward compatibility.
        
        Args:
            db_mode (str, optional): Database mode (e.g., 'dev', 'prod')
            db_id (str, optional): Database identifier
            
        Returns:
            DatabaseInterface: An instance of a class implementing the DatabaseInterface
        """
        # Get the database type from environment variables
        db_type = os.getenv("DB_TYPE", "sqlite").lower()
        
        if db_type == "mysql":
            # Get MySQL-specific database name
            db_name = os.getenv("DB_NAME", db_id)
            return MySQLDatabaseManager(db_name=db_name, db_id=db_id)
        else:
            # Default to SQLite
            return SQLiteDatabaseManager(db_mode=db_mode, db_id=db_id)
            
    @staticmethod
    def get_database_manager_for_name(db_name: str) -> DatabaseInterface:
        """
        Create a database manager for a specific database name.
        Primarily used for MySQL direct connections.
        
        Args:
            db_name (str): Name of the database to connect to
            
        Returns:
            DatabaseInterface: Database manager instance
        """
        db_type = os.getenv("DB_TYPE", "sqlite").lower()
        
        if db_type == "mysql":
            return MySQLDatabaseManager(db_name=db_name, db_id=None)
        else:
            raise ValueError(f"Direct database name connection only supported for MySQL, not {db_type}")