# CHESS+ Installation Guide

This guide walks through the process of setting up CHESS+ for development and testing.

## Prerequisites

- Python 3.9+ with pip
- MySQL 8.0+ (for database operations)
- Git
- 16GB+ RAM recommended (8GB minimum)
- 50GB+ disk space for development databases
- CUDA-compatible GPU recommended for local LLM deployment

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/chess-plus.git
cd chess-plus
```

## Step 2: Set Up a Virtual Environment

Using Python's built-in venv:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Optional: Install Development Dependencies

For development, testing, and documentation:

```bash
pip install -r requirements-dev.txt
```

## Step 4: Configure Environment Variables

Copy the example environment file:

```bash
cp dotenv_copy .env
```

Open the `.env` file in a text editor and configure the following:

```
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_ROOT_DIRECTORY=/path/to/your/databases

# LLM Configuration
LLM_PROVIDER=openai  # Options: openai, anthropic, google, vllm
LLM_MODEL=gpt-4      # Specific model to use
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key

# vLLM Configuration (for local deployment)
VLLM_HOST=localhost
VLLM_PORT=8000
VLLM_MODEL=meta-llama/Llama-2-7b-chat-hf
```

## Step 5: Set Up a Database

For testing, you can use the sample databases provided:

```bash
# Create database directory
mkdir -p ./data/databases

# Run the preprocessing script to prepare the database
python src/preprocess.py --db_root_directory ./data/databases --db_id "wtl_employee_tracker"
```

## Step 6: Verify Installation

Run a basic test to verify your installation:

```bash
python interface.py --mode test
```

If successful, you should see a confirmation message that all components are working correctly.

## Optional: Set Up vLLM for Local Model Deployment

For local LLM deployment, you'll need to set up vLLM:

### Install vLLM

```bash
pip install vllm
```

### Download and Run a Model

```bash
# Start the vLLM server with your chosen model
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --host localhost \
    --port 8000
```

### Test vLLM Connection

```bash
python test_vllm_connection.py
```

## Development Workflow

Once the installation is complete, you can:

1. Run the main pipeline:
   ```bash
   python src/main.py --data_mode dev --data_path ./data/dev/fin.json --pipeline_nodes keyword_extraction+entity_retrieval+context_retrieval+column_filtering+table_selection+column_selection+candidate_generation+revision+evaluation
   ```

2. Start the chat interface:
   ```bash
   python interface.py --mode chat
   ```

3. Run preprocessing for a different database:
   ```bash
   python src/preprocess.py --db_root_directory $DB_ROOT_DIRECTORY --db_id "your_database_name"
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify MySQL is running: `systemctl status mysql`
   - Check credentials in `.env` file
   - Ensure the database exists: `mysql -u root -p -e "SHOW DATABASES;"`

2. **LLM API Errors**
   - Verify API keys in `.env` file
   - Check internet connection
   - Ensure you have sufficient quota/credits

3. **vLLM Setup Issues**
   - Check GPU compatibility and drivers
   - Ensure you have enough VRAM for the chosen model
   - Verify the model is correctly downloaded

4. **Import Errors**
   - Ensure virtual environment is activated
   - Verify all dependencies are installed
   - Check for conflicting package versions

### Getting Help

If you encounter issues not covered here:

1. Check the logs in the `logs/` directory
2. Consult the project documentation
3. Open an issue on the project repository

## Next Steps

- Visit the [Database Setup Guide](../database/setup.md) for more information on working with databases
- Check the [Developer Guide](../workflow/development.md) for contribution guidelines
- Explore the [Examples](../examples/README.md) for usage patterns