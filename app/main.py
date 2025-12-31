"""
Main FastAPI application for PC Recommendation System
Clean rebuild with proper structure and error handling
"""
import logging
logging.basicConfig(level=logging.DEBUG)
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from app.api.routes import auth
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.database import connect_to_mongo, close_mongo_connection

# Setup logging
setup_logging()
logger = get_logger(__name__)

print("AUTH ROUTER LOADED:", auth)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with graceful shutdown"""
    logger.info("Lifespan: Starting lifespan context")
    try:
        logger.info("Starting PC Recommendation System...")
        logger.info(f"Version: {settings.version}")
        logger.info(f"Environment: {'development' if settings.debug else 'production'}")
        
        # Connect to MongoDB (allow failure for graceful degradation)
        logger.info("Lifespan: Attempting to connect to MongoDB")
        try:
            await connect_to_mongo()
            logger.info("MongoDB connection established")
        except Exception as e:
            logger.warning(f"Database connection failed (continuing without DB): {e}")
            logger.warning("Lifespan: Database connection failed, but continuing")
        
        logger.info("Lifespan: About to yield control to application")
        yield
        logger.info("Lifespan: Application yielded back control")
    except Exception as e:
        logger.error(f"Lifespan: Exception in lifespan: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down PC Recommendation System...")
        try:
            await close_mongo_connection()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")
        logger.info("Lifespan: Lifespan context ended")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Intelligent PC recommendation system based on user requirements",
    version=settings.version,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# Configure CORS middleware for production deployment
allowed_origins = list(settings.allowed_origins) if settings.allowed_origins else []

# In production, use environment-defined origins or allow from same origin
if not settings.debug:
    # Production: Allow frontend domain and common patterns
    production_origins = [
        "https://yourdomain.com",  # Replace with actual domain
        "https://www.yourdomain.com",  # Replace with actual domain
        "https://app.yourdomain.com",  # Replace with actual domain
        "https://pc-recommendation-system-frontend.vercel.app",  # Vercel frontend
    ]
    # Only add if not already present
    for origin in production_origins:
        if origin not in allowed_origins and not origin.startswith("https://yourdomain"):
            allowed_origins.append(origin)
else:
    # Development: Allow all origins for development (remove wildcard in production)
    if '*' not in allowed_origins:
        allowed_origins.append('*')

# Add CORS middleware with mobile-friendly settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,  # Essential for mobile authentication
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",  # Additional headers that mobile browsers might send
        "X-Forwarded-For"
    ],
    expose_headers=["Authorization"],  # Allow frontend to read auth headers
    max_age=86400  # Cache preflight for 24 hours (mobile optimization)
)


# Centralized exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")

    # Convert errors to JSON serializable format
    serializable_errors = []
    for error in exc.errors():
        serializable_error = dict(error)
        # Convert any non-serializable values to strings
        for key, value in serializable_error.items():
            if key == 'ctx' and isinstance(value, dict):
                serializable_error[key] = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                                          for k, v in value.items()}
        serializable_errors.append(serializable_error)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": serializable_errors
            }
        }
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle general Pydantic validation errors"""
    logger.warning(f"Pydantic validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Data validation failed",
                "details": exc.errors()
            }
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors"""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    
    # Don't expose internal errors in production
    error_details = str(exc) if settings.debug else None
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": error_details
            }
        }
    )


# Router registration
# Health check (no auth required)
try:
    from app.api.routes import health
    app.include_router(health.router, prefix=settings.api_prefix, tags=["Health"])
    logger.info("Health router registered")
except Exception as e:
    logger.error(f"Failed to register health router: {e}")

# Authentication routes (public endpoints)
try:
    from app.api.routes import auth
    app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["Authentication"])
    logger.info("Auth router registered")
except Exception as e:
    logger.error(f"Failed to register auth router: {e}")

    

# Components routes
try:
    from app.api.routes import components
    app.include_router(components.router, prefix=settings.api_prefix, tags=["Components"])
    logger.info("Components router registered")
except Exception as e:
    logger.error(f"Failed to register components router: {e}")

# User management routes
try:
    from app.api.routes import users
    app.include_router(users.router, prefix=f"{settings.api_prefix}/users", tags=["User Management"])
    logger.info("Users router registered")
except Exception as e:
    logger.error(f"Failed to register users router: {e}")

# Recommendations routes
try:
    from app.api.routes import recommendations
    app.include_router(recommendations.router, prefix=settings.api_prefix, tags=["Recommendations"])
    logger.info("Recommendations router registered")
except Exception as e:
    logger.error(f"Failed to register recommendations router: {e}")

# Feedback routes
try:
    from app.api.routes import feedback
    app.include_router(feedback.router, prefix=settings.api_prefix, tags=["Feedback"])
    logger.info("Feedback router registered")
except Exception as e:
    logger.error(f"Failed to register feedback router: {e}")

# PC Catalog routes
try:
    from app.api.routes import pc_catalog
    app.include_router(pc_catalog.router, prefix=settings.api_prefix, tags=["PC Catalog"])
    logger.info("PC Catalog router registered")
except Exception as e:
    logger.error(f"Failed to register PC catalog router: {e}")

# Analytics routes
try:
    from app.api.routes import analytics
    app.include_router(analytics.router, prefix=f"{settings.api_prefix}/analytics", tags=["Analytics"])  # POST /api/v1/analytics/events
    logger.info("Analytics router registered")
except Exception as e:
    logger.error(f"Failed to register analytics router: {e}")

# AI routes
try:
    from app.api.routes import ai
    app.include_router(ai.router, prefix=f"{settings.api_prefix}/ai", tags=["AI"])  # POST /api/v1/ai/chat
    logger.info("AI router registered")
except Exception as e:
    logger.error(f"Failed to register AI router: {e}")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )
