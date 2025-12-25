"""
Components API routes
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.logging import get_logger
from app.core.dependencies import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = get_logger(__name__)

router = APIRouter()


class ComponentResponse(BaseModel):
    """Component response model"""
    id: str
    type: str
    name: str
    brand: str
    model: str
    price: float
    specifications: Dict[str, Any]


class ComponentsListResponse(BaseModel):
    """Components list response model"""
    components: List[ComponentResponse]
    total: int
    page: int = 1
    page_size: int = 100


@router.get(
    "/components",
    status_code=status.HTTP_200_OK,
    summary="List PC components",
    description="Retrieve a list of available PC components with optional filtering"
)
async def list_components(
    component_type: Optional[str] = Query(None, description="Filter by component type"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> ComponentsListResponse:
    """List available PC components from database"""
    try:
        logger.info(f"Listing components - type: {component_type}, brand: {brand}, page: {page}")
        
        # Build query filter
        query_filter: Dict[str, Any] = {}
        if component_type:
            query_filter["type"] = component_type
        if brand:
            query_filter["brand"] = {"$regex": brand, "$options": "i"}
        if min_price is not None or max_price is not None:
            price_filter: Dict[str, float] = {}
            if min_price is not None:
                price_filter["$gte"] = min_price
            if max_price is not None:
                price_filter["$lte"] = max_price
            query_filter["price.value"] = price_filter

        # Get total count
        total = await db.components.count_documents(query_filter)
        
        # Calculate pagination
        skip = (page - 1) * page_size
        
        # Query components
        cursor = db.components.find(query_filter).skip(skip).limit(page_size)
        components_list = await cursor.to_list(length=page_size)
        
        # Transform to response format
        components_response = []
        for comp in components_list:
            components_response.append(ComponentResponse(
                id=str(comp.get("_id", "")),
                type=comp.get("type", ""),
                name=comp.get("name", ""),
                brand=comp.get("brand", ""),
                model=comp.get("model", ""),
                price=comp.get("price", {}).get("value", 0.0),
                specifications=comp.get("specifications", {})
            ))
        
        logger.info(f"Retrieved {len(components_response)} components out of {total} total")
        
        return ComponentsListResponse(
            components=components_response,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing components: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve components: {str(e) if logger.level == logging.DEBUG else 'Internal server error'}"
        )


@router.get(
    "/components/{component_id}",
    status_code=status.HTTP_200_OK,
    summary="Get component details",
    description="Retrieve detailed information about a specific component"
)
async def get_component_details(
    component_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> ComponentResponse:
    """Get detailed information about a specific component"""
    try:
        logger.info(f"Fetching component details for ID: {component_id}")
        
        from bson import ObjectId
        try:
            comp = await db.components.find_one({"_id": ObjectId(component_id)})
        except Exception:
            comp = None
        
        if not comp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Component with ID {component_id} not found"
            )
        
        return ComponentResponse(
            id=str(comp.get("_id", "")),
            type=comp.get("type", ""),
            name=comp.get("name", ""),
            brand=comp.get("brand", ""),
            model=comp.get("model", ""),
            price=comp.get("price", {}).get("value", 0.0),
            specifications=comp.get("specifications", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching component {component_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve component: {str(e) if logger.level == logging.DEBUG else 'Internal server error'}"
        )
