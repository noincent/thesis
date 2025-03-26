# vLLM Integration for CHESS-Plus

## Overview

This document outlines the integration of local vLLM models into the CHESS workflow for SQL generation.

## Key Components

### 1. Model Configuration (src/llm/engine_configs.py)

```python
# Local vLLM models using OpenAI completions API compatibility
"vllm-gemma-2b": {
    "constructor": OpenAI,  # Using OpenAI for completions API
    "params": {
        "model_name": "google/gemma-2b",
        "openai_api_key": "EMPTY",
        "openai_api_base": VLLM_BASE_URL,
        "max_tokens": 100,
        "temperature": 0.2,
    }
},
"vllm-gemma-7b": {
    "constructor": OpenAI,  # Using OpenAI for completions API
    "params": {
        "model_name": "google/gemma-7b",
        "openai_api_key": "EMPTY", 
        "openai_api_base": VLLM_BASE_URL,
        "max_tokens": 200,
        "temperature": 0.1,
    }
}
```

### 2. Custom Parser for vLLM (src/llm/parsers.py)

```python
class VLLMSQLMarkdownParser(BaseOutputParser):
    """Parser specifically for vLLM SQL responses."""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def parse(self, output: str) -> Dict[str, str]:
        """
        Parses the output from vLLM models to extract SQL queries.
        Handles both string and object responses.
        """
        # Handle different input types
        if hasattr(output, 'content'):
            text_content = output.content
        else:
            text_content = str(output)
            
        # Extract content using the same pattern as Gemini parser
        plan = ""
        if "<FINAL_ANSWER>" in text_content and "</FINAL_ANSWER>" in text_content:
            plan = text_content.split("<FINAL_ANSWER>")[0]
            text_content = text_content.split("<FINAL_ANSWER>")[1].split(
            "</FINAL_ANSWER>"
            )[0]
        
        # Clean and format the SQL query
        query = text_content.replace("```sql", "").replace("```", "").replace("\n", " ")
        
        return {"SQL": query, "plan": plan}
```

### 3. LangChain-Compatible Wrapper (src/llm/models.py)

```python
class VLLMCompletionsWrapper(RunnableSerializable):
    """Full implementation of LangChain interface for vLLM completions models."""
    
    llm: Any  # The underlying LLM (OpenAI)
    
    def __init__(self, llm: Any):
        """Initialize with an OpenAI completions model."""
        super().__init__()
        self.llm = llm
    
    def invoke(
        self, 
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> Union[str, BaseMessage]:
        """Process the input and return either a string or ChatMessage."""
        # Convert input to string if it's not already
        if isinstance(input, (list, tuple)) and len(input) > 0:
            if hasattr(input[-1], "content"):
                prompt = input[-1].content
            else:
                prompt = str(input[-1])
        elif isinstance(input, BaseMessage):
            prompt = input.content
        else:
            prompt = str(input)
            
        # Get the response from the underlying model
        text_response = self.llm.invoke(prompt, **kwargs)
        
        # If it's already an object with .content, extract the content
        if hasattr(text_response, 'content'):
            text_response = text_response.content
            
        # Return either a string or AIMessage based on the input type
        if isinstance(input, (list, tuple)) and all(isinstance(x, BaseMessage) for x in input):
            return AIMessage(content=text_response)
        else:
            return text_response
```

### 4. Configuration in wtl.yaml

```yaml
candidate_generator:
  engine: 'gpt-4o-mini'
  tools:
    generate_candidate:
      generator_configs:
        - template_name: 'mysql_wtl'
          engine_config:
            engine_name: 'vllm-gemma-2b'  # Local model
            temperature: 0.2
          parser_name: 'generate_candidate_vllm_cot'  # vLLM-specific parser
          sampling_count: 1
        - template_name: 'mysql_wtl'
          engine_config:
            engine_name: 'gemini-2.0-flash-exp'  # Cloud backup
            temperature: 0.0
          parser_name: 'generate_candidate_gemini_markdown_cot'
          sampling_count: 1
```

## Testing

Two test scripts are provided to verify the integration:

1. `test_vllm_connection.py` - Tests basic connectivity to vLLM server
2. `test_direct_vllm.py` - Tests SQL generation with vLLM

## Usage

1. Start the vLLM server on port 5005
   ```
   python -m vllm.entrypoints.openai.api_server --model google/gemma-2b --port 5005
   ```

2. Run CHESS with normal command
   ```
   python backend.py
   ```

3. The system will automatically use the local vLLM model for SQL generation,
   with fallback to cloud models if needed.

## Troubleshooting

- If the vLLM server is not running, the system will automatically fallback to cloud models
- Check vLLM server logs for any errors
- In case of parser errors, examine the raw output format of the vLLM model