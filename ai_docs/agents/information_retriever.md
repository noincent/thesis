# Information Retriever Agent

## Overview

The Information Retriever (IR) agent is responsible for extracting relevant information from the user query and retrieving context that can help with SQL generation. It plays a critical role in the early stages of the CHESS+ pipeline by:

1. Extracting keywords from the natural language query
2. Identifying named entities that could correspond to database values
3. Retrieving relevant context from documentation and knowledge sources

## Components

The Information Retriever is composed of three main tools:

### 1. ExtractKeywords Tool

**Purpose**: Identifies important terms in the user query that can be mapped to database schema elements.

**Implementation**: 
- Uses an LLM to extract keywords from the query
- Template-based approach with prompt engineering
- Keywords are categorized by type (table name, column name, function, etc.)
- Includes confidence scores for each extracted keyword

**Example Output**:
```json
{
  "keywords": [
    {"keyword": "employees", "type": "table", "confidence": 0.95},
    {"keyword": "salary", "type": "column", "confidence": 0.92},
    {"keyword": "department", "type": "column", "confidence": 0.88},
    {"keyword": "greater than", "type": "operator", "confidence": 0.75}
  ]
}
```

### 2. RetrieveEntity Tool

**Purpose**: Identifies named entities in the query that might correspond to specific values in the database.

**Implementation**:
- Uses LLM for entity recognition
- Maps entities to potential database columns and values
- Supports various entity types: dates, names, locations, organizations, etc.
- Handles ambiguous entities with candidate mappings

**Example Output**:
```json
{
  "entities": [
    {
      "entity": "Marketing", 
      "type": "department",
      "potential_columns": ["department_name", "dept_name"],
      "confidence": 0.87
    },
    {
      "entity": "50000", 
      "type": "number",
      "potential_columns": ["salary", "budget"],
      "confidence": 0.92
    }
  ]
}
```

### 3. RetrieveContext Tool

**Purpose**: Finds relevant documentation, examples, and knowledge that can help with query understanding.

**Implementation**:
- Semantic search for relevant documentation
- Retrieval of similar past queries and their SQL
- Integration with vector databases for efficient retrieval
- Context ranking based on relevance to the query

**Example Output**:
```json
{
  "contexts": [
    {
      "source": "database_documentation",
      "content": "The employees table contains records of all current and past employees...",
      "relevance_score": 0.89
    },
    {
      "source": "query_examples",
      "content": "Example query: 'SELECT * FROM employees WHERE salary > 50000'",
      "relevance_score": 0.76
    }
  ]
}
```

## Integration Points

The Information Retriever integrates with:

- **ChatContextAnalyzer**: Receives enhanced queries
- **SchemaSelector**: Provides keywords and entities to help with schema pruning
- **CandidateGenerator**: Supplies retrieved context for better SQL generation

## Configuration Options

The agent can be configured through YAML configurations:

```yaml
information_retriever:
  keyword_extraction:
    enabled: true
    llm_model: "gpt-4"
    confidence_threshold: 0.6
  entity_retrieval:
    enabled: true
    llm_model: "gpt-4"
    confidence_threshold: 0.7
  context_retrieval:
    enabled: true
    max_documents: 5
    relevance_threshold: 0.6
```

## Performance Considerations

- Keyword extraction and entity retrieval are parallelized for efficiency
- Context retrieval uses vector embeddings for fast similarity search
- Caching mechanisms for previously processed queries
- Incremental processing to avoid redundant computations

## Example Prompts

The Information Retriever uses template-based prompts, such as:

```
You are a SQL assistant analyzing a user question to extract keywords.
Look for table names, column names, functions, and conditions.

User Question: {query}

Extract all relevant keywords from this question that would help in constructing a SQL query.
For each keyword, specify its type and give a confidence score.
```

## Error Handling

The Information Retriever implements several fallback mechanisms:

1. If keyword extraction fails, it falls back to generic schema mapping
2. If entity recognition is low-confidence, it provides multiple candidates
3. If context retrieval returns limited results, it broadens the search criteria

## Usage Examples

```python
from workflow.agents.information_retriever.information_retriever import InformationRetriever

ir_agent = InformationRetriever()
result = ir_agent.process(system_state)

# Extracted keywords are available in system_state.keywords
# Retrieved entities are available in system_state.entities
# Retrieved context is available in system_state.retrieved_context
```