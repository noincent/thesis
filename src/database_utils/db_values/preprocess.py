import pickle
from datasketch import MinHash, MinHashLSH
from pathlib import Path
from tqdm import tqdm
import logging
from typing import Dict, List, Any, Tuple

from database_utils.execution import execute_sql

def _get_unique_values(db_interface) -> Dict[str, Dict[str, List[str]]]:
    """
    Retrieves unique text values from the database excluding primary keys.

    Args:
        db_interface: The database interface (either SQLite path or DatabaseInterface).

    Returns:
        Dict[str, Dict[str, List[str]]]: A dictionary containing unique values for each table and column.
    """
    # Handle different types of db_interface
    if isinstance(db_interface, str):
        # SQLite path provided - use traditional execution
        db_path = db_interface
        is_sqlite = True
    else:
        # Database interface provided (likely MySQLDatabaseManager)
        db_manager = db_interface
        is_sqlite = False
    
    # Get table names based on database type
    if is_sqlite:
        result = execute_sql(db_path, "SELECT name FROM sqlite_master WHERE type='table';", fetch="all")
        table_names = [table[0] for table in result]
    else:
        schema = db_manager.get_db_schema()
        table_names = list(schema.keys())
    
    # Get primary keys
    primary_keys = []
    for table_name in table_names:
        if is_sqlite:
            columns = execute_sql(db_path, f"PRAGMA table_info('{table_name}')", fetch="all")
            for column in columns:
                if column[5] > 0:  # Check if it's a primary key
                    column_name = column[1]
                    if column_name.lower() not in [c.lower() for c in primary_keys]:
                        primary_keys.append(column_name)
        else:
            # For MySQL, query information_schema
            query = f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = '{db_manager.db_name}'
                AND TABLE_NAME = '{table_name}'
                AND CONSTRAINT_NAME = 'PRIMARY'
            """
            result = db_manager.execute_sql(query)
            if result["success"] and result["results"]:
                for row in result["results"]:
                    column_name = row["COLUMN_NAME"]
                    if column_name.lower() not in [c.lower() for c in primary_keys]:
                        primary_keys.append(column_name)
    
    # Process tables and columns
    unique_values: Dict[str, Dict[str, List[str]]] = {}
    for table_name in table_names:
        if table_name == "sqlite_sequence" or table_name in ["lsh_signatures", "vector_metadata"]:
            continue
            
        logging.info(f"Processing {table_name}")
        
        # Get text columns
        if is_sqlite:
            columns_result = execute_sql(db_path, f"PRAGMA table_info('{table_name}')", fetch="all")
            columns = [col[1] for col in columns_result if ("TEXT" in col[2] and col[1].lower() not in [c.lower() for c in primary_keys])]
        else:
            # For MySQL, query information_schema
            query = f"""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{db_manager.db_name}'
                AND TABLE_NAME = '{table_name}'
            """
            result = db_manager.execute_sql(query)
            columns = []
            if result["success"] and result["results"]:
                for row in result["results"]:
                    column_name = row["COLUMN_NAME"]
                    data_type = row["DATA_TYPE"]
                    if (data_type in ["varchar", "text", "char", "longtext"] and 
                        column_name.lower() not in [c.lower() for c in primary_keys]):
                        columns.append(column_name)
        
        table_values: Dict[str, List[str]] = {}
        
        for column in columns:
            if any(keyword in column.lower() for keyword in ["_id", " id", "url", "email", "web", "time", "phone", "date", "address"]) or column.endswith("Id"):
                continue

            try:
                # Query to count and measure distinct values
                query = f"""
                    SELECT SUM(LENGTH(unique_values)), COUNT(unique_values)
                    FROM (
                        SELECT DISTINCT `{column}` AS unique_values
                        FROM `{table_name}`
                        WHERE `{column}` IS NOT NULL
                    ) AS subquery
                """
                
                if is_sqlite:
                    result = execute_sql(db_path, query, fetch="one", timeout=480)
                else:
                    result_dict = db_manager.execute_sql(query)
                    if result_dict["success"] and result_dict["results"]:
                        result = (
                            list(result_dict["results"][0].values())[0],
                            list(result_dict["results"][0].values())[1]
                        )
                    else:
                        result = 0, 0
            except:
                result = 0, 0

            sum_of_lengths, count_distinct = result
            if sum_of_lengths is None or count_distinct == 0:
                continue

            average_length = sum_of_lengths / count_distinct
            logging.info(f"Column: {column}, sum_of_lengths: {sum_of_lengths}, count_distinct: {count_distinct}, average_length: {average_length}")
            
            if ("name" in column.lower() and sum_of_lengths < 5000000) or (sum_of_lengths < 2000000 and average_length < 25) or count_distinct < 100:
                logging.info(f"Fetching distinct values for {column}")
                try:
                    query = f"SELECT DISTINCT `{column}` FROM `{table_name}` WHERE `{column}` IS NOT NULL"
                    
                    if is_sqlite:
                        result = execute_sql(db_path, query, fetch="all", timeout=480)
                        values = [str(value[0]) for value in result]
                    else:
                        result_dict = db_manager.execute_sql(query)
                        if result_dict["success"] and result_dict["results"]:
                            values = [str(row[column]) for row in result_dict["results"]]
                        else:
                            values = []
                except:
                    values = []
                logging.info(f"Number of different values: {len(values)}")
                table_values[column] = values
        
        unique_values[table_name] = table_values

    return unique_values

def _create_minhash(signature_size: int, string: str, n_gram: int) -> MinHash:
    """
    Creates a MinHash object for a given string.

    Args:
        signature_size (int): The size of the MinHash signature.
        string (str): The input string to create the MinHash for.
        n_gram (int): The n-gram size for the MinHash.

    Returns:
        MinHash: The MinHash object for the input string.
    """
    m = MinHash(num_perm=signature_size)
    for d in [string[i:i + n_gram] for i in range(len(string) - n_gram + 1)]:
        m.update(d.encode('utf8'))
    return m

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

def skip_column(column_name: str, column_values: List[str]) -> bool:
    """
    Determines whether to skip processing a column based on its values.

    Args:
        column_name (str): The name of the column.
        column_values (List[str]): The list of values in the column.

    Returns:
        bool: True if the column should be skipped, False otherwise.
    """
    if "name" in column_name.lower():
        return False
    sum_of_lengths = sum(len(value) for value in column_values)
    average_length = sum_of_lengths / len(column_values)
    return (sum_of_lengths > 50000) and (average_length > 20)

def make_lsh(unique_values: Dict[str, Dict[str, List[str]]] = None, signature_size: int = 128, n_gram: int = 3, threshold: float = 0.01, 
          verbose: bool = True, db_manager = None, source_id: str = None,
          table_values: List[str] = None, table_value_ids: List[str] = None, source_id_list: List[str] = None,
          num_perm: int = None, database_manager = None) -> Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]:
    """
    Creates a MinHash LSH from unique values or provided table values.
    This function supports two calling styles for backward compatibility:
    
    1. Original style: with unique_values dictionary containing tables/columns/values
    2. Test style: with flat lists of values, ids, and source_ids

    Args:
        unique_values (Dict[str, Dict[str, List[str]]], optional): The dictionary of unique values.
        signature_size (int, optional): The size of the MinHash signature.
        n_gram (int, optional): The n-gram size for the MinHash.
        threshold (float, optional): The threshold for the MinHash LSH.
        verbose (bool, optional): Whether to display progress information.
        db_manager (DatabaseInterface, optional): Database manager for MySQL storage.
        source_id (str, optional): Database ID for the source.
        table_values (List[str], optional): Alternative input - flat list of text values.
        table_value_ids (List[str], optional): Alternative input - IDs for each value.
        source_id_list (List[str], optional): Alternative input - source ID for each value.
        num_perm (int, optional): Alternative param name for signature_size.

    Returns:
        Tuple[MinHashLSH, Dict[str, Tuple[MinHash, str, str, str]]]: The MinHash LSH object and the dictionary of MinHashes.
    """
    # Handle alternative parameter name for db_manager
    if database_manager is not None and db_manager is None:
        db_manager = database_manager
        
    use_mysql = db_manager is not None
    
    # Handle alternative parameter name
    if num_perm is not None:
        signature_size = num_perm
    
    # Create LSH structure for traditional storage even if using MySQL
    # This ensures compatibility with existing code
    lsh = MinHashLSH(threshold=threshold, num_perm=signature_size)
    minhashes: Dict[str, Tuple[MinHash, str, str, str]] = {}
    
    try:
        # Determine which mode we're using based on parameters
        using_flat_lists = table_values is not None and table_value_ids is not None
        
        if using_flat_lists:
            # Test-style flat lists mode
            if verbose:
                print(f"Using flat list mode with {len(table_values)} values")
            
            # For MySQL batch operations
            if use_mysql:
                batch_size = 100
                current_batch = []
            
            # Process each value in the flat lists
            for i, value in enumerate(table_values):
                # Get appropriate IDs
                value_id = table_value_ids[i] if i < len(table_value_ids) else f"value_{i}"
                item_source_id = source_id_list[i] if source_id_list and i < len(source_id_list) else source_id or "unknown"
                
                # Create minhash
                minhash = _create_minhash(signature_size, value, n_gram)
                minhash_key = value_id
                
                # Store in memory dictionary
                minhashes[minhash_key] = (minhash, "test_table", "text_column", value)
                lsh.insert(minhash_key, minhash)
                
                # Store in MySQL if requested
                if use_mysql:
                    # Get signature hashes
                    signature = minhash.digest()
                    
                    # For each hash in the signature, create a batch entry
                    for bucket_id, sig_hash in enumerate(signature):
                        # Add to current batch
                        current_batch.append((
                            str(sig_hash),  # signature_hash
                            bucket_id,      # bucket_id
                            minhash_key,    # data_reference
                            item_source_id  # source_id
                        ))
                        
                        # Process batch if it's full
                        if len(current_batch) >= batch_size:
                            # Store the batch in MySQL
                            for entry in current_batch:
                                db_manager.store_lsh_signature(
                                    signature_hash=entry[0],
                                    bucket_id=entry[1],
                                    data_ref=entry[2],
                                    source_id=entry[3]
                                )
                            # Clear the batch
                            current_batch = []
            
            # Process any remaining batch items for MySQL
            if use_mysql and current_batch:
                for entry in current_batch:
                    db_manager.store_lsh_signature(
                        signature_hash=entry[0],
                        bucket_id=entry[1],
                        data_ref=entry[2],
                        source_id=entry[3]
                    )
                
        elif unique_values:
            # Original dictionary-style mode
            total_unique_values = sum(len(column_values) for table_values in unique_values.values() for column_values in table_values.values())
            logging.info(f"Total unique values: {total_unique_values}")
            
            progress_bar = tqdm(total=total_unique_values, desc="Creating LSH") if verbose else None
            
            # For MySQL batch operations
            if use_mysql:
                # For larger datasets, process in batches
                batch_size = 100
                current_batch = []
            
            for table_name, table_values in unique_values.items():
                for column_name, column_values in table_values.items():
                    if column_name.lower() == "doctype":
                        print("="*20)
                        print("Doctype found")
                        print("="*20)
                    logging.info(f"Processing {table_name} - {column_name} - {len(column_values)}")
                    
                    for id, value in enumerate(column_values):
                        # Create minhash signature
                        minhash = _create_minhash(signature_size, value, n_gram)
                        minhash_key = f"{table_name}_{column_name}_{id}"
                        
                        # Store in memory dictionary for traditional LSH
                        minhashes[minhash_key] = (minhash, table_name, column_name, value)
                        lsh.insert(minhash_key, minhash)
                        
                        # Store in MySQL if requested
                        if use_mysql:
                            # Get signature hashes
                            signature = minhash.digest()
                            
                            # For each hash in the signature, create a batch entry
                            for bucket_id, sig_hash in enumerate(signature):
                                # Add to current batch
                                current_batch.append((
                                    str(sig_hash),  # signature_hash
                                    bucket_id,      # bucket_id
                                    minhash_key,    # data_reference
                                    source_id       # source_id
                                ))
                                
                                # Process batch if it's full
                                if len(current_batch) >= batch_size:
                                    # Store the batch in MySQL
                                    for entry in current_batch:
                                        db_manager.store_lsh_signature(
                                            signature_hash=entry[0],
                                            bucket_id=entry[1],
                                            data_ref=entry[2],
                                            source_id=entry[3]
                                        )
                                    # Clear the batch
                                    current_batch = []
                        
                        if verbose:
                            progress_bar.update(1)
            
            # Process any remaining batch items for MySQL
            if use_mysql and current_batch:
                for entry in current_batch:
                    db_manager.store_lsh_signature(
                        signature_hash=entry[0],
                        bucket_id=entry[1],
                        data_ref=entry[2],
                        source_id=entry[3]
                    )
            
            if progress_bar:
                progress_bar.close()
        else:
            raise ValueError("Either unique_values or table_values must be provided")
    except Exception as e:
        logging.error(f"Error creating LSH: {e}")
        raise
    
    return lsh, minhashes

def make_db_lsh(db_directory_path, signature_size: int = 20, n_gram: int = 3, 
               threshold: float = 0.01, verbose: bool = True, db_manager = None) -> None:
    """
    Creates a MinHash LSH for the database and saves the results.

    Args:
        db_directory_path (str or Path): The path to the database directory.
        signature_size (int, optional): Size of the MinHash signature.
        n_gram (int, optional): N-gram size for MinHash.
        threshold (float, optional): LSH threshold.
        verbose (bool, optional): Whether to display progress information.
        db_manager (DatabaseInterface, optional): Database manager for MySQL storage.
    """
    if isinstance(db_directory_path, str):
        db_directory_path = Path(db_directory_path)
        
    db_id = db_directory_path.name
    preprocessed_path = db_directory_path / "preprocessed"
    preprocessed_path.mkdir(exist_ok=True)
    
    # Get unique values from database
    if db_manager is None:
        # SQLite path
        sqlite_path = str(db_directory_path / f"{db_id}.sqlite")
        unique_values = _get_unique_values(sqlite_path)
    else:
        # MySQL database manager
        unique_values = _get_unique_values(db_manager)
    
    logging.info("Unique values obtained")
    
    # Save unique values to pickle (for reference)
    with open(preprocessed_path / f"{db_id}_unique_values.pkl", "wb") as file:
        pickle.dump(unique_values, file)
    logging.info("Saved unique values")
    
    # Generate LSH signatures
    lsh, minhashes = make_lsh(
        unique_values, 
        signature_size=signature_size, 
        n_gram=n_gram, 
        threshold=threshold, 
        verbose=verbose,
        db_manager=db_manager,
        source_id=db_id
    )
    
    # Save to pickle (for reference or SQLite compatibility)
    with open(preprocessed_path / f"{db_id}_lsh.pkl", "wb") as file:
        pickle.dump(lsh, file)
    with open(preprocessed_path / f"{db_id}_minhashes.pkl", "wb") as file:
        pickle.dump(minhashes, file)
    
    logging.info("LSH data generation complete")
