# Database Schema Management in CHESS+

## Overview

CHESS+ includes a comprehensive system for managing database schemas, which is crucial for translating natural language to SQL. The schema management components enable the system to:

1. Parse and represent database schemas
2. Preprocess schema information for efficient retrieval
3. Provide schema context to LLM prompts
4. Filter schema elements based on query relevance

## Schema Representation

### Database Schema Classes

The core schema classes are defined in `src/database_utils/schema.py`:

```python
class Column:
    """Represents a database column with type information and foreign key details."""
    name: str
    type: str
    is_primary_key: bool
    foreign_key: Optional[ForeignKey]
    description: Optional[str]

class Table:
    """Represents a database table with its columns and relationships."""
    name: str
    columns: List[Column]
    primary_keys: List[str]
    description: Optional[str]

class Database:
    """Represents a complete database schema."""
    db_id: str
    tables: List[Table]
    foreign_keys: List[Dict]
    table_names_original: List[str]
    column_names_original: List[List[str]]
    column_types: List[str]
    primary_keys: List[int]
```

### Schema Loading

Schemas are loaded from JSON files in a standard format:

```python
from database_utils.schema import load_schema

# Load schema from file
schema = load_schema("/path/to/schema.json")

# Access schema components
tables = schema.tables
for table in tables:
    print(f"Table: {table.name}")
    for column in table.columns:
        print(f"  - {column.name} ({column.type})")
```

## Schema Preprocessing

Before SQL generation, schemas undergo preprocessing to enhance performance:

### Preprocessing Steps

1. **Normalization**: Standardize table and column names
2. **Type Inference**: Enhance data type information
3. **Relationship Analysis**: Identify foreign key relationships
4. **Metadata Enrichment**: Add descriptions and sample values
5. **Indexing**: Create search indexes for tables and columns

### Preprocessing Command

```bash
python src/preprocess.py --db_root_directory ./data/databases --db_id "wtl_employee_tracker"
```

This command generates preprocessed schema files in the database directory.

## Schema Selection

A key capability of CHESS+ is schema selection - identifying the most relevant parts of large schemas based on the user query:

### Table Selection

The `SchemaSelector` agent uses the `SelectTables` tool to identify relevant tables:

```python
class SelectTables:
    """Tool for selecting tables relevant to a query."""
    
    def run(self, query: str, keywords: List[Dict], table_info: Dict) -> List[str]:
        """Select relevant tables based on query and keywords."""
        # Implementation uses LLM to identify relevant tables
        # Returns list of table names
```

### Column Selection

After table selection, the `SelectColumns` tool identifies relevant columns:

```python
class SelectColumns:
    """Tool for selecting columns relevant to a query."""
    
    def run(self, query: str, keywords: List[Dict], 
            selected_tables: List[str], table_info: Dict) -> Dict[str, List[str]]:
        """Select relevant columns for each selected table."""
        # Implementation uses LLM to identify relevant columns
        # Returns mapping of table names to column lists
```

### Column Filtering

For large tables, the `FilterColumn` tool further prunes columns:

```python
class FilterColumn:
    """Tool for filtering columns based on relevance threshold."""
    
    def run(self, query: str, table_columns: Dict[str, List[str]], 
            table_info: Dict) -> Dict[str, List[str]]:
        """Filter columns based on relevance to the query."""
        # Implementation uses relevance scoring to filter columns
        # Returns pruned mapping of table names to column lists
```

## Schema Presentation

The schema is presented to LLMs in a structured format:

### Table Information Format

```
Table: employees
Columns:
- id (INT, primary key)
- name (VARCHAR)
- department_id (INT, foreign key to departments.id)
- salary (DECIMAL)
- hire_date (DATE)

Table: departments
Columns:
- id (INT, primary key)
- name (VARCHAR)
- location (VARCHAR)
```

### Foreign Key Information

```
Foreign Keys:
- employees.department_id -> departments.id
```

## Cached Schema Access

For performance, CHESS+ implements schema caching:

```python
from database_utils.db_info import get_db_info

# Cached schema access
db_info = get_db_info("wtl_employee_tracker")

# Access schema components
tables = db_info["tables"]
columns = db_info["columns"]
foreign_keys = db_info["foreign_keys"]
```

## Sample Values

To improve SQL generation quality, CHESS+ can include sample values:

```
Table: departments
Columns:
- id (INT, primary key)
  Sample values: 1, 2, 3
- name (VARCHAR)
  Sample values: "Marketing", "Engineering", "Finance"
- location (VARCHAR)
  Sample values: "New York", "San Francisco", "Chicago"
```

Sample values are collected during preprocessing and stored with the schema.

## Schema Customization

Custom schema metadata can be added through annotations:

### Adding Column Descriptions

```json
{
  "column_descriptions": {
    "employees.salary": "Base salary in USD per year, not including bonuses",
    "employees.department_id": "ID reference to the department table"
  }
}
```

### Adding Table Descriptions

```json
{
  "table_descriptions": {
    "employees": "Contains all current and past employee records",
    "departments": "Contains all company departments and their locations"
  }
}
```

## Schema Storage

Schemas are stored in a standardized format:

1. **Raw Schema**: Original JSON schema files
2. **Processed Schema**: Preprocessed schema with additional metadata
3. **Vector Embeddings**: For semantic search of schema elements

The default location is in the database root directory specified in the environment configuration.