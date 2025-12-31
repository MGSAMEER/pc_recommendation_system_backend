"""
Recommendations API routes
"""
import logging
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.api.models.user_profile import UserProfileCreate, UserProfile
from app.api.models.recommendation import RecommendationCreate, Recommendation
from app.api.services.recommendation_engine import recommendation_engine
from typing import List, Optional, Any
from pydantic import BaseModel
from app.api.routes.users import get_current_user
from app.api.services.auth_service import auth_service

# Optional authentication dependency
security_optional = HTTPBearer(auto_error=False)

async def get_optional_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_optional)):
    if not credentials:
        return None
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    if not token_data:
        return None
    return token_data


class RecommendationRequest(BaseModel):
    session_id: Optional[str] = None
    purpose: str
    budget: dict  # We'll validate this separately
    performance_level: Optional[str] = None  # Removed silent default
    preferred_brands: Optional[List[str]] = None  # Changed from [] to None
    must_have_features: Optional[List[str]] = None  # Changed from [] to None
    max_recommendations: Optional[int] = None  # Changed from 3 to None
    safe_mode: Optional[bool] = False  # Safe recommendation mode


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "Test endpoint works"}

@router.post(
    "/recommendations",
    summary="Generate PC recommendations",
    description="Generate personalized PC recommendations based on user requirements"
)
async def create_recommendations(request: RecommendationRequest):
    """Generate PC recommendations based on user requirements with enhanced validation"""
    try:
        logger.info(f"Received recommendation request: {request}")
        logger.info("Processing recommendation request")

        # Convert to dict for validation
        request_dict = request.dict()

        # Validate request structure
        validation_errors = validate_recommendation_request(request_dict)
        if validation_errors:
            logger.warning(f"Request validation failed: {validation_errors}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid request data", "details": validation_errors}
            )

        # Convert request to UserProfile
        try:
            user_profile = create_user_profile_from_request(request_dict)
        except Exception as e:
            logger.error(f"Failed to create user profile: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user profile data: {str(e)}"
            )

        # Generate recommendations using the engine
        start_time = datetime.utcnow()
        try:
            recommendations, cache_used = await recommendation_engine.generate_recommendations(
                user_profile=user_profile,
                max_recommendations=request.max_recommendations or 3,
                safe_mode=request.safe_mode
            )

        except ValueError as e:
            # Handle no recommendations found
            logger.warning(f"No recommendations available: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No PC configurations match your current requirements. Try adjusting your budget range or performance expectations."
            )
        except Exception as e:
            logger.error(f"Recommendation engine failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate recommendations"
            )

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Check for fallback usage
        fallback_used = any(rec.get('fallback_type') for rec in recommendations if rec.get('fallback_type'))

        # Create recommendation document for database
        recommendation_doc = {
            "user_profile": user_profile.dict(),
            "recommended_configs": recommendations,
            "recommendation_metadata": {
                "algorithm_version": "2.0.0",  # Updated version
                "processing_time_ms": round(processing_time, 2),
                "total_considered": len(recommendations),
                "cache_used": cache_used,
                "fallback_used": fallback_used,
                "fallback_types": list(set(rec.get('fallback_type') for rec in recommendations if rec.get('fallback_type')))
            },
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=30),
            "session_id": user_profile.session_id or "",
            "user_feedback": None
        }

        # Save to database with error handling
        try:
            db = await get_database()
            result = await db.recommendations.insert_one(recommendation_doc)
            recommendation_id = str(result.inserted_id)
        except Exception as e:
            logger.error(f"Database save failed: {e}")
            # Still return recommendations even if save fails
            recommendation_id = f"temp_{datetime.utcnow().timestamp()}"

        response_data = {
            "recommendation_id": recommendation_id,
            "recommendations": recommendations,
            "metadata": recommendation_doc["recommendation_metadata"],
            "expires_at": recommendation_doc["expires_at"].isoformat(),
            "processing_time_ms": round(processing_time, 2)
        }

        logger.info(f"Generated {len(recommendations)} recommendations in {processing_time:.2f}ms")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating recommendations"
        )


def validate_recommendation_request(request: dict) -> List[str]:
    """Validate recommendation request data with explicit validation for all fields"""
    errors = []

    # Check required fields
    required_fields = ["purpose", "budget"]
    for field in required_fields:
        if field not in request:
            errors.append(f"Missing required field: {field}")

    # Validate purpose
    if "purpose" in request:
        valid_purposes = ["gaming", "office", "creative", "programming", "general"]
        if request["purpose"] not in valid_purposes:
            errors.append(f"Invalid purpose. Must be one of: {', '.join(valid_purposes)}")

    # Validate budget
    if "budget" in request:
        budget = request["budget"]
        if isinstance(budget, (int, float)):
            # Convert number to dict
            request["budget"] = {"min": budget, "max": budget}
        elif isinstance(budget, dict):
            if "min" not in budget or "max" not in budget:
                errors.append("Budget must have 'min' and 'max' fields")
            elif not isinstance(budget.get("min"), (int, float)) or not isinstance(budget.get("max"), (int, float)):
                errors.append("Budget min and max must be numbers")
            elif budget["min"] < 0 or budget["max"] < budget["min"]:
                errors.append("Invalid budget range")
            elif budget["min"] < 100 or budget["max"] > 10000:  # Reasonable budget limits
                errors.append("Budget must be between $100 and $10,000")
        else:
            errors.append("Budget must be a number or an object with 'min' and 'max' fields")

    # Validate performance level (required)
    if "performance_level" not in request or request["performance_level"] is None:
        errors.append("performance_level is required. Must be one of: basic, standard, high, professional")
    else:
        valid_levels = ["basic", "standard", "high", "professional"]
        if request["performance_level"] not in valid_levels:
            errors.append(f"Invalid performance_level. Must be one of: {', '.join(valid_levels)}")

    # Validate max_recommendations (optional, defaults to 3)
    if "max_recommendations" in request and request["max_recommendations"] is not None:
        max_rec = request["max_recommendations"]
        if not isinstance(max_rec, int) or max_rec < 1 or max_rec > 10:
            errors.append("max_recommendations must be an integer between 1 and 10")

    # Validate preferred_brands
    if "preferred_brands" in request and request["preferred_brands"] is not None:
        if not isinstance(request["preferred_brands"], list):
            errors.append("preferred_brands must be an array of strings")
        else:
            for brand in request["preferred_brands"]:
                if not isinstance(brand, str) or not brand.strip():
                    errors.append("preferred_brands must contain non-empty strings")

    # Validate must_have_features
    if "must_have_features" in request and request["must_have_features"] is not None:
        if not isinstance(request["must_have_features"], list):
            errors.append("must_have_features must be an array of strings")
        else:
            for feature in request["must_have_features"]:
                if not isinstance(feature, str) or not feature.strip():
                    errors.append("must_have_features must contain non-empty strings")

    return errors


def create_user_profile_from_request(request: dict) -> UserProfileCreate:
    """Create UserProfile object from request data with explicit handling"""
    from app.api.models.user_profile import UserProfileCreate

    session_id = request.get("session_id")
    if not session_id:
        session_id = f"session_{datetime.utcnow().timestamp()}"

    profile_data = {
        "session_id": session_id,
        "purpose": request["purpose"],
        "budget": request["budget"],
        "performance_level": request["performance_level"],  # Now required, no default
        "preferred_brands": request.get("preferred_brands", []),  # Default to empty list if None
        "must_have_features": request.get("must_have_features", [])  # Default to empty list if None
    }

    profile_create = UserProfileCreate(**profile_data)
    return profile_create


@router.get(
    "/recommendations/{recommendation_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get recommendation details",
    description="Retrieve detailed information about a specific recommendation"
)
async def get_recommendation_details(recommendation_id: str):
    """
    Get detailed recommendation information

    - **recommendation_id**: Unique identifier for the recommendation
    """
    try:
        db = await get_database()

        # Find recommendation
        from bson import ObjectId
        recommendation_doc = await db.recommendations.find_one({"_id": ObjectId(recommendation_id)})

        if not recommendation_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found"
            )

        # Check if expired
        if recommendation_doc.get("expires_at") and recommendation_doc["expires_at"] < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation has expired"
            )

        # Return recommendation details
        return {
            "recommendation_id": recommendation_id,
            "user_requirements": recommendation_doc.get("user_profile", {}),
            "recommendations": recommendation_doc.get("recommended_configs", []),
            "metadata": recommendation_doc.get("recommendation_metadata", {}),
            "created_at": recommendation_doc.get("created_at", datetime.utcnow()).isoformat(),
            "expires_at": recommendation_doc.get("expires_at", datetime.utcnow() + timedelta(days=30)).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recommendation {recommendation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recommendation"
        )

