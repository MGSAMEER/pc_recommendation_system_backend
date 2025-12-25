#!/usr/bin/env python3
"""
Simple script to seed PC configurations with USD prices
"""
import asyncio
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from motor.motor_asyncio import AsyncIOMotorClient

async def seed_data():
    # Connect to MongoDB (use the same URL as the backend)
    client = AsyncIOMotorClient("mongodb://mongodb:27017")
    db = client.pc_recommendation_db

    # Clear existing data
    await db.pc_configurations.delete_many({})
    print("Cleared existing PC configurations")

    # Seed data with USD prices
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
    print(f"Inserted {len(result.inserted_ids)} PC configurations")

    # Verify the data
    count = await db.pc_configurations.count_documents({})
    print(f"Total documents in collection: {count}")

    # Show sample
    sample = await db.pc_configurations.find().limit(1).to_list(length=None)
    if sample:
        print(f"Sample document: {sample[0]['name']} - ${sample[0]['total_price']}")

    client.close()

if __name__ == "__main__":
    asyncio.run(seed_data())