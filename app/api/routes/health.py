"""
Health check API routes
"""
import logging
import time
from datetime import datetime
from fastapi import APIRouter, status, HTTPException
from typing import Dict, Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns health status of the application and dependencies"
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint with system metrics
    """
    start_time = time.time()
    health_status = "healthy"
    errors = []

    try:
        # Basic health check
        response_data: Dict[str, Any] = {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.version,
            "service": settings.app_name,
            "environment": "development" if settings.debug else "production"
        }

        # System metrics (optional, graceful failure if psutil not available)
        try:
            import psutil
            import os
            
            memory = psutil.virtual_memory()
            process = psutil.Process(os.getpid())
            app_memory_mb = process.memory_info().rss / 1024 / 1024
            
            response_data["system"] = {
                "memory_usage_percent": round(memory.percent, 1),
                "memory_available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
                "app_memory_mb": round(app_memory_mb, 1)
            }
        except ImportError:
            logger.debug("psutil not available, skipping system metrics")
        except Exception as sys_error:
            logger.warning(f"System metrics collection failed: {sys_error}")

        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        response_data["response_time_ms"] = round(response_time, 2)

        # Update status based on errors
        if errors:
            response_data["errors"] = errors
            if health_status == "healthy":
                health_status = "degraded"
        
        response_data["status"] = health_status

        return response_data

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        response_time = (time.time() - start_time) * 1000
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.version,
            "service": settings.app_name,
            "response_time_ms": round(response_time, 2),
            "error": str(e) if settings.debug else "Internal error"
        }


@router.get(
    "/health/database",
    status_code=status.HTTP_200_OK,
    summary="Database health check",
    description="Tests database connectivity and basic operations"
)
async def database_health() -> Dict[str, Any]:
    """
    Database-specific health check endpoint
    """
    try:
        from app.core.database import get_database, get_database_health
        db = await get_database()

        # Test connection (will raise exception if not connected)
        await db.command('ping')

        # Get enhanced health info
        health_info = await get_database_health()

        # Get basic stats
        collections = await db.list_collection_names()
        components_count = 0
        recommendations_count = 0
        users_count = 0

        try:
            components_count = await db.components.count_documents({})
            recommendations_count = await db.recommendations.count_documents({})
            users_count = await db.users.count_documents({})
        except Exception:
            pass  # Collections might not exist yet

        return {
            "database": "connected",
            "status": health_info.get("status", "unknown"),
            "response_time_ms": health_info.get("response_time_ms"),
            "mongodb_version": health_info.get("mongodb_version"),
            "collections": collections,
            "stats": {
                "components": components_count,
                "recommendations": recommendations_count,
                "users": users_count
            },
            "connections": health_info.get("connections", {}),
            "memory": health_info.get("memory", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "database": "unavailable",
            "error": str(e) if settings.debug else "Connection failed"
        }


@router.get(
    "/health/cache",
    status_code=status.HTTP_200_OK,
    summary="Cache health check",
    description="Tests cache system health and performance"
)
async def cache_health() -> Dict[str, Any]:
    """
    Cache system health check endpoint
    """
    try:
        from app.core.cache import cache
        health_info = await cache.health_check()

        return {
            "status": "healthy" if health_info["redis_cache"]["healthy"] or health_info["memory_cache"]["healthy"] else "degraded",
            "memory_cache": health_info["memory_cache"],
            "redis_cache": health_info["redis_cache"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Application metrics",
    description="Returns application performance metrics and statistics"
)
async def application_metrics() -> Dict[str, Any]:
    """
    Application metrics endpoint for monitoring
    """
    try:
        from app.core.database import get_database
        from app.core.cache import cache

        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - start_time if 'start_time' in globals() else 0,
        }

        # Database metrics
        try:
            db = await get_database()
            server_status = await db.command('serverStatus')

            metrics["database"] = {
                "connections_current": server_status.get('connections', {}).get('current', 0),
                "connections_available": server_status.get('connections', {}).get('available', 0),
                "opcounters": server_status.get('opcounters', {}),
                "mem_resident_mb": server_status.get('mem', {}).get('resident', 0),
                "mem_virtual_mb": server_status.get('mem', {}).get('virtual', 0)
            }
        except Exception as e:
            metrics["database"] = {"error": str(e)}

        # Cache metrics
        try:
            cache_health = await cache.health_check()
            metrics["cache"] = cache_health
        except Exception as e:
            metrics["cache"] = {"error": str(e)}

        # System metrics
        try:
            import psutil
            import os

            memory = psutil.virtual_memory()
            process = psutil.Process(os.getpid())

            metrics["system"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / 1024 / 1024 / 1024, 2),
                "memory_available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
                "app_memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
                "app_cpu_percent": process.cpu_percent(interval=0.1)
            }
        except ImportError:
            metrics["system"] = {"note": "psutil not available"}
        except Exception as e:
            metrics["system"] = {"error": str(e)}

        return metrics

    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


# Store application start time for uptime calculation
start_time = time.time()
