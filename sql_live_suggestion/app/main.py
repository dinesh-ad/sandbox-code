"""FastAPI application entry point for SQL Live Suggestion Service."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.suggest import router as suggest_router
from app.routers.validate import router as validate_router
from app.services.metadata_cache import metadata_cache_manager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events:
    - Startup: Load all environment metadata pickles into memory
    - Shutdown: Cleanup (if needed)
    """
    # Startup
    logger.info("Starting SQL Live Suggestion Service...")
    logger.info(f"Loading metadata for environments: {settings.available_environments}")
    
    # Load all available environment caches
    results = metadata_cache_manager.load_all_environments()
    
    for env, status in results.items():
        if "loaded" in status:
            logger.info(f"  [{env.upper()}] {status}")
        elif "not found" in status:
            logger.warning(f"  [{env.upper()}] {status}")
        else:
            logger.error(f"  [{env.upper()}] {status}")
    
    if metadata_cache_manager.is_any_loaded:
        logger.info(f"Service ready. Available environments: {metadata_cache_manager.available_environments}")
    else:
        logger.warning("No environment caches loaded. Service will start but validation unavailable.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SQL Live Suggestion Service...")


# Create FastAPI application
app = FastAPI(
    title="SQL Live Suggestion Service",
    description=(
        "A standalone microservice for pre-validating database object names "
        "(schemas, tables, columns) against cached metadata with fuzzy suggestions. "
        "Supports multiple environments (prod, stage, qa, dev). "
        "Call this service BEFORE hitting your actual database APIs."
    ),
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(validate_router, prefix=settings.api_prefix)
app.include_router(suggest_router, prefix=settings.api_prefix)


@app.get("/", tags=["root"])
async def root() -> dict:
    """Root endpoint with service information."""
    return {
        "service": "SQL Live Suggestion Service",
        "version": "1.1.0",
        "description": "Pre-validation microservice for database object names",
        "available_environments": metadata_cache_manager.available_environments,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/validate/health",
        "environments": f"{settings.api_prefix}/validate/environments",
    }


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Basic health check endpoint."""
    return {
        "status": "healthy" if metadata_cache_manager.is_any_loaded else "degraded",
        "available_environments": metadata_cache_manager.available_environments,
    }
