import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import pymysql
from pymysql.cursors import DictCursor

from src.runner.mysql_manager import MySQLDatabaseManager

@patch.dict('os.environ', {
    'DB_IP': 'localhost',
    'DB_USERNAME': 'test_user',
    'DB_PASSWORD': 'test_password',
    'MYSQL_PORT': '3306',
    'DB_ROOT_PATH': '/tmp'
})
class TestMySQLDatabaseManager(unittest.TestCase):
    """Test cases for MySQLDatabaseManager"""
    
    def setUp(self):
        """Set up test environment - with mocked MySQL connection"""
        self.db_name = "test_db"
        self.db_id = "test_db_id"
        
        # Create patch for PooledDB
        self.mock_pooled_db = patch('src.runner.mysql_manager.PooledDB').start()
        
        # Mock the pool connection
        self.mock_pool = MagicMock()
        self.mock_pooled_db.return_value = self.mock_pool
        
        # Mock connection and cursor
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock(spec=DictCursor)
        self.mock_pool.connection.return_value = self.mock_connection
        self.mock_connection.cursor.return_value = self.mock_cursor
        
        # Create manager instance
        self.manager = MySQLDatabaseManager(db_name=self.db_name, db_id=self.db_id)
    
    def tearDown(self):
        """Clean up after test"""
        patch.stopall()
    
    def test_initialization(self):
        """Test manager initialization"""
        self.assertEqual(self.manager.db_name, self.db_name)
        self.assertEqual(self.manager.db_id, self.db_id)
        self.assertEqual(self.manager.host, "localhost")
        self.assertEqual(self.manager.user, "test_user")
        self.assertEqual(self.manager.password, "test_password")
        self.assertEqual(self.manager.port, 3306)
        
        # Check that pool was initialized
        self.mock_pooled_db.assert_called_once()
        args, kwargs = self.mock_pooled_db.call_args
        self.assertEqual(kwargs["creator"], pymysql)
        self.assertEqual(kwargs["host"], "localhost")
        self.assertEqual(kwargs["user"], "test_user")
        self.assertEqual(kwargs["password"], "test_password")
        self.assertEqual(kwargs["port"], 3306)
        self.assertEqual(kwargs["database"], self.db_name)
    
    def test_connect_disconnect(self):
        """Test connect and disconnect methods"""
        # Connection should be None initially
        self.assertIsNone(self.manager._connection)
        
        # Connect should get connection from pool
        self.manager.connect()
        self.mock_pool.connection.assert_called_once()
        self.assertEqual(self.manager._connection, self.mock_connection)
        self.assertEqual(self.manager._cursor, self.mock_cursor)
        
        # Disconnect should close connection
        self.manager.disconnect()
        self.mock_connection.close.assert_called_once()
        self.assertIsNone(self.manager._connection)
        self.assertIsNone(self.manager._cursor)
    
    def test_execute_sql_select(self):
        """Test SQL SELECT execution"""
        # Mock cursor fetchall results
        self.mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Test"}
        ]
        self.mock_cursor.rowcount = 1
        
        # Execute a SELECT query
        result = self.manager.execute_sql("SELECT * FROM test_table")
        
        # Check result structure
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["results"])
        self.assertEqual(result["rowcount"], 1)
        self.assertIsNone(result["error"])
        
        # Check cursor was called correctly
        self.mock_cursor.execute.assert_called_once_with("SELECT * FROM test_table", None)
        self.mock_cursor.fetchall.assert_called_once()
        
        # No commit for SELECT
        self.mock_connection.commit.assert_not_called()
    
    def test_execute_sql_insert(self):
        """Test SQL INSERT execution"""
        # Mock cursor
        self.mock_cursor.rowcount = 1
        
        # Execute an INSERT query
        result = self.manager.execute_sql("INSERT INTO test_table VALUES (1, 'Test')")
        
        # Check result structure
        self.assertTrue(result["success"])
        self.assertIsNone(result["results"])
        self.assertEqual(result["rowcount"], 1)
        self.assertIsNone(result["error"])
        
        # Check cursor was called correctly
        self.mock_cursor.execute.assert_called_once_with("INSERT INTO test_table VALUES (1, 'Test')", None)
        self.mock_cursor.fetchall.assert_not_called()
        
        # Commit should be called for INSERT
        self.mock_connection.commit.assert_called_once()
    
    def test_execute_sql_error(self):
        """Test SQL execution with error"""
        # Mock cursor to raise exception
        error_msg = "SQL syntax error"
        self.mock_cursor.execute.side_effect = Exception(error_msg)
        
        # Execute query that triggers error
        result = self.manager.execute_sql("INVALID SQL")
        
        # Check result structure
        self.assertFalse(result["success"])
        self.assertIsNone(result["results"])
        self.assertEqual(result["rowcount"], 0)
        self.assertEqual(result["error"], error_msg)
    
    def test_get_db_schema(self):
        """Test schema retrieval"""
        # Mock SHOW TABLES result
        self.mock_cursor.fetchall.side_effect = [
            [{"Tables_in_test_db": "table1"}, {"Tables_in_test_db": "table2"}],
            [{"Field": "id"}, {"Field": "name"}],
            [{"Field": "id"}, {"Field": "value"}]
        ]
        
        # Call get_db_schema
        schema = self.manager.get_db_schema()
        
        # Check schema structure
        self.assertIn("table1", schema)
        self.assertIn("table2", schema)
        self.assertEqual(schema["table1"], ["id", "name"])
        self.assertEqual(schema["table2"], ["id", "value"])
        
        # Check SQL calls
        self.assertEqual(self.mock_cursor.execute.call_count, 3)
        calls = [
            call("SHOW TABLES"),
            call("DESCRIBE `table1`"),
            call("DESCRIBE `table2`")
        ]
        self.mock_cursor.execute.assert_has_calls(calls, any_order=False)
    
    def test_transactions(self):
        """Test transaction methods"""
        # Test begin_transaction
        self.manager.begin_transaction()
        self.mock_cursor.execute.assert_called_once_with("START TRANSACTION")
        self.mock_cursor.execute.reset_mock()
        
        # Test commit
        self.manager.commit()
        self.mock_connection.commit.assert_called_once()
        self.mock_connection.commit.reset_mock()
        
        # Test rollback
        self.manager.rollback()
        self.mock_connection.rollback.assert_called_once()
    
    def test_ensure_schema_exists(self):
        """Test schema creation for LSH and vectors"""
        # Call _ensure_schema_exists
        self.manager._ensure_schema_exists()
        
        # Verify the CREATE TABLE statements were executed
        self.assertEqual(self.mock_cursor.execute.call_count, 2)
        
        # Check SQL contains expected CREATE TABLE statements
        calls = self.mock_cursor.execute.call_args_list
        self.assertIn("CREATE TABLE IF NOT EXISTS `lsh_signatures`", calls[0][0][0])
        self.assertIn("CREATE TABLE IF NOT EXISTS `vector_metadata`", calls[1][0][0])
        
        # Verify commit was called
        self.mock_connection.commit.assert_called_once()
    
    @patch('src.runner.mysql_manager.Chroma')
    def test_init_vector_db(self, mock_chroma):
        """Test vector database initialization"""
        # Mock Chroma
        mock_chroma_instance = MagicMock()
        mock_chroma.return_value = mock_chroma_instance
        
        # Set up db_directory_path for testing
        self.manager.db_directory_path = Path("/tmp/test_path")
        
        # Call _init_vector_db
        self.manager._init_vector_db()
        
        # Verify Chroma was instantiated correctly
        mock_chroma.assert_called_once()
        args, kwargs = mock_chroma.call_args
        self.assertEqual(kwargs["persist_directory"], str(self.manager.db_directory_path / "context_vector_db"))
        self.assertEqual(self.manager.vector_db, mock_chroma_instance)
    
    @patch('src.runner.mysql_manager.uuid.uuid4')
    def test_store_vector(self, mock_uuid):
        """Test vector storage"""
        # Mock dependencies
        mock_uuid.return_value = "test-uuid-12345"
        self.manager._ensure_schema_exists = MagicMock()
        self.manager._init_vector_db = MagicMock()
        self.manager.vector_db = MagicMock()
        
        # Test data
        vector = [0.1, 0.2, 0.3]
        metadata = {"key": "value", "text_chunk_id": "chunk123"}
        source_id = "test_source"
        
        # Call store_vector
        result_id = self.manager.store_vector(vector, metadata, source_id)
        
        # Check result is the expected UUID
        self.assertEqual(result_id, "test-uuid-12345")
        
        # Verify schema was ensured
        self.manager._ensure_schema_exists.assert_called_once()
        
        # Verify vector_db was initialized
        self.manager._init_vector_db.assert_called_once()
        
        # Verify vector was added to ChromaDB
        self.manager.vector_db.add.assert_called_once()
        args, kwargs = self.manager.vector_db.add.call_args
        self.assertEqual(kwargs["embeddings"], [vector])
        self.assertEqual(len(kwargs["metadatas"]), 1)
        self.assertEqual(kwargs["metadatas"][0]["source_id"], source_id)
        self.assertEqual(kwargs["metadatas"][0]["chroma_id"], "test-uuid-12345")
        self.assertEqual(kwargs["ids"], ["test-uuid-12345"])
        
        # Verify metadata was stored in MySQL
        self.mock_cursor.execute.assert_called_once()
        args, kwargs = self.mock_cursor.execute.call_args
        self.assertIn("INSERT INTO vector_metadata", args[0])
        self.assertEqual(args[1][0], "test-uuid-12345")  # chroma_id
        self.assertEqual(args[1][1], source_id)  # source_id
        self.assertEqual(args[1][2], "chunk123")  # text_chunk_id
        json_metadata = json.loads(args[1][3])  # metadata JSON
        self.assertEqual(json_metadata["key"], "value")
        
        # Verify commit was called
        self.mock_connection.commit.assert_called_once()
    
    def test_query_vector_db_no_filter(self):
        """Test vector querying without filters"""
        # Mock dependencies
        self.manager._init_vector_db = MagicMock()
        self.manager.vector_db = MagicMock()
        
        # Mock ChromaDB query result
        mock_result = {
            'ids': [['id1', 'id2']],
            'metadatas': [[{'key1': 'value1'}, {'key2': 'value2'}]],
            'distances': [[0.1, 0.2]]
        }
        self.manager.vector_db.query.return_value = mock_result
        
        # Call query_vector_db without filters
        query_vector = [0.1, 0.2, 0.3]
        results = self.manager.query_vector_db(query_vector, 2)
        
        # Verify vector_db was initialized
        self.manager._init_vector_db.assert_called_once()
        
        # Verify no MySQL query was performed for filtering
        self.mock_cursor.execute.assert_not_called()
        
        # Verify ChromaDB query was called correctly
        self.manager.vector_db.query.assert_called_once()
        args, kwargs = self.manager.vector_db.query.call_args
        self.assertEqual(kwargs["query_embeddings"], [query_vector])
        self.assertEqual(kwargs["n_results"], 2)
        self.assertIsNone(kwargs["where"])
        
        # Verify results format
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], 'id1')
        self.assertEqual(results[0]['metadata'], {'key1': 'value1'})
        self.assertEqual(results[0]['score'], 0.1)
        self.assertEqual(results[1]['id'], 'id2')
        self.assertEqual(results[1]['metadata'], {'key2': 'value2'})
        self.assertEqual(results[1]['score'], 0.2)
    
    def test_query_vector_db_with_filter(self):
        """Test vector querying with filters"""
        # Mock dependencies
        self.manager._init_vector_db = MagicMock()
        self.manager.vector_db = MagicMock()
        
        # Mock MySQL query result for filtering
        self.mock_cursor.fetchall.return_value = [
            {"chroma_id": "id1"},
            {"chroma_id": "id2"}
        ]
        
        # Mock ChromaDB query result
        mock_result = {
            'ids': [['id1', 'id2']],
            'metadatas': [[{'key1': 'value1'}, {'key2': 'value2'}]],
            'distances': [[0.1, 0.2]]
        }
        self.manager.vector_db.query.return_value = mock_result
        
        # Call query_vector_db with filters
        query_vector = [0.1, 0.2, 0.3]
        filter_criteria = {
            "source_id": "test_source",
            "text_chunk_id": "chunk123",
            "category": "test"
        }
        results = self.manager.query_vector_db(query_vector, 2, filter_criteria)
        
        # Verify vector_db was initialized
        self.manager._init_vector_db.assert_called_once()
        
        # Verify MySQL query was called correctly for filtering
        self.mock_cursor.execute.assert_called_once()
        args, kwargs = self.mock_cursor.execute.call_args
        self.assertIn("SELECT chroma_id FROM vector_metadata", args[0])
        self.assertIn("source_id = %s", args[0])
        self.assertIn("text_chunk_id = %s", args[0])
        self.assertIn("JSON_CONTAINS(metadata, %s, '$.category')", args[0])
        self.assertEqual(args[1][0], "test_source")
        self.assertEqual(args[1][1], "chunk123")
        
        # Verify ChromaDB query was called with the filtered IDs
        self.manager.vector_db.query.assert_called_once()
        args, kwargs = self.manager.vector_db.query.call_args
        self.assertEqual(kwargs["query_embeddings"], [query_vector])
        self.assertEqual(kwargs["n_results"], 2)
        self.assertEqual(kwargs["where"], {"chroma_id": {"$in": ["id1", "id2"]}})
        
        # Verify results format
        self.assertEqual(len(results), 2)
    
    def test_store_lsh_signature(self):
        """Test LSH signature storage"""
        # Mock _ensure_schema_exists
        self.manager._ensure_schema_exists = MagicMock()
        
        # Call store_lsh_signature
        self.manager.store_lsh_signature(
            signature_hash="test_hash",
            bucket_id=42,
            data_ref="test_data_ref",
            source_id="test_source"
        )
        
        # Verify schema was ensured
        self.manager._ensure_schema_exists.assert_called_once()
        
        # Verify SQL was executed correctly
        self.mock_cursor.execute.assert_called_once()
        args, kwargs = self.mock_cursor.execute.call_args
        self.assertIn("INSERT INTO lsh_signatures", args[0])
        self.assertEqual(args[1][0], "test_hash")
        self.assertEqual(args[1][1], 42)
        self.assertEqual(args[1][2], "test_data_ref")
        self.assertEqual(args[1][3], "test_source")
        
        # Verify commit was called
        self.mock_connection.commit.assert_called_once()
    
    def test_query_lsh(self):
        """Test LSH querying"""
        # Mock cursor fetchall results
        self.mock_cursor.fetchall.return_value = [
            {"data_reference": "ref1", "matches": 3},
            {"data_reference": "ref2", "matches": 1}
        ]
        
        # Call query_lsh
        query_signature = ["hash1", "hash2", "hash3"]
        top_n = 2
        results = self.manager.query_lsh(query_signature, top_n)
        
        # Verify SQL was executed correctly
        self.mock_cursor.execute.assert_called_once()
        args, kwargs = self.mock_cursor.execute.call_args
        self.assertIn("SELECT data_reference, COUNT(*) as matches", args[0])
        self.assertIn("FROM lsh_signatures", args[0])
        self.assertIn("WHERE signature_hash IN", args[0])
        self.assertIn("GROUP BY data_reference", args[0])
        self.assertIn("ORDER BY matches DESC", args[0])
        self.assertIn("LIMIT %s", args[0])
        
        # Check parameters include signature hashes and top_n
        self.assertEqual(args[1][:3], query_signature)
        self.assertEqual(args[1][3], top_n)
        
        # Verify results format
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["data_ref"], "ref1")
        self.assertEqual(results[0]["matches"], 3)
        self.assertEqual(results[1]["data_ref"], "ref2")
        self.assertEqual(results[1]["matches"], 1)
    
    def test_clear_lsh_data(self):
        """Test clearing LSH data"""
        # Call clear_lsh_data
        self.manager.clear_lsh_data()
        
        # Verify SQL was executed correctly
        self.mock_cursor.execute.assert_called_once_with("TRUNCATE TABLE lsh_signatures")
        
        # Verify commit was called
        self.mock_connection.commit.assert_called_once()
    
    def test_clear_vector_data(self):
        """Test clearing vector data"""
        # Setup mock vector_db
        self.manager.vector_db = MagicMock()
        
        # Call clear_vector_data
        self.manager.clear_vector_data()
        
        # Verify SQL was executed correctly for MySQL part
        self.mock_cursor.execute.assert_called_once_with("TRUNCATE TABLE vector_metadata")
        
        # Verify ChromaDB data was cleared
        self.manager.vector_db.delete.assert_called_once_with(where={})
        
        # Verify vector_db was reset
        self.assertIsNone(self.manager.vector_db)
        
        # Verify commit was called
        self.mock_connection.commit.assert_called_once()
        
if __name__ == '__main__':
    unittest.main()