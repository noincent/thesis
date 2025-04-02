import os
import time
import uuid
import pymysql
import json
import logging
import numpy as np
from pathlib import Path
from threading import Lock
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
from langchain_chroma import Chroma
from dbutils.pooled_db import PooledDB

from database_utils.database_interface import DatabaseInterface
from database_utils.schema import DatabaseSchema
from database_utils.schema_generator import DatabaseSchemaGenerator
from database_utils.db_catalog.preprocess import EMBEDDING_FUNCTION
from database_utils.db_catalog.csv_utils import load_tables_description

load_dotenv(override=True)

class MySQLDatabaseManager(DatabaseInterface):
    """
    MySQL implementation of the DatabaseInterface.
    Provides database operations including core database functions, LSH/MinHash
    and vector database integration with ChromaDB.
    """
    # Connection pool is shared across all instances
    _pool = None
    _pool_lock = Lock()

    def __init__(self, db_name: Optional[str], db_id: Optional[str]):
        """
        Initialize the MySQL connection and database settings.
        
        Args:
            db_name (str, optional): Name of the database to connect to
            db_id (str, optional): Database identifier used for vector and LSH operations
        """
        self.db_name = db_name
        self.db_id = db_id
        self.host = os.getenv("DB_IP", "localhost")
        self.user = os.getenv("DB_USERNAME", "root")
        self.password = os.getenv("DB_PASSWORD", "")
        self.port = int(os.getenv("MYSQL_PORT", "3306"))
        self._connection = None
        self._cursor = None
        self.vector_db = None
        self._lock = Lock()  # Instance-level lock for thread safety
        self._in_transaction = False  # Track transaction state
        
        # Define paths for ChromaDB
        if db_id:
            db_root_path = Path(os.getenv("DB_ROOT_PATH", "."))
            self.db_directory_path = db_root_path / f"{db_name}_databases" / db_id
        else:
            self.db_directory_path = None

        # Initialize connection pool if not already created
        with self.__class__._pool_lock:
            if self.__class__._pool is None and db_name:
                self._setup_connection_pool()

    def _setup_connection_pool(self):
        """Set up a connection pool for MySQL database connections."""
        try:
            self.__class__._pool = PooledDB(
                creator=pymysql,
                maxconnections=10,
                mincached=2,
                maxcached=5,
                blocking=True,
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                database=self.db_name,
                cursorclass=pymysql.cursors.DictCursor
            )
        except Exception as e:
            raise Exception(f"Failed to set up MySQL connection pool: {e}")

    def connect(self) -> None:
        """Establish connection to the MySQL database from the pool."""
        try:
            if self.__class__._pool is None:
                self._setup_connection_pool()
                
            self._connection = self.__class__._pool.connection()
            self._cursor = self._connection.cursor()
        except Exception as e:
            raise Exception(f"Failed to connect to MySQL: {e}")

    def disconnect(self) -> None:
        """Return the connection to the pool."""
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
        if not self._connection:
            self.connect()
            
        try:
            self._cursor.execute(query, params)
            
            if query.strip().upper().startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")):
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
                
        except Exception as err:
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
        if not self._connection:
            self.connect()
            
        try:
            self._cursor.execute("SHOW TABLES")
            tables = [table[f"Tables_in_{self.db_name}"] for table in self._cursor.fetchall()]
            
            for table in tables:
                self._cursor.execute(f"DESCRIBE `{table}`")
                columns = [column["Field"] for column in self._cursor.fetchall()]
                schema[table] = columns
                
            return schema
        except Exception as err:
            raise Exception(f"Failed to get database schema: {err}")

    def begin_transaction(self) -> None:
        """
        Begin a database transaction with enhanced error handling.
        
        This implementation handles the complexities of transaction management
        with connection pooling in DBUtils+PyMySQL.
        """
        with self._lock:  # Ensure thread safety
            if not self._connection:
                self.connect()
                
            # Mark transaction as active in this instance
            self._in_transaction = True
            
            # Start a transaction - try multiple approaches
            try:
                # First attempt: explicit START TRANSACTION
                self._cursor.execute("START TRANSACTION")
                logging.debug("Transaction started with START TRANSACTION")
                return
            except Exception as e:
                logging.debug(f"START TRANSACTION failed: {e}, trying alternative methods")
                
                try:
                    # Second attempt: disable autocommit
                    self._cursor.execute("SET autocommit=0")
                    logging.debug("Transaction started with SET autocommit=0")
                    return
                except Exception as inner_e:
                    try:
                        # Third attempt: use connection-level autocommit setting
                        # This is specific to PyMySQL's implementation
                        setattr(self._connection, 'autocommit', False)
                        logging.debug("Transaction started with connection.autocommit=False")
                        return
                    except Exception as conn_e:
                        # If all methods fail, log warning but continue
                        # PyMySQL's default behavior should be autocommit=False
                        logging.warning(f"Could not explicitly start transaction, using default behavior: {e}, {inner_e}, {conn_e}")

    def commit(self) -> None:
        """
        Commit the current transaction with enhanced error handling.
        """
        with self._lock:  # Ensure thread safety
            if not self._connection:
                logging.warning("Commit called but no active connection")
                return
                
            try:
                # Commit at the connection level
                self._connection.commit()
                logging.debug("Transaction committed successfully")
            except Exception as e:
                logging.error(f"Failed to commit transaction: {e}")
                # Re-establish connection on serious errors
                try:
                    self.disconnect()
                    self.connect()
                except Exception as reconnect_e:
                    logging.error(f"Failed to reconnect after commit error: {reconnect_e}")
            finally:
                # Clear transaction state
                self._in_transaction = False
                
                # Reset autocommit if needed
                try:
                    self._cursor.execute("SET autocommit=1")
                except Exception:
                    # Ignore errors, as we'll get a fresh connection next time
                    pass

    def rollback(self) -> None:
        """
        Rollback the current transaction with improved reliability.
        
        This implementation addresses issues with DBUtils pooled connections
        by using multiple fallback approaches and explicit connection reset.
        """
        with self._lock:  # Ensure thread safety
            if not self._connection:
                logging.warning("Rollback called but no active connection")
                return
                
            try:
                # First attempt: standard rollback
                self._connection.rollback()
                logging.debug("Transaction rolled back successfully")
            except Exception as e:
                logging.warning(f"Standard rollback failed: {e}, trying alternative approaches")
                
                try:
                    # Second attempt: explicit SQL ROLLBACK
                    self._cursor.execute("ROLLBACK")
                    logging.debug("Transaction rolled back with explicit ROLLBACK statement")
                except Exception as sql_e:
                    logging.error(f"SQL ROLLBACK also failed: {sql_e}")
            finally:
                # Always release and re-acquire connection from pool to ensure clean state
                # This is critical for pooled connections where transaction state may persist
                old_connection = self._connection
                self.disconnect()
                self.connect()
                logging.debug("Connection reset after rollback attempt")
                
                # Clear transaction state
                self._in_transaction = False

    def _ensure_schema_exists(self):
        """Ensure the necessary tables for LSH and vector data exist."""
        if not self._connection:
            self.connect()
            
        # Create LSH signatures table if it doesn't exist
        self._cursor.execute("""
        CREATE TABLE IF NOT EXISTS `lsh_signatures` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `signature_hash` VARCHAR(255) NOT NULL,
            `bucket_id` INT NOT NULL,
            `data_reference` VARCHAR(255) NOT NULL,
            `source_id` VARCHAR(255) NOT NULL,
            INDEX `idx_signature_hash` (`signature_hash`),
            INDEX `idx_bucket_id` (`bucket_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        # Create vector metadata table if it doesn't exist
        self._cursor.execute("""
        CREATE TABLE IF NOT EXISTS `vector_metadata` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `chroma_id` VARCHAR(255) UNIQUE,
            `source_id` VARCHAR(255) NOT NULL,
            `text_chunk_id` VARCHAR(255),
            `metadata` JSON,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_source_id` (`source_id`),
            INDEX `idx_text_chunk_id` (`text_chunk_id`),
            INDEX `idx_chroma_id` (`chroma_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        self._connection.commit()

    def _init_vector_db(self) -> None:
        """Initialize ChromaDB connection for vector operations."""
        if not self.vector_db and self.db_directory_path:
            try:
                vector_db_path = self.db_directory_path / "context_vector_db"
                vector_db_path.mkdir(parents=True, exist_ok=True)
                self.vector_db = Chroma(persist_directory=str(vector_db_path), embedding_function=EMBEDDING_FUNCTION)
            except Exception as e:
                raise Exception(f"Failed to initialize vector database: {e}")

    def store_vector(self, vector: List[float], metadata: Dict[str, Any], source_id: str) -> str:
        """
        Store a vector with its metadata in the vector database with MySQL integration.
        
        Args:
            vector (List[float]): The vector embedding to store
            metadata (Dict[str, Any]): Associated metadata
            source_id (str): Identifier for the source document/data
            
        Returns:
            str: Identifier for the stored vector (Chroma ID)
        """
        # Ensure schema exists
        self._ensure_schema_exists()
        
        # Initialize vector DB if not already done
        self._init_vector_db()
        
        # Generate a unique ID for the vector
        chroma_id = str(uuid.uuid4())
        
        # Prepare metadata for MySQL storage
        mysql_metadata = metadata.copy()
        text_chunk_id = mysql_metadata.pop("text_chunk_id", None)
        
        # Store in ChromaDB first
        metadata_for_chroma = metadata.copy()
        metadata_for_chroma["source_id"] = source_id
        metadata_for_chroma["chroma_id"] = chroma_id
        
        # Use the appropriate method for ChromaDB based on the langchain-chroma version
        try:
            # New ChromaDB API method
            from langchain_core.documents import Document
            document = Document(page_content="", metadata=metadata_for_chroma)
            self.vector_db.add_documents(
                documents=[document],
                embeddings=[vector],
                ids=[chroma_id]
            )
        except (ImportError, AttributeError, TypeError):
            try:
                # Alternative approach for newer ChromaDB versions
                self.vector_db._collection.add(
                    embeddings=[vector],
                    metadatas=[metadata_for_chroma],
                    ids=[chroma_id]
                )
            except (AttributeError, TypeError):
                # Fallback for direct ChromaDB client usage
                import chromadb
                client = chromadb.PersistentClient(path=str(self.db_directory_path / "context_vector_db"))
                collection = client.get_or_create_collection("default_collection")
                collection.add(
                    embeddings=[vector],
                    metadatas=[metadata_for_chroma],
                    ids=[chroma_id]
                )
        
        # Store metadata in MySQL
        self._cursor.execute(
            """
            INSERT INTO vector_metadata 
            (chroma_id, source_id, text_chunk_id, metadata) 
            VALUES (%s, %s, %s, %s)
            """,
            (chroma_id, source_id, text_chunk_id, json.dumps(mysql_metadata))
        )
        self._connection.commit()
        
        return chroma_id

    def query_vector_db(self, query_vector: List[float], top_k: int, filter_criteria: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Query the vector database for similar vectors with MySQL integration.
        
        Args:
            query_vector (List[float]): Vector to search for
            top_k (int): Number of results to return
            filter_criteria (Dict[str, Any], optional): Criteria to filter results
            
        Returns:
            List[Dict[str, Any]]: List of matching results with their metadata
        """
        # Initialize vector DB if not already done
        self._init_vector_db()
        
        # Process filter criteria if provided
        chroma_ids = None
        if filter_criteria:
            if not self._connection:
                self.connect()
                
            # Build WHERE clause for MySQL query
            where_clauses = []
            params = []
            
            for key, value in filter_criteria.items():
                if key == "source_id":
                    where_clauses.append("source_id = %s")
                    params.append(value)
                elif key == "text_chunk_id":
                    where_clauses.append("text_chunk_id = %s")
                    params.append(value)
                else:
                    # Handle nested JSON fields in metadata
                    where_clauses.append(f"JSON_CONTAINS(metadata, %s, '$.{key}')")
                    params.append(json.dumps(value))
            
            if where_clauses:
                query = f"""
                SELECT chroma_id FROM vector_metadata 
                WHERE {' AND '.join(where_clauses)}
                """
                
                self._cursor.execute(query, params)
                results = self._cursor.fetchall()
                chroma_ids = [row["chroma_id"] for row in results]
                
                # If no matching IDs found with filters, return empty list
                if not chroma_ids:
                    return []
        
        # Query ChromaDB - handling different versions and APIs
        where_filter = None
        if chroma_ids:
            where_filter = {"chroma_id": {"$in": chroma_ids}}
        
        formatted_results = []
        try:
            # Try the newer ChromaDB API method
            results = self.vector_db.similarity_search_with_relevance_scores(
                query=str(query_vector),  # Convert to string representation for compatibility
                k=top_k,
                filter=where_filter
            )
            
            # Process similarity_search results format
            # Suppress the warning from ChromaDB about relevance scores not being between 0-1
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                for document, score in results:
                    # Normalize score to ensure it's between 0 and 1
                    normalized_score = self._normalize_relevance_score(score)
                    formatted_results.append({
                        'id': document.metadata.get('chroma_id', ''),
                        'metadata': document.metadata,
                        'score': normalized_score,
                        'content': document.page_content
                    })
                
        except (AttributeError, TypeError):
            try:
                # Try alternative approach with _collection direct access
                results = self.vector_db._collection.query(
                    query_embeddings=[query_vector],
                    n_results=top_k,
                    where=where_filter
                )
                
                # Process and return results from _collection.query format
                if results and len(results['metadatas']) > 0:
                    for i in range(len(results['metadatas'][0])):
                        raw_score = results['distances'][0][i] if 'distances' in results else None
                        normalized_score = self._normalize_relevance_score(raw_score)
                        formatted_results.append({
                            'id': results['ids'][0][i],
                            'metadata': results['metadatas'][0][i],
                            'score': normalized_score
                        })
            except (AttributeError, TypeError):
                # Last resort: Use direct ChromaDB client
                try:
                    import chromadb
                    client = chromadb.PersistentClient(path=str(self.db_directory_path / "context_vector_db"))
                    collection = client.get_or_create_collection("default_collection")
                    
                    results = collection.query(
                        query_embeddings=[query_vector],
                        n_results=top_k,
                        where=where_filter
                    )
                    
                    # Process results from direct ChromaDB client
                    if 'metadatas' in results and results['metadatas']:
                        for i in range(len(results['metadatas'][0])):
                            raw_score = results['distances'][0][i] if 'distances' in results else None
                            normalized_score = self._normalize_relevance_score(raw_score)
                            formatted_results.append({
                                'id': results['ids'][0][i],
                                'metadata': results['metadatas'][0][i],
                                'score': normalized_score
                            })
                except Exception as e:
                    logging.error(f"All ChromaDB query methods failed: {e}")
                
        return formatted_results
        
    def _normalize_relevance_score(self, score: Optional[float]) -> Optional[float]:
        """
        Normalize ChromaDB relevance scores to ensure they're between 0 and 1.
        
        Different versions of ChromaDB may return scores in different ranges:
        - Some return cosine similarity (0 to 1, higher is better)
        - Others return distance (-1 to 1, lower is better)
        - Some return negative scores
        
        This function normalizes scores to a 0-1 range where higher is better.
        
        Args:
            score (Optional[float]): The raw score from ChromaDB
            
        Returns:
            Optional[float]: Normalized score between 0 and 1
        """
        if score is None:
            return None
            
        try:
            # Handle negative scores (convert distance to similarity)
            if score < 0:
                # For scores that are negative (likely L2 distance or negative cosine)
                # Convert to a 0-1 range where 1 is perfect match
                # We use exponential transformation to handle various distance metrics
                normalized = max(0.0, min(1.0, np.exp(score)))
                return float(normalized)
                
            # Check if score is already between 0-1
            elif 0 <= score <= 1:
                return float(score)
                
            # Handle scores > 1 (could be unusual distance metrics)
            elif score > 1:
                # Map to 0-1 range using a sigmoid-like function
                normalized = 1.0 / (1.0 + np.exp(-score + 5))
                return float(normalized)
                
            # Fallback - shouldn't reach here with proper input
            else:
                logging.warning(f"Unexpected score value: {score}, returning as-is")
                return float(score)
                
        except Exception as e:
            logging.warning(f"Error normalizing score {score}: {e}")
            # Return original score if normalization fails
            return score if isinstance(score, float) else None

    def store_lsh_signature(self, signature_hash: str, bucket_id: int, data_ref: str, source_id: str) -> None:
        """
        Store an LSH signature in the MySQL database.
        
        Args:
            signature_hash (str): The hash value of the signature
            bucket_id (int): The LSH bucket identifier
            data_ref (str): Reference to the original data
            source_id (str): Identifier for the source document/data
        """
        # Ensure schema exists
        self._ensure_schema_exists()
        
        if not self._connection:
            self.connect()
            
        # Store the signature
        self._cursor.execute(
            """
            INSERT INTO lsh_signatures 
            (signature_hash, bucket_id, data_reference, source_id) 
            VALUES (%s, %s, %s, %s)
            """,
            (signature_hash, bucket_id, data_ref, source_id)
        )
        self._connection.commit()

    def query_lsh(self, query_signature: List[str], top_n: int) -> List[Dict[str, Any]]:
        """
        Query the LSH database for similar items using MySQL.
        
        Args:
            query_signature (List[str]): The signature hashes to query
            top_n (int): Number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of matching results
        """
        if not self._connection:
            self.connect()
            
        # Convert list of signature hashes to placeholders for SQL query
        placeholders = ", ".join(["%s"] * len(query_signature))
        
        # Query to find matches based on signature hashes
        query = f"""
        SELECT data_reference, COUNT(*) as matches 
        FROM lsh_signatures 
        WHERE signature_hash IN ({placeholders}) 
        GROUP BY data_reference 
        ORDER BY matches DESC 
        LIMIT %s
        """
        
        # Execute with parameters
        params = query_signature + [top_n]
        self._cursor.execute(query, params)
        results = self._cursor.fetchall()
        
        # Format results
        return [
            {"data_ref": row["data_reference"], "matches": row["matches"]}
            for row in results
        ]

    def clear_lsh_data(self) -> None:
        """Clear all LSH data from the MySQL database."""
        if not self._connection:
            self.connect()
            
        self._cursor.execute("TRUNCATE TABLE lsh_signatures")
        self._connection.commit()

    def clear_vector_data(self) -> None:
        """Clear all vector data from MySQL and ChromaDB."""
        if not self._connection:
            self.connect()
            
        # Clear MySQL vector metadata
        self._cursor.execute("TRUNCATE TABLE vector_metadata")
        self._connection.commit()
        
        # Clear ChromaDB if initialized
        if self.vector_db:
            try:
                # Get all vector IDs from MySQL first
                self._cursor.execute("SELECT chroma_id FROM vector_metadata")
                results = self._cursor.fetchall()
                chroma_ids = [row["chroma_id"] for row in results]
                
                # Delete by IDs if we have any
                if chroma_ids:
                    self.vector_db.delete(ids=chroma_ids)
                
            except Exception as e:
                logging.warning(f"Could not delete vectors from ChromaDB: {e}")
                # Alternative approaches for different ChromaDB versions
                try:
                    # Try direct collection access
                    self.vector_db._collection.delete(where_document={"source_id": {"$exists": True}})
                except Exception:
                    try:
                        # Recreate the vector DB from scratch
                        if self.db_directory_path:
                            vector_db_path = self.db_directory_path / "context_vector_db"
                            if vector_db_path.exists():
                                import shutil
                                shutil.rmtree(str(vector_db_path))
                            self._init_vector_db()
                    except Exception as rec_e:
                        logging.error(f"Failed to recreate vector DB: {rec_e}")
            
            finally:
                # Reset the vector DB reference
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
        if not self.db_directory_path:
            raise ValueError("Database directory path not set")
            
        schema_with_descriptions = load_tables_description(self.db_directory_path, use_value_description)
        database_schema_generator = DatabaseSchemaGenerator(
            tentative_schema=DatabaseSchema.from_schema_dict(tentative_schema if tentative_schema else self.get_db_schema()),
            schema_with_examples=DatabaseSchema.from_schema_dict_with_examples(schema_with_examples),
            schema_with_descriptions=DatabaseSchema.from_schema_dict_with_descriptions(schema_with_descriptions),
            db_id=self.db_id,
            db_path=None,  # not used for MySQL
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
            db_path=None,  # not used for MySQL
        )
        schema_string = schema_generator.generate_schema_string(include_value_description=include_value_description)
        return schema_string