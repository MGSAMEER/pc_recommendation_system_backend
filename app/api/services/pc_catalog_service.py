"""
PC Catalog service for managing PC catalog data
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId

from app.core.database import get_database
from app.api.models.pc_catalog import PCCatalogCreate, PCCatalogUpdate, PCCatalogInDB


logger = logging.getLogger(__name__)


class PCCatalogService:
    """Service for managing PC catalog operations"""

    def __init__(self):
        self.collection_name = "pc_catalog"

    async def initialize(self):
        """Initialize database collection and indexes"""
        db = await get_database()
        collection = db[self.collection_name]

        # Create indexes for better query performance
        await collection.create_index("brand")
        await collection.create_index("primary_use")
        await collection.create_index("performance_level")
        await collection.create_index("price")
        await collection.create_index([("pc_name", 1), ("brand", 1)])

        logger.info("PC catalog collection initialized with indexes")

    async def create_pc(self, pc_data: PCCatalogCreate) -> PCCatalogInDB:
        """Create a new PC in the catalog"""
        db = await get_database()
        collection = db[self.collection_name]

        pc_doc = {
            **pc_data.dict(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = await collection.insert_one(pc_doc)
        pc_doc["_id"] = result.inserted_id

        return PCCatalogInDB(**pc_doc)

    async def get_pc_by_id(self, pc_id: str) -> Optional[PCCatalogInDB]:
        """Get PC by ID"""
        db = await get_database()
        collection = db[self.collection_name]

        try:
            pc_doc = await collection.find_one({"_id": ObjectId(pc_id)})
            if pc_doc:
                pc_data = dict(pc_doc)
                if "_id" in pc_data:
                    pc_data["id"] = str(pc_data["_id"])
                    del pc_data["_id"]
                return PCCatalogInDB(**pc_data)
        except:
            pass
        return None

    async def get_pcs(
        self,
        brand: Optional[str] = None,
        primary_use: Optional[str] = None,
        performance_level: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[PCCatalogInDB]:
        """Get PCs with optional filtering"""
        db = await get_database()
        collection = db[self.collection_name]

        # Build query
        query = {}
        if brand:
            query["brand"] = brand
        if primary_use:
            query["primary_use"] = primary_use
        if performance_level:
            query["performance_level"] = performance_level
        if min_price is not None or max_price is not None:
            price_query = {}
            if min_price is not None:
                price_query["$gte"] = min_price
            if max_price is not None:
                price_query["$lte"] = max_price
            query["price"] = price_query

        cursor = collection.find(query).skip(skip).limit(limit)
        pcs = await cursor.to_list(length=None)

        # Convert ObjectId to string for each PC
        result = []
        for pc in pcs:
            pc_data = dict(pc)
            if "_id" in pc_data:
                pc_data["id"] = str(pc_data["_id"])
                del pc_data["_id"]
            result.append(PCCatalogInDB(**pc_data))
        return result

    async def update_pc(self, pc_id: str, update_data: PCCatalogUpdate) -> Optional[PCCatalogInDB]:
        """Update PC information"""
        db = await get_database()
        collection = db[self.collection_name]

        update_dict = update_data.dict(exclude_unset=True)
        if update_dict:
            update_dict["updated_at"] = datetime.utcnow()

            try:
                result = await collection.update_one(
                    {"_id": ObjectId(pc_id)},
                    {"$set": update_dict}
                )

                if result.modified_count > 0:
                    return await self.get_pc_by_id(pc_id)
            except:
                pass
        return None

    async def delete_pc(self, pc_id: str) -> bool:
        """Delete PC from catalog"""
        db = await get_database()
        collection = db[self.collection_name]

        try:
            result = await collection.delete_one({"_id": ObjectId(pc_id)})
            return result.deleted_count > 0
        except:
            return False

    async def get_catalog_stats(self) -> Dict[str, Any]:
        """Get catalog statistics"""
        db = await get_database()
        collection = db[self.collection_name]

        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_pcs": {"$sum": 1},
                    "avg_price": {"$avg": "$price"},
                    "min_price": {"$min": "$price"},
                    "max_price": {"$max": "$price"},
                    "brands": {"$addToSet": "$brand"},
                    "uses": {"$addToSet": "$primary_use"},
                    "performance_levels": {"$addToSet": "$performance_level"}
                }
            }
        ]

        result = await collection.aggregate(pipeline).to_list(length=1)
        if result:
            stats = result[0]
            stats["brands_count"] = len(stats["brands"])
            stats["uses_count"] = len(stats["uses"])
            stats["performance_levels_count"] = len(stats["performance_levels"])
            return stats

        return {
            "total_pcs": 0,
            "avg_price": 0,
            "min_price": 0,
            "max_price": 0,
            "brands_count": 0,
            "uses_count": 0,
            "performance_levels_count": 0
        }

    async def search_pcs(self, query: str, limit: int = 20) -> List[PCCatalogInDB]:
        """Search PCs by name or brand"""
        db = await get_database()
        collection = db[self.collection_name]

        # Simple text search on pc_name and brand
        search_regex = {"$regex": query, "$options": "i"}
        search_query = {
            "$or": [
                {"pc_name": search_regex},
                {"brand": search_regex}
            ]
        }

        cursor = collection.find(search_query).limit(limit)
        pcs = await cursor.to_list(length=None)

        # Convert ObjectId to string for each PC
        result = []
        for pc in pcs:
            pc_data = dict(pc)
            if "_id" in pc_data:
                pc_data["id"] = str(pc_data["_id"])
                del pc_data["_id"]
            result.append(PCCatalogInDB(**pc_data))
        return result

    async def get_pcs_by_price_range(self, min_price: float, max_price: float) -> List[PCCatalogInDB]:
        """Get PCs within price range"""
        db = await get_database()
        collection = db[self.collection_name]

        query = {"price": {"$gte": min_price, "$lte": max_price}}
        cursor = collection.find(query)
        pcs = await cursor.to_list(length=None)

        # Convert ObjectId to string for each PC
        result = []
        for pc in pcs:
            pc_data = dict(pc)
            if "_id" in pc_data:
                pc_data["id"] = str(pc_data["_id"])
                del pc_data["_id"]
            result.append(PCCatalogInDB(**pc_data))
        return result


# Global PC catalog service instance
pc_catalog_service = PCCatalogService()