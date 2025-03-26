# LLM Integration in CHESS+

## Overview

CHESS+ uses a flexible LLM integration approach that supports multiple model providers and deployment options. The system is designed to be model-agnostic, allowing for easy switching between different LLMs based on requirements.

## Supported Model Providers

The system currently supports the following model providers:

1. **OpenAI** (gpt-3.5-turbo, gpt-4, etc.)
2. **Anthropic** (claude-3-opus, claude-3-sonnet, etc.)
3. **Google** (gemini-pro, etc.)
4. **Local Models** via vLLM

## Architecture

The LLM integration layer consists of several key components:

```
┌─────────────────────────────────────┐
│           Agent/Tool Layer          │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│          LLM Abstraction            │
│                                     │
│  ┌─────────┐  ┌─────────┐  ┌─────┐  │
│  │ Prompts │  │ Parsers │  │ API │  │
│  └─────────┘  └─────────┘  └─────┘  │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│         Provider Adapters           │
│                                     │
│ ┌───────┐ ┌────────┐ ┌────────────┐ │
│ │OpenAI │ │Anthropic│ │Google/vLLM│ │
│ └───────┘ └────────┘ └────────────┘ │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│            LLM Services             │
└─────────────────────────────────────┘
```

### Key Components

1. **LLM Model Abstraction** (`src/llm/models.py`)
   - Provides a unified interface for all LLM providers
   - Handles authentication, API calls, and error handling
   - Implements retries and fallback strategies

2. **Engine Configurations** (`src/llm/engine_configs.py`)
   - Contains provider-specific configuration profiles
   - Allows for environment-based configuration selection
   - Defines model parameters (temperature, max tokens, etc.)

3. **Prompt Templates** (`src/llm/prompts.py` and `/templates/`)
   - Template-based approach to prompt generation
   - Supports parameterized prompts with variable substitution
   - Includes role-based formatting for chat models

4. **Response Parsers** (`src/llm/parsers.py`)
   - Extracts structured data from LLM responses
   - Implements error-tolerant parsing strategies
   - Supports multiple output formats (JSON, YAML, etc.)

## Integration with vLLM

CHESS+ includes special integration with vLLM for local model deployment:

1. **vLLM Wrapper** (`src/llm/models.py`)
   - Custom wrapper making vLLM compatible with LangChain interface
   - Supports streaming responses
   - Handles batching for improved throughput

2. **Connection Management**
   - Automatic connection initialization and teardown
   - Health checking and reconnection logic
   - Configuration via environment variables

## Usage Examples

### Basic LLM Calling

```python
from llm.models import get_llm

# Get default LLM based on config
llm = get_llm()

# Simple completion
result = llm.invoke("Generate a SQL query to find all employees with salary > 50000")

# Chat completion with messages
from langchain.schema import HumanMessage, SystemMessage

messages = [
    SystemMessage(content="You are a helpful SQL assistant."),
    HumanMessage(content="Write a query to find all employees in the marketing department")
]

response = llm.invoke(messages)
```

### Using Templates

```python
from llm.prompts import load_prompt_template

# Load a template
template = load_prompt_template("generate_candidate")

# Format with variables
formatted_prompt = template.format(
    query="Find all employees in the marketing department",
    table_info="employees(id, name, department, salary)",
    context="Marketing department is coded as 'MKT' in the database"
)

# Send to LLM
result = llm.invoke(formatted_prompt)
```

### Parsing Responses

```python
from llm.parsers import parse_sql_response

# Parse structured data from response
sql_query = parse_sql_response(result)

# Handle parsing errors
if sql_query is None:
    # Fallback handling
    pass
```

## Configuration

Engine configurations are defined in YAML format and can be selected at runtime:

```yaml
llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.2
  max_tokens: 1024
  timeout: 30
  retries: 3
```

Environment variables can override configuration:
- `LLM_PROVIDER`: The provider to use (openai, anthropic, google, vllm)
- `LLM_MODEL`: Specific model to use
- `LLM_TEMPERATURE`: Temperature setting
- `VLLM_HOST`: Hostname for vLLM server
- `VLLM_PORT`: Port for vLLM server

## Error Handling

The LLM integration implements robust error handling:

1. **Connection Errors**: Automatic retries with exponential backoff
2. **Rate Limiting**: Adaptive throttling and request queuing
3. **Timeout Handling**: Graceful timeout recovery
4. **Fallback Strategy**: Cascading to backup models if primary fails
5. **Content Filtering**: Handling of filtered or rejected responses

## Best Practices

1. **Provider Selection**:
   - Use OpenAI/Anthropic for highest quality responses
   - Use vLLM with open models for lower cost and privacy

2. **Prompt Engineering**:
   - Keep system prompts concise and task-focused
   - Use examples for few-shot learning
   - Structure complex outputs with clear formatting instructions

3. **Performance Optimization**:
   - Batch similar requests when possible
   - Cache responses for identical or similar queries
   - Use streaming for long-running generations