import os
import unittest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.runner.sqlite_manager import SQLiteDatabaseManager

class TestSQLiteDatabaseManager(unittest.TestCase):
    """Test cases for SQLiteDatabaseManager"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary directory for test databases
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_root_path = Path(self.temp_dir.name)
        
        # Create a test database directory structure
        self.db_mode = "test"
        self.db_id = "test_db"
        self.db_dir = self.db_root_path / f"{self.db_mode}_databases" / self.db_id
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test SQLite database file
        self.db_file = self.db_dir / f"{self.db_id}.sqlite"
        conn = sqlite3.connect(str(self.db_file))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO test_table VALUES (1, 'Test')")
        conn.commit()
        conn.close()
        
        # Create preprocessed directory for LSH/minhash pickle files
        self.preprocessed_dir = self.db_dir / "preprocessed"
        self.preprocessed_dir.mkdir(parents=True, exist_ok=True)
        
        # Patch environment variable
        self.env_patcher = patch.dict('os.environ', {'DB_ROOT_PATH': str(self.db_root_path)})
        self.env_patcher.start()
        
        # Create manager instance
        self.manager = SQLiteDatabaseManager(db_mode=self.db_mode, db_id=self.db_id)
    
    def tearDown(self):
        """Clean up after test"""
        self.env_patcher.stop()
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test manager initialization"""
        self.assertEqual(self.manager.db_mode, self.db_mode)
        self.assertEqual(self.manager.db_id, self.db_id)
        self.assertEqual(self.manager.db_path, self.db_file)
        self.assertEqual(self.manager.db_directory_path, self.db_dir)
    
    def test_connect_disconnect(self):
        """Test connect and disconnect methods"""
        # Connection should be None initially
        self.assertIsNone(self.manager._connection)
        
        # Connect should establish connection
        self.manager.connect()
        self.assertIsNotNone(self.manager._connection)
        self.assertIsNotNone(self.manager._cursor)
        
        # Disconnect should close connection
        self.manager.disconnect()
        self.assertIsNone(self.manager._connection)
        self.assertIsNone(self.manager._cursor)
    
    def test_execute_sql(self):
        """Test SQL execution"""
        # Execute a SELECT query
        result = self.manager.execute_sql("SELECT * FROM test_table")
        
        # Check result structure
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["results"])
        self.assertGreater(result["rowcount"], 0)
        self.assertIsNone(result["error"])
        
        # Check the data
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["id"], 1)
        self.assertEqual(result["results"][0]["name"], "Test")
    
    def test_get_db_schema(self):
        """Test schema retrieval"""
        schema = self.manager.get_db_schema()
        
        # Schema should include our test table
        self.assertIn("test_table", schema)
        self.assertIn("id", schema["test_table"])
        self.assertIn("name", schema["test_table"])
    
    def test_transactions(self):
        """Test transaction methods"""
        # Set up a test with transaction
        self.manager.connect()
        self.manager.begin_transaction()
        
        # Execute an INSERT in transaction
        self.manager._cursor.execute("INSERT INTO test_table VALUES (2, 'Transaction Test')")
        
        # Test rollback
        self.manager.rollback()
        
        # Verify the inserted row was rolled back
        self.manager._cursor.execute("SELECT COUNT(*) FROM test_table WHERE id = 2")
        count = self.manager._cursor.fetchone()[0]
        self.assertEqual(count, 0)
        
        # Test commit
        self.manager.begin_transaction()
        self.manager._cursor.execute("INSERT INTO test_table VALUES (3, 'Commit Test')")
        self.manager.commit()
        
        # Verify the inserted row was committed
        self.manager._cursor.execute("SELECT COUNT(*) FROM test_table WHERE id = 3")
        count = self.manager._cursor.fetchone()[0]
        self.assertEqual(count, 1)
        
        self.manager.disconnect()
    
    @patch('src.runner.sqlite_manager.pickle.load')
    def test_set_lsh(self, mock_pickle_load):
        """Test LSH loading"""
        # Mock the pickle load operation
        mock_lsh = MagicMock()
        mock_minhashes = MagicMock()
        mock_pickle_load.side_effect = [mock_lsh, mock_minhashes]
        
        # Create empty pickle files
        lsh_path = self.preprocessed_dir / f"{self.db_id}_lsh.pkl"
        minhash_path = self.preprocessed_dir / f"{self.db_id}_minhashes.pkl"
        lsh_path.touch()
        minhash_path.touch()
        
        # Test LSH loading
        result = self.manager.set_lsh()
        
        # Check result
        self.assertEqual(result, "success")
        self.assertEqual(self.manager.lsh, mock_lsh)
        self.assertEqual(self.manager.minhashes, mock_minhashes)
    
    @patch('src.runner.sqlite_manager.Chroma')
    def test_set_vector_db(self, mock_chroma):
        """Test vector DB loading"""
        # Mock Chroma
        mock_chroma_instance = MagicMock()
        mock_chroma.return_value = mock_chroma_instance
        
        # Create vector db directory
        vector_db_path = self.db_dir / "context_vector_db"
        vector_db_path.mkdir(parents=True, exist_ok=True)
        
        # Test vector DB loading
        result = self.manager.set_vector_db()
        
        # Check result
        self.assertEqual(result, "success")
        self.assertEqual(self.manager.vector_db, mock_chroma_instance)
        
        # Verify Chroma was instantiated correctly
        mock_chroma.assert_called_once()
        args, kwargs = mock_chroma.call_args
        self.assertEqual(kwargs["persist_directory"], str(vector_db_path))
    
    @patch('src.runner.sqlite_manager.SQLiteDatabaseManager.set_lsh')
    @patch('src.runner.sqlite_manager.db_query_lsh')
    def test_query_lsh(self, mock_query_lsh, mock_set_lsh):
        """Test LSH querying"""
        # Mock dependencies
        mock_set_lsh.return_value = "success"
        mock_results = {
            "result1": ["value1", "value2"],
            "result2": ["value3"]
        }
        mock_query_lsh.return_value = mock_results
        
        # Test query_lsh
        query_signature = ["hash1", "hash2"]
        results = self.manager.query_lsh(query_signature, 10)
        
        # Verify results format matches interface spec
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["data_ref"], "result1")
        self.assertEqual(results[0]["matches"], 2)
        self.assertEqual(results[1]["data_ref"], "result2")
        self.assertEqual(results[1]["matches"], 1)
    
    @patch('src.runner.sqlite_manager.SQLiteDatabaseManager.set_vector_db')
    def test_store_vector(self, mock_set_vector_db):
        """Test vector storage"""
        # Mock dependencies
        mock_set_vector_db.return_value = "success"
        self.manager.vector_db = MagicMock()
        self.manager.vector_db.add.return_value = None
        
        # Test store_vector
        vector = [0.1, 0.2, 0.3]
        metadata = {"key": "value"}
        source_id = "test_source"
        
        result_id = self.manager.store_vector(vector, metadata, source_id)
        
        # Check result is a string (vector ID)
        self.assertIsInstance(result_id, str)
        
        # Verify vector_db.add was called correctly
        self.manager.vector_db.add.assert_called_once()
        args, kwargs = self.manager.vector_db.add.call_args
        self.assertEqual(kwargs["embeddings"], [vector])
        self.assertEqual(len(kwargs["metadatas"]), 1)
        self.assertEqual(kwargs["metadatas"][0]["source_id"], source_id)
    
    @patch('src.runner.sqlite_manager.SQLiteDatabaseManager.set_vector_db')
    def test_query_vector_db(self, mock_set_vector_db):
        """Test vector querying"""
        # Mock dependencies
        mock_set_vector_db.return_value = "success"
        self.manager.vector_db = MagicMock()
        
        # Mock query result
        mock_result = {
            'ids': [['id1', 'id2']],
            'metadatas': [[{'key1': 'value1'}, {'key2': 'value2'}]],
            'distances': [[0.1, 0.2]]
        }
        self.manager.vector_db.query.return_value = mock_result
        
        # Test query_vector_db
        query_vector = [0.1, 0.2, 0.3]
        filter_criteria = {"field": "value"}
        results = self.manager.query_vector_db(query_vector, 2, filter_criteria)
        
        # Verify results format
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], 'id1')
        self.assertEqual(results[0]['metadata'], {'key1': 'value1'})
        self.assertEqual(results[0]['score'], 0.1)
        self.assertEqual(results[1]['id'], 'id2')
        self.assertEqual(results[1]['metadata'], {'key2': 'value2'})
        self.assertEqual(results[1]['score'], 0.2)
        
        # Verify vector_db.query was called correctly
        self.manager.vector_db.query.assert_called_once()
        args, kwargs = self.manager.vector_db.query.call_args
        self.assertEqual(kwargs["query_embeddings"], [query_vector])
        self.assertEqual(kwargs["n_results"], 2)
        self.assertEqual(kwargs["where"], filter_criteria)
        
if __name__ == '__main__':
    unittest.main()