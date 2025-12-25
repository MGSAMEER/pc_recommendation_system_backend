#!/usr/bin/env python3
"""
Seed PC catalog with sample data
"""
import asyncio
import logging
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api.services.pc_catalog_service import pc_catalog_service
from app.api.models.pc_catalog import PCCatalogCreate, PCSpecs


# Sample PC catalog data
SAMPLE_PC_DATA = [
    {
        "pc_name": "Dell Inspiron 15",
        "brand": "Dell",
        "primary_use": "Office Work",
        "performance_level": "Standard",
        "price": 42000,
        "specs": {
            "cpu": "Intel i3 11th Gen",
            "gpu": "Integrated",
            "ram_gb": 8,
            "storage": "512GB SSD"
        }
    },
    {
        "pc_name": "HP Pavilion 14",
        "brand": "HP",
        "primary_use": "Office Work",
        "performance_level": "Standard",
        "price": 52000,
        "specs": {
            "cpu": "Ryzen 5 5500U",
            "gpu": "Integrated Radeon",
            "ram_gb": 16,
            "storage": "512GB SSD"
        }
    },
    {
        "pc_name": "Lenovo ThinkPad E14",
        "brand": "Lenovo",
        "primary_use": "Office Work",
        "performance_level": "High",
        "price": 65000,
        "specs": {
            "cpu": "Intel i5 12th Gen",
            "gpu": "Integrated",
            "ram_gb": 16,
            "storage": "1TB SSD"
        }
    },
    {
        "pc_name": "ASUS VivoBook 15",
        "brand": "ASUS",
        "primary_use": "Student",
        "performance_level": "Standard",
        "price": 48000,
        "specs": {
            "cpu": "Intel i5 11th Gen",
            "gpu": "Integrated",
            "ram_gb": 8,
            "storage": "512GB SSD"
        }
    },
    {
        "pc_name": "Acer Aspire 7",
        "brand": "Acer",
        "primary_use": "Coding",
        "performance_level": "High",
        "price": 58000,
        "specs": {
            "cpu": "Ryzen 5 5500U",
            "gpu": "GTX 1650",
            "ram_gb": 16,
            "storage": "512GB SSD"
        }
    },
    {
        "pc_name": "Lenovo IdeaPad Gaming 3",
        "brand": "Lenovo",
        "primary_use": "Gaming",
        "performance_level": "High",
        "price": 72000,
        "specs": {
            "cpu": "Ryzen 5 5600H",
            "gpu": "GTX 1650",
            "ram_gb": 16,
            "storage": "512GB SSD"
        }
    },
    {
        "pc_name": "ASUS TUF F15",
        "brand": "ASUS",
        "primary_use": "Gaming",
        "performance_level": "High",
        "price": 88000,
        "specs": {
            "cpu": "Intel i7 11800H",
            "gpu": "RTX 3050",
            "ram_gb": 16,
            "storage": "1TB SSD"
        }
    },
    {
        "pc_name": "MSI Creator Z16",
        "brand": "MSI",
        "primary_use": "Video Editing",
        "performance_level": "Very High",
        "price": 145000,
        "specs": {
            "cpu": "Intel i9 11900H",
            "gpu": "RTX 3060",
            "ram_gb": 32,
            "storage": "1TB SSD"
        }
    },
    {
        "pc_name": "Apple MacBook Air M1",
        "brand": "Apple",
        "primary_use": "Office Work",
        "performance_level": "High",
        "price": 90000,
        "specs": {
            "cpu": "Apple M1",
            "gpu": "Integrated",
            "ram_gb": 8,
            "storage": "256GB SSD"
        }
    },
    {
        "pc_name": "Custom Budget PC",
        "brand": "Custom",
        "primary_use": "Office Work",
        "performance_level": "Standard",
        "price": 35000,
        "specs": {
            "cpu": "Intel i3 10th Gen",
            "gpu": "Integrated",
            "ram_gb": 8,
            "storage": "256GB SSD"
        }
    }
]


async def seed_pc_catalog():
    """Seed the PC catalog with sample data"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Connect to database
        await connect_to_mongo()
        logger.info("Connected to database")

        # Initialize PC catalog service
        await pc_catalog_service.initialize()
        logger.info("PC catalog service initialized")

        # Check if data already exists
        existing_pcs = await pc_catalog_service.get_pcs(limit=1)
        if existing_pcs:
            logger.info("PC catalog already has data, skipping seed")
            return

        # Insert sample data
        inserted_count = 0
        for pc_data in SAMPLE_PC_DATA:
            try:
                # Create PC catalog entry
                specs = PCSpecs(**pc_data["specs"])
                pc_create = PCCatalogCreate(
                    pc_name=pc_data["pc_name"],
                    brand=pc_data["brand"],
                    primary_use=pc_data["primary_use"],
                    performance_level=pc_data["performance_level"],
                    price=pc_data["price"],
                    specs=specs
                )

                # Insert into database
                pc = await pc_catalog_service.create_pc(pc_create)
                inserted_count += 1
                logger.info(f"Inserted PC: {pc.pc_name}")

            except Exception as e:
                logger.error(f"Failed to insert PC {pc_data['pc_name']}: {e}")

        logger.info(f"Successfully seeded {inserted_count} PCs into catalog")

        # Get catalog stats
        stats = await pc_catalog_service.get_catalog_stats()
        logger.info(f"Catalog stats: {stats}")

    except Exception as e:
        logger.error(f"Error seeding PC catalog: {e}")
        raise
    finally:
        await close_mongo_connection()
        logger.info("Database connection closed")


if __name__ == "__main__":
    asyncio.run(seed_pc_catalog())