"""
SQL Live Suggestion - Standalone Core Library

A pure Python library for validating database object names with fuzzy matching.
No web framework dependencies - can be used in any Python application.

Example Usage:
    from standalone import MetadataCache, Validator
    
    # Load metadata
    cache = MetadataCache()
    cache.load_from_pickle("data/metadata_dev.pkl")
    
    # Create validator
    validator = Validator(cache)
    
    # Validate a table name
    result = validator.validate_table("studnt", schema="public")
    
    if result.is_valid():
        print(f"✓ Found: {result.match}")
    elif result.has_suggestions():
        print("Did you mean:")
        for s in result.suggestions:
            print(f"  - {s.name} ({s.score}%)")
    else:
        print("✗ Not found")
"""

from .metadata_cache import MetadataCache
from .fuzzy_matcher import FuzzyMatcher, FuzzyMatch
from .validator import (
    Validator,
    ValidationResult,
    ValidationStatus,
    Suggestion,
    Scope,
)

__all__ = [
    # Main classes
    "MetadataCache",
    "Validator",
    "FuzzyMatcher",
    
    # Result types
    "ValidationResult",
    "ValidationStatus",
    "Suggestion",
    "FuzzyMatch",
    "Scope",
]

__version__ = "1.0.0"
