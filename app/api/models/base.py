"""
Base Pydantic models for standard API responses
"""
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime


class ErrorDetail(BaseModel):
    """Error detail model"""
    field: Optional[str] = Field(None, description="Field name that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class StandardErrorResponse(BaseModel):
    """Standard error response schema"""
    error: Dict[str, Any] = Field(
        ...,
        description="Error information",
        example={
            "code": "VALIDATION_ERROR",
            "message": "Invalid input data",
            "details": []
        }
    )


class StandardSuccessResponse(BaseModel):
    """Standard success response schema"""
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Number of items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel):
    """Paginated response schema"""
    items: List[Any] = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")


class HealthCheckResponse(BaseModel):
    """Health check response schema"""
    status: str = Field(..., description="Service status", example="healthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(..., description="Application version")
    service: str = Field(..., description="Service name")

