"""
PC Catalog models for PC Recommendation System
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PCSpecs(BaseModel):
    """PC specifications model"""
    cpu: str
    gpu: str
    ram_gb: int
    storage: str


class PCCatalogBase(BaseModel):
    """Base PC catalog model"""
    pc_name: str
    brand: str
    primary_use: str
    performance_level: str
    price: float
    specs: PCSpecs


class PCCatalogCreate(PCCatalogBase):
    """PC catalog creation model"""
    pass


class PCCatalogUpdate(BaseModel):
    """PC catalog update model"""
    pc_name: Optional[str] = None
    brand: Optional[str] = None
    primary_use: Optional[str] = None
    performance_level: Optional[str] = None
    price: Optional[float] = None
    specs: Optional[PCSpecs] = None


class PCCatalogInDB(PCCatalogBase):
    """PC catalog database model"""
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "validate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }

    @classmethod
    def from_mongo(cls, data: dict):
        """Create instance from MongoDB document"""
        # Convert ObjectId to string and prepare data
        clean_data = {}
        for key, value in data.items():
            if key == "_id":
                clean_data["id"] = str(value)
            else:
                clean_data[key] = value
        return cls(**clean_data)


class PCCatalog(PCCatalogBase):
    """PC catalog response model"""
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }