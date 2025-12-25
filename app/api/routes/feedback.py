"""
Feedback API routes for collecting user feedback on recommendations
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status

from app.core.database import get_database
from app.core.cache import cache


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/feedback",
    status_code=status.HTTP_201_CREATED,
    summary="Submit recommendation feedback",
    description="Submit user feedback on a recommendation for continuous improvement"
)
async def submit_feedback(feedback_data: dict):
    """
    Submit feedback on a recommendation

    - **recommendation_id**: ID of the recommendation
    - **rating**: Optional rating (1-5 stars)
    - **helpful**: Whether the recommendation was helpful
    - **purchased_config_id**: Optional ID of purchased configuration
    - **comments**: Optional feedback comments
    """
    try:
        required_fields = ["recommendation_id", "helpful"]
        for field in required_fields:
            if field not in feedback_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )

        # Validate rating if provided
        if "rating" in feedback_data:
            rating = feedback_data["rating"]
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rating must be an integer between 1 and 5"
                )

        # Validate helpful field
        if not isinstance(feedback_data["helpful"], bool):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Helpful must be a boolean value"
            )

        db = await get_database()

        # Verify recommendation exists
        from bson import ObjectId
        recommendation_id = feedback_data["recommendation_id"]
        existing_rec = await db.recommendations.find_one({"_id": ObjectId(recommendation_id)})

        if not existing_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found"
            )

        # Add feedback to recommendation
        feedback_doc = {
            "rating": feedback_data.get("rating"),
            "helpful": feedback_data["helpful"],
            "purchased_config": feedback_data.get("purchased_config_id"),
            "comments": feedback_data.get("comments"),
            "submitted_at": datetime.utcnow(),
            "user_agent": feedback_data.get("user_agent", ""),
            "session_id": feedback_data.get("session_id", "")
        }

        await db.recommendations.update_one(
            {"_id": ObjectId(recommendation_id)},
            {"$set": {"user_feedback": feedback_doc}}
        )

        # Invalidate related caches
        await cache.clear_pattern(f"recommendations:{recommendation_id}")

        # Log feedback for analytics
        logger.info(f"Feedback submitted for recommendation {recommendation_id}: helpful={feedback_data['helpful']}")

        # Store feedback summary for analytics (optional)
        try:
            analytics_doc = {
                "recommendation_id": recommendation_id,
                "helpful": feedback_data["helpful"],
                "rating": feedback_data.get("rating"),
                "has_comments": bool(feedback_data.get("comments")),
                "timestamp": datetime.utcnow()
            }
            await db.feedback_analytics.insert_one(analytics_doc)
        except Exception as e:
            logger.warning(f"Failed to store feedback analytics: {e}")

        return {
            "feedback_id": f"feedback_{recommendation_id}",
            "submitted_at": feedback_doc["submitted_at"].isoformat(),
            "message": "Feedback submitted successfully",
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


@router.get(
    "/feedback/stats",
    status_code=status.HTTP_200_OK,
    summary="Get feedback statistics",
    description="Retrieve aggregated feedback statistics for system improvement"
)
async def get_feedback_stats(days: int = 30):
    """
    Get feedback statistics for the specified number of days

    - **days**: Number of days to look back (default: 30)
    """
    try:
        db = await get_database()

        # Calculate date threshold
        from datetime import datetime, timedelta
        start_date = datetime.utcnow() - timedelta(days=days)

        # Aggregate feedback statistics
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_feedback": {"$sum": 1},
                    "helpful_count": {
                        "$sum": {"$cond": ["$helpful", 1, 0]}
                    },
                    "unhelpful_count": {
                        "$sum": {"$cond": ["$helpful", 0, 1]}
                    },
                    "average_rating": {"$avg": "$rating"},
                    "with_comments": {
                        "$sum": {"$cond": ["$has_comments", 1, 0]}
                    },
                    "with_ratings": {
                        "$sum": {"$cond": [{"$ne": ["$rating", None]}, 1, 0]}
                    }
                }
            }
        ]

        result = await db.feedback_analytics.aggregate(pipeline).to_list(length=1)

        if result:
            stats = result[0]
            stats.pop("_id", None)  # Remove MongoDB _id

            # Calculate percentages
            total = stats["total_feedback"]
            if total > 0:
                stats["helpful_percentage"] = round((stats["helpful_count"] / total) * 100, 1)
                stats["unhelpful_percentage"] = round((stats["unhelpful_count"] / total) * 100, 1)
                stats["comment_rate"] = round((stats["with_comments"] / total) * 100, 1)
                stats["rating_rate"] = round((stats["with_ratings"] / total) * 100, 1)

            return {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "statistics": stats
            }

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "statistics": {
                "total_feedback": 0,
                "helpful_count": 0,
                "unhelpful_count": 0,
                "helpful_percentage": 0,
                "unhelpful_percentage": 0,
                "average_rating": 0,
                "comment_rate": 0,
                "rating_rate": 0
            }
        }

    except Exception as e:
        logger.error(f"Error retrieving feedback stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback statistics"
        )
