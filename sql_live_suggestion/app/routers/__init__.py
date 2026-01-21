"""API routers for the validation service."""

from app.routers.suggest import router as suggest_router
from app.routers.validate import router as validate_router

__all__ = ["suggest_router", "validate_router"]
