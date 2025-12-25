"""
User data models for PC Recommendation System
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic models"""

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class UserBase(BaseModel):
    """Base user model with common fields"""
    email: EmailStr = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="User's full name")

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Full name cannot be empty if provided')
        return v.strip() if v else v


class UserCreate(UserBase):
    """Model for user creation"""
    password: str = Field(..., min_length=8, description="User's password")

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        # Check byte length (bcrypt limit is 72 bytes)
        

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain at least one uppercase letter, one lowercase letter, and one digit')

        return v


class UserUpdate(BaseModel):
    """Model for user profile updates"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Full name cannot be empty if provided')
        return v.strip() if v else v


class UserInDB(UserBase):
    """User model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    password_hash: str = Field(..., description="Hashed password")
    is_active: bool = Field(default=True, description="Account status")
    is_verified: bool = Field(default=False, description="Email verification status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last profile update")
    last_login: Optional[datetime] = Field(None, description="Last successful login")
    login_attempts: int = Field(default=0, description="Failed login attempts")
    locked_until: Optional[datetime] = Field(None, description="Account lockout expiration")

    model_config = {
        "validate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class UserResponse(UserBase):
    """User model for API responses"""
    id: str = Field(..., description="User ID")
    is_active: bool = Field(default=True, description="Account status")
    is_verified: bool = Field(default=False, description="Email verification status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")


class PasswordChangeRequest(BaseModel):
    """Model for password change requests"""
    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_new_password_strength(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        # Check byte length (bcrypt limit is 72 bytes)
        password_bytes = v.encode('utf-8')
        if len(password_bytes) > 72:
            raise ValueError('Password cannot exceed 72 bytes')

        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain at least one uppercase letter, one lowercase letter, and one digit')

        return v


class UserLoginRequest(BaseModel):
    """Model for user login requests"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

    @field_validator('password')
    @classmethod
    def validate_password_presence(cls, v):
        if not v or not v.strip():
            raise ValueError('Password is required')
        return v


class UserSignupRequest(UserCreate):
    """Model for user signup requests (same as create but explicit)"""
    pass


class UserProfile(BaseModel):
    """User profile model"""
    user_id: PyObjectId = Field(..., description="Associated user")
    experience_level: str = Field(..., pattern="^(beginner|intermediate|advanced)$", description="User expertise level")
    primary_use: str = Field(..., pattern="^(gaming|office|creative|programming|general)$", description="Main use case")
    budget_range: dict = Field(..., description="Budget preferences")
    preferred_brands: list[str] = Field(default_factory=list, description="Preferred component brands")
    must_have_features: list[str] = Field(default_factory=list, description="Required features")
    avoided_features: list[str] = Field(default_factory=list, description="Features to avoid")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Profile creation")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update")

    model_config = {
        "validate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class UserProfileUpdateRequest(BaseModel):
    """Model for user profile updates"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Full name cannot be empty if provided')
        return v.strip() if v else v
