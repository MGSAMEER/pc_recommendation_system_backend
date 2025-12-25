from pydantic import BaseModel, Field
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


class ComponentSummary(BaseModel):
    id: str = Field(..., description="Component ID")
    type: ComponentType
    name: str
    brand: str
    price: float = Field(..., gt=0)
    quantity: int = Field(default=1, ge=1)


class CompatibilityWarning(BaseModel):
    severity: str = Field(..., pattern="^(error|warning|info)$")
    message: str
    affected_components: List[str] = Field(default_factory=list)


class Bottleneck(BaseModel):
    component_type: ComponentType
    impact: str = Field(..., pattern="^(high|medium|low)$")
    recommendation: str


class CompatibilityStatus(BaseModel):
    is_compatible: bool = Field(default=True)
    warnings: List[CompatibilityWarning] = Field(default_factory=list)
    bottlenecks: List[Bottleneck] = Field(default_factory=list)


class PerformanceProfile(BaseModel):
    gaming_performance: float = Field(..., ge=0, le=100)
    productivity_performance: float = Field(..., ge=0, le=100)
    creative_performance: float = Field(..., ge=0, le=100)
    overall_performance: float = Field(..., ge=0, le=100)


class SuitabilityScores(BaseModel):
    gaming: float = Field(..., ge=0, le=100)
    office: float = Field(..., ge=0, le=100)
    creative: float = Field(..., ge=0, le=100)
    programming: float = Field(..., ge=0, le=100)
    general: float = Field(..., ge=0, le=100)


class PCConfigurationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    components: List[ComponentSummary] = Field(..., min_items=1)
    performance_profile: PerformanceProfile
    compatibility_status: CompatibilityStatus = Field(default_factory=CompatibilityStatus)
    suitability_scores: SuitabilityScores
    source: str = Field(default="generated", pattern="^(generated|curated|user_submitted)$")


class PCConfigurationCreate(PCConfigurationBase):
    total_price: float = Field(..., gt=0, description="Total price in USD")


class PCConfigurationInDB(PCConfigurationCreate):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "validate_by_name": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class PCConfiguration(PCConfigurationInDB):
    pass
