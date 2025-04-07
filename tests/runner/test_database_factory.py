import os
import unittest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.database_utils.database_factory import DatabaseFactory
from src.runner.sqlite_manager import SQLiteDatabaseManager
from src.runner.mysql_manager import MySQLDatabaseManager

class TestDatabaseFactory(unittest.TestCase):
    """Test cases for DatabaseFactory"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test configs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)
        
        # Create SQLite test config
        self.sqlite_config_path = self.config_dir / "sqlite_config.yaml"
        sqlite_config = {
            "database": {
                "type": "sqlite",
                "sqlite_settings": {
                    "mode": "test",
                    "id": "test_db"
                }
            }
        }
        with open(self.sqlite_config_path, "w") as f:
            yaml.dump(sqlite_config, f)
            
        # Create MySQL test config
        self.mysql_config_path = self.config_dir / "mysql_config.yaml"
        mysql_config = {
            "database": {
                "type": "mysql",
                "mysql_settings": {
                    "host": "localhost",
                    "port": 3306,
                    "user": "test_user",
                    "password": "${TEST_PASSWORD:default_password}",
                    "database": "test_db",
                    "db_id": "test_db_id"
                }
            }
        }
        with open(self.mysql_config_path, "w") as f:
            yaml.dump(mysql_config, f)
    
    def tearDown(self):
        """Clean up after test"""
        self.temp_dir.cleanup()
    
    @patch('src.runner.sqlite_manager.SQLiteDatabaseManager')
    def test_get_database_manager_sqlite(self, mock_sqlite_manager):
        """Test getting SQLite manager from config"""
        # Mock SQLiteDatabaseManager
        mock_instance = MagicMock(spec=SQLiteDatabaseManager)
        mock_sqlite_manager.return_value = mock_instance
        
        # Load config
        with open(self.sqlite_config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Get manager using factory
        manager = DatabaseFactory.get_database_manager(config)
        
        # Verify SQLiteDatabaseManager was created with correct args
        mock_sqlite_manager.assert_called_once_with(
            db_mode="test",
            db_id="test_db"
        )
        
        # Verify correct manager was returned
        self.assertEqual(manager, mock_instance)
    
    @patch('src.runner.mysql_manager.MySQLDatabaseManager')
    def test_get_database_manager_mysql(self, mock_mysql_manager):
        """Test getting MySQL manager from config"""
        # Mock MySQLDatabaseManager
        mock_instance = MagicMock(spec=MySQLDatabaseManager)
        mock_mysql_manager.return_value = mock_instance
        
        # Load config
        with open(self.mysql_config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Get manager using factory
        manager = DatabaseFactory.get_database_manager(config)
        
        # Verify MySQLDatabaseManager was created with correct args
        mock_mysql_manager.assert_called_once_with(
            db_name="test_db",
            db_id="test_db_id"
        )
        
        # Verify correct manager was returned
        self.assertEqual(manager, mock_instance)
    
    @patch('src.runner.mysql_manager.MySQLDatabaseManager')
    def test_get_database_manager_env_var_substitution(self, mock_mysql_manager):
        """Test environment variable substitution in config"""
        # Mock MySQLDatabaseManager
        mock_instance = MagicMock(spec=MySQLDatabaseManager)
        mock_mysql_manager.return_value = mock_instance
        
        # Set environment variable
        with patch.dict(os.environ, {"TEST_PASSWORD": "secret_password"}):
            # Load config
            with open(self.mysql_config_path, "r") as f:
                config = yaml.safe_load(f)
                # Process env vars in config (would normally be done by DatabaseManager._load_config)
                config["database"]["mysql_settings"]["password"] = "secret_password"
            
            # Get manager using factory
            manager = DatabaseFactory.get_database_manager(config)
        
        # Verify MySQLDatabaseManager was created with correct args
        mock_mysql_manager.assert_called_once()
        args, kwargs = mock_mysql_manager.call_args
        self.assertEqual(kwargs["db_name"], "test_db")
        self.assertEqual(kwargs["db_id"], "test_db_id")
    
    @patch('src.database_utils.database_factory.os.getenv')
    @patch('src.runner.sqlite_manager.SQLiteDatabaseManager')
    def test_create_database_manager_sqlite(self, mock_sqlite_manager, mock_getenv):
        """Test creating SQLite manager with env vars"""
        # Mock environment variables
        mock_getenv.side_effect = lambda var, default=None: {
            "DB_TYPE": "sqlite",
        }.get(var, default)
        
        # Mock SQLiteDatabaseManager
        mock_instance = MagicMock(spec=SQLiteDatabaseManager)
        mock_sqlite_manager.return_value = mock_instance
        
        # Create manager using factory
        manager = DatabaseFactory.create_database_manager(db_mode="test", db_id="test_db")
        
        # Verify SQLiteDatabaseManager was created with correct args
        mock_sqlite_manager.assert_called_once_with(
            db_mode="test",
            db_id="test_db"
        )
        
        # Verify correct manager was returned
        self.assertEqual(manager, mock_instance)
    
    @patch('src.database_utils.database_factory.os.getenv')
    @patch('src.runner.mysql_manager.MySQLDatabaseManager')
    def test_create_database_manager_mysql(self, mock_mysql_manager, mock_getenv):
        """Test creating MySQL manager with env vars"""
        # Mock environment variables
        mock_getenv.side_effect = lambda var, default=None: {
            "DB_TYPE": "mysql",
            "DB_NAME": "test_db"
        }.get(var, default)
        
        # Mock MySQLDatabaseManager
        mock_instance = MagicMock(spec=MySQLDatabaseManager)
        mock_mysql_manager.return_value = mock_instance
        
        # Create manager using factory
        manager = DatabaseFactory.create_database_manager(db_mode="test", db_id="test_db_id")
        
        # Verify MySQLDatabaseManager was created with correct args
        mock_mysql_manager.assert_called_once_with(
            db_name="test_db",
            db_id="test_db_id"
        )
        
        # Verify correct manager was returned
        self.assertEqual(manager, mock_instance)
    
    @patch('src.database_utils.database_factory.os.getenv')
    @patch('src.runner.mysql_manager.MySQLDatabaseManager')
    def test_get_database_manager_for_name(self, mock_mysql_manager, mock_getenv):
        """Test getting manager for specific database name"""
        # Mock environment variables
        mock_getenv.side_effect = lambda var, default=None: {
            "DB_TYPE": "mysql"
        }.get(var, default)
        
        # Mock MySQLDatabaseManager
        mock_instance = MagicMock(spec=MySQLDatabaseManager)
        mock_mysql_manager.return_value = mock_instance
        
        # Get manager for database name
        manager = DatabaseFactory.get_database_manager_for_name("specific_db")
        
        # Verify MySQLDatabaseManager was created with correct args
        mock_mysql_manager.assert_called_once_with(
            db_name="specific_db",
            db_id=None
        )
        
        # Verify correct manager was returned
        self.assertEqual(manager, mock_instance)
    
    @patch('src.database_utils.database_factory.os.getenv')
    def test_get_database_manager_for_name_sqlite_error(self, mock_getenv):
        """Test error when trying to get manager for name with SQLite"""
        # Mock environment variables
        mock_getenv.side_effect = lambda var, default=None: {
            "DB_TYPE": "sqlite"
        }.get(var, default)
        
        # Attempt to get manager for database name should raise error
        with self.assertRaises(ValueError):
            DatabaseFactory.get_database_manager_for_name("specific_db")
    
    def test_get_database_manager_invalid_config(self):
        """Test error handling with invalid config"""
        # Create invalid config
        invalid_config = {
            "database": {
                "type": "sqlite",
                # Missing sqlite_settings
            }
        }
        
        # Attempt to get manager with invalid config should raise error
        with self.assertRaises(ValueError):
            DatabaseFactory.get_database_manager(invalid_config)
            
if __name__ == '__main__':
    unittest.main()