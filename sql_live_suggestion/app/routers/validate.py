"""Validation endpoint router for the SQL Live Suggestion Service."""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ValidationRequest, ValidationResponse
from app.services.metadata_cache import metadata_cache_manager
from app.services.validator import Validator


router = APIRouter(prefix="/validate", tags=["validation"])


@router.post(
    "",
    response_model=ValidationResponse,
    summary="Validate database object name",
    description=(
        "Validates a schema, table, or column name against the cached metadata "
        "for a specific environment. Returns 'valid' for exact matches, "
        "'suggestions' for fuzzy matches, or 'not_found' when no similar names exist."
    ),
    responses={
        200: {
            "description": "Validation result",
            "content": {
                "application/json": {
                    "examples": {
                        "valid": {
                            "summary": "Exact match found",
                            "value": {
                                "status": "valid",
                                "match": "student",
                                "suggestions": None,
                            },
                        },
                        "suggestions": {
                            "summary": "Fuzzy matches found",
                            "value": {
                                "status": "suggestions",
                                "match": None,
                                "suggestions": [
                                    {"name": "student", "score": 92},
                                    {"name": "students", "score": 85},
                                ],
                            },
                        },
                        "not_found": {
                            "summary": "No matches found",
                            "value": {
                                "status": "not_found",
                                "match": None,
                                "suggestions": [],
                            },
                        },
                    }
                }
            },
        },
        400: {
            "description": "Environment not available",
        },
        503: {
            "description": "Service unavailable - no metadata loaded",
        },
    },
)
async def validate(request: ValidationRequest) -> ValidationResponse:
    """
    Validate a database object name against the cached metadata.
    
    This endpoint should be called BEFORE hitting the actual database API.
    Only proceed with the DB call when status is 'valid'.
    
    - **environment**: Database environment (prod, stage, qa, dev)
    - **scope**: Type of object to validate (schema, table, or column)
    - **search_term**: The name to validate
    - **context**: Optional schema/table context to narrow search
    """
    # Check if any cache is loaded
    if not metadata_cache_manager.is_any_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No metadata caches loaded. Service is starting up.",
        )
    
    # Get cache for the requested environment
    cache = metadata_cache_manager.get_cache(request.environment)
    
    if cache is None or not cache.is_loaded:
        available = metadata_cache_manager.available_environments
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Environment '{request.environment}' not available. Available: {available}",
        )
    
    # Create validator with environment-specific cache
    validator = Validator(cache=cache)
    
    return validator.validate(
        scope=request.scope,
        search_term=request.search_term,
        context=request.context,
    )


@router.get(
    "/health",
    summary="Check validation service health",
    description="Returns the health status including all loaded environment caches.",
)
async def health_check() -> dict:
    """
    Health check endpoint for the validation service.
    
    Returns cache loading status for all environments.
    """
    return {
        "status": "healthy" if metadata_cache_manager.is_any_loaded else "loading",
        "available_environments": metadata_cache_manager.available_environments,
        "environments": metadata_cache_manager.get_all_stats(),
    }


@router.get(
    "/environments",
    summary="List available environments",
    description="Returns list of environments with loaded metadata caches.",
)
async def list_environments() -> dict:
    """
    List all available environments with their statistics.
    """
    return {
        "available": metadata_cache_manager.available_environments,
        "details": metadata_cache_manager.get_all_stats(),
    }
