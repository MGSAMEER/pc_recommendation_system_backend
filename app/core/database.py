from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Database:
    client: AsyncIOMotorClient = None
    database = None


db = Database()


async def connect_to_mongo():
    """Connect to MongoDB with enhanced connection pooling and monitoring"""
    try:
        # Enhanced connection pooling configuration for concurrent users
        client_kwargs = {
            "maxPoolSize": 100,  # Increased for concurrent users
            "minPoolSize": 10,   # Maintain minimum connections
            "maxIdleTimeMS": 45000,  # Increased idle time
            "serverSelectionTimeoutMS": 5000,  # Faster server selection
            "connectTimeoutMS": 5000,  # Faster connection timeout
            "socketTimeoutMS": 30000,  # Reasonable socket timeout
            "waitQueueTimeoutMS": 2000,  # Shorter wait queue timeout
            "heartbeatFrequencyMS": 15000,  # Balanced heartbeat
            "retryWrites": True,
            "retryReads": True,
            "maxConnecting": 5,  # Limit concurrent connection attempts
            "appname": "PC_Recommendation_System",  # Application identifier
        }

        # SSL configuration for production
        if settings.mongodb_uri.startswith('mongodb+srv://'):
            client_kwargs.update({
                "tls": True,
                "tlsAllowInvalidCertificates": False,
                "tlsAllowInvalidHostnames": False,
            })

        db.client = AsyncIOMotorClient(settings.mongodb_uri, **client_kwargs)
        db.database = db.client[settings.database_name]

        # Test the connection with timeout
        await asyncio.wait_for(db.client.admin.command('ping'), timeout=5.0)
        logger.info(f"Connected to MongoDB: {settings.database_name}")

        # Log enhanced connection pool stats
        server_info = await db.client.server_info()
        logger.info(f"MongoDB version: {server_info.get('version', 'unknown')}")

        # Log connection pool configuration
        pool_info = {
            "max_pool_size": client_kwargs['maxPoolSize'],
            "min_pool_size": client_kwargs['minPoolSize'],
            "current_connections": len(db.client._topology._servers) if hasattr(db.client, '_topology') else 'unknown'
        }
        logger.info(f"Connection pool configured: {pool_info}")

        # Setup connection monitoring
        await setup_connection_monitoring()

    except asyncio.TimeoutError:
        logger.error("MongoDB connection timeout")
        raise
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def setup_connection_monitoring():
    """Setup connection pool monitoring"""
    try:
        # Create monitoring collection if it doesn't exist
        monitoring_collection = db.database.connection_monitoring

        # Log initial connection stats
        initial_stats = {
            "timestamp": datetime.utcnow(),
            "event": "connection_established",
            "pool_size": getattr(db.client, '_pool_size', 'unknown'),
            "active_connections": getattr(db.client, '_active_connections', 'unknown')
        }

        await monitoring_collection.insert_one(initial_stats)
        logger.debug("Connection monitoring initialized")

    except Exception as e:
        logger.warning(f"Failed to setup connection monitoring: {e}")


async def get_database_health() -> Dict[str, Any]:
    """Get database connection health status"""
    try:
        if not db.client or not db.database:
            return {"status": "disconnected", "error": "No database connection"}

        # Test connection
        start_time = time.time()
        await db.client.admin.command('ping')
        response_time = time.time() - start_time

        # Get server status
        server_status = await db.client.admin.command('serverStatus')

        health_info = {
            "status": "healthy",
            "response_time_ms": round(response_time * 1000, 2),
            "mongodb_version": server_status.get('version', 'unknown'),
            "connections": {
                "current": server_status.get('connections', {}).get('current', 0),
                "available": server_status.get('connections', {}).get('available', 0),
                "total_created": server_status.get('connections', {}).get('totalCreated', 0)
            },
            "memory": {
                "resident_mb": server_status.get('mem', {}).get('resident', 0),
                "virtual_mb": server_status.get('mem', {}).get('virtual', 0)
            }
        }

        return health_info

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def close_mongo_connection():
    """Close MongoDB connection"""
    try:
        if db.client:
            db.client.close()
            logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")


async def get_database():
    """Get database instance"""
    return db.database
