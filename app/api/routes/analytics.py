"""
Analytics endpoints for collecting frontend events
"""
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status

from app.core.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/events",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest analytics event"
)
async def ingest_event(event: dict):
    """Receive a single analytics event from the frontend and store it."""
    try:
        db = await get_database()
        if db is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database_not_available")

        # Basic validation
        if 'eventName' not in event and 'event_name' not in event:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing_event_name")

        doc = {
            "event": event,
            "received_at": datetime.utcnow()
        }

        try:
            await db.analytics_events.insert_one(doc)
        except Exception as e:
            logger.warning(f"Failed to store analytics event: {e}")

        return {"status": "accepted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error ingesting analytics event: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="failed_to_ingest_event")
