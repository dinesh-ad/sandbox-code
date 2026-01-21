"""Pydantic models for API request and response schemas."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Scope(str, Enum):
    """Valid scope options for validation."""
    
    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"


class Environment(str, Enum):
    """Valid database environments."""
    
    PROD = "prod"
    STAGE = "stage"
    QA = "qa"
    DEV = "dev"


class ValidationStatus(str, Enum):
    """Possible validation status values."""
    
    VALID = "valid"
    SUGGESTIONS = "suggestions"
    NOT_FOUND = "not_found"


class Context(BaseModel):
    """Optional context to narrow down the search scope."""
    
    schema_name: str | None = Field(
        default=None,
        description="Schema name to search within (required for table/column scope)",
    )
    table_name: str | None = Field(
        default=None,
        description="Table name to search within (required for column scope)",
    )


class ValidationRequest(BaseModel):
    """Request model for the validation endpoint."""
    
    environment: Literal["prod", "stage", "qa", "dev"] = Field(
        ...,
        description="Database environment to validate against",
    )
    scope: Literal["schema", "table", "column"] = Field(
        ...,
        description="The type of database object to validate",
    )
    search_term: str = Field(
        ...,
        min_length=1,
        description="The name to validate against the metadata cache",
    )
    context: Context | None = Field(
        default=None,
        description="Optional context to narrow search scope",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "environment": "dev",
                    "scope": "table",
                    "search_term": "student",
                    "context": {"schema_name": "public"},
                },
                {
                    "environment": "prod",
                    "scope": "schema",
                    "search_term": "public",
                },
                {
                    "environment": "qa",
                    "scope": "column",
                    "search_term": "email",
                    "context": {"schema_name": "public", "table_name": "student"},
                },
            ]
        }
    }


class Suggestion(BaseModel):
    """A fuzzy match suggestion with similarity score."""
    
    name: str = Field(
        ...,
        description="The suggested name (original casing)",
    )
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Similarity score (0-100)",
    )


class ValidationResponse(BaseModel):
    """Response model for the validation endpoint."""
    
    status: Literal["valid", "suggestions", "not_found"] = Field(
        ...,
        description="Validation result status",
    )
    match: str | None = Field(
        default=None,
        description="The exact match found (original casing), only when status is 'valid'",
    )
    suggestions: list[Suggestion] | None = Field(
        default=None,
        description="List of fuzzy match suggestions when status is 'suggestions'",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "valid",
                    "match": "student",
                    "suggestions": None,
                },
                {
                    "status": "suggestions",
                    "match": None,
                    "suggestions": [
                        {"name": "student", "score": 92},
                        {"name": "students", "score": 85},
                    ],
                },
                {
                    "status": "not_found",
                    "match": None,
                    "suggestions": [],
                },
            ]
        }
    }
