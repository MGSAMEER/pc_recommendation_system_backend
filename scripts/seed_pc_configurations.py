#!/usr/bin/env python3
"""
Seed PC configurations with dummy data for testing
"""
import asyncio
import logging
from app.core.database import connect_to_mongo, close_mongo_connection, get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_pc_configurations():
    """Seed pc_configurations collection with dummy data"""
    try:
        await connect_to_mongo()
        db = await get_database()
        logger.info("Connected to database")

        # Clear existing
        await db.pc_configurations.delete_many({})
        logger.info("Cleared existing PC configurations")

        # Dummy configurations with USD prices
        configs = [
            {
                "id": "config1",
                "name": "Budget Office PC",
                "total_price": 400,
                "suitability_scores": {
                    "office": 85,
                    "gaming": 30,
                    "creative": 40,
                    "programming": 50,
                    "general": 70
                },
                "performance_profile": {
                    "overall_performance": 45,
                    "cpu_performance": 40,
                    "gpu_performance": 30,
                    "ram_performance": 50,
                    "storage_performance": 60
                },
                "components": [],
                "purpose": "office",
                "performance_level": "standard"
            },
            {
                "id": "config2",
                "name": "Gaming PC",
                "total_price": 800,
                "suitability_scores": {
                    "office": 40,
                    "gaming": 90,
                    "creative": 60,
                    "programming": 70,
                    "general": 50
                },
                "performance_profile": {
                    "overall_performance": 75,
                    "cpu_performance": 70,
                    "gpu_performance": 85,
                    "ram_performance": 70,
                    "storage_performance": 65
                },
                "components": [],
                "purpose": "gaming",
                "performance_level": "high"
            },
            {
                "id": "config3",
                "name": "Creative Workstation",
                "total_price": 1000,
                "suitability_scores": {
                    "office": 50,
                    "gaming": 70,
                    "creative": 95,
                    "programming": 80,
                    "general": 60
                },
                "performance_profile": {
                    "overall_performance": 85,
                    "cpu_performance": 80,
                    "gpu_performance": 90,
                    "ram_performance": 85,
                    "storage_performance": 75
                },
                "components": [],
                "purpose": "creative",
                "performance_level": "high"
            },
            {
                "id": "config4",
                "name": "Programming Laptop",
                "total_price": 600,
                "suitability_scores": {
                    "office": 60,
                    "gaming": 50,
                    "creative": 70,
                    "programming": 90,
                    "general": 75
                },
                "performance_profile": {
                    "overall_performance": 65,
                    "cpu_performance": 75,
                    "gpu_performance": 50,
                    "ram_performance": 80,
                    "storage_performance": 70
                },
                "components": [],
                "purpose": "programming",
                "performance_level": "standard"
            },
            {
                "id": "config5",
                "name": "General Use PC",
                "total_price": 500,
                "suitability_scores": {
                    "office": 75,
                    "gaming": 55,
                    "creative": 65,
                    "programming": 70,
                    "general": 85
                },
                "performance_profile": {
                    "overall_performance": 60,
                    "cpu_performance": 60,
                    "gpu_performance": 55,
                    "ram_performance": 65,
                    "storage_performance": 70
                },
                "components": [],
                "purpose": "general",
                "performance_level": "standard"
            },
            {
                "id": "config6",
                "name": "High-End Gaming PC",
                "total_price": 1500,
                "suitability_scores": {
                    "office": 35,
                    "gaming": 95,
                    "creative": 75,
                    "programming": 65,
                    "general": 45
                },
                "performance_profile": {
                    "overall_performance": 90,
                    "cpu_performance": 85,
                    "gpu_performance": 95,
                    "ram_performance": 90,
                    "storage_performance": 80
                },
                "components": [],
                "purpose": "gaming",
                "performance_level": "professional"
            },
            {
                "id": "config7",
                "name": "Basic Office PC",
                "total_price": 300,
                "suitability_scores": {
                    "office": 90,
                    "gaming": 25,
                    "creative": 30,
                    "programming": 40,
                    "general": 80
                },
                "performance_profile": {
                    "overall_performance": 35,
                    "cpu_performance": 35,
                    "gpu_performance": 25,
                    "ram_performance": 40,
                    "storage_performance": 50
                },
                "components": [],
                "purpose": "office",
                "performance_level": "basic"
            },
            {
                "id": "config8",
                "name": "Professional Workstation",
                "total_price": 2000,
                "suitability_scores": {
                    "office": 45,
                    "gaming": 80,
                    "creative": 90,
                    "programming": 85,
                    "general": 55
                },
                "performance_profile": {
                    "overall_performance": 95,
                    "cpu_performance": 95,
                    "gpu_performance": 90,
                    "ram_performance": 95,
                    "storage_performance": 85
                },
                "components": [],
                "purpose": "creative",
                "performance_level": "professional"
            }
        ]

        result = await db.pc_configurations.insert_many(configs)
        logger.info(f"Inserted {len(result.inserted_ids)} PC configurations")

    except Exception as e:
        logger.error(f"Error seeding PC configurations: {e}")
    finally:
        await close_mongo_connection()
        logger.info("Database connection closed")

if __name__ == "__main__":
    asyncio.run(seed_pc_configurations())