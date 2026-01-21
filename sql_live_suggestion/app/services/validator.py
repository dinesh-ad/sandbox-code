"""Validator service that orchestrates scope-aware validation with exact and fuzzy matching."""

from app.config import settings
from app.models.schemas import (
    Context,
    Suggestion,
    ValidationResponse,
    ValidationStatus,
)
from app.services.fuzzy_matcher import FuzzyMatcher
from app.services.metadata_cache import EnvironmentCache


class Validator:
    """
    Scope-aware validator for database object names.
    
    Performs validation in two stages:
    1. Exact match lookup (O(1) using sets)
    2. Fuzzy matching if no exact match found
    """
    
    def __init__(
        self,
        cache: EnvironmentCache,
        fuzzy_matcher: FuzzyMatcher | None = None,
    ) -> None:
        """
        Initialize the validator.
        
        Args:
            cache: EnvironmentCache instance with loaded metadata
            fuzzy_matcher: Optional FuzzyMatcher instance (creates default if None)
        """
        self.cache = cache
        self.fuzzy_matcher = fuzzy_matcher or FuzzyMatcher(
            threshold=settings.fuzzy_threshold,
            max_results=settings.max_suggestions,
        )
    
    def validate(
        self,
        scope: str,
        search_term: str,
        context: Context | None = None,
    ) -> ValidationResponse:
        """
        Validate a search term against the metadata cache.
        
        Args:
            scope: The type of object to validate ("schema", "table", "column")
            search_term: The name to validate
            context: Optional context with schema/table names for scoped search
        
        Returns:
            ValidationResponse with status, match, and/or suggestions
        """
        # Normalize the search term
        normalized_term = search_term.lower().strip()
        
        # Extract context values
        schema_name = context.schema_name if context else None
        table_name = context.table_name if context else None
        
        # Stage 1: Try exact match (O(1) lookup)
        exact_match = self._check_exact_match(
            scope=scope,
            normalized_term=normalized_term,
            schema_name=schema_name,
            table_name=table_name,
        )
        
        if exact_match:
            return ValidationResponse(
                status=ValidationStatus.VALID,
                match=exact_match,
                suggestions=None,
            )
        
        # Stage 2: Try fuzzy matching
        suggestions = self._find_fuzzy_suggestions(
            scope=scope,
            search_term=search_term,
            schema_name=schema_name,
            table_name=table_name,
        )
        
        if suggestions:
            return ValidationResponse(
                status=ValidationStatus.SUGGESTIONS,
                match=None,
                suggestions=suggestions,
            )
        
        # No match found
        return ValidationResponse(
            status=ValidationStatus.NOT_FOUND,
            match=None,
            suggestions=[],
        )
    
    def _check_exact_match(
        self,
        scope: str,
        normalized_term: str,
        schema_name: str | None,
        table_name: str | None,
    ) -> str | None:
        """
        Check for exact match using O(1) set lookup.
        
        Returns the original casing if found, None otherwise.
        """
        if scope == "schema":
            if self.cache.schema_exists(normalized_term):
                return self.cache.get_original_schema(normalized_term)
        
        elif scope == "table":
            if self.cache.table_exists(normalized_term, schema=schema_name):
                return self.cache.get_original_table(normalized_term)
        
        elif scope == "column":
            if self.cache.column_exists(
                normalized_term, schema=schema_name, table=table_name
            ):
                return self.cache.get_original_column(normalized_term)
        
        return None
    
    def _find_fuzzy_suggestions(
        self,
        scope: str,
        search_term: str,
        schema_name: str | None,
        table_name: str | None,
    ) -> list[Suggestion] | None:
        """
        Find fuzzy match suggestions for the search term.
        
        Returns list of Suggestion objects or None if no matches found.
        """
        # Get appropriate candidates based on scope and context
        candidates = self.cache.get_candidates_for_scope(
            scope=scope,
            schema=schema_name,
            table=table_name,
        )
        
        if not candidates:
            return None
        
        # Find fuzzy matches
        matches = self.fuzzy_matcher.find_matches(
            query=search_term,
            candidates=candidates,
        )
        
        if not matches:
            return None
        
        # Convert to Suggestion objects with original casing
        suggestions = []
        for match in matches:
            original_name = self.cache.get_original_for_scope(scope, match.name)
            if original_name:
                suggestions.append(
                    Suggestion(name=original_name, score=match.score)
                )
        
        return suggestions if suggestions else None
