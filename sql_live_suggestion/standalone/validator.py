"""
Database object name validator with exact and fuzzy matching.

This module provides validation logic without any web framework dependencies.
"""

from dataclasses import dataclass
from enum import Enum

from .fuzzy_matcher import FuzzyMatcher
from .metadata_cache import MetadataCache


class ValidationStatus(str, Enum):
    """Possible validation result statuses."""
    VALID = "valid"
    SUGGESTIONS = "suggestions"
    NOT_FOUND = "not_found"


class Scope(str, Enum):
    """Valid scope options for validation."""
    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"


@dataclass
class Suggestion:
    """A fuzzy match suggestion with score."""
    name: str
    score: int


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    status: ValidationStatus
    match: str | None = None
    suggestions: list[Suggestion] | None = None
    
    def is_valid(self) -> bool:
        """Check if the result is a valid exact match."""
        return self.status == ValidationStatus.VALID
    
    def has_suggestions(self) -> bool:
        """Check if there are fuzzy match suggestions."""
        return self.status == ValidationStatus.SUGGESTIONS and bool(self.suggestions)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "match": self.match,
            "suggestions": [
                {"name": s.name, "score": s.score} 
                for s in (self.suggestions or [])
            ] if self.suggestions else None,
        }


class Validator:
    """
    Database object name validator with two-stage matching.
    
    Stage 1: Exact match lookup (O(1) using sets)
    Stage 2: Fuzzy matching if no exact match found
    
    Example:
        cache = MetadataCache()
        cache.load_from_pickle("data/metadata_dev.pkl")
        
        validator = Validator(cache)
        
        # Validate a table name
        result = validator.validate("table", "student", schema="public")
        if result.is_valid():
            print(f"Found: {result.match}")
        elif result.has_suggestions():
            print("Did you mean:", [s.name for s in result.suggestions])
        else:
            print("Not found")
    """
    
    def __init__(
        self,
        cache: MetadataCache,
        fuzzy_threshold: int = 50,
        max_suggestions: int = 5,
    ):
        """
        Initialize the validator.
        
        Args:
            cache: MetadataCache instance with loaded metadata
            fuzzy_threshold: Minimum similarity score (0-100) for suggestions
            max_suggestions: Maximum number of suggestions to return
        """
        self.cache = cache
        self.fuzzy_matcher = FuzzyMatcher(
            threshold=fuzzy_threshold,
            max_results=max_suggestions,
        )
    
    def validate(
        self,
        scope: str,
        search_term: str,
        schema: str | None = None,
        table: str | None = None,
    ) -> ValidationResult:
        """
        Validate a database object name.
        
        Args:
            scope: Type of object - "schema", "table", or "column"
            search_term: The name to validate
            schema: Schema context (for table/column scope)
            table: Table context (for column scope)
        
        Returns:
            ValidationResult with status, match, and/or suggestions
        """
        normalized_term = search_term.lower().strip()
        
        # Stage 1: Exact match (O(1))
        exact_match = self._check_exact_match(scope, normalized_term, schema, table)
        
        if exact_match:
            return ValidationResult(
                status=ValidationStatus.VALID,
                match=exact_match,
            )
        
        # Stage 2: Fuzzy matching
        suggestions = self._find_suggestions(scope, search_term, schema, table)
        
        if suggestions:
            return ValidationResult(
                status=ValidationStatus.SUGGESTIONS,
                suggestions=suggestions,
            )
        
        # No match found
        return ValidationResult(
            status=ValidationStatus.NOT_FOUND,
            suggestions=[],
        )
    
    def validate_schema(self, name: str) -> ValidationResult:
        """Shortcut to validate a schema name."""
        return self.validate("schema", name)
    
    def validate_table(self, name: str, schema: str | None = None) -> ValidationResult:
        """Shortcut to validate a table name."""
        return self.validate("table", name, schema=schema)
    
    def validate_column(
        self, name: str, schema: str | None = None, table: str | None = None
    ) -> ValidationResult:
        """Shortcut to validate a column name."""
        return self.validate("column", name, schema=schema, table=table)
    
    def _check_exact_match(
        self,
        scope: str,
        normalized_term: str,
        schema: str | None,
        table: str | None,
    ) -> str | None:
        """Check for exact match, return original casing if found."""
        if scope == "schema":
            if self.cache.schema_exists(normalized_term):
                return self.cache.get_original_schema(normalized_term)
        
        elif scope == "table":
            if self.cache.table_exists(normalized_term, schema=schema):
                return self.cache.get_original_table(normalized_term)
        
        elif scope == "column":
            if self.cache.column_exists(normalized_term, schema=schema, table=table):
                return self.cache.get_original_column(normalized_term)
        
        return None
    
    def _find_suggestions(
        self,
        scope: str,
        search_term: str,
        schema: str | None,
        table: str | None,
    ) -> list[Suggestion] | None:
        """Find fuzzy match suggestions."""
        # Get candidates based on scope
        if scope == "schema":
            candidates = self.cache.get_schema_candidates()
        elif scope == "table":
            candidates = self.cache.get_table_candidates(schema=schema)
        elif scope == "column":
            candidates = self.cache.get_column_candidates(schema=schema, table=table)
        else:
            return None
        
        if not candidates:
            return None
        
        # Find fuzzy matches
        matches = self.fuzzy_matcher.find_matches(search_term, candidates)
        
        if not matches:
            return None
        
        # Convert to Suggestion objects with original casing
        suggestions = []
        for match in matches:
            if scope == "schema":
                original = self.cache.get_original_schema(match.name)
            elif scope == "table":
                original = self.cache.get_original_table(match.name)
            else:
                original = self.cache.get_original_column(match.name)
            
            if original:
                suggestions.append(Suggestion(name=original, score=match.score))
        
        return suggestions if suggestions else None
