# import sys
# from pathlib import Path

# current_dir = Path(__file__).parent
# src_dir = str(current_dir / "src")
# sys.path.append(src_dir)
# from llm.models import get_llm_chain, call_engine


# def test_vllm_qwen_connection():
#     """Tests if we can connect to the vLLM server and get a response from Qwen."""

#     engine_name = "Qwen/Qwen2.5-1.5B-Instruct"  # Make sure this matches your config
#     engine = get_llm_chain(engine_name=engine_name)

#     try:
#         response = call_engine("Tell me a short joke.", engine)
#         print("Response from Qwen/vLLM:")
#         print(response)

#         if response and isinstance(response, str) and len(response.strip()) > 0:
#             print("\n✅ Connection to vLLM and Qwen model successful!")
#         else:
#             print("\n❌  Received an empty or invalid response. Check vLLM server and configuration.")

#     except Exception as e:
#         print(f"\n❌  Error during test: {e}")
#         print("   Check if the vLLM server is running and accessible.")

# if __name__ == "__main__":
#     test_vllm_qwen_connection()
import sys
import uuid
import json
import requests
from pathlib import Path
from datetime import datetime

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = str(current_dir / "src")
sys.path.append(src_dir)

# Import necessary components
from llm.models import get_llm_chain, call_engine
from runner.logger import Logger
from runner.task import Task
from runner.database_manager import DatabaseManager
from dotenv import load_dotenv
import os

def setup_environment():
    """Set up necessary environment and components before testing."""
    # Load environment variables
    load_dotenv(override=True)
    
    # Create results directory for logs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("results") / "tests" / timestamp
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize Logger with required parameters
    Logger(
        db_id="test_db",
        question_id=f"test_{uuid.uuid4().hex[:8]}",
        result_directory=str(results_dir)
    )
    
    print(f"Environment and Logger initialized. Results directory: {results_dir}")
    return results_dir

def test_vllm_connection():
    """Tests if we can connect to the vLLM server using our new engine configs."""
    results_dir = setup_environment()
    
    # Initialize database manager with default settings if needed for logging
    try:
        DatabaseManager(db_mode='dev', db_id='test_db')
    except Exception as e:
        print(f"Warning: Could not initialize DatabaseManager: {e}")
        print("Continuing test anyway as we're just testing LLM connectivity...")
    
    vllm_base_url = "http://localhost:5005"
    model_name = "microsoft/Phi-4-mini-instruct"
    
    print(f"Testing connection to vLLM server at {vllm_base_url}")
    print(f"Using model: {model_name}")
    
    # First, verify connection with direct API call
    completions_url = f"{vllm_base_url}/v1/completions"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "prompt": "San Francisco is a",
        "max_tokens": 50,
        "temperature": 0.5
    }
    
    try:
        print("Step 1: Verifying direct connection to vLLM server...")
        response = requests.post(completions_url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            print("✅ Direct API connection successful!")
            
            # Test our pre-configured vLLM models
            print("\nStep 2: Testing with our pre-configured vLLM models...")
            
            # Test vllm-gemma-2b
            try:
                print("\nTesting vllm-phi-4-mini:")
                engine = get_llm_chain(engine_name="vllm-phi-4-mini")
                prompt = "Tell me a short story about"
                print(f"Prompt: '{prompt}'")
                response_text = engine.invoke(prompt)
                
                print("\nResponse:")
                content = response_text.content if hasattr(response_text, 'content') else str(response_text)
                print(content)
                
                if content and len(str(content).strip()) > 0:
                    print("\n✅ vllm-phi-4-mini test successful!")
                else:
                    print("\n❌ vllm-phi-4-mini test failed. Empty response.")
            except Exception as e:
                print(f"\n❌ Error testing vllm-phi-4-mini: {e}")
                
            # Test common use case with call_engine helper (with our wrapper)
            try:
                print("\nStep 3: Testing with call_engine helper with our CompletionsAPIWrapper...")
                engine = get_llm_chain(engine_name="vllm-phi-4-mini")
                prompt = "What are three interesting facts about"
                print(f"Prompt: '{prompt}'")
                response_text = call_engine(prompt, engine)
                
                print("\nResponse through call_engine:")
                print(response_text)
                
                if response_text and isinstance(response_text, str) and len(response_text.strip()) > 0:
                    print("\n✅ call_engine integration successful!")
                else:
                    print("\n❌ call_engine integration failed. Check implementation.")
            except Exception as e:
                print(f"\n❌ Error during call_engine integration: {e}")
                
            # Test SQL generation capability with the enhanced wrapper
            try:
                print("\nStep 4: Testing SQL generation capability with RunnableSerializable wrapper...")
                engine = get_llm_chain(engine_name="vllm-phi-4-mini")
                prompt = "Write a SQL query to find all employees who worked more than 40 hours last week"
                print(f"Prompt: '{prompt}'")
                response_text = call_engine(prompt, engine)
                
                print("\nGenerated SQL:")
                print(response_text)
                
                if "SELECT" in response_text.upper():
                    print("\n✅ SQL generation successful!")
                else:
                    print("\n⚠️ Response doesn't appear to contain SQL. Model may need fine-tuning for SQL tasks.")
                
                # Test as part of LangChain pipe
                from langchain_core.prompts import ChatPromptTemplate
                print("\nStep 5: Testing with LangChain pipe...")
                prompt_template = ChatPromptTemplate.from_template("Generate a SQL query to {task}")
                pipe = prompt_template | engine
                result = pipe.invoke({"task": "find employees in AI team"})
                print("\nLangChain pipe result:")
                if isinstance(result, str):
                    print(result)
                else:
                    print(result.content)
                
                if "SELECT" in str(result).upper():
                    print("\n✅ LangChain pipe integration successful!")
                else:
                    print("\n⚠️ LangChain pipe result doesn't contain SQL.")
                
            except Exception as e:
                print(f"\n❌ Error during SQL generation test: {e}")
            
        else:
            print(f"\n❌ API request failed: HTTP {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        print("   Check if the vLLM server is running and accessible.")
        
        # Save error information to the results directory
        error_file = results_dir / "vllm_test_error.txt"
        with open(error_file, 'w') as f:
            f.write(f"Error testing vLLM connection: {e}")
        print(f"Error details saved to: {error_file}")

if __name__ == "__main__":
    test_vllm_connection()