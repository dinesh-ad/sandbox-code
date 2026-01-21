# SQL Live Suggestion Service

A standalone FastAPI microservice that pre-validates database object names (schemas, tables, columns) against cached metadata and provides fuzzy suggestions. Supports multiple environments (prod, stage, qa, dev).

## Purpose

This service acts as a **gatekeeper** before actual database API calls:
- Always validates against in-memory cached metadata
- Never hits the actual database for validation
- Returns validation results that consuming applications use to decide whether to proceed
- Supports multiple environments with separate metadata caches

## Flow

```
User Input → Validation Service → valid/suggestions/not_found → (if valid) → Existing DB API
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare Metadata Pickle Files

Create pickle files for each environment in the `data/` directory:
- `data/metadata_prod.pkl`
- `data/metadata_stage.pkl`
- `data/metadata_qa.pkl`
- `data/metadata_dev.pkl`

Expected structure for each pickle file:

```python
{
    "schemas": {
        "public": {
            "tables": {
                "student": ["id", "name", "email"],
                "course": ["id", "title", "credits"]
            }
        },
        "hr": {
            "tables": {
                "employee": ["emp_id", "first_name", "salary"]
            }
        }
    },
    "exported_at": "2026-01-21T10:00:00Z"
}
```

Or use the sample script to create test data:

```bash
python scripts/create_sample_pickle.py
```

### 3. Run the Service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger documentation.

## API Endpoints

### POST /api/v1/validate

Validates a database object name. Call this BEFORE hitting your DB API.

**Request:**
```json
{
    "environment": "prod",
    "scope": "table",
    "search_term": "student",
    "context": {
        "schema_name": "public"
    }
}
```

**Response (valid):**
```json
{
    "status": "valid",
    "match": "student",
    "suggestions": null
}
```

**Response (suggestions):**
```json
{
    "status": "suggestions",
    "match": null,
    "suggestions": [
        {"name": "student", "score": 92},
        {"name": "students", "score": 85}
    ]
}
```

**Response (not_found):**
```json
{
    "status": "not_found",
    "match": null,
    "suggestions": []
}
```

### GET /api/v1/suggest

Real-time suggestions for autocomplete/typeahead. Matches on actual object name, returns qualified path.

**Request:**
```
GET /api/v1/suggest?environment=dev&scope=table&q=stu&threshold=50&limit=5
```

**Response:**
```json
["public.student", "public.instructor"]
```

### GET /api/v1/suggest/with-scores

Same as `/suggest` but includes similarity scores.

**Response:**
```json
[
    {"name": "public.student", "score": 90},
    {"name": "public.instructor", "score": 60}
]
```

### GET /api/v1/validate/environments

List all available environments.

### GET /api/v1/validate/health

Health check with cache statistics.

## Configuration

Environment variables (prefix: `SQL_SUGGESTION_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SQL_SUGGESTION_PICKLE_BASE_DIR` | `data` | Directory containing pickle files |
| `SQL_SUGGESTION_FUZZY_THRESHOLD` | `50` | Minimum similarity score (0-100) |
| `SQL_SUGGESTION_MAX_SUGGESTIONS` | `5` | Maximum suggestions to return |
| `SQL_SUGGESTION_API_PREFIX` | `/api/v1` | API route prefix |
| `SQL_SUGGESTION_AVAILABLE_ENVIRONMENTS` | `["prod", "stage", "qa", "dev"]` | Environments to load |

## Architecture

```
sql_live_suggestion/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app with lifespan
│   ├── config.py               # pydantic-settings configuration
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Request/Response Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── metadata_cache.py   # Multi-environment cache manager
│   │   ├── validator.py        # Scope-aware validation logic
│   │   └── fuzzy_matcher.py    # RapidFuzz wrapper
│   └── routers/
│       ├── __init__.py
│       ├── validate.py         # /validate endpoint
│       └── suggest.py          # /suggest endpoint
├── data/
│   ├── metadata_prod.pkl
│   ├── metadata_stage.pkl
│   ├── metadata_qa.pkl
│   └── metadata_dev.pkl
├── scripts/
│   └── create_sample_pickle.py
├── requirements.txt
└── README.md
```

## Key Features

- **Multi-Environment Support**: Separate caches for prod/stage/qa/dev
- **Fuzzy Matching**: RapidFuzz for high-performance string matching
- **Qualified Names**: Returns `schema.table.column` format
- **O(1) Exact Match**: Uses sets for instant lookups
- **Configurable Threshold**: Adjustable similarity threshold per request
