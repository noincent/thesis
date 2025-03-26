# CHESS+ AI Documentation

This directory contains comprehensive documentation for the CHESS+ system, designed to help understand the architecture, components, and workflows.

## Documentation Structure

- **[Core System](./core/)**
  - [Architecture Overview](./core/architecture.md): High-level system design
  - [Component Interaction](./core/component_interaction.md): How components communicate

- **[Agents](./agents/)**
  - [Information Retriever](./agents/information_retriever.md): Query analysis and context retrieval
  - Schema Selector: Database schema pruning
  - Candidate Generator: SQL query generation
  - Unit Tester: Query validation and testing
  - Chat Context Analyzer: Conversation understanding
  - Response Generator: Natural language output formatting
  - SQL Executor: Database query execution

- **[LLM Integration](./llm/)**
  - [Integration](./llm/integration.md): Model integration architecture
  - Prompt Engineering: Template-based prompts
  - Model Configuration: Provider-specific settings
  - vLLM Setup: Local model deployment

- **[Workflow](./workflow/)**
  - [Pipeline](./workflow/pipeline.md): End-to-end processing flow
  - State Management: System state tracking
  - Agent Configuration: Customizing behavior
  - Error Handling: Failure recovery strategies

- **[Database Utilities](./database/)**
  - [Schema Management](./database/schema.md): Database schema representation
  - SQL Execution: Query execution and result handling
  - Data Preprocessing: Schema preparation utilities

- **[Installation Guide](./installation/)**
  - [Setup](./installation/setup.md): Development environment setup
  - Configuration: Environment variables and settings
  - Dependencies: Required libraries and tools

- **[Deployment Guide](./deployment/)**
  - Production Deployment: Server setup guidelines
  - Performance Tuning: Optimization strategies
  - Scaling: Handling increased load

- **[Examples](./examples/)**
  - [Basic Usage](./examples/basic_usage.md): Common usage patterns
  - Advanced Scenarios: Complex interaction examples
  - Customization: Extending the system

## Key Components Overview

CHESS+ (Contextual Harnessing for Efficient SQL Synthesis) is an enhanced framework for SQL generation from natural language, featuring:

1. **Core Agents**:
   - **Information Retriever (IR)**: Extracts relevant data through keyword extraction, entity recognition, and context retrieval
   - **Schema Selector (SS)**: Prunes large schemas to focus on relevant tables and columns
   - **Candidate Generator (CG)**: Generates SQL queries based on the enhanced query and schema information
   - **Unit Tester (UT)**: Validates queries for correctness and performance

2. **Chat Extensions**:
   - **Chat Context Analyzer**: Understands user intent across conversation turns
   - **Response Generator**: Creates natural language responses with formatted results
   - **SQL Executor**: Manages query execution against the database

3. **LLM Integration**:
   - Multiple model support (OpenAI, Anthropic, Google)
   - vLLM server integration for local model deployment
   - Custom parsers and template-based prompts
   - Error handling with retries and fallbacks

4. **Pipeline Architecture**:
   - Multi-step workflow for SQL generation with configurable nodes
   - Parallel processing capabilities for batch operations
   - State-based processing with shared context

## Getting Started

For a quick overview of the system, start with the [Architecture Overview](./core/architecture.md) and [Component Interaction](./core/component_interaction.md) documents.

To set up a development environment, see the [Installation Guide](./installation/setup.md).

For example usage patterns, check out the [Basic Usage Guide](./examples/basic_usage.md).

## Available Documentation

The following documentation files are currently available (more coming soon):

- [Core Architecture](./core/architecture.md)
- [Component Interaction](./core/component_interaction.md) 
- [Information Retriever Agent](./agents/information_retriever.md)
- [LLM Integration](./llm/integration.md)
- [Pipeline Workflow](./workflow/pipeline.md)
- [Database Schema Management](./database/schema.md)
- [Installation Setup](./installation/setup.md)
- [Basic Usage Examples](./examples/basic_usage.md)