"""
User management API routes
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from app.api.models.user import UserUpdate, UserProfileUpdateRequest
from app.api.services.user_service import user_service
from app.api.services.auth_service import auth_service
from app.core.security import input_validator

logger = logging.getLogger(__name__)


router = APIRouter()
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    logger.debug(f"Verifying token: {token[:20]}...")
    token_data = auth_service.verify_token(token)

    if not token_data:
        logger.warning("Token verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"Token verified for user {token_data.user_id}")
    return token_data


@router.get(
    "/profile",
    status_code=status.HTTP_200_OK,
    summary="Get user profile",
    description="Retrieve current user's profile and account information"
)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    try:
        user = await user_service.get_user_profile(current_user.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_login": user.last_login
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.put(
    "/profile",
    status_code=status.HTTP_200_OK,
    summary="Update user profile",
    description="Update user's profile information"
)
async def update_user_profile(
    profile_data: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update user profile"""
    try:
        # Validate input
        if profile_data.full_name:
            profile_data.full_name = input_validator.sanitize_text(profile_data.full_name, 100)

        if profile_data.email and not input_validator.validate_email(profile_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )

        # Update profile
        user = await user_service.update_user_profile(current_user.user_id, profile_data)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "updated_at": user.updated_at
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.get(
    "/preferences",
    status_code=status.HTTP_200_OK,
    summary="Get user PC preferences",
    description="Retrieve user's PC building preferences and requirements"
)
async def get_user_preferences(current_user: dict = Depends(get_current_user)):
    """Get user PC preferences"""
    try:
        preferences = await user_service.get_user_preferences(current_user.user_id)

        if preferences is None:
            # Return default preferences if none set
            return {
                "experience_level": "beginner",
                "primary_use": "general",
                "budget_range": {"min": 500, "max": 2000},
                "preferred_brands": [],
                "must_have_features": [],
                "avoided_features": []
            }

        return preferences

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user preferences"
        )


@router.put(
    "/preferences",
    status_code=status.HTTP_200_OK,
    summary="Update user PC preferences",
    description="Update user's PC building preferences and requirements"
)
async def update_user_preferences(
    preferences: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update user PC preferences"""
    try:
        logger.info(f"Updating preferences for user {current_user.user_id}: {preferences}")

        # Ensure user exists
        user = await user_service.get_user_profile(current_user.user_id)
        if not user:
            logger.error(f"User {current_user.user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        # Validate preferences
        if "primary_use" in preferences:
            if not input_validator.validate_purpose(preferences["primary_use"]):
                valid_uses = ["gaming", "office", "creative", "programming", "general"]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid primary use. Must be one of: {valid_uses}"
                )

        if "budget_range" in preferences:
            budget = preferences["budget_range"]
            if not isinstance(budget, dict) or "min" not in budget or "max" not in budget:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Budget range must include 'min' and 'max' values"
                )

            if not input_validator.validate_price(budget["min"]) or not input_validator.validate_price(budget["max"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Budget values must be between 0 and 10,000"
                )

            if budget["min"] >= budget["max"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Budget min must be less than max"
                )

        # Sanitize text fields
        if "must_have_features" in preferences:
            preferences["must_have_features"] = [
                input_validator.sanitize_text(feature, 50)
                for feature in preferences["must_have_features"]
                if isinstance(feature, str)
            ]

        if "avoided_features" in preferences:
            preferences["avoided_features"] = [
                input_validator.sanitize_text(feature, 50)
                for feature in preferences["avoided_features"]
                if isinstance(feature, str)
            ]

        success = await user_service.update_user_preferences(current_user.user_id, preferences)
        if not success:
            user = await user_service.get_user_profile(current_user.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            return {"message": "Preferences updated successfully", "changed": False}
        return {"message": "Preferences updated successfully", "changed": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user preferences"
        )


@router.get(
    "/recommendations",
    status_code=status.HTTP_200_OK,
    summary="Get user recommendation history",
    description="Retrieve user's past PC recommendations"
)
async def get_user_recommendations(
    limit: int = Query(20, ge=1, le=50, description="Number of recommendations to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: dict = Depends(get_current_user)
):
    """Get user recommendation history"""
    try:
        recommendations = await user_service.get_user_recommendation_history(
            current_user.user_id, limit, offset
        )

        return {
            "recommendations": recommendations,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(recommendations) == limit
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recommendation history"
        )


@router.get(
    "/feedback",
    status_code=status.HTTP_200_OK,
    summary="Get user feedback history",
    description="Retrieve user's feedback on recommendations"
)
async def get_user_feedback(
    limit: int = Query(20, ge=1, le=50, description="Number of feedback items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: dict = Depends(get_current_user)
):
    """Get user feedback history"""
    try:
        feedback = await user_service.get_user_feedback_history(
            current_user.user_id, limit, offset
        )

        return {
            "feedback": feedback,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": len(feedback) == limit
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback history"
        )


@router.post(
    "/delete",
    status_code=status.HTTP_200_OK,
    summary="Request account deletion",
    description="Initiate account deletion process (GDPR compliance)"
)
async def delete_user_account(
    deletion_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Request account deletion"""
    try:
        # Validate reason
        valid_reasons = ["no_longer_needed", "privacy_concerns", "poor_experience", "switching_service", "other"]
        reason = deletion_data.get("reason")

        if not reason or reason not in valid_reasons:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Valid reason required. Must be one of: {valid_reasons}"
            )

        # Sanitize feedback
        feedback = deletion_data.get("feedback", "")
        if feedback:
            feedback = input_validator.sanitize_text(feedback, 500)

        # Delete account
        success = await user_service.delete_user_account(
            current_user.user_id,
            reason=reason
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete account"
            )

        return {
            "message": "Account deletion initiated successfully",
            "note": "Your account will be permanently deleted within 30 days"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process account deletion request"
        )


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Get user statistics",
    description="Retrieve user's activity and usage statistics"
)
async def get_user_statistics(current_user: dict = Depends(get_current_user)):
    """Get user activity statistics"""
    try:
        stats = await user_service.get_user_statistics(current_user.user_id)

        return {
            "user_id": current_user.user_id,
            "statistics": stats
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user statistics"
        )
