# CHESS+ Architecture Overview

## System Architecture

CHESS+ (Contextual Harnessing for Efficient SQL Synthesis) is a modular agent-based system designed for natural language to SQL processing. The architecture follows these key design principles:

- **Modular Agent-Based Design**: Multiple specialized agents collaborating on different aspects of SQL generation
- **Pipeline Architecture**: Sequential multi-step workflow with clear data flow between components
- **State-Based Processing**: Shared system state that evolves as it passes through pipeline nodes
- **Configuration-Driven Development**: YAML configuration files for controlling system behavior
- **Template-Driven Prompt Engineering**: Standardized prompt templates for LLM interactions
- **Composition Over Inheritance**: Agents composed of tools rather than complex inheritance hierarchies
- **Strong Typing**: Type annotations and generics for interface clarity

## High-Level Component Overview

```
┌─────────────────────────────────────┐
│              User Input             │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│        Chat Context Analyzer        │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│        Information Retriever        │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│           Schema Selector           │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│        Candidate Generator          │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│            Unit Tester              │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│            SQL Executor             │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│         Response Generator          │
└───────────────────┬─────────────────┘
                    ▼
┌─────────────────────────────────────┐
│            User Response            │
└─────────────────────────────────────┘
```

## Key Subsystems

### Runner Layer
- **RunManager**: Manages task execution, coordinate agents, and tracks statistics
- **Task**: Defines execution units with input/output specifications
- **DatabaseManager**: Handles database connections and setup
- **StatisticsManager**: Tracks performance metrics

### Agent Layer
- **Team Builder**: Constructs the agent pipeline using LangGraph's StateGraph
- **Agent Base**: Common interface for all agents
- **Tools**: Composable, reusable capabilities for agents
- **System State**: Shared context passed between pipeline nodes

### LLM Layer
- **Model Integration**: Abstract interface for different LLM providers
- **Engine Configs**: Configuration profiles for various LLM engines
- **Parsers**: Utilities for extracting structured data from LLM responses
- **Prompts**: Template-driven prompt generation

### Database Layer
- **Schema Management**: Database schema representation and utilities
- **SQL Parsing**: Tools for parsing and analyzing SQL queries
- **Execution**: Database query execution and result handling

## Execution Flow

1. User sends a natural language query
2. Chat Context Analyzer processes user intent and enhances the query
3. Information Retriever extracts keywords and retrieves relevant context
4. Schema Selector prunes large database schemas to relevant tables/columns
5. Candidate Generator creates SQL query candidates based on retrieved information
6. Unit Tester validates the generated SQL queries
7. SQL Executor runs the final query against the database
8. Response Generator formats results and creates a natural language response
9. The final response is presented to the user

## Configuration System

The system behavior is controlled through YAML configuration files that define:
- Pipeline composition (which agents to include)
- LLM engine selection and parameters
- Agent-specific settings
- Logging and debugging options