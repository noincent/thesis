Refined CHESS+ MySQL Support Migration Plan (Full Migration - Agentic Workflow - File-Specific)

Goal: Fully migrate CHESS+ to use MySQL as the primary database, refactoring LSH, MinHash, and Vector Database functionality to operate on MySQL data (using ChromaDB for vector search). Ensure feature parity. Structure for iterative implementation and testing using the existing file structure.

Key Changes from Original Code:

Replace Singleton DatabaseManager with Factory/DI.

LSH/Vector data generation reads from MySQL, stores results in MySQL (LSH) or MySQL+Chroma (Vectors).

LSH/Vector querying reads from MySQL (LSH) or MySQL+Chroma (Vectors).

Remove pickle loading for LSH/Minhashes.

Iterative Implementation Steps:

(Setup: Instruct agent to check requirements.txt and add PyMySQL (or mysql-connector-python), DBUtils (or sqlalchemy for its pool), and chromadb-client if missing.)

Step 1: Define Core Interface & Adapt Existing Managers

1a. Code: Instruct the agent:

"Create src/runner/database_interface.py. Define an ABC DatabaseInterface with abstract methods: connect, disconnect, execute_sql, get_db_schema, begin_transaction, commit, rollback, store_vector, query_vector_db, store_lsh_signature, query_lsh, clear_lsh_data, clear_vector_data. Add basic docstrings and type hints (use Any for complex return types initially)."

1b. Code: Instruct the agent:

"Rename src/runner/database_manager.py to src/runner/sqlite_manager.py. Modify the class (now SQLiteManager) inside:

Remove the Singleton pattern (_instance, _lock, __new__). The constructor __init__ should take db_mode and db_id directly.

Make SQLiteManager inherit from DatabaseInterface.

Implement connect (likely implicitly handled by SQLite driver), disconnect (no-op usually), begin_transaction, commit, rollback (using standard sqlite3 connection methods).

Keep the existing _set_paths, set_lsh, set_vector_db methods, but make them regular instance methods (remove _lock).

Ensure execute_sql, get_db_schema (and others added via add_methods_to_class) work correctly using self.db_path.

Implement the interface's LSH/vector methods (store_vector, store_lsh_signature, clear_lsh_data, clear_vector_data) by raising NotImplementedError as SQLite won't be the target for storing new data in this migration.

The existing query_lsh and query_vector_db methods should remain, calling self.set_lsh() / self.set_vector_db() first, and then calling the underlying functions from database_utils. These implement the interface methods for the SQLite case."

Remove the add_methods_to_class logic at the end. Instead, explicitly define methods like execute_sql, get_db_schema etc., within the class, potentially calling the underlying functions from database_utils.execution or database_utils.schema and passing self.db_path."

1c. Code: Instruct the agent:

"Modify src/runner/mysql_manager.py. Make its class MySQLManager inherit from DatabaseInterface.

Implement __init__ to take MySQL connection config (host, user, pass, db, pool settings). Store these. Initialize connection pool (e.g., using DBUtils.PooledDB with PyMySQL) but don't connect yet.

Implement connect to get a connection from the pool. Implement disconnect to close the connection (return to pool).

Implement execute_sql using the pooled connection's cursor, handling parameter substitution correctly. Fetch results as specified. Implement basic MySQL error handling (e.g., connection errors, syntax errors).

Implement get_db_schema using INFORMATION_SCHEMA queries.

Implement begin_transaction, commit, rollback using the connection object.

Implement placeholder (NotImplementedError) versions for all LSH/vector methods (store_vector, query_vector_db, store_lsh_signature, query_lsh, clear_lsh_data, clear_vector_data)."

1d. Test: Instruct the agent:

"Create tests/runner/ directory if needed.
Create tests/runner/test_sqlite_manager.py. Add tests verifying SQLiteManager instantiation, core methods (execute_sql, get_db_schema, transactions), and that query_lsh/query_vector_db still function by loading pickles/Chroma path (mock file loading/Chroma if needed).
Create tests/runner/test_mysql_manager.py. Test MySQLManager instantiation, connection pooling (connect/disconnect), core methods (execute_sql, get_db_schema, transactions) against a test MySQL database. Verify LSH/vector methods raise NotImplementedError."

Step 2: Factory, Config & Dependency Injection

2a. Code: Instruct the agent:

"Create src/runner/database_factory.py. Implement DatabaseFactory class with get_database_manager(config: dict) -> DatabaseInterface. It reads config['database']['type']. If 'sqlite', return SQLiteManager(db_mode=config['database']['sqlite_settings']['mode'], db_id=config['database']['sqlite_settings']['id']). If 'mysql', return MySQLManager(config['database']['mysql_settings']). Handle errors."

2b. Code: Instruct the agent:

"Modify config files (e.g., run/configs/CHESS_ALL.yaml). Add database: section with type: 'mysql' (or 'sqlite'), sqlite_settings: {mode: 'dev', id: 'some_db'}, mysql_settings: {host: '...', port: ..., user: '...', password: '${MYSQL_PASSWORD:default_pass}', database: '...', pool_size: 5}. Add chromadb: {host: '...', port: ..., collection_name: '...'}. Update config loading logic (likely in src/runner/run_manager.py or src/main.py) to parse these sections and handle environment variable substitution for password."

2c. Code: Instruct the agent:

"In src/runner/run_manager.py, locate the line DatabaseManager(db_mode=self.args.data_mode, db_id=task.db_id). Replace this logic. Instead: 1. Load the full config (if not already done). 2. Create the appropriate DB manager instance using db_manager = DatabaseFactory.get_database_manager(config). 3. Pass this db_manager instance to components that need it (e.g., potentially store it on the RunManager instance or pass it down).
Search for other direct uses of DatabaseManager() (e.g., in src/workflow/agents/information_retriever/tool_kit/retrieve_entity.py, retrieve_context.py). Refactor these classes/functions to accept the db_manager: DatabaseInterface instance via their constructor or a method parameter."

2d. Test: Instruct the agent:

"Create tests/runner/test_database_factory.py. Test config loading with env var override. Update integration tests for RunManager or application startup to ensure the correct DB manager is created and injected based on config."

Step 3: SQL Dialect Handling (Core Queries)

3a. Code: Instruct the agent:

"Review src/database_utils/execution.py (functions like execute_sql, validate_sql_query) and src/workflow/agents/sql_executor/sql_executor.py. If they construct SQL strings directly, refactor to use SQLAlchemy Core expression language for dialect neutrality where possible, especially for common operations like LIMIT/OFFSET. Ensure execute_sql in the managers correctly handles parameter placeholders (? for SQLite, %s for PyMySQL)."

3b. Test: Instruct the agent:

"Update tests for SQL execution (SQLExecutor agent tests) to run against both SQLite and MySQL configurations, verifying correct execution and results."

Step 4: Vector Database Integration (MySQL + Chroma)

4a. Code: Instruct the agent:

"Define MySQL table vector_metadata (id, source_doc_id, text_chunk_id, chroma_id, metadata JSON). Add schema to ai_docs/database/schema.md or database/mysql_schema.sql. Add indexes."

4b. Code: Instruct the agent:

"Implement store_vector in src/runner/mysql_manager.py. It gets vector, metadata, source_id. 1. Insert metadata into MySQL vector_metadata (get MySQL ID). 2. Init Chroma client (using config). 3. Add vector + metadata (incl. MySQL ID) to Chroma (get chroma_id). 4. Update MySQL row with chroma_id."

4c. Code: Instruct the agent:

"Implement query_vector_db in src/runner/mysql_manager.py. It gets query_vector, top_k, filter_criteria. 1. Init Chroma client. 2. If filter_criteria needs MySQL lookup, query vector_metadata for relevant chroma_ids. 3. Build Chroma where filter. 4. Query Chroma. 5. Return results."

4d. Code: Instruct the agent:

"Implement clear_vector_data in src/runner/mysql_manager.py (delete from MySQL vector_metadata, clear Chroma collection)."

4e. Code: Instruct the agent:

"Refactor vector generation in src/database_utils/db_catalog/preprocess.py (make_db_context_vec_db). It should accept db_manager: DatabaseInterface. Instead of creating a Chroma DB directly on disk, it should call db_manager.store_vector(...) for each embedding. Modify src/preprocess.py to pass the created db_manager instance to make_db_context_vec_db."

4f. Test: Instruct the agent:

"Add unit tests for store_vector, query_vector_db, clear_vector_data in tests/runner/test_mysql_manager.py (mock Chroma client). Test the refactored make_db_context_vec_db by running src/preprocess.py (targeting MySQL) and verifying calls to db_manager.store_vector (mocked) and data in MySQL vector_metadata. Update tests for RetrieveContext agent."

Step 5: LSH/MinHash Refactoring (Generation)

5a. Code: Instruct the agent:

"Define MySQL table lsh_signatures (id, signature_hash, bucket_id, data_reference, source_doc_id). Add schema to docs/SQL file. Add indexes."

5b. Code: Instruct the agent:

"Implement store_lsh_signature in src/runner/mysql_manager.py using batch inserts (executemany)."

5c. Code: Instruct the agent:

"Implement clear_lsh_data in src/runner/mysql_manager.py (DELETE FROM lsh_signatures)."

5d. Code: Instruct the agent:

"Refactor LSH generation in src/database_utils/db_values/preprocess.py:

Modify _get_unique_values to accept db_manager: DatabaseInterface instead of db_path. Change its SQL execution calls to use db_manager.execute_sql(...). It now reads from the primary database (MySQL).

Modify make_lsh to accept db_manager: DatabaseInterface. Inside the loop where it calculates minhash, instead of inserting into the in-memory lsh object and minhashes dict, it should collect batches of (signature_hash, bucket_id, data_reference, source_doc_id) and call db_manager.store_lsh_signature(...) periodically with these batches. The data_reference should point to MySQL identifiers. This function no longer needs to return the lsh object or minhashes dict.

Modify make_db_lsh to accept db_manager: DatabaseInterface. It calls the modified _get_unique_values and make_lsh, passing the db_manager. Remove the pickle saving logic.

Modify src/preprocess.py to pass the created db_manager instance to make_db_lsh."

5e. Test: Instruct the agent:

"Add unit tests for store_lsh_signature, clear_lsh_data in tests/runner/test_mysql_manager.py. Refactor LSH generation tests: Set up source data in test MySQL DB, run refactored src/preprocess.py (targeting MySQL), verify lsh_signatures table in MySQL is populated correctly."

Step 6: LSH/MinHash Refactoring (Querying)

6a. Code: Instruct the agent:

"Implement query_lsh in src/runner/mysql_manager.py. It gets query_signature (hashes). Construct and execute the optimized SQL query against MySQL lsh_signatures table (e.g., SELECT data_reference, COUNT(*) ... WHERE signature_hash IN (...) ... GROUP BY ... ORDER BY ... LIMIT ...). Return results."

6b. Code: Instruct the agent:

"Refactor src/database_utils/db_values/search.py (query_lsh function). This function should now accept db_manager: DatabaseInterface and the query parameters. It should compute the query minhash, identify candidate hashes/buckets, and then call db_manager.query_lsh(...) passing the relevant hashes. It should no longer load pickles.
Update callers like src/workflow/agents/information_retriever/tool_kit/retrieve_entity.py to pass the injected db_manager to this refactored query_lsh function."

6c. Test: Instruct the agent:

"Add unit tests for query_lsh in tests/runner/test_mysql_manager.py using pre-populated MySQL test data. Refactor LSH query integration tests (e.g., for RetrieveEntity): Set up test data (source + signatures in MySQL), run logic triggering LSH queries (targeting MySQL), verify results."

Step 7: Final Integration, Documentation & Cleanup

7a. Test: Instruct the agent:

"Perform end-to-end testing with MySQL config. Test chat, SQL execution, context retrieval (vector), entity retrieval (LSH)."

7b. Code: Instruct the agent:

"Update documentation (README.md, ai_docs/) for MySQL setup, configuration, and preprocessing targeting MySQL. Remove SQLite-specific instructions or mark as legacy."

7c. Code: Instruct the agent:

"(Optional) Remove src/runner/sqlite_manager.py and its tests if no longer needed. Update deployment scripts (run/run_main.sh, Dockerfiles) for MySQL. Recommend using Alembic for schema migrations."