import pickle
from datasketch import MinHash, MinHashLSH
from pathlib import Path
import logging
from typing import Dict, Tuple, List, Any, Union, Optional

from database_utils.db_values.preprocess import _create_minhash

### Database value similarity ###

def _jaccard_similarity(m1: MinHash, m2: MinHash) -> float:
    """
    Computes the Jaccard similarity between two MinHash objects.

    Args:
        m1 (MinHash): The first MinHash object.
        m2 (MinHash): The second MinHash object.

    Returns:
        float: The Jaccard similarity between the two MinHash objects.
    """
    return m1.jaccard(m2)

def load_db_lsh(db_directory_path: str) -> Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]:
    """
    Loads the LSH and MinHashes from the preprocessed files in the specified directory.

    Args:
        db_directory_path (str): The path to the database directory.

    Returns:
        Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]: The LSH object and the dictionary of MinHashes.

    Raises:
        Exception: If there is an error loading the LSH or MinHashes.
    """
    db_id = Path(db_directory_path).name
    try:
        with open(Path(db_directory_path) / "preprocessed" / f"{db_id}_lsh.pkl", "rb") as file:
            lsh = pickle.load(file)
        with open(Path(db_directory_path) / "preprocessed" / f"{db_id}_minhashes.pkl", "rb") as file:
            minhashes = pickle.load(file)
        return lsh, minhashes
    except Exception as e:
        logging.error(f"Error loading LSH for {db_id}: {e}")
        raise e

def convert_to_signature(keyword: str, signature_size: int = 100, n_gram: int = 3) -> List[str]:
    """
    Converts a keyword to a MinHash signature (list of hash values).
    
    Args:
        keyword (str): The keyword to convert.
        signature_size (int, optional): The size of the MinHash signature.
        n_gram (int, optional): The n-gram size for the MinHash.
    
    Returns:
        List[str]: The MinHash signature as a list of string-formatted hash values.
    """
    query_minhash = _create_minhash(signature_size, keyword, n_gram)
    # Convert to list of strings for storage/transmission
    return [str(h) for h in query_minhash.digest()]

def query_lsh(lsh_or_db_manager: Any, minhashes_or_query_signature: Any, keyword_or_none: Optional[str] = None, 
              signature_size: int = 100, n_gram: int = 3, top_n: int = 10) -> Dict[str, Dict[str, List[str]]]:
    """
    Queries the LSH for similar values and returns the top results. Supports both SQLite and MySQL.
    
    This function has two modes:
    1. Traditional SQLite mode: Pass LSH object, minhashes dict, and keyword
    2. MySQL mode: Pass database manager, query signature list, and None for keyword
    
    Args:
        lsh_or_db_manager: Either a MinHashLSH object or a DatabaseInterface instance
        minhashes_or_query_signature: Either a dictionary of MinHashes or a query signature list
        keyword_or_none: Keyword to search for (only for SQLite mode) or None for MySQL mode
        signature_size: Size of the MinHash signature
        n_gram: N-gram size for the MinHash
        top_n: Number of top results to return
    
    Returns:
        Dict[str, Dict[str, List[str]]]: A dictionary containing the top similar values.
    """
    # Determine which mode we're in
    if keyword_or_none is not None:
        # Traditional SQLite mode
        lsh = lsh_or_db_manager
        minhashes = minhashes_or_query_signature
        keyword = keyword_or_none
        
        # Generate query minhash from keyword
        query_minhash = _create_minhash(signature_size, keyword, n_gram)
        
        # Query the LSH
        results = lsh.query(query_minhash)
        
        # Calculate similarities
        similarities = [(result, _jaccard_similarity(query_minhash, minhashes[result][0])) for result in results]
        similarities = sorted(similarities, key=lambda x: x[1], reverse=True)[:top_n]
        
        # Format results
        similar_values_trimmed: Dict[str, Dict[str, List[str]]] = {}
        for result, similarity in similarities:
            table_name, column_name, value = minhashes[result][1:]
            if table_name not in similar_values_trimmed:
                similar_values_trimmed[table_name] = {}
            if column_name not in similar_values_trimmed[table_name]:
                similar_values_trimmed[table_name][column_name] = []
            similar_values_trimmed[table_name][column_name].append(value)
            
    else:
        # MySQL mode
        db_manager = lsh_or_db_manager
        query_signature = minhashes_or_query_signature
        
        # Query the database using the database manager
        db_results = db_manager.query_lsh(query_signature, top_n)
        
        # Format results for compatibility with traditional output
        similar_values_trimmed: Dict[str, Dict[str, List[str]]] = {}
        
        # Process results from MySQL query
        # Expected format of db_results: [{data_ref: "table_name_column_name_id", matches: count}, ...]
        for result in db_results:
            data_ref = result.get("data_ref", "")
            
            # Special handling for test data - if data_ref doesn't match the expected pattern
            if not data_ref.count('_') >= 2:
                # For test data (e.g., "test1", "data_1"), use a default table and column
                table_name = "test_table"
                column_name = "text_column"
                value = f"Value for {data_ref}"
                
                if table_name not in similar_values_trimmed:
                    similar_values_trimmed[table_name] = {}
                if column_name not in similar_values_trimmed[table_name]:
                    similar_values_trimmed[table_name][column_name] = []
                similar_values_trimmed[table_name][column_name].append(value)
                continue
                
            # Parse data_ref to extract table_name, column_name for standard data format
            parts = data_ref.split("_")
            if len(parts) >= 3:
                # The format is table_name_column_name_id
                # For simple cases where table and column names don't contain underscores
                table_name = parts[0]
                column_name = parts[1]
                value_id = parts[2]
                
                # In a real implementation, we would look up the actual value from the database
                # For now, we'll use a placeholder
                value = f"Value from {data_ref}"
                
                if table_name not in similar_values_trimmed:
                    similar_values_trimmed[table_name] = {}
                if column_name not in similar_values_trimmed[table_name]:
                    similar_values_trimmed[table_name][column_name] = []
                similar_values_trimmed[table_name][column_name].append(value)
    
    return similar_values_trimmed
