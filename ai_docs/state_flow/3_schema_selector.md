# Schema Selector State Flow

## Agent Overview
The Schema Selector agent prunes large database schemas to identify the tables and columns most relevant to the query, creating a tentative schema that downstream agents can use for SQL generation.

## State Input
- **SystemState/ChatSystemState** with:
  - task.question (enhanced query)
  - keywords (from InformationRetriever)
  - Retrieved context (if available)
  - In chat mode: chat_context with referenced tables/columns from past interactions

## Tools Analysis

### 1. SelectTables

#### State Changes
- **`tentative_schema`**: Initializes or updates with selected tables
- May indirectly update `similar_columns` by introducing new tables

#### State Flow Details
```
Input: 
  state.task.question
  state.keywords
  state.chat_context (in chat mode)

Processing:
  1. Retrieves full database schema
  2. Calls LLM to identify relevant tables for the query
  3. Creates or updates tentative_schema with selected tables
  4. May initialize columns as empty lists for each selected table

Output:
  state with updated tentative_schema containing selected tables
```

#### Implementation Notes
- Uses keywords to provide context for table selection
- May leverage chat history for table continuity
- Likely filters out irrelevant tables from large schemas

#### Unchanged Attributes
- keywords and other Information Retriever outputs
- task attributes
- Most SystemState base attributes

### 2. SelectColumns

#### State Changes
- **`tentative_schema`**: Updates with columns for previously selected tables
- **`similar_columns`**: May populate with similar column mappings

#### State Flow Details
```
Input: 
  state.task.question
  state.keywords
  state.tentative_schema (with tables from SelectTables)
  state.chat_context (in chat mode)

Processing:
  1. For each table in tentative_schema
  2. Calls LLM to identify relevant columns
  3. Updates tentative_schema with selected columns
  4. May update similar_columns with column similarity mappings

Output:
  state with tentative_schema containing tables and columns
```

#### Implementation Notes
- Depends on table selection from previous tool
- Uses keywords to guide column selection
- May use natural language understanding to map query terms to columns

#### Unchanged Attributes
- Keywords and other Information Retriever outputs
- task attributes
- Original tentative_schema tables (only columns are added)

### 3. FilterColumn

#### State Changes
- **`tentative_schema`**: Refines by removing irrelevant columns
- **`schema_with_examples`**: May populate with example values for columns
- **`schema_with_descriptions`**: May populate with column descriptions

#### State Flow Details
```
Input: 
  state.task.question
  state.keywords
  state.tentative_schema (with tables and columns)

Processing:
  1. Evaluates relevance of each column in tentative_schema
  2. Removes columns deemed irrelevant to the query
  3. May add example values for remaining columns
  4. May add descriptions for remaining columns

Output:
  state with refined tentative_schema and optional metadata
```

#### Implementation Notes
- Final pruning stage for the schema
- May add valuable metadata about columns
- Helps maintain a focused schema for SQL generation

#### Unchanged Attributes
- Keywords and other Information Retriever outputs
- task attributes
- Original tentative_schema tables (only columns are filtered)

## Comprehensive State Changes

| State Attribute | Before Agent | After Agent | Notes |
|----------------|--------------|-------------|-------|
| tentative_schema | Not set or empty | Populated with relevant tables and columns | Core change |
| similar_columns | Empty dict | May contain column similarity mappings | Optional enhancement |
| schema_with_examples | Empty dict | May contain example values for columns | Optional enhancement |
| schema_with_descriptions | Empty dict | May contain column descriptions | Optional enhancement |

## Data Flow Optimization

### Efficient Properties
- Progressive refinement (tables → columns → filtered columns)
- Only selected tables and columns carried forward
- Addition of useful metadata (examples, descriptions)

### Inefficiencies
- **Multiple LLM calls**: Each selection step requires separate LLM calls
- **Potential reprocessing**: Similar analysis may occur across steps
- **Full schema loading**: May load entire schema even for small queries

## Improvement Opportunities

1. **Progressive schema loading**: Load schema details only for selected tables
   ```python
   # Only load column details for selected tables
   for table in selected_tables:
       state.tentative_schema[table] = load_columns_for_table(table)
   ```

2. **Unified selection**: Combine table and initial column selection
   ```python
   # Select tables and key columns in one step
   response = llm_call(prompt_for_tables_and_key_columns)
   state.tentative_schema = response["tables_and_columns"]
   ```

3. **Schema caching**: Cache schema for frequent queries
   ```python
   # Use cached schema for similar queries
   if query_hash in schema_cache:
       state.tentative_schema = schema_cache[query_hash]
   ```

4. **Hierarchical refinement**: Use tiered approach to schema selection
   ```python
   # First broad selection, then specific refinement
   candidate_tables = select_candidate_tables(state)
   final_tables = refine_table_selection(state, candidate_tables)
   state.tentative_schema = build_schema(final_tables)
   ```

5. **Chat-aware selection**: Give priority to tables/columns in chat history
   ```python
   # Prioritize previously used tables/columns
   if hasattr(state, 'chat_context') and state.chat_context:
       prioritize_tables(state.tentative_schema, state.chat_context.referenced_tables)
   ```

## Interaction with Other Agents

### Input From
- **InformationRetriever**: Receives keywords and query context

### Output To
- **CandidateGenerator**: Provides pruned schema for SQL generation
- **SQLExecutor**: Provides schema information for SQL execution

## Technical Debt Considerations

1. Incomplete metadata propagation (examples, descriptions may be missing)
2. Lack of clear state validation between steps
3. No specific handling for schema version changes
4. Limited feedback mechanism for schema selection quality
5. Missing optimization for repeated queries on same tables

## State Connections

### State Methods Used
- **add_columns_to_tentative_schema**: Updates schema with new columns
- **check_schema_status**: Validates schema against ground truth
- **add_connections_to_tentative_schema**: Adds foreign key relationships
- **get_schema_string**: Serializes schema for use in prompts

### Database Manager Integration
The Schema Selector heavily interacts with DatabaseManager for:
1. Retrieving full database schema
2. Getting column information
3. Adding table connections
4. Validating schema selections against ground truth</content>