"""
User management service for PC Recommendation System
Handles user profiles, preferences, and personalization
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bson import ObjectId

from app.core.database import get_database
from app.api.models.user import UserInDB, UserProfile, UserUpdate, UserProfileUpdateRequest
from app.api.models.pc_config import PCConfiguration


class UserService:
    """Service for managing user profiles and preferences"""

    async def get_user_profile(self, user_id: str) -> Optional[UserInDB]:
        """Get user profile by ID"""
        db = await get_database()
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        return UserInDB(**user_doc) if user_doc else None

    async def update_user_profile(self, user_id: str, update_data: UserProfileUpdateRequest) -> Optional[UserInDB]:
        """Update user profile"""
        db = await get_database()

        # Build update document
        update_doc = {"updated_at": datetime.now(timezone.utc)}
        if update_data.full_name is not None:
            update_doc["full_name"] = update_data.full_name
        if update_data.email is not None:
            # Check if email is already taken by another user
            existing_user = await db.users.find_one({
                "email": update_data.email.lower(),
                "_id": {"$ne": ObjectId(user_id)}
            })
            if existing_user:
                raise ValueError("Email already in use")
            update_doc["email"] = update_data.email.lower()

        # Update user
        result = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_doc}
        )

        if result.modified_count == 0:
            return None

        # Return updated user
        return await self.get_user_profile(user_id)

    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user PC preferences"""
        db = await get_database()
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})

        if not user_doc:
            return None

        # Return preferences or default values
        return {
            "experience_level": user_doc.get("experience_level", "beginner"),
            "primary_use": user_doc.get("primary_use", "general"),
            "budget_range": user_doc.get("budget_range", {"min": 500, "max": 2000}),
            "preferred_brands": user_doc.get("preferred_brands", []),
            "must_have_features": user_doc.get("must_have_features", []),
            "avoided_features": user_doc.get("avoided_features", [])
        }

    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Update user PC preferences"""
        db = await get_database()

        # Validate preferences
        valid_experience_levels = ["beginner", "intermediate", "advanced"]
        valid_primary_uses = ["gaming", "office", "creative", "programming", "general"]

        if "experience_level" in preferences:
            if preferences["experience_level"] not in valid_experience_levels:
                raise ValueError(f"Invalid experience level. Must be one of: {valid_experience_levels}")

        if "primary_use" in preferences:
            if preferences["primary_use"] not in valid_primary_uses:
                raise ValueError(f"Invalid primary use. Must be one of: {valid_primary_uses}")

        if "budget_range" in preferences:
            budget = preferences["budget_range"]
            if "min" in budget and "max" in budget:
                if budget["min"] >= budget["max"]:
                    raise ValueError("Budget min must be less than max")
                if budget["min"] < 200:
                    raise ValueError("Budget min must be at least $200")
                if budget["max"] > 10000:
                    raise ValueError("Budget max cannot exceed $10,000")

        # Update preferences
        update_doc = {"updated_at": datetime.now(timezone.utc)}
        update_doc.update(preferences)

        result = await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_doc}
        )

        return result.modified_count > 0

    async def get_user_recommendation_history(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's recommendation history"""
        db = await get_database()

        # Get user's recommendations
        cursor = db.pc_recommendations.find(
            {"$or": [
                {"user_id": ObjectId(user_id)},
                {"session_id": {"$regex": f"user_{user_id}", "$options": "i"}}
            ]}
        ).sort("created_at", -1).skip(offset).limit(limit)

        recommendations = await cursor.to_list(length=limit)

        # Format for response
        history = []
        for rec in recommendations:
            history.append({
                "id": str(rec["_id"]),
                "created_at": rec.get("created_at", datetime.now(timezone.utc)),
                "expires_at": rec.get("expires_at", datetime.now(timezone.utc) + timezone.timedelta(days=30)),
                "config_count": len(rec.get("recommended_configs", [])),
                "has_feedback": rec.get("user_feedback") is not None
            })

        return history

    async def get_user_feedback_history(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's feedback history"""
        db = await get_database()

        # Get user's recommendations that have feedback
        cursor = db.pc_recommendations.find(
            {"$or": [
                {"user_id": ObjectId(user_id)},
                {"session_id": {"$regex": f"user_{user_id}", "$options": "i"}}
            ]},
            {"user_feedback": 1, "created_at": 1, "_id": 1}
        ).sort("created_at", -1).skip(offset).limit(limit)

        recommendations = await cursor.to_list(length=limit)

        # Extract feedback
        feedback_history = []
        for rec in recommendations:
            if rec.get("user_feedback"):
                feedback = rec["user_feedback"]
                feedback_history.append({
                    "id": f"feedback_{rec['_id']}",
                    "recommendation_id": str(rec["_id"]),
                    "rating": feedback.get("rating"),
                    "helpful": feedback.get("helpful"),
                    "comments": feedback.get("comments"),
                    "submitted_at": feedback.get("submitted_at", rec.get("created_at"))
                })

        return feedback_history

    async def personalize_recommendations(self, user_id: str, base_recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply user personalization to recommendations"""
        # Get user preferences
        preferences = await self.get_user_preferences(user_id)

        if not preferences:
            return base_recommendations

        # Apply preference-based filtering and ranking
        personalized = []

        for rec in base_recommendations:
            score_boost = 0

            # Boost score for preferred brands
            if preferences.get("preferred_brands"):
                components = rec.get("components", [])
                for comp in components:
                    if comp.get("brand") in preferences["preferred_brands"]:
                        score_boost += 0.1

            # Adjust based on experience level
            exp_level = preferences.get("experience_level", "beginner")
            if exp_level == "advanced":
                # Advanced users prefer higher-end components
                score_boost += 0.05
            elif exp_level == "beginner":
                # Beginner users prefer simpler configurations
                score_boost -= 0.05

            # Update confidence score
            rec["confidence_score"] = min(100, rec.get("confidence_score", 50) + (score_boost * 100))

            # Add personalization note
            if not rec.get("match_reasons"):
                rec["match_reasons"] = []

            if score_boost > 0:
                rec["match_reasons"].append({
                    "factor": "user_preferences",
                    "weight": score_boost,
                    "explanation": f"Matches your preferred brands and experience level"
                })

            personalized.append(rec)

        # Re-sort by updated confidence scores
        personalized.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)

        return personalized

    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user activity statistics"""
        db = await get_database()

        # Count recommendations
        rec_count = await db.pc_recommendations.count_documents({
            "$or": [
                {"user_id": ObjectId(user_id)},
                {"session_id": {"$regex": f"user_{user_id}", "$options": "i"}}
            ]
        })

        # Count feedback given
        feedback_count = await db.pc_recommendations.count_documents({
            "$or": [
                {"user_id": ObjectId(user_id)},
                {"session_id": {"$regex": f"user_{user_id}", "$options": "i"}}
            ]},
            {"user_feedback": {"$exists": True}}
        )

        # Get most recent activity
        recent_rec = await db.pc_recommendations.find_one(
            {"$or": [
                {"user_id": ObjectId(user_id)},
                {"session_id": {"$regex": f"user_{user_id}", "$options": "i"}}
            ]},
            sort=[("created_at", -1)]
        )

        return {
            "total_recommendations": rec_count,
            "feedback_given": feedback_count,
            "last_activity": recent_rec.get("created_at") if recent_rec else None,
            "account_created": (await self.get_user_profile(user_id)).created_at if await self.get_user_profile(user_id) else None
        }

    async def delete_user_account(self, user_id: str, reason: str = None) -> bool:
        """Delete user account and related data"""
        db = await get_database()

        # Start a session for transaction-like behavior
        # Note: MongoDB transactions would be better here in production

        # Delete user sessions
        await db.user_sessions.delete_many({"user_id": ObjectId(user_id)})

        # Delete user recommendations (but keep feedback for analytics)
        # In a real system, you might anonymize instead of delete
        await db.pc_recommendations.update_many(
            {"user_id": ObjectId(user_id)},
            {"$set": {"user_id": None, "anonymized": True}}
        )

        # Delete audit logs (keep for compliance)
        await db.audit_logs.update_many(
            {"user_id": ObjectId(user_id)},
            {"$set": {"user_id": None, "anonymized": True}}
        )

        # Finally delete the user
        result = await db.users.delete_one({"_id": ObjectId(user_id)})

        # Log account deletion
        await db.audit_logs.insert_one({
            "user_id": None,  # Anonymized
            "action": "account_deleted",
            "resource_type": "user",
            "resource_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "details": {"reason": reason, "anonymized": True},
            "severity": "medium"
        })

        return result.deleted_count > 0


# Global user service instance
user_service = UserService()
