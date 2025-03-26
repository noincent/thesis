# Candidate Generator State Flow

## Agent Overview
The Candidate Generator creates SQL query candidates based on the user's question and the tentative schema provided by the Schema Selector. It leverages LLM capabilities to generate, refine, and optimize SQL queries that satisfy the user's intent.

## State Input
- **SystemState/ChatSystemState** with:
  - task.question (enhanced query)
  - keywords (from InformationRetriever)
  - tentative_schema (from SchemaSelector)
  - schema_with_examples (if available)
  - schema_with_descriptions (if available)
  - In chat mode: chat_context with referenced tables/columns from past interactions

## Tools Analysis

### 1. GenerateCandidate

#### State Changes
- **`SQL_meta_infos`**: Initializes with generated SQL candidates
- Each candidate includes metadata like confidence, rationale

#### State Flow Details
```
Input: 
  state.task.question
  state.tentative_schema
  state.schema_with_examples (optional)
  state.schema_with_descriptions (optional)

Processing:
  1. Formats database schema information from tentative_schema
  2. Calls LLM to generate multiple SQL candidate queries
  3. Parses and validates each candidate
  4. Creates SQLMetaInfo objects for each valid candidate
  5. Populates state.SQL_meta_infos with candidate collection

Output:
  state with populated SQL_meta_infos containing candidate queries
```

#### Implementation Notes
- May generate multiple candidates with different approaches
- Uses schema metadata (examples, descriptions) if available
- Likely includes confidence scores or rankings

#### Unchanged Attributes
- tentative_schema and schema metadata
- keywords and task attributes
- conversation history

### 2. Revise

#### State Changes
- **`SQL_meta_infos`**: Updates with revised SQL candidates
- Adds feedback and improvement history
- May update confidence scores

#### State Flow Details
```
Input: 
  state.task.question
  state.SQL_meta_infos (initial candidates)
  state.tentative_schema
  state.execution_history (if available)

Processing:
  1. Analyzes initial candidates for issues
  2. Generates feedback for each candidate
  3. Creates revised versions addressing identified issues
  4. Creates new SQLMetaInfo objects with revisions
  5. Updates state.SQL_meta_infos with improved candidates

Output:
  state with updated SQL_meta_infos containing revised candidates
```

#### Implementation Notes
- Builds on initial candidate generation
- Incorporates feedback mechanism for improvement
- May prioritize candidates based on quality
- Could have multiple revision rounds

#### Unchanged Attributes
- tentative_schema and schema metadata
- keywords and task attributes
- conversation history

## Comprehensive State Changes

| State Attribute | Before Agent | After Agent | Notes |
|----------------|--------------|-------------|-------|
| SQL_meta_infos | Empty dict | Dict with SQL candidates | Key output of this agent |
| execution_history | May be empty or contain previous steps | May add candidate generation entries | For tracking purposes |

## Data Flow Optimization

### Efficient Properties
- Generation and revision separation allows for focused improvements
- Maintains multiple candidates for robustness
- Preserves feedback and improvement history

### Inefficiencies
- **Multiple LLM calls**: Generation and revision as separate calls
- **Potential redundancy**: Similar logic may be duplicated across candidates
- **Complete regeneration**: May regenerate similar queries rather than modify

## Improvement Opportunities

1. **Incremental refinement**: Track changes between revision iterations
   ```python
   # Record specific changes made during revision
   for candidate in revised_candidates:
       candidate.revision_changes = compute_diff(candidate.original, candidate.revised)
   ```

2. **Speculative execution**: Test simple queries while generating complex ones
   ```python
   # Execute simple queries early while still generating complex ones
   simple_candidates = filter(is_simple, candidates)
   if simple_candidates:
       execute_in_background(simple_candidates[0])
   ```

3. **Template-based generation**: Use common patterns for similar queries
   ```python
   # Detect query patterns and apply templates
   pattern = detect_query_pattern(state.task.question)
   if pattern in query_templates:
       candidates.extend(apply_template(query_templates[pattern], state))
   ```

4. **Candidate diversity**: Ensure generated candidates explore different approaches
   ```python
   # Ensure diversity in candidate set
   candidates = ensure_diversity(candidates, min_distance=0.3)
   ```

5. **Chat-aware generation**: Reuse query patterns from past interactions
   ```python
   # Learn from previous successful queries in chat
   if hasattr(state, 'chat_context') and state.chat_context:
       previous_query_patterns = extract_patterns(state.chat_context)
       candidates.extend(apply_patterns(previous_query_patterns, state))
   ```

## Interaction with Other Agents

### Input From
- **SchemaSelector**: Receives tentative_schema with relevant tables/columns
- **InformationRetriever**: Uses keywords for query generation

### Output To
- **UnitTester**: Provides SQL candidates for testing
- **SQLExecutor**: Provides best candidate for execution

## Technical Debt Considerations

1. Lack of structured approach to candidate diversity
2. Limited schema validation before query generation
3. No clear mechanism for handling complex queries (e.g., subqueries, CTEs)
4. Missing optimization for frequently used query patterns
5. Limited use of historical query performance in chat mode

## State Management Complexity

### SQLMetaInfo Object
The candidate generator uses SQLMetaInfo objects to store:
- The SQL query itself
- Confidence score
- Rationale for generation
- Feedback from revision
- Version history for iterative improvement

This creates a complex nested structure in state.SQL_meta_infos that requires careful management:

```python
# Example structure
state.SQL_meta_infos = {
    "initial": [SQLMetaInfo(SQL="...", confidence=0.8, rationale="...")],
    "revised": [SQLMetaInfo(SQL="...", confidence=0.9, rationale="...", feedbacks=["..."])]
}
```

### Construction of SQL History
The `construct_history` method on SystemState shows how the SQL_meta_infos are used to build a history of SQL generation and revision:

```python
def construct_history(self) -> Dict:
    history = ""
    values_list = list(self.SQL_meta_infos.values())
    
    for index in range(len(values_list) - 1):
        history += f"Step: {index + 1}\n"
        history += f"Original SQL: {self.remove_new_lines(values_list[index][0].SQL)}\n"
        history += f"Feedbacks: {self.remove_new_lines(self._get_feedback_string(values_list[index][0].feedbacks))}\n"
        history += f"Refined SQL: {self.remove_new_lines(values_list[index + 1][0].SQL)}\n"
        history += "\n"
    
    return history
```

This complex state structure allows for rich history tracking but increases the complexity of state management.</content>