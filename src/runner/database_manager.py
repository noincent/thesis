import os
import yaml
from pathlib import Path
from typing import Callable, Dict, List, Any, Optional
from dotenv import load_dotenv

from database_utils.database_factory import DatabaseFactory
from database_utils.database_interface import DatabaseInterface

load_dotenv(override=True)

# Default config path
CONFIG_PATH = os.getenv("DB_CONFIG_PATH", "run/configs/database_config.yaml")

class DatabaseManager:
    """
    A wrapper class that uses the appropriate database manager implementation
    based on configuration. Acts as a facade to maintain backward compatibility.
    """
    _instance = None

    @staticmethod
    def _load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from YAML file with environment variable substitution.
        
        Args:
            config_path (str, optional): Path to config file
            
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        path = config_path or CONFIG_PATH
        
        try:
            with open(path, 'r') as file:
                config = yaml.safe_load(file)
                
                # Process environment variable substitutions
                # Format: ${ENV_VAR:default_value}
                def process_env_vars(item):
                    if isinstance(item, dict):
                        return {k: process_env_vars(v) for k, v in item.items()}
                    elif isinstance(item, list):
                        return [process_env_vars(i) for i in item]
                    elif isinstance(item, str) and item.startswith("${") and item.endswith("}"):
                        # Extract env var name and default value
                        env_var = item[2:-1]
                        if ":" in env_var:
                            env_name, default = env_var.split(":", 1)
                            return os.getenv(env_name, default)
                        else:
                            return os.getenv(env_var, "")
                    else:
                        return item
                
                return process_env_vars(config)
        except Exception as e:
            print(f"Error loading config from {path}: {e}")
            # Return a default config
            return {
                "database": {
                    "type": os.getenv("DB_TYPE", "sqlite"),
                    "sqlite_settings": {
                        "mode": "dev",
                        "id": "wtl_employee_tracker"
                    },
                    "mysql_settings": {
                        "host": os.getenv("DB_IP", "localhost"),
                        "port": int(os.getenv("MYSQL_PORT", "3306")),
                        "user": os.getenv("DB_USERNAME", "root"),
                        "password": os.getenv("DB_PASSWORD", ""),
                        "database": os.getenv("DB_NAME", "chess_plus"),
                        "db_id": "wtl_employee_tracker"
                    }
                }
            }

    def __new__(cls, db_mode=None, db_id=None, config_path=None):
        """
        Creates or returns the appropriate database manager instance.
        
        Args:
            db_mode (str, optional): Database mode (e.g., 'train', 'test')
            db_id (str, optional): Database identifier
            config_path (str, optional): Path to config file
            
        Returns:
            DatabaseManager: A wrapped instance of a DatabaseInterface implementation
        """
        # Load config from file
        config = cls._load_config(config_path)
        
        # Override with provided parameters if available
        if db_mode is not None and db_id is not None:
            # Detect database type from config
            db_type = config.get('database', {}).get('type', 'sqlite').lower()
            
            if db_type == 'mysql':
                # Update MySQL settings
                if 'mysql_settings' not in config.get('database', {}):
                    config['database']['mysql_settings'] = {}
                config['database']['mysql_settings']['db_id'] = db_id
            else:
                # Update SQLite settings
                if 'sqlite_settings' not in config.get('database', {}):
                    config['database']['sqlite_settings'] = {}
                config['database']['sqlite_settings']['mode'] = db_mode
                config['database']['sqlite_settings']['id'] = db_id
        
        # Create manager using factory with config
        cls._instance = DatabaseFactory.get_database_manager(config)
        
        # Add db_mode and db_id attributes for compatibility if needed
        if db_mode is not None and not hasattr(cls._instance, 'db_mode'):
            cls._instance.db_mode = db_mode
        if db_id is not None and not hasattr(cls._instance, 'db_id'):
            cls._instance.db_id = db_id
            
        return cls._instance

    def __getattr__(self, name):
        """
        Delegates attribute access to the underlying database implementation.
        
        Args:
            name (str): Name of the attribute
            
        Returns:
            Any: The requested attribute from the database implementation
        """
        # This is only called if the attribute doesn't exist on this class
        if self._instance and hasattr(self._instance, name):
            return getattr(self._instance, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        
    # For backwards compatibility with code that uses query_lsh with keyword conversion
    def query_lsh(self, keyword: str, signature_size: int = 100, n_gram: int = 3, top_n: int = 10) -> Dict[str, List[str]]:
        """
        Compatibility method for querying the LSH database.
        
        Args:
            keyword (str): The keyword to search for
            signature_size (int): Size of signature
            n_gram (int): Size of n-grams
            top_n (int): Number of results to return
            
        Returns:
            Dict[str, List[str]]: LSH query results
        """
        from database_utils.db_values.search import convert_to_signature
        
        # Generate a signature from the keyword
        signature = convert_to_signature(keyword, signature_size, n_gram)
        
        # Call the underlying implementation with the signature
        return self._instance.query_lsh(signature, top_n)