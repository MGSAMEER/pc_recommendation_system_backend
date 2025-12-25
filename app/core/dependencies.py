"""
FastAPI dependencies for dependency injection
"""
from app.core.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase


async def get_db() -> AsyncIOMotorDatabase:
    """Dependency to get database instance for FastAPI injection"""
    from app.core.database import get_database
    db_instance = await get_database()
    # Note: Database objects don't support truth value testing, so we just try to use it
    # If it's None, it will fail naturally when we try to use it
    return db_instance

