import os
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC, abstractmethod


class DatabaseInterface(ABC):
    """
    Abstract interface for database operations in CHESS+.
    Implementations include both core database operations and specialized
    functionality for LSH/MinHash and vector storage/search.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close the database connection."""
        pass

    @abstractmethod
    def execute_sql(self, query: str, params: tuple = None) -> Dict[str, Any]:
        """
        Execute a SQL query and return the results.
        
        Args:
            query (str): SQL query to execute
            params (tuple, optional): Parameters for the SQL query
            
        Returns:
            Dict[str, Any]: Dictionary containing execution results
        """
        pass

    @abstractmethod
    def get_db_schema(self) -> Dict[str, List[str]]:
        """
        Get the database schema including all tables and their columns.
        
        Returns:
            Dict[str, List[str]]: Dictionary with table names as keys and lists of column names as values
        """
        pass

    @abstractmethod
    def begin_transaction(self) -> None:
        """Begin a database transaction."""
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the current transaction."""
        pass

    @abstractmethod
    def store_vector(self, vector: List[float], metadata: Dict[str, Any], source_id: str) -> str:
        """
        Store a vector with its metadata in the vector database.
        
        Args:
            vector (List[float]): The vector embedding to store
            metadata (Dict[str, Any]): Associated metadata
            source_id (str): Identifier for the source document/data
            
        Returns:
            str: Identifier for the stored vector
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def store_lsh_signature(self, signature_hash: str, bucket_id: int, data_ref: str, source_id: str) -> None:
        """
        Store an LSH signature in the database.
        
        Args:
            signature_hash (str): The hash value of the signature
            bucket_id (int): The LSH bucket identifier
            data_ref (str): Reference to the original data
            source_id (str): Identifier for the source document/data
        """
        pass

    @abstractmethod
    def query_lsh(self, query_signature: List[str], top_n: int) -> List[Dict[str, Any]]:
        """
        Query the LSH database for similar items.
        
        Args:
            query_signature (List[str]): The signature to query
            top_n (int): Number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of matching results
        """
        pass

    @abstractmethod
    def clear_lsh_data(self) -> None:
        """Clear all LSH data from the database."""
        pass

    @abstractmethod
    def clear_vector_data(self) -> None:
        """Clear all vector data from the database."""
        pass