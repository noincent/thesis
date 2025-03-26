import sys
from pathlib import Path
import requests
import json
import os

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = str(current_dir / "src")
sys.path.append(src_dir)

# Import necessary components
from llm.models import get_llm_chain, call_engine
from llm.parsers import get_parser

def test_vllm_for_sql():
    """Test direct and integrated SQL generation with vLLM."""
    print("Testing vLLM for SQL generation...")
    
    # Define the base template from mysql_wtl
    # A simplified version for testing
    mysql_template = """
**MySQL 8.0 Database Admin Instructions**

These instructions are crucial for maintaining data integrity and ensuring accurate query results.

<database_schema>
{schema}
</database_schema>

Question: 
{question}

**************************
【Answer】
"""

    example_schema = """
Database Schema and Description
This database has tables: employee, project, work_hour, team, client.
- employee: stores employee information (uuid, name, department, alias, position, salary)
- project: stores project details (uuid, name, team_id, client_id, revenue)
- work_hour: tracks hours worked (uuid, project_id, employee_id, hour, start_date, end_date)
- team: contains team information (uuid, name, description)
- client: stores client information (uuid, name, company, contact)
"""

    # Test 1: Direct API call to vLLM
    print("\n=== Test 1: Direct API call to vLLM ===")
    vllm_base_url = "http://localhost:5005"
    completions_url = f"{vllm_base_url}/v1/completions"
    model_name = "google/gemma-2b"
    
    prompt = mysql_template.format(
        schema=example_schema,
        question="Find all employees who worked more than 40 hours last week"
    )
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model_name,
        "prompt": prompt,
        "max_tokens": 500,
        "temperature": 0.2
    }
    
    try:
        response = requests.post(completions_url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract the generated text
            if 'choices' in result and len(result['choices']) > 0:
                generated_text = result['choices'][0].get('text', '')
                print("\nResponse from vLLM Direct API:")
                print(generated_text)
                
                if "SELECT" in generated_text.upper():
                    print("\n✅ SQL generation successful via direct API!")
                else:
                    print("\n⚠️ Response doesn't appear to contain SQL.")
        else:
            print(f"\n❌ API request failed: HTTP {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"\n❌ Error during direct API test: {e}")
    
    # Test 2: Using our VLLMCompletionsWrapper with the vLLM parser
    print("\n=== Test 2: Using VLLMCompletionsWrapper with vLLM parser ===")
    try:
        engine = get_llm_chain(engine_name="vllm-gemma-2b")
        parser = get_parser("generate_candidate_vllm_cot")
        
        prompt = mysql_template.format(
            schema=example_schema,
            question="List all projects with their total work hours"
        )
        
        # First try invoking the engine directly
        raw_response = engine.invoke(prompt)
        print("\nRaw output from engine:")
        if hasattr(raw_response, 'content'):
            print(raw_response.content[:200] + "...")
        else:
            print(str(raw_response)[:200] + "...")
        
        # Then parse the response
        parsed_response = parser.parse(raw_response)
        print("\nParsed response:")
        print(parsed_response)
        
        if "SQL" in parsed_response and "SELECT" in parsed_response["SQL"].upper():
            print("\n✅ SQL generation and parsing successful!")
        else:
            print("\n⚠️ Parsing might not have extracted SQL correctly.")
    except Exception as e:
        print(f"\n❌ Error during wrapper and parser test: {e}")
    
    # Test 3: Using call_engine helper function for simplified usage
    print("\n=== Test 3: Using call_engine helper function ===")
    try:
        engine = get_llm_chain(engine_name="vllm-gemma-2b")
        
        prompt = mysql_template.format(
            schema=example_schema,
            question="Calculate the average hours worked per department"
        )
        
        response_text = call_engine(prompt, engine)
        
        print("\nResponse via call_engine:")
        print(response_text[:200] + "...")
        
        # Check if the response contains SQL
        if "SELECT" in response_text.upper():
            print("\n✅ SQL generation via call_engine successful!")
        else:
            print("\n⚠️ Response doesn't appear to contain SQL.")
            
        # Now test parsing the response
        parsed_response = parser.parse(response_text)
        print("\nParsed response from call_engine:")
        print(parsed_response)
        
    except Exception as e:
        print(f"\n❌ Error during call_engine test: {e}")

    print("\n=== All tests completed ===")

if __name__ == "__main__":
    test_vllm_for_sql()