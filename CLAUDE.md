# CHESS+ Development Guide

## Commands
- Run main pipeline: `python3 src/main.py --data_mode dev --data_path ./data/dev/fin.json --pipeline_nodes keyword_extraction+entity_retrieval+context_retrieval+column_filtering+table_selection+column_selection+candidate_generation+revision+evaluation`
- Run preprocessing: `python3 src/preprocess.py --db_root_directory $DB_ROOT_DIRECTORY --db_id "wtl_employee_tracker"`
- Start chat interface: `python interface.py --mode chat`
- Test vLLM integration: `python test_direct_vllm.py`
- Test vLLM connection: `python test_vllm_connection.py`

## Code Style
- Use 4-space indentation consistently
- Type annotations required for all function arguments and return values
- Follow import order: standard library → third-party packages → local modules
- Use Google-style docstrings for functions and classes
- Class names use PascalCase, functions/variables use snake_case
- Use consistent error handling with try-except blocks and proper logging
- Prefer composition over inheritance where appropriate
- Use descriptive variable names that indicate purpose and type
- For configuration, prefer unified structure - avoid duplicate configurations
- When refactoring, maintain backward compatibility with warning logs

## Project Structure
- `/src` - Main source code
  - `/chat` - Chat session management components
  - `/database_utils` - Database interaction utilities
  - `/llm` - Language model integration
  - `/runner` - Execution and pipeline management
  - `/workflow` - Agent system implementation
- `/templates` - Prompt templates for LLM interactions
- `/run` - Shell scripts for running various pipelines
- `/ai_docs` - Documentation for AI components

## Development Patterns
- Agent-based architecture with tool composition
- Template-driven prompt engineering
- Configuration-driven development with YAML files
- Strong typing with generics for flexibility
- Logging at appropriate severity levels
- Error handling with fallbacks and retries for LLM failures