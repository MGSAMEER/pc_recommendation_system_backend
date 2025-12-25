#!/usr/bin/env python3
"""
Database seeding script for PC Recommendation System
"""
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_database():
    """Seed the database with initial data"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(settings.mongodb_url)
        db = client[settings.database_name]

        logger.info(f"Connected to database: {settings.database_name}")

        # Clear existing data (optional - remove in production)
        await db.components.delete_many({})
        await db.pc_configurations.delete_many({})

        logger.info("Cleared existing data")

        # Load component data
        await load_basic_components(db)

        # Create sample PC configurations
        await create_sample_configurations(db)

        # Create indexes
        await create_indexes(db)

        logger.info("Database seeding completed successfully!")

    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        raise
    finally:
        client.close()


async def load_basic_components(db):
    """Load basic component data"""
    def make_id(t, brand, model):
        return f"{t}_{brand}_{model}".lower().replace(" ", "_")

    components = [
        # CPUs
        {
            "id": make_id("cpu", "AMD", "5600X"),
            "type": "cpu",
            "name": "AMD Ryzen 5 5600X",
            "brand": "AMD",
            "model": "5600X",
            "price": {"amount": 199.99, "currency": "USD"},
            "specifications": {"cores": 6, "threads": 12, "socket": "AM4"},
            "compatibility": {"socket": "AM4"},
            "performance_scores": {"gaming_score": 85, "productivity_score": 80, "creative_score": 75, "overall_score": 82},
            "availability": {"in_stock": True, "stock_quantity": 50}
        },
        {
            "id": make_id("cpu", "Intel", "i5-12600K"),
            "type": "cpu",
            "name": "Intel Core i5-12600K",
            "brand": "Intel",
            "model": "i5-12600K",
            "price": {"amount": 229.99, "currency": "USD"},
            "specifications": {"cores": 10, "threads": 16, "socket": "LGA1700"},
            "compatibility": {"socket": "LGA1700"},
            "performance_scores": {"gaming_score": 88, "productivity_score": 85, "creative_score": 82, "overall_score": 86},
            "availability": {"in_stock": True, "stock_quantity": 30}
        },

        # GPUs
        {
            "id": make_id("gpu", "NVIDIA", "RTX 4060"),
            "type": "gpu",
            "name": "NVIDIA GeForce RTX 4060",
            "brand": "NVIDIA",
            "model": "RTX 4060",
            "price": {"amount": 299.99, "currency": "USD"},
            "specifications": {"vram": 8, "memory_type": "GDDR6"},
            "performance_scores": {"gaming_score": 85, "productivity_score": 70, "creative_score": 75, "overall_score": 78},
            "availability": {"in_stock": True, "stock_quantity": 40}
        },
        {
            "id": make_id("gpu", "AMD", "RX 7600"),
            "type": "gpu",
            "name": "AMD Radeon RX 7600",
            "brand": "AMD",
            "model": "RX 7600",
            "price": {"amount": 269.99, "currency": "USD"},
            "specifications": {"vram": 8, "memory_type": "GDDR6"},
            "performance_scores": {"gaming_score": 82, "productivity_score": 68, "creative_score": 72, "overall_score": 75},
            "availability": {"in_stock": True, "stock_quantity": 35}
        },

        # RAM
        {
            "id": make_id("ram", "Corsair", "Vengeance LPX"),
            "type": "ram",
            "name": "Corsair Vengeance LPX 16GB",
            "brand": "Corsair",
            "model": "Vengeance LPX",
            "price": {"amount": 79.99, "currency": "USD"},
            "specifications": {"capacity": 16, "speed": 3200, "type": "DDR4"},
            "performance_scores": {"gaming_score": 75, "productivity_score": 80, "creative_score": 78, "overall_score": 77},
            "availability": {"in_stock": True, "stock_quantity": 100}
        },

        # Storage
        {
            "id": make_id("storage", "Samsung", "970 EVO"),
            "type": "storage",
            "name": "Samsung 970 EVO 1TB",
            "brand": "Samsung",
            "model": "970 EVO",
            "price": {"amount": 89.99, "currency": "USD"},
            "specifications": {"capacity": 1000, "type": "SSD", "interface": "NVMe"},
            "performance_scores": {"gaming_score": 85, "productivity_score": 90, "creative_score": 88, "overall_score": 87},
            "availability": {"in_stock": True, "stock_quantity": 75}
        },

        # Motherboards
        {
            "id": make_id("motherboard", "MSI", "B450 Tomahawk"),
            "type": "motherboard",
            "name": "MSI B450 Tomahawk",
            "brand": "MSI",
            "model": "B450 Tomahawk",
            "price": {"amount": 119.99, "currency": "USD"},
            "specifications": {"socket": "AM4", "form_factor": "ATX"},
            "compatibility": {"supported_sockets": ["AM4"], "supported_ram_types": ["DDR4"]},
            "performance_scores": {"gaming_score": 70, "productivity_score": 75, "creative_score": 72, "overall_score": 73},
            "availability": {"in_stock": True, "stock_quantity": 25}
        },

        # Cases
        {
            "id": make_id("case", "Fractal Design", "Meshify C"),
            "type": "case",
            "name": "Fractal Design Meshify C",
            "brand": "Fractal Design",
            "model": "Meshify C",
            "price": {"amount": 99.99, "currency": "USD"},
            "specifications": {"form_factor": "Mid Tower"},
            "compatibility": {"form_factor_support": ["ATX", "Micro-ATX", "Mini-ITX"]},
            "performance_scores": {"gaming_score": 75, "productivity_score": 70, "creative_score": 68, "overall_score": 72},
            "availability": {"in_stock": True, "stock_quantity": 30}
        },

        # PSUs
        {
            "id": make_id("psu", "Corsair", "RM650x"),
            "type": "psu",
            "name": "Corsair RM650x",
            "brand": "Corsair",
            "model": "RM650x",
            "price": {"amount": 129.99, "currency": "USD"},
            "specifications": {"wattage": 650, "efficiency_rating": "80+ Gold", "modular": True},
            "performance_scores": {"gaming_score": 80, "productivity_score": 78, "creative_score": 76, "overall_score": 79},
            "availability": {"in_stock": True, "stock_quantity": 45}
        }
    ]

    result = await db.components.insert_many(components)
    logger.info(f"Loaded {len(result.inserted_ids)} basic components")


async def create_sample_configurations(db):
    """Create sample PC configurations"""
    # Get component IDs
    components = await db.components.find().to_list(length=None)

    # Create component lookup
    component_lookup = {}
    for comp in components:
        key = f"{comp['type']}_{comp['brand']}_{comp['model']}"
        component_lookup[key] = str(comp['_id'])

    configurations = [
        {
            "name": "Gaming Build - Mid Range",
            "description": "Balanced gaming PC for 1080p/1440p gaming",
            "components": [
                {
                    "component_id": component_lookup.get("cpu_AMD_5600X"),
                    "type": "cpu",
                    "quantity": 1
                },
                {
                    "component_id": component_lookup.get("gpu_NVIDIA_RTX 4060"),
                    "type": "gpu",
                    "quantity": 1
                },
                {
                    "component_id": component_lookup.get("ram_Corsair_Vengeance LPX"),
                    "type": "ram",
                    "quantity": 1
                },
                {
                    "component_id": component_lookup.get("storage_Samsung_970 EVO"),
                    "type": "storage",
                    "quantity": 1
                },
                {
                    "component_id": component_lookup.get("motherboard_MSI_B450 Tomahawk"),
                    "type": "motherboard",
                    "quantity": 1
                },
                {
                    "component_id": component_lookup.get("case_Fractal Design_Meshify C"),
                    "type": "case",
                    "quantity": 1
                },
                {
                    "component_id": component_lookup.get("psu_Corsair_RM650x"),
                    "type": "psu",
                    "quantity": 1
                }
            ],
            "total_price": 1119.92,
            "performance_profile": {
                "gaming_performance": 85,
                "productivity_performance": 78,
                "creative_performance": 75,
                "overall_performance": 80
            },
            "suitability_scores": {
                "gaming": 88,
                "office": 65,
                "creative": 70,
                "programming": 72,
                "general": 75
            },
            "source": "curated"
        }
    ]

    # Only create configurations if we have the required components
    valid_configs = [config for config in configurations if all(
        comp['component_id'] for comp in config['components']
    )]

    if valid_configs:
        result = await db.pc_configurations.insert_many(valid_configs)
        logger.info(f"Created {len(result.inserted_ids)} sample PC configurations")
    else:
        logger.warning("Could not create sample configurations - missing component references")


async def create_indexes(db):
    """Create database indexes for performance"""
    # Component indexes
    await db.components.create_index("type")
    await db.components.create_index("brand")
    await db.components.create_index([("price.amount", 1)])
    await db.components.create_index([("performance_scores.overall_score", -1)])
    await db.components.create_index([("availability.in_stock", 1)])

    # PC Configuration indexes
    await db.pc_configurations.create_index([("total_price", 1)])
    await db.pc_configurations.create_index([("performance_profile.overall_performance", -1)])
    await db.pc_configurations.create_index("suitability_scores.gaming")
    await db.pc_configurations.create_index("source")

    logger.info("Database indexes created successfully")


async def main():
    """Main entry point"""
    logger.info("Starting database seeding...")
    await seed_database()


if __name__ == "__main__":
    asyncio.run(main())
