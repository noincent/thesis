# Information Retriever State Flow

## Agent Overview
The Information Retriever is the second agent in the pipeline (or first in non-chat mode). It extracts keywords, entities, and relevant context from the user query to support downstream SQL generation.

## State Input
- **SystemState/ChatSystemState** with:
  - task.question (original or enhanced from ChatContextAnalyzer)
  - task.evidence (hint or additional context)
  - In chat mode: chat_context with conversation history

## Tools Analysis

### 1. ExtractKeywords

#### State Changes
- **`keywords`**: Populates with list of extracted keywords from query and hint
- Ensures keywords are unique while preserving order

#### State Flow Details
```
Input: 
  state.task.question (original or enhanced query)
  state.task.evidence (hint data if available)
  state.chat_context (in chat mode)

Processing:
  1. Retrieves conversation summary if in chat mode
  2. Calls LLM to extract keywords from query and hint
  3. Validates response format is a list of keywords
  4. Removes duplicate keywords while preserving order
  5. Sets state.keywords = cleaned_keywords list

Output:
  state with populated keywords list
```

#### Implementation Notes
- Adapts to chat/non-chat mode - uses conversation context when available
- Handles duplicate keywords automatically
- Validates LLM response format with proper error handling

#### Unchanged Attributes
- All other SystemState attributes
- task properties
- Original chat context structure (only used as input)

### 2. RetrieveEntity

#### State Changes
- Does not directly update state attributes in visible code
- Likely extracts entities that could be used by other tools (implicit)

#### State Flow Details
```
Input: 
  state.task.question
  state.keywords (from ExtractKeywords)

Processing:
  Calls LLM to identify named entities in query (database and domain-specific)
  [Implementation details not fully visible in provided code]

Output:
  Extracts entities but storage/update mechanism not shown in provided code
```

#### Implementation Notes
- Appears to be called after ExtractKeywords
- May store entities in a way not visible in the provided code snippets
- Possible missing update to state.entities or similar attribute

### 3. RetrieveContext

#### State Changes
- Likely updates context-related fields (not fully visible in provided code)
- May update `retrieved_context` or similar field

#### State Flow Details
```
Input: 
  state.task.question
  state.keywords (from ExtractKeywords)
  state.entities (if populated by RetrieveEntity)

Processing:
  Uses keywords and entities to retrieve relevant context
  [Implementation details not fully visible in provided code]

Output:
  Updates context-related fields in state
```

#### Implementation Notes
- Likely depends on output from both previous tools
- Intended to provide context for SQL generation
- May integrate with external knowledge sources

## Comprehensive State Changes

| State Attribute | Before Agent | After Agent | Notes |
|----------------|--------------|-------------|-------|
| keywords | Empty list | Populated with extracted keywords | Main visible change |
| entities | Not set | Possibly populated (implementation not shown) | Implicit from agent functionality |
| retrieved_context | Not set | Possibly populated (implementation not shown) | Implicit from agent functionality |

## Data Flow Optimization

### Efficient Properties
- Clear sequence of operations (keywords → entities → context)
- Proper validation of LLM responses before updating state
- Reuses conversation context in chat mode

### Inefficiencies
- **Incomplete state update visibility**: Some tools may not properly update state attributes
- **Multiple LLM calls**: Each tool makes a separate LLM call
- **Potential redundancy**: Similar context may be processed multiple times

## Improvement Opportunities

1. **Explicit entity storage**: Add direct state update for entities
   ```python
   # Clear entity storage in state
   state.entities = extracted_entities
   ```

2. **Batch processing**: Combine keyword and entity extraction in one LLM call
   ```python
   # Extract both in a single request
   response = async_llm_chain_call(
       prompt=combined_extraction_prompt,
       # ...
   )
   state.keywords = response["keywords"]
   state.entities = response["entities"]
   ```

3. **Context persistence**: Cache retrieved context for similar queries
   ```python
   # Check for similar previous queries
   if query_is_similar(state.task.question, previous_queries):
       state.retrieved_context = cached_context
   ```

4. **Progressive enhancement**: Add confidence scores to extracted items
   ```python
   # Add confidence metadata
   state.keywords_with_confidence = [
       {"keyword": k, "confidence": score} for k, score in extracted_with_scores
   ]
   ```

5. **Parallelized extraction**: Run keyword and entity extraction in parallel
   ```python
   # Parallel execution
   keyword_future = asyncio.create_task(extract_keywords(state))
   entity_future = asyncio.create_task(extract_entities(state))
   await asyncio.gather(keyword_future, entity_future)
   ```

## Interaction with Other Agents

### Input From
- **ChatContextAnalyzer** (in chat mode): Receives enhanced query with historical context

### Output To
- **SchemaSelector**: Provides keywords and entities for table/column selection
- **CandidateGenerator**: Provides context for SQL generation

## Technical Debt Considerations

1. Incomplete implementation of entity storage in state
2. Lack of configuration for keyword extraction parameters
3. Missing validation for entity extraction
4. No clear error recovery for failed context retrieval
5. Potential for out-of-sync state between keywords and entities</content>