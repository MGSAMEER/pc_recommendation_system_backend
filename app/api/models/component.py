from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ComponentType(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    MOTHERBOARD = "motherboard"
    RAM = "ram"
    STORAGE = "storage"
    CASE = "case"
    PSU = "psu"
    COOLER = "cooler"


class Price(BaseModel):
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD")
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class PerformanceScores(BaseModel):
    gaming_score: float = Field(..., ge=0, le=100)
    productivity_score: float = Field(..., ge=0, le=100)
    creative_score: float = Field(..., ge=0, le=100)
    overall_score: float = Field(..., ge=0, le=100)


class Retailer(BaseModel):
    name: str
    url: str
    price: float = Field(..., gt=0)


class Availability(BaseModel):
    in_stock: bool = Field(default=True)
    stock_quantity: Optional[int] = Field(None, ge=0)
    estimated_delivery: Optional[str] = None
    retailers: List[Retailer] = Field(default_factory=list)


class ComponentSpecifications(BaseModel):
    """Flexible specifications that vary by component type"""
    pass

    model_config = {
        "extra": "allow"  # Allow additional fields for different component types
    }


class CompatibilityRequirements(BaseModel):
    """Compatibility requirements that vary by component type"""
    pass

    model_config = {
        "extra": "allow"
    }


class ComponentMetadata(BaseModel):
    source: str = Field(default="manual", description="Data source")
    last_verified: Optional[datetime] = None
    image_urls: List[str] = Field(default_factory=list)
    reviews: Optional[Dict[str, Any]] = None


class ComponentBase(BaseModel):
    type: ComponentType
    name: str = Field(..., min_length=1, max_length=200)
    brand: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=200)
    price: Price
    specifications: ComponentSpecifications
    compatibility: CompatibilityRequirements = Field(default_factory=CompatibilityRequirements)
    performance_scores: PerformanceScores
    availability: Availability = Field(default_factory=Availability)
    metadata: ComponentMetadata = Field(default_factory=ComponentMetadata)


class ComponentCreate(ComponentBase):
    pass


class ComponentInDB(ComponentCreate):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "validate_by_name": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class Component(ComponentInDB):
    pass


class ComponentSummary(BaseModel):
    id: str
    type: ComponentType
    name: str
    brand: str
    price: float
    performance_score: float = Field(..., ge=0, le=100)

    # @validator('performance_score', pre=True, always=True)
    # def set_performance_score(cls, v, values):
    #     # Extract from performance_scores.overall_score if available
    #     if 'performance_scores' in values and hasattr(values['performance_scores'], 'overall_score'):
    #         return values['performance_scores'].overall_score
    #     return v or 50  # Default fallback
