"""Fuzzy matching service using RapidFuzz for high-performance string matching."""

from dataclasses import dataclass

from rapidfuzz import fuzz, process


@dataclass
class FuzzyMatch:
    """Result of a fuzzy match operation."""
    
    name: str  # The matched candidate (normalized)
    score: int  # Similarity score (0-100)


class FuzzyMatcher:
    """
    High-performance fuzzy string matcher using RapidFuzz.
    
    Uses WRatio scorer which handles:
    - Character typos (Levenshtein-based)
    - Partial matches
    - Token rearrangements
    """
    
    def __init__(self, threshold: int = 50, max_results: int = 5) -> None:
        """
        Initialize the fuzzy matcher.
        
        Args:
            threshold: Minimum similarity score (0-100) to include in results
            max_results: Maximum number of suggestions to return
        """
        self.threshold = threshold
        self.max_results = max_results
    
    def find_matches(
        self,
        query: str,
        candidates: list[str],
        threshold: int | None = None,
        limit: int | None = None,
    ) -> list[FuzzyMatch]:
        """
        Find fuzzy matches for a query string against a list of candidates.
        
        Args:
            query: The search term to match
            candidates: List of candidate strings to match against
            threshold: Override default threshold (optional)
            limit: Override default max results (optional)
        
        Returns:
            List of FuzzyMatch objects sorted by score (descending)
        """
        if not candidates:
            return []
        
        effective_threshold = threshold if threshold is not None else self.threshold
        effective_limit = limit if limit is not None else self.max_results
        
        # Normalize query for matching
        query_normalized = query.lower().strip()
        
        # Use rapidfuzz process.extract for efficient batch matching
        # scorer=fuzz.WRatio provides weighted ratio that handles various typo patterns
        results = process.extract(
            query_normalized,
            candidates,
            scorer=fuzz.WRatio,
            limit=effective_limit,
            score_cutoff=effective_threshold,
        )
        
        # Convert to FuzzyMatch objects
        # results format: [(match, score, index), ...]
        return [
            FuzzyMatch(name=match, score=int(score))
            for match, score, _ in results
        ]
    
    def find_best_match(
        self,
        query: str,
        candidates: list[str],
        threshold: int | None = None,
    ) -> FuzzyMatch | None:
        """
        Find the single best fuzzy match for a query.
        
        Args:
            query: The search term to match
            candidates: List of candidate strings to match against
            threshold: Minimum score to consider a match (optional)
        
        Returns:
            The best FuzzyMatch or None if no match meets threshold
        """
        if not candidates:
            return None
        
        effective_threshold = threshold if threshold is not None else self.threshold
        query_normalized = query.lower().strip()
        
        result = process.extractOne(
            query_normalized,
            candidates,
            scorer=fuzz.WRatio,
            score_cutoff=effective_threshold,
        )
        
        if result is None:
            return None
        
        match, score, _ = result
        return FuzzyMatch(name=match, score=int(score))
