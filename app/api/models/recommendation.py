from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from .user_profile import UserProfileBase
from .pc_config import PCConfiguration


class MatchReason(BaseModel):
    factor: str = Field(..., description="Type of matching factor")
    weight: float = Field(..., ge=0, le=1, description="Importance weight")
    explanation: str = Field(..., description="Human-readable explanation")


class TradeOff(BaseModel):
    type: str = Field(..., description="Type of trade-off")
    impact: str = Field(..., pattern="^(positive|negative|neutral)$")
    description: str


class RecommendedConfig(BaseModel):
    configuration_id: str
    rank: int = Field(..., ge=1)
    confidence_score: float = Field(..., ge=0, le=100)
    match_reasons: List[MatchReason] = Field(default_factory=list)
    trade_offs: List[TradeOff] = Field(default_factory=list)


class RecommendationMetadata(BaseModel):
    algorithm_version: str = Field(default="1.0.0")
    processing_time_ms: int = Field(..., ge=0)
    total_configs_considered: int = Field(..., ge=0)
    filtering_criteria: dict = Field(default_factory=dict)


class RecommendationBase(BaseModel):
    user_profile_id: str
    recommended_configs: List[RecommendedConfig] = Field(..., min_items=1, max_items=10)
    recommendation_metadata: RecommendationMetadata


class RecommendationCreate(RecommendationBase):
    pass


class RecommendationInDB(RecommendationCreate):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(...)

    model_config = {
        "validate_by_name": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class Recommendation(RecommendationInDB):
    pass


class RecommendationDetail(BaseModel):
    recommendation_id: str
    user_requirements: UserProfileBase
    recommendations: List[dict]  # Detailed config data
    metadata: RecommendationMetadata
    created_at: datetime
    expires_at: datetime
