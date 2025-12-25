"""
Authentication models for PC Recommendation System
"""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId

from .user import PyObjectId


class TokenData(BaseModel):
    """Data encoded in JWT tokens"""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    exp: datetime = Field(..., description="Token expiration time")
    iat: datetime = Field(default_factory=datetime.utcnow, description="Token issued at time")
    token_type: str = Field(..., description="Token type (access/refresh)")


class TokenResponse(BaseModel):
    """Response model for token operations"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: dict = Field(..., description="User information")


class RefreshTokenRequest(BaseModel):
    """Model for refresh token requests"""
    refresh_token: str = Field(..., description="JWT refresh token")


class UserSessionInDB(BaseModel):
    """User session model as stored in database"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(..., description="Associated user")
    session_token: str = Field(..., unique=True, description="JWT session identifier")
    refresh_token: Optional[str] = Field(None, unique=True, description="JWT refresh token")
    ip_address: str = Field(..., description="Client IP address")
    user_agent: str = Field(..., description="Client browser/device info")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session start")
    expires_at: datetime = Field(..., description="Session expiration")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Last API call")
    is_active: bool = Field(default=True, description="Session status")

    model_config = {
        "validate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class UserSessionResponse(BaseModel):
    """User session model for API responses"""
    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Session start time")
    expires_at: datetime = Field(..., description="Session expiration time")
    last_activity: datetime = Field(..., description="Last activity time")
    is_active: bool = Field(..., description="Session status")


class AuthAuditLog(BaseModel):
    """Audit log entry for authentication events"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: Optional[PyObjectId] = Field(None, description="Associated user (if applicable)")
    action: str = Field(..., description="Action performed (login, logout, password_change, etc.)")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="ID of affected resource")
    ip_address: str = Field(..., description="Client IP address")
    user_agent: str = Field(..., description="Client browser/device info")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    details: Optional[dict] = Field(None, description="Additional context data")
    severity: str = Field(default="low", description="Event severity (low/medium/high/critical)")

    model_config = {
        "validate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class PasswordResetRequest(BaseModel):
    """Model for password reset requests"""
    email: str = Field(..., description="User's email address")


class PasswordResetConfirm(BaseModel):
    """Model for password reset confirmation"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_new_password_strength(cls, v):
        """Validate new password strength requirements"""
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


class ChangePasswordRequest(BaseModel):
    """Model for password change requests"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_new_password_strength(cls, v):
        """Validate new password strength requirements"""
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

    class PasswordResetResponse(BaseModel):
        """Response for password reset operations"""
        message: str = Field(..., description="Success message")
        email_sent: bool = Field(default=False, description="Whether reset email was sent")
