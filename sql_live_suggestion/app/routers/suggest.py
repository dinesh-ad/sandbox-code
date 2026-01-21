"""Real-time suggestion endpoint for typeahead/autocomplete functionality."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from rapidfuzz import fuzz, process

from app.config import settings
from app.services.metadata_cache import metadata_cache_manager


router = APIRouter(prefix="/suggest", tags=["suggestions"])


@router.get(
    "",
    summary="Real-time suggestions (typeahead)",
    description=(
        "Returns suggestions as the user types. Matches on the actual object name "
        "(not the full path), but returns qualified names."
    ),
)
async def suggest(
    environment: Literal["prod", "stage", "qa", "dev"] = Query(
        ...,
        description="Database environment to search",
    ),
    scope: Literal["schema", "table", "column"] = Query(
        ...,
        description="Type of database object to search",
    ),
    q: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="Search query (minimum 2 characters)",
    ),
    schema_name: str | None = Query(
        default=None,
        description="Filter to specific schema",
    ),
    table_name: str | None = Query(
        default=None,
        description="Filter to specific table (for column scope)",
    ),
    threshold: int = Query(
        default=settings.fuzzy_threshold,
        ge=0,
        le=100,
        description="Minimum similarity score (0-100)",
    ),
    limit: int = Query(
        default=settings.max_suggestions,
        ge=1,
        le=20,
        description="Maximum number of suggestions",
    ),
) -> list[str]:
    """
    Real-time suggestions for autocomplete.
    
    Matches on actual object name (e.g., 'student', 'email'), 
    returns qualified name (e.g., 'public.student', 'public.student.email').
    """
    cache = metadata_cache_manager.get_cache(environment)
    
    if cache is None or not cache.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Environment '{environment}' not available.",
        )
    
    # Get searchable candidates: (search_key, qualified_name) tuples
    candidates = cache.get_searchable_candidates_for_scope(
        scope=scope,
        schema=schema_name,
        table=table_name,
    )
    
    if not candidates:
        return []
    
    # Create mapping: search_key -> qualified_name
    search_keys = [c[0] for c in candidates]
    key_to_qualified = {c[0]: c[1] for c in candidates}
    
    # Fuzzy match on search keys only (the actual names, not paths)
    query_lower = q.lower().strip()
    matches = process.extract(
        query_lower,
        search_keys,
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=threshold,
    )
    
    # Return qualified names with original casing
    results = []
    for match_key, score, _ in matches:
        qualified_lower = key_to_qualified[match_key]
        original = cache.get_original_qualified(scope, qualified_lower)
        if original and original not in results:
            results.append(original)
    
    return results


@router.get(
    "/with-scores",
    summary="Real-time suggestions with similarity scores",
    description="Same as /suggest but includes similarity scores.",
)
async def suggest_with_scores(
    environment: Literal["prod", "stage", "qa", "dev"] = Query(
        ...,
        description="Database environment to search",
    ),
    scope: Literal["schema", "table", "column"] = Query(
        ...,
        description="Type of database object to search",
    ),
    q: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="Search query (minimum 2 characters)",
    ),
    schema_name: str | None = Query(
        default=None,
        description="Filter to specific schema",
    ),
    table_name: str | None = Query(
        default=None,
        description="Filter to specific table (for column scope)",
    ),
    threshold: int = Query(
        default=settings.fuzzy_threshold,
        ge=0,
        le=100,
        description="Minimum similarity score (0-100)",
    ),
    limit: int = Query(
        default=settings.max_suggestions,
        ge=1,
        le=20,
        description="Maximum number of suggestions",
    ),
) -> list[dict]:
    """
    Real-time suggestions with scores.
    
    Matches on actual object name, returns qualified name with score.
    """
    cache = metadata_cache_manager.get_cache(environment)
    
    if cache is None or not cache.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Environment '{environment}' not available.",
        )
    
    # Get searchable candidates: (search_key, qualified_name) tuples
    candidates = cache.get_searchable_candidates_for_scope(
        scope=scope,
        schema=schema_name,
        table=table_name,
    )
    
    if not candidates:
        return []
    
    # Create mapping: search_key -> qualified_name
    search_keys = [c[0] for c in candidates]
    key_to_qualified = {c[0]: c[1] for c in candidates}
    
    # Fuzzy match on search keys only
    query_lower = q.lower().strip()
    matches = process.extract(
        query_lower,
        search_keys,
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=threshold,
    )
    
    # Return qualified names with scores
    results = []
    seen = set()
    for match_key, score, _ in matches:
        qualified_lower = key_to_qualified[match_key]
        original = cache.get_original_qualified(scope, qualified_lower)
        if original and original not in seen:
            results.append({"name": original, "score": int(score)})
            seen.add(original)
    
    return results
