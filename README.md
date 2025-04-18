# CHESS+: Enhanced Contextual SQL Synthesis with Chat Capabilities

This repository contains an enhanced version of CHESS (Contextual Harnessing for Efficient SQL Synthesis), extending it with interactive chat capabilities and additional components.

## Original CHESS Framework
This project builds upon the original CHESS framework, which addresses text-to-SQL translation through four specialized agents:

1. **Information Retriever (IR)**: Extracts relevant data
2. **Schema Selector (SS)**: Prunes large schemas
3. **Candidate Generator (CG)**: Generates high-quality candidates
4. **Unit Tester (UT)**: Validates queries through LLM-based testing

## New Features

### Interactive Chat Capabilities
The enhanced version introduces interactive chat functionality through new specialized components:

1. **Chat Context Analyzer**: Understands user intent and conversation flow
2. **Response Generator**: Produces natural language responses
3. **SQL Executor**: Manages query execution and result formatting
4. **Enhanced Information Retriever**: Improved keyword extraction and context management

### Key Enhancements
- **Interactive Sessions**: Maintain context across multiple queries
- **Natural Conversations**: More intuitive interaction with the SQL generation system
- **Result Formatting**: Clean presentation of query results
- **Context-Aware Responses**: Improved understanding of follow-up questions

## Setting up the Environment

1. **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/CHESS.git
    cd CHESS
    ```

2. **Create a `.env` file** in the root directory with your configuration:
    ```bash
    DATA_MODE="dev"
    DATA_PATH="./data/dev/dev.json"
    DB_ROOT_DIRECTORY="./data/dev/dev_databases"
    DATA_TABLES_PATH="./data/dev/dev_tables.json"
    INDEX_SERVER_HOST='localhost'
    INDEX_SERVER_PORT=12345

    # Database type: sqlite (default) or mysql
    DB_TYPE="sqlite"

    # MySQL configuration (only needed when DB_TYPE=mysql)
    # DB_IP="localhost"
    # DB_USERNAME="root"
    # DB_PASSWORD="your_password_here"
    # MYSQL_PORT=3306
    # DB_NAME="chess_plus"

    OPENAI_API_KEY=
    GCP_PROJECT=''
    GCP_REGION='us-central1'
    GCP_CREDENTIALS=''
    GOOGLE_CLOUD_PROJECT=''
    ```

3. **Install required packages**:
    ```bash
    pip install -r requirements.txt
    ```

### MySQL Database Support

CHESS+ now supports MySQL as the primary database backend, offering improved performance and scalability for larger datasets. The MySQL integration includes optimized vector similarity search and LSH-based retrieval.

#### Setting up MySQL

1. **Install MySQL Server** if you don't have it already:
   ```bash
   sudo apt update
   sudo apt install mysql-server
   ```

2. **Create a database and user** for CHESS+:
   ```bash
   sudo mysql
   ```
   
   Then in the MySQL prompt:
   ```sql
   CREATE DATABASE chess_plus;
   CREATE USER 'chess_user'@'localhost' IDENTIFIED BY 'your_password_here';
   GRANT ALL PRIVILEGES ON chess_plus.* TO 'chess_user'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

3. **Configure CHESS+ to use MySQL** by editing your `.env` file:
   ```
   DB_TYPE="mysql"
   DB_IP="localhost"
   DB_USERNAME="chess_user"
   DB_PASSWORD="your_password_here"
   MYSQL_PORT=3306
   DB_NAME="chess_plus"
   ```

4. **Initialize the MySQL schema**:
   ```bash
   mysql -u chess_user -p chess_plus < src/database_utils/mysql_schema.sql
   ```

5. **Test the MySQL integration**:
   ```bash
   ./run_mysql_tests.sh
   ```
   This script will verify:
   - Basic connection functionality
   - LSH signature storage and retrieval
   - Vector database integration
   - Transaction support

#### MySQL Integration Architecture

The CHESS+ MySQL implementation uses a hybrid approach:

1. **Core Data Storage**: MySQL tables for primary application data
2. **LSH/MinHash**: MySQL-based LSH signature storage with optimized indexing
3. **Vector Embeddings**: Hybrid implementation combining:
   - Vector metadata and filtering in MySQL
   - Actual vector embeddings in ChromaDB
   - Normalized relevance scoring across different ChromaDB versions

This architecture provides:
- **Scalability**: Efficient querying for large datasets
- **Performance**: Fast filtering using MySQL B-tree indices
- **Flexibility**: Support for complex metadata filtering
- **Reliability**: Transaction support with improved error handling
- **Compatibility**: Works with different versions of ChromaDB

#### Runtime Behavior

When using MySQL, the system will:
- Store LSH signatures and vector metadata in MySQL tables
- Use ChromaDB for vector similarity search, integrated with MySQL metadata
- Support transaction operations with improved connection management
- Normalize all relevance scores for consistent ranking regardless of vector distance metric
- Support all existing functionality with backward compatibility
- Provide improved performance for larger datasets

## Preprocessing

To retrieve database catalogs and find the most similar database values to a question, preprocess the databases:

1. **Run the preprocessing script**:
    ```bash
    sh run/run_preprocess.sh
    ```

    This will create the minhash, LSH, and vector databases for each of the databases in the specified directory.

### Advanced Preprocessing Options

CHESS+ now supports additional preprocessing options, especially useful when working with MySQL databases:

```bash
python src/preprocess.py \
  --db_root_directory "./data/dev/dev_databases" \
  --db_id "wtl_employee_tracker" \
  --signature_size 20 \
  --n_gram 3 \
  --threshold 0.01 \
  --clear_existing \
  --verbose True
```

Additional flags available:
- `--clear_existing`: Clear existing LSH and vector data before processing
- `--skip_lsh`: Skip LSH generation (only process vectors)
- `--skip_vectors`: Skip vector generation (only process LSH)

When using MySQL, the preprocessing will:
1. Generate LSH signatures and store them in the MySQL `lsh_signatures` table
2. Generate vector embeddings and store metadata in MySQL with the actual vectors in ChromaDB

## Running the Code

After preprocessing the databases, generate SQL queries for the BIRD dataset by choosing a configuration:

1. **Run the main script**:
    ```bash
    sh run/run_main_ir_cg_ut.sh
    ```

    or

    ```bash
    sh run/run_main_ir_ss_ch.sh
    ```

## Sub-sampled Development Set (SDS)

The sub-sampled development set (SDS) is a subset of the BIRD dataset with 10% of samples from each database. It is used for ablation studies and is available in `sub_sampled_bird_dev_set.json`.

## Supporting Other LLMs

To use your own LLM, modify the `get_llm_chain(engine, temperature, base_uri=None)` function and add your LLM in `run/langchain_utils.py`.

## Using Chat Features

To interact with the system using chat:

1. **Start a chat session**:
    ```bash
    python interface.py --mode chat
    ```

2. **Ask questions naturally**, for example:
    - "Show me all employees in the Sales department"
    - "How many of them were hired last year?"
    - "What's the average salary?"

The system will maintain context across questions and provide formatted responses.

## Web Interface Integration

CHESS+ provides a FastAPI-based web interface that allows easy integration with any frontend application. The web server exposes a RESTful API that handles natural language queries and returns SQL responses.

### Starting the Web Server

1. **Run the web server**:
   ```bash
   python web_interface.py
   ```
   The server will start on `http://0.0.0.0:8010`

### API Endpoints

#### POST /create_session
Creates a new chat session.

**Request Format**:
```json
{
    "user_id": "unique_user_identifier",
    "db_id": "optional_database_id"  // defaults to "wtl_employee_tracker"
}
```

**Response Format**:
```json
{
    "session_id": "generated_uuid",
    "db_id": "database_id",
    "user_id": "user_id"
}
```

#### POST /generate
Processes natural language queries using an existing session.

**Request Format**:
```json
{
    "prompt": "Your natural language query",
    "session_id": "session_id_from_create_session"
}
```

**Response Format**:
```json
{
    "result": "Natural language response from CHESS"
}
```

#### POST /end_session/{session_id}
Explicitly ends a chat session.

**Response Format**:
```json
{
    "message": "Session ended successfully"
}
```

### Testing with curl

You can test the API directly using curl commands. First, install jq for better JSON formatting:
```bash
sudo apt install jq
```

Then run these commands in sequence:

1. Create a new session:
```bash
curl -X POST http://localhost:8010/create_session \
-H "Content-Type: application/json" \
-d '{"user_id": "test_user", "db_id": "wtl_employee_tracker"}' | jq
```

2. Store the session ID (replace YOUR_SESSION_ID with the id from previous response):
```bash
export SESSION_ID="YOUR_SESSION_ID"
```

3. Make a query:
```bash
curl -X POST http://localhost:8010/generate \
-H "Content-Type: application/json" \
-d "{\"prompt\": \"Show me all employees\", \"session_id\": \"$SESSION_ID\"}" | jq
```

4. Make a follow-up query:
```bash
curl -X POST http://localhost:8010/generate \
-H "Content-Type: application/json" \
-d "{\"prompt\": \"How many of them are in sales?\", \"session_id\": \"$SESSION_ID\"}" | jq
```

5. End the session:
```bash
curl -X POST "http://localhost:8010/end_session/$SESSION_ID" | jq
```

### Frontend Integration Example

```javascript
// Example frontend usage
async function chatWithCHESS() {
    // Step 1: Create a new session
    const sessionResponse = await fetch('http://localhost:8010/create_session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_id: 'user123',
            db_id: 'employee_db'
        })
    });
    const { session_id } = await sessionResponse.json();

    // Step 2: Use the session for queries
    const queryResponse = await fetch('http://localhost:8010/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            prompt: "Show me all employees in the sales department",
            session_id: session_id
        })
    });
    const result = await queryResponse.json();
    console.log(result.result);

    // Step 3: End the session when done
    await fetch(`http://localhost:8010/end_session/${session_id}`, {
        method: 'POST'
    });
}
```

### Session Management
The web interface uses a session-based system to maintain conversation context:

1. **Creating Sessions**: 
   - Each conversation starts with a new session
   - Sessions are unique even for the same user and database
   - Use `/create_session` to start a fresh conversation

2. **Using Sessions**:
   - Include the `session_id` with each query
   - Sessions maintain conversation context
   - Invalid or expired sessions return 400 error

3. **Ending Sessions**:
   - Sessions can be explicitly ended using `/end_session`
   - Start a new session to begin a fresh conversation

### CORS Configuration
The web interface has CORS enabled and allows:
- All origins (`*`)
- All methods
- All headers
- Credentials

### Error Handling
The API returns standard HTTP status codes:
- `400`: Bad Request (invalid input or expired session)
- `404`: Session not found (when ending session)
- `500`: Internal Server Error

## Attribution

This project is based on the original CHESS framework. If you use this enhanced version in your research, please cite both this repository and the original CHESS paper:

```bibtex
@article{talaei2024chess,
  title={CHESS: Contextual Harnessing for Efficient SQL Synthesis},
  author={Talaei, Shayan and Pourreza, Mohammadreza and Chang, Yu-Chen and Mirhoseini, Azalia and Saberi, Amin},
  journal={arXiv preprint arXiv:2405.16755},
  year={2024}
}