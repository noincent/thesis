# CHESS+ Basic Usage Examples

This guide demonstrates common usage patterns for the CHESS+ system.

## 1. Running the Complete Pipeline

This example shows how to run the complete NL-to-SQL pipeline on a development dataset:

```bash
python src/main.py \
  --data_mode dev \
  --data_path ./data/dev/fin.json \
  --pipeline_nodes keyword_extraction+entity_retrieval+context_retrieval+column_filtering+table_selection+column_selection+candidate_generation+revision+evaluation
```

### Key Parameters:

- `--data_mode`: Specifies the dataset mode (dev, test, prod)
- `--data_path`: Path to the dataset file (JSON format)
- `--pipeline_nodes`: Comma-separated list of pipeline nodes to execute

## 2. Interactive Chat Mode

For interactive SQL generation through a chat interface:

```bash
python interface.py --mode chat
```

This launches a terminal-based chat interface where you can:
- Ask natural language questions about the database
- Get SQL queries and their results
- Maintain context across multiple questions

## 3. Database Preprocessing

Before using a new database with CHESS+, preprocess it:

```bash
python src/preprocess.py --db_root_directory ./data/databases --db_id "wtl_employee_tracker"
```

The preprocessing step:
- Analyzes schema structure
- Collects sample values
- Creates search indexes
- Prepares metadata for efficient retrieval

## 4. Custom Pipeline Configuration

Create a custom YAML configuration file for specific requirements:

```yaml
# configs/custom_pipeline.yaml
pipeline_nodes:
  - keyword_extraction
  - entity_retrieval
  - table_selection
  - column_selection
  - candidate_generation
  - evaluation

llm:
  provider: "anthropic"
  model: "claude-3-opus"
  temperature: 0.1
  max_tokens: 2000

parallelism:
  batch_size: 1
  max_workers: 1
```

Run with your custom configuration:

```bash
python src/main.py --config ./configs/custom_pipeline.yaml --data_path ./data/test.json
```

## 5. Programmatic API Usage

Use CHESS+ components in your Python code:

```python
from workflow.team_builder import TeamBuilder
from workflow.system_state import SystemState
from database_utils.db_info import get_db_info

# Load database info
db_info = get_db_info("wtl_employee_tracker")

# Create initial state
initial_state = SystemState(
    query="Find employees in the Marketing department with salaries over 50000",
    table_info=db_info,
    chat_history=[]
)

# Configure and build the pipeline
config = {
    "pipeline_nodes": [
        "keyword_extraction", 
        "table_selection", 
        "column_selection", 
        "candidate_generation", 
        "evaluation"
    ],
    "llm": {
        "provider": "openai",
        "model": "gpt-4"
    }
}

# Build and run the pipeline
team_builder = TeamBuilder(config)
graph = team_builder.build_team()
final_state = graph.invoke(initial_state)

# Access results
sql_query = final_state.candidate_queries[0]
print(f"Generated SQL: {sql_query}")
```

## 6. Using Local Models with vLLM

To run CHESS+ with local models via vLLM:

### Step 1: Start the vLLM server

```bash
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --host localhost \
    --port 8000
```

### Step 2: Configure environment variables

```bash
export LLM_PROVIDER=vllm
export VLLM_HOST=localhost
export VLLM_PORT=8000
```

### Step 3: Run CHESS+ with local model

```bash
python src/main.py --data_path ./data/test.json
```

## 7. Batch Processing Multiple Queries

Process a batch of queries from a JSON file:

```json
[
  {
    "question": "How many employees work in the Marketing department?",
    "db_id": "wtl_employee_tracker"
  },
  {
    "question": "What is the average salary in each department?",
    "db_id": "wtl_employee_tracker"
  }
]
```

Run with batch processing:

```bash
python src/main.py --data_mode batch --data_path ./data/batch_queries.json --parallel
```

## 8. Evaluating SQL Generation Quality

Run evaluation on a test dataset with gold standard SQL:

```bash
python src/main.py \
  --data_mode test \
  --data_path ./data/test/spider_dev.json \
  --eval_mode \
  --output_path ./results/evaluation_results.json
```

The evaluation produces metrics including:
- Execution accuracy
- Exact match accuracy
- Component match scores
- Error analysis

## 9. Custom Agent Configuration

You can customize specific agent behavior through configuration:

```yaml
# configs/custom_agent.yaml
information_retriever:
  keyword_extraction:
    enabled: true
    llm_model: "gpt-4"
    confidence_threshold: 0.7
  
candidate_generator:
  revision_enabled: true
  max_candidates: 3
  temperature: 0.3
```

## 10. Debugging Pipeline Execution

For detailed logs to diagnose issues:

```bash
python src/main.py \
  --data_path ./data/test.json \
  --debug \
  --log_level verbose \
  --save_intermediate_states
```

This will:
- Show detailed logs for each step
- Save intermediate state snapshots
- Record all LLM prompts and responses
- Print timing information for performance analysis