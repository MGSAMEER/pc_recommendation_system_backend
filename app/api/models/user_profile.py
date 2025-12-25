from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime


class Budget(BaseModel):
    min: float = Field(..., gt=0, description="Minimum budget in USD")
    max: float = Field(..., gt=0, description="Maximum budget in USD")
    currency: str = Field(default="USD", description="Currency code")

    # @validator('max')
    # def max_must_be_greater_than_min(cls, v, values):
    #     if 'min' in values and v <= values['min']:
    #         raise ValueError('max must be greater than min')
    #     return v


class UserProfileBase(BaseModel):
    purpose: str = Field(..., description="Primary use case", pattern="^(gaming|office|creative|programming|general)$")
    budget: Budget
    performance_level: str = Field(..., description="Required performance level", pattern="^(basic|standard|high|professional)$")
    preferred_brands: Optional[List[str]] = Field(default_factory=list, description="Preferred component brands")
    must_have_features: Optional[List[str]] = Field(default_factory=list, description="Required features")


class UserProfileCreate(UserProfileBase):
    session_id: str = Field(..., description="Anonymous session identifier")
    user_id: Optional[str] = Field(None, description="Registered user ID")


class UserProfileInDB(UserProfileCreate):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "validate_by_name": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }


class UserProfile(UserProfileInDB):
    pass
