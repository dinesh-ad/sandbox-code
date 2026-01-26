# SQL Live Suggestion - Standalone Core Library

A **pure Python library** for validating database object names (schemas, tables, columns) with fuzzy matching support. 

**No web framework dependencies** - can be used in any Python application, CLI tool, or integrated into existing systems.

## Purpose

This standalone module provides:

1. **Embeddable validation logic** - Use in any Python project without FastAPI/HTTP overhead
2. **CLI tool integration** - Build command-line tools for database validation
3. **Testing isolation** - Test core logic independently from the API layer
4. **Library usage** - Import and use in data pipelines, scripts, or other applications
5. **Lightweight deployment** - Only needs `rapidfuzz` as a dependency

## Installation

Only one dependency required:

```bash
pip install rapidfuzz
```

## Quick Start

```python
from standalone import MetadataCache, Validator

# 1. Load metadata from pickle file
cache = MetadataCache()
cache.load_from_pickle("data/metadata_dev.pkl")

# 2. Create validator
validator = Validator(cache, fuzzy_threshold=50, max_suggestions=5)

# 3. Validate!
result = validator.validate_table("student", schema="public")

if result.is_valid():
    print(f"✓ Found: {result.match}")
elif result.has_suggestions():
    print("Did you mean:")
    for s in result.suggestions:
        print(f"  - {s.name} ({s.score}%)")
else:
    print("✗ Not found")
```

## Usage Examples

### Basic Validation

```python
from standalone import MetadataCache, Validator

cache = MetadataCache()
cache.load_from_pickle("data/metadata_dev.pkl")
validator = Validator(cache)

# Validate schema
result = validator.validate_schema("public")
print(result.status)  # "valid"

# Validate table
result = validator.validate_table("student", schema="public")
print(result.match)   # "student"

# Validate column
result = validator.validate_column("email", schema="public", table="student")
print(result.is_valid())  # True
```

### Handling Typos

```python
# User typed "studnt" (typo)
result = validator.validate_table("studnt", schema="public")

if result.has_suggestions():
    print(f"Status: {result.status}")  # "suggestions"
    for s in result.suggestions:
        print(f"  {s.name}: {s.score}%")
        # student: 92%
```

### Convert Result to Dictionary

```python
result = validator.validate_table("employee")
data = result.to_dict()
# {
#     "status": "valid",
#     "match": "employee",
#     "suggestions": None
# }
```

### Direct Fuzzy Matching

```python
from standalone import FuzzyMatcher

matcher = FuzzyMatcher(threshold=50, max_results=5)

candidates = ["student", "course", "employee", "department"]
matches = matcher.find_matches("stu", candidates)

for m in matches:
    print(f"{m.name}: {m.score}%")
    # student: 90%
```

### Load from Dictionary (No Pickle)

```python
from standalone import MetadataCache, Validator

# Build metadata programmatically
metadata = {
    "schemas": {
        "public": {
            "tables": {
                "users": ["id", "name", "email"],
                "orders": ["id", "user_id", "total"],
            }
        }
    }
}

cache = MetadataCache()
cache.load_from_dict(metadata)

validator = Validator(cache)
result = validator.validate_table("users")
```

### Check Statistics

```python
cache = MetadataCache()
cache.load_from_pickle("data/metadata_dev.pkl")

stats = cache.get_stats()
print(f"Schemas: {stats['schemas_count']}")
print(f"Tables: {stats['tables_count']}")
print(f"Columns: {stats['columns_count']}")
```

### Direct Cache Lookups (O(1))

```python
cache = MetadataCache()
cache.load_from_pickle("data/metadata_dev.pkl")

# Fast existence checks
if cache.table_exists("student", schema="public"):
    print("Table exists!")

if cache.column_exists("email", schema="public", table="student"):
    print("Column exists!")

# Get original casing
original = cache.get_original_table("STUDENT")  # Returns "student" or "Student"
```

## CLI Tool Example

```python
#!/usr/bin/env python3
"""Simple CLI for database name validation."""

import sys
from standalone import MetadataCache, Validator

def main():
    if len(sys.argv) < 3:
        print("Usage: validate.py <scope> <name> [schema] [table]")
        print("  scope: schema, table, or column")
        sys.exit(1)
    
    scope = sys.argv[1]
    name = sys.argv[2]
    schema = sys.argv[3] if len(sys.argv) > 3 else None
    table = sys.argv[4] if len(sys.argv) > 4 else None
    
    cache = MetadataCache()
    cache.load_from_pickle("data/metadata_dev.pkl")
    validator = Validator(cache)
    
    result = validator.validate(scope, name, schema=schema, table=table)
    
    if result.is_valid():
        print(f"✓ VALID: {result.match}")
        sys.exit(0)
    elif result.has_suggestions():
        print(f"? SUGGESTIONS for '{name}':")
        for s in result.suggestions:
            print(f"    {s.name} ({s.score}%)")
        sys.exit(1)
    else:
        print(f"✗ NOT FOUND: {name}")
        sys.exit(2)

if __name__ == "__main__":
    main()
```

## API Reference

### `MetadataCache`

| Method | Description |
|--------|-------------|
| `load_from_pickle(path)` | Load metadata from a pickle file |
| `load_from_dict(data)` | Load metadata from a dictionary |
| `schema_exists(name)` | Check if schema exists (O(1)) |
| `table_exists(name, schema)` | Check if table exists (O(1)) |
| `column_exists(name, schema, table)` | Check if column exists (O(1)) |
| `get_original_schema(name)` | Get original casing for schema |
| `get_original_table(name)` | Get original casing for table |
| `get_original_column(name)` | Get original casing for column |
| `get_schema_candidates()` | Get all schemas for fuzzy matching |
| `get_table_candidates(schema)` | Get tables for fuzzy matching |
| `get_column_candidates(schema, table)` | Get columns for fuzzy matching |
| `get_stats()` | Get cache statistics |

### `Validator`

| Method | Description |
|--------|-------------|
| `validate(scope, name, schema, table)` | Validate any database object |
| `validate_schema(name)` | Validate a schema name |
| `validate_table(name, schema)` | Validate a table name |
| `validate_column(name, schema, table)` | Validate a column name |

### `ValidationResult`

| Property/Method | Description |
|-----------------|-------------|
| `status` | ValidationStatus enum (valid/suggestions/not_found) |
| `match` | The exact match found (when valid) |
| `suggestions` | List of Suggestion objects (when suggestions) |
| `is_valid()` | Returns True if exact match found |
| `has_suggestions()` | Returns True if fuzzy suggestions available |
| `to_dict()` | Convert to dictionary |

### `FuzzyMatcher`

| Method | Description |
|--------|-------------|
| `find_matches(query, candidates, threshold, limit)` | Find all fuzzy matches |
| `find_best_match(query, candidates, threshold)` | Find single best match |

## Differences from API Version

| Feature | API Version | Standalone |
|---------|-------------|------------|
| Dependencies | FastAPI, uvicorn, pydantic, rapidfuzz | rapidfuzz only |
| Usage | HTTP endpoints | Python imports |
| Multi-environment | Managed by CacheManager | One cache per instance |
| Configuration | Environment variables | Constructor arguments |
| Output format | JSON over HTTP | Python objects |
