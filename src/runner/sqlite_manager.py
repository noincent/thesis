import os
import socket
import pickle
from threading import Lock
from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from typing import Callable, Dict, List, Any, Optional, Tuple
import time
import sqlite3

from database_utils.database_interface import DatabaseInterface
from database_utils.schema import DatabaseSchema
from database_utils.schema_generator import DatabaseSchemaGenerator
from database_utils.execution import execute_sql, compare_sqls, validate_sql_query, aggregate_sqls, get_execution_status, subprocess_sql_executor
from database_utils.db_info import get_db_all_tables, get_table_all_columns, get_db_schema
from database_utils.sql_parser import get_sql_tables, get_sql_columns_dict, get_sql_condition_literals
from database_utils.db_values.search import query_lsh as db_query_lsh
from database_utils.db_catalog.search import query_vector_db as db_query_vector_db
from database_utils.db_catalog.preprocess import EMBEDDING_FUNCTION
from database_utils.db_catalog.csv_utils import load_tables_description

load_dotenv(override=True)
DB_ROOT_PATH = Path(os.getenv("DB_ROOT_PATH"))

INDEX_SERVER_HOST = os.getenv("INDEX_SERVER_HOST")
INDEX_SERVER_PORT = int(os.getenv("INDEX_SERVER_PORT"))

class SQLiteDatabaseManager(DatabaseInterface):
    """
    SQLite implementation of the DatabaseInterface.
    Manages database operations including schema generation, querying LSH and vector databases,
    and managing column profiles.
    """
    
    def __init__(self, db_mode: str, db_id: str):
        """
        Initializes the SQLiteDatabaseManager instance.

        Args:
            db_mode (str): The mode of the database (e.g., 'train', 'test').
            db_id (str): The database identifier.
        """
        self.db_mode = db_mode
        self.db_id = db_id
        self._set_paths()
        self.lsh = None
        self.minhashes = None
        self.vector_db = None
        self._connection = None
        self._cursor = None
        self._lock = Lock()  # Lock for thread safety, but not singleton related

    def _set_paths(self):
        """Sets the paths for the database files and directories."""
        self.db_path = DB_ROOT_PATH / f"{self.db_mode}_databases" / self.db_id / f"{self.db_id}.sqlite"
        self.db_directory_path = DB_ROOT_PATH / f"{self.db_mode}_databases" / self.db_id

    def connect(self) -> None:
        """Establish connection to the SQLite database."""
        try:
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
            self._cursor = self._connection.cursor()
        except sqlite3.Error as e:
            raise Exception(f"Failed to connect to SQLite database: {e}")

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
        Execute a SQL query in the SQLite database and return the results.
        
        Args:
            query (str): SQL query to execute
            params (tuple, optional): Parameters for the SQL query
            
        Returns:
            Dict[str, Any]: Dictionary containing execution results
        """
        return execute_sql(self.db_path, query, params)

    def get_db_schema(self) -> Dict[str, List[str]]:
        """
        Get the database schema including all tables and their columns.
        
        Returns:
            Dict[str, List[str]]: Dictionary with table names as keys and lists of column names as values
        """
        return get_db_schema(self.db_path)

    def begin_transaction(self) -> None:
        """Begin a database transaction."""
        if not self._connection:
            self.connect()
        self._connection.execute("BEGIN TRANSACTION")

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._connection:
            self._connection.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._connection:
            self._connection.rollback()

    def set_lsh(self) -> str:
        """Sets the LSH and minhashes attributes by loading from pickle files."""
        with self._lock:  # Thread safety for instance-level operations
            if self.lsh is None:
                try:
                    with (self.db_directory_path / "preprocessed" / f"{self.db_id}_lsh.pkl").open("rb") as file:
                        self.lsh = pickle.load(file)
                    with (self.db_directory_path / "preprocessed" / f"{self.db_id}_minhashes.pkl").open("rb") as file:
                        self.minhashes = pickle.load(file)
                    return "success"
                except Exception as e:
                    self.lsh = "error"
                    self.minhashes = "error"
                    print(f"Error loading LSH for {self.db_id}: {e}")
                    return "error"
            elif self.lsh == "error":
                return "error"
            else:
                return "success"

    def set_vector_db(self) -> str:
        """Sets the vector_db attribute by loading from the context vector database."""
        if self.vector_db is None:
            try:
                vector_db_path = self.db_directory_path / "context_vector_db"
                self.vector_db = Chroma(persist_directory=str(vector_db_path), embedding_function=EMBEDDING_FUNCTION)
                return "success"
            except Exception as e:
                self.vector_db = "error"
                print(f"Error loading Vector DB for {self.db_id}: {e}")
                return "error"
        elif self.vector_db == "error":
            return "error"
        else:
            return "success"

    def query_lsh(self, query_signature: List[str], top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Queries the LSH for similar values using the precomputed query signature.

        Args:
            query_signature (List[str]): The precomputed signature hashes to search for.
            top_n (int, optional): The number of top results to return. Defaults to 10.

        Returns:
            List[Dict[str, Any]]: List of matching results.
        """
        lsh_status = self.set_lsh()
        if lsh_status == "success":
            # Note: This is a simplified adapter - the actual implementation 
            # would need to convert the input signature format as needed
            keyword = " ".join(query_signature) if isinstance(query_signature, list) else query_signature
            results = db_query_lsh(self.lsh, self.minhashes, keyword, 100, 3, top_n)
            
            # Convert to the expected return format
            return [{"data_ref": k, "matches": len(v)} for k, v in results.items()]
        else:
            raise Exception(f"Error loading LSH for {self.db_id}")

    def store_vector(self, vector: List[float], metadata: Dict[str, Any], source_id: str) -> str:
        """
        Store a vector with its metadata in the vector database.
        In SQLite implementation, this directly stores into ChromaDB.
        
        Args:
            vector (List[float]): The vector embedding to store
            metadata (Dict[str, Any]): Associated metadata
            source_id (str): Identifier for the source document/data
            
        Returns:
            str: Identifier for the stored vector
        """
        vector_db_status = self.set_vector_db()
        if vector_db_status != "success":
            raise Exception(f"Error loading Vector DB for {self.db_id}")
            
        # Add source_id to metadata
        metadata["source_id"] = source_id
        
        # Generate a unique ID for the vector
        vector_id = f"{source_id}_{int(time.time() * 1000)}"
        
        # Store in ChromaDB
        self.vector_db.add(
            embeddings=[vector],
            metadatas=[metadata],
            ids=[vector_id]
        )
        
        return vector_id

    def query_vector_db(self, query_vector: List[float], top_k: int, filter_criteria: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Query the vector database for similar vectors.
        
        Args:
            query_vector (List[float]): Vector to search for
            top_k (int): Number of results to return
            filter_criteria (Dict[str, Any], optional): Criteria to filter results
            
        Returns:
            List[Dict[str, Any]]: List of matching results with their metadata
        """
        vector_db_status = self.set_vector_db()
        if vector_db_status != "success":
            raise Exception(f"Error loading Vector DB for {self.db_id}")
            
        # Convert filter_criteria to ChromaDB where_document format if provided
        where = filter_criteria if filter_criteria else None
            
        # Query ChromaDB
        results = self.vector_db.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where
        )
        
        # Process and return results
        formatted_results = []
        if results and len(results['metadatas']) > 0:
            for i in range(len(results['metadatas'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': results['distances'][0][i] if 'distances' in results else None
                })
                
        return formatted_results

    def store_lsh_signature(self, signature_hash: str, bucket_id: int, data_ref: str, source_id: str) -> None:
        """
        Store an LSH signature in the database.
        For SQLite implementation, this is a placeholder as LSH is stored in pickle files.
        
        Args:
            signature_hash (str): The hash value of the signature
            bucket_id (int): The LSH bucket identifier
            data_ref (str): Reference to the original data
            source_id (str): Identifier for the source document/data
        """
        # In the SQLite implementation, LSH signatures are stored in memory and pickled
        # This is just a placeholder implementation
        print("SQLite implementation doesn't directly support store_lsh_signature. "
              "LSH data is managed through pickle files.")
        pass

    def clear_lsh_data(self) -> None:
        """
        Clear all LSH data.
        For SQLite implementation, this resets the in-memory LSH data structures.
        """
        self.lsh = None
        self.minhashes = None
        # Optional: Remove pickle files if they should be deleted
        lsh_path = self.db_directory_path / "preprocessed" / f"{self.db_id}_lsh.pkl"
        minhash_path = self.db_directory_path / "preprocessed" / f"{self.db_id}_minhashes.pkl"
        if lsh_path.exists():
            lsh_path.unlink()
        if minhash_path.exists():
            minhash_path.unlink()

    def clear_vector_data(self) -> None:
        """
        Clear all vector data from ChromaDB.
        """
        vector_db_status = self.set_vector_db()
        if vector_db_status == "success":
            # Clear the ChromaDB collection
            self.vector_db.delete(where={})
            # Reset the vector_db reference
            self.vector_db = None

    def get_column_profiles(self, schema_with_examples: Dict[str, Dict[str, List[str]]],
                        use_value_description: bool, with_keys: bool, 
                        with_references: bool,
                        tentative_schema: Dict[str, List[str]] = None) -> Dict[str, Dict[str, str]]:
        """
        Generates column profiles for the schema.

        Args:
            schema_with_examples (Dict[str, List[str]]): Schema with example values.
            use_value_description (bool): Whether to use value descriptions.
            with_keys (bool): Whether to include keys.
            with_references (bool): Whether to include references.

        Returns:
            Dict[str, Dict[str, str]]: The dictionary of column profiles.
        """
        schema_with_descriptions = load_tables_description(self.db_directory_path, use_value_description)
        database_schema_generator = DatabaseSchemaGenerator(
            tentative_schema=DatabaseSchema.from_schema_dict(tentative_schema if tentative_schema else self.get_db_schema()),
            schema_with_examples=DatabaseSchema.from_schema_dict_with_examples(schema_with_examples),
            schema_with_descriptions=DatabaseSchema.from_schema_dict_with_descriptions(schema_with_descriptions),
            db_id=self.db_id,
            db_path=self.db_path,
            add_examples=True,
        )
        
        column_profiles = database_schema_generator.get_column_profiles(with_keys, with_references)
        return column_profiles

    def get_database_schema_string(self, tentative_schema: Dict[str, List[str]], 
                               schema_with_examples: Dict[str, List[str]], 
                               schema_with_descriptions: Dict[str, Dict[str, Dict[str, Any]]], 
                               include_value_description: bool) -> str:
        """
        Generates a schema string for the database.

        Args:
            tentative_schema (Dict[str, List[str]]): The tentative schema.
            schema_with_examples (Dict[str, List[str]]): Schema with example values.
            schema_with_descriptions (Dict[str, Dict[str, Dict[str, Any]]]): Schema with descriptions.
            include_value_description (bool): Whether to include value descriptions.

        Returns:
            str: The generated schema string.
        """
        schema_generator = DatabaseSchemaGenerator(
            tentative_schema=DatabaseSchema.from_schema_dict(tentative_schema),
            schema_with_examples=DatabaseSchema.from_schema_dict_with_examples(schema_with_examples) if schema_with_examples else None,
            schema_with_descriptions=DatabaseSchema.from_schema_dict_with_descriptions(schema_with_descriptions) if schema_with_descriptions else None,
            db_id=self.db_id,
            db_path=self.db_path,
        )
        schema_string = schema_generator.generate_schema_string(include_value_description=include_value_description)
        return schema_string
    
    def add_connections_to_tentative_schema(self, tentative_schema: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Adds connections to the tentative schema.

        Args:
            tentative_schema (Dict[str, List[str]]): The tentative schema.

        Returns:
            Dict[str, List[str]]: The updated schema with connections.
        """
        schema_generator = DatabaseSchemaGenerator(
            tentative_schema=DatabaseSchema.from_schema_dict(tentative_schema),
            db_id=self.db_id,
            db_path=self.db_path,
        )
        return schema_generator.get_schema_with_connections()

    def get_union_schema_dict(self, schema_dict_list: List[Dict[str, List[str]]]) -> Dict[str, List[str]]:
        """
        Unions a list of schemas.

        Args:
            schema_dict_list (List[Dict[str, List[str]]): The list of schemas.

        Returns:
            Dict[str, List[str]]: The unioned schema.
        """
        full_schema = DatabaseSchema.from_schema_dict(self.get_db_schema())
        actual_name_schemas = []
        for schema in schema_dict_list:
            subselect_schema = full_schema.subselect_schema(DatabaseSchema.from_schema_dict(schema))
            schema_dict = subselect_schema.to_dict()
            actual_name_schemas.append(schema_dict)
        union_schema = {}
        for schema in actual_name_schemas:
            for table, columns in schema.items():
                if table not in union_schema:
                    union_schema[table] = columns
                else:
                    union_schema[table] = list(set(union_schema[table] + columns))
        return union_schema

# Helper function for interacting with the index server
def receive_data_in_chunks(conn, chunk_size=1024):
    length_bytes = conn.recv(4)
    if not length_bytes:
        return None
    data_length = int.from_bytes(length_bytes, byteorder='big')
    chunks = []
    bytes_received = 0
    while bytes_received < data_length:
        chunk = conn.recv(min(data_length - bytes_received, chunk_size))
        if not chunk:
            raise ConnectionError("Connection lost")
        chunks.append(chunk)
        bytes_received += len(chunk)
    return pickle.loads(b''.join(chunks))