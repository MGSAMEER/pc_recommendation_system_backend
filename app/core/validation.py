"""
Input validation middleware and utilities for PC Recommendation System
Provides comprehensive validation for all incoming requests
"""

import re
import logging
from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException, status
from pydantic import BaseModel, ValidationError, validator
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for comprehensive input validation"""

    def __init__(self, app, exclude_paths: List[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip validation for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        try:
            # Validate request based on method and content type
            if request.method in ["POST", "PUT", "PATCH"]:
                await self._validate_request_body(request)
            elif request.method == "GET":
                await self._validate_query_params(request)

            # Validate common headers
            self._validate_headers(request)

            # Validate path parameters
            self._validate_path_params(request)

            response = await call_next(request)
            return response

        except ValidationError as e:
            logger.warning(f"Validation error for {request.url.path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Validation error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected validation error for {request.url.path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request format"
            )

    async def _validate_request_body(self, request: Request):
        """Validate JSON request body"""
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                body = await request.json()
                self._validate_json_structure(body)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in request body"
            )

    async def _validate_query_params(self, request: Request):
        """Validate query parameters"""
        query_params = dict(request.query_params)

        # Check for suspicious query parameters
        suspicious_patterns = [
            r'<.*>',  # HTML tags
            r'javascript:',  # JavaScript URLs
            r'data:',  # Data URLs
            r'vbscript:',  # VBScript
        ]

        for key, value in query_params.items():
            for pattern in suspicious_patterns:
                if re.search(pattern, str(value), re.IGNORECASE):
                    logger.warning(f"Suspicious query parameter detected: {key}={value}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid query parameters"
                    )

    def _validate_headers(self, request: Request):
        """Validate request headers"""
        # Check Content-Length for reasonable limits
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > 10 * 1024 * 1024:  # 10MB limit
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Request too large"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Content-Length header"
                )

        # Validate User-Agent (basic check)
        user_agent = request.headers.get("user-agent", "")
        if len(user_agent) > 500:  # Reasonable limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid User-Agent header"
            )

    def _validate_path_params(self, request: Request):
        """Validate path parameters"""
        path = request.url.path

        # Check for directory traversal attempts
        if ".." in path or path.startswith("/"):
            # Allow legitimate paths but flag suspicious ones
            if re.search(r'\.\./|\.\.\\', path):
                logger.warning(f"Potential directory traversal attempt: {path}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid path"
                )

    def _validate_json_structure(self, data: Any, max_depth: int = 10, current_depth: int = 0):
        """Validate JSON structure for security"""
        if current_depth > max_depth:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON structure too deep"
            )

        if isinstance(data, dict):
            # Check for reasonable number of keys
            if len(data) > 100:  # Arbitrary limit
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Too many fields in request"
                )

            for key, value in data.items():
                # Validate key names
                if not isinstance(key, str) or len(key) > 100:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid field name"
                    )

                # Recursively validate nested structures
                self._validate_json_structure(value, max_depth, current_depth + 1)

        elif isinstance(data, list):
            # Check for reasonable array length
            if len(data) > 1000:  # Arbitrary limit
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Array too large"
                )

            for item in data:
                self._validate_json_structure(item, max_depth, current_depth + 1)

class InputValidator:
    """Utility class for various input validations"""

    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 1000) -> str:
        """Sanitize and validate string input"""
        if not isinstance(input_str, str):
            raise ValueError("Input must be a string")

        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', input_str.strip())

        # Check length
        if len(sanitized) > max_length:
            raise ValueError(f"Input too long (max {max_length} characters)")

        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>]', '', sanitized)

        return sanitized

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not isinstance(email, str):
            return False

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))

    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        if not isinstance(password, str):
            return {"valid": False, "errors": ["Password must be a string"]}

        errors = []
        score = 0

        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        else:
            score += 1

        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        else:
            score += 1

        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        else:
            score += 1

        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        else:
            score += 1

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        else:
            score += 1

        # Strength assessment
        if score >= 5:
            strength = "strong"
        elif score >= 3:
            strength = "medium"
        else:
            strength = "weak"

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "score": score,
            "strength": strength
        }

    @staticmethod
    def validate_price(price: float, min_price: float = 0, max_price: float = 10000) -> bool:
        """Validate price input"""
        try:
            price_float = float(price)
            return min_price <= price_float <= max_price
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_purpose(purpose: str) -> bool:
        """Validate purpose input"""
        valid_purposes = ['gaming', 'office', 'creative', 'programming', 'general']
        return purpose in valid_purposes

    @staticmethod
    def validate_performance_level(level: str) -> bool:
        """Validate performance level input"""
        valid_levels = ['basic', 'standard', 'high', 'professional']
        return level in valid_levels

    @staticmethod
    def validate_component_type(component_type: str) -> bool:
        """Validate component type"""
        valid_types = ['cpu', 'gpu', 'motherboard', 'ram', 'storage', 'case', 'psu', 'cooler']
        return component_type in valid_types

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        if not isinstance(url, str):
            return False

        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url.strip()))

# Pydantic models for request validation
class UserProfileRequest(BaseModel):
    experience_level: Optional[str]
    primary_use: Optional[str]
    budget: Optional[Dict[str, float]]
    preferred_brands: Optional[List[str]]
    must_have_features: Optional[List[str]]
    avoided_features: Optional[List[str]]

    @validator('experience_level')
    def validate_experience_level(cls, v):
        if v is not None and not InputValidator.validate_performance_level(v):
            raise ValueError('Invalid experience level')
        return v

    @validator('primary_use')
    def validate_primary_use(cls, v):
        if v is not None and not InputValidator.validate_purpose(v):
            raise ValueError('Invalid primary use')
        return v

    @validator('budget')
    def validate_budget(cls, v):
        if v is not None:
            if 'min' in v and 'max' in v:
                if v['min'] > v['max']:
                    raise ValueError('Budget min cannot be greater than max')
                if not (0 <= v['min'] <= 50000 and 0 <= v['max'] <= 50000):
                    raise ValueError('Budget values must be between 0 and 50000')
        return v

class ComponentFilterRequest(BaseModel):
    type: Optional[str]
    brand: Optional[str]
    min_price: Optional[float]
    max_price: Optional[float]
    min_performance_score: Optional[float]

    @validator('type')
    def validate_type(cls, v):
        if v is not None and not InputValidator.validate_component_type(v):
            raise ValueError('Invalid component type')
        return v

    @validator('min_price', 'max_price')
    def validate_price(cls, v):
        if v is not None and not InputValidator.validate_price(v):
            raise ValueError('Invalid price')
        return v

    @validator('min_performance_score')
    def validate_performance_score(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError('Performance score must be between 0 and 100')
        return v

# Global instances
input_validator = InputValidator()
