"""
PC Catalog API routes
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.api.models.pc_catalog import PCCatalogCreate, PCCatalogUpdate, PCCatalog
from app.api.services.pc_catalog_service import pc_catalog_service


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/catalog/stats",
    status_code=status.HTTP_200_OK,
    summary="Get catalog statistics",
    description="Retrieve statistics about the PC catalog"
)
async def get_catalog_stats():
    """Get PC catalog statistics"""
    try:
        stats = await pc_catalog_service.get_catalog_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting catalog stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve catalog statistics"
        )


@router.get(
    "/catalog/search",
    response_model=List[PCCatalog],
    status_code=status.HTTP_200_OK,
    summary="Search PCs",
    description="Search PCs by name or brand"
)
async def search_pcs(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Number of results to return")
):
    """Search PCs by query"""
    try:
        if not q or len(q.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query must be at least 2 characters long"
            )

        pcs = await pc_catalog_service.search_pcs(q.strip(), limit)
        return [PCCatalog(**pc.dict()) for pc in pcs]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching PCs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search PCs"
        )


@router.get(
    "/catalog",
    response_model=List[PCCatalog],
    status_code=status.HTTP_200_OK,
    summary="List PC catalog",
    description="Retrieve a list of PCs from the catalog with optional filtering"
)
async def list_pc_catalog(
    brand: Optional[str] = Query(None, description="Filter by brand"),
    primary_use: Optional[str] = Query(None, description="Filter by primary use"),
    performance_level: Optional[str] = Query(None, description="Filter by performance level"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    skip: int = Query(0, ge=0, description="Number of items to skip")
):
    """List PCs from catalog with optional filtering"""
    try:
        pcs = await pc_catalog_service.get_pcs(
            brand=brand,
            primary_use=primary_use,
            performance_level=performance_level,
            min_price=min_price,
            max_price=max_price,
            limit=limit,
            skip=skip
        )

        return [PCCatalog(**pc.dict()) for pc in pcs]

    except Exception as e:
        logger.error(f"Error listing PC catalog: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve PC catalog"
        )


@router.get(
    "/catalog/{pc_id}",
    response_model=PCCatalog,
    status_code=status.HTTP_200_OK,
    summary="Get PC details",
    description="Retrieve detailed information about a specific PC"
)
async def get_pc_details(pc_id: str):
    """Get PC details by ID"""
    try:
        pc = await pc_catalog_service.get_pc_by_id(pc_id)

        if not pc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PC not found"
            )

        return PCCatalog(**pc.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting PC details {pc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve PC details"
        )


@router.post(
    "/catalog",
    response_model=PCCatalog,
    status_code=status.HTTP_201_CREATED,
    summary="Create PC",
    description="Add a new PC to the catalog"
)
async def create_pc(pc_data: PCCatalogCreate):
    """Create a new PC in the catalog"""
    try:
        pc = await pc_catalog_service.create_pc(pc_data)
        return PCCatalog(**pc.dict())

    except Exception as e:
        logger.error(f"Error creating PC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create PC"
        )


@router.put(
    "/catalog/{pc_id}",
    response_model=PCCatalog,
    status_code=status.HTTP_200_OK,
    summary="Update PC",
    description="Update an existing PC in the catalog"
)
async def update_pc(pc_id: str, update_data: PCCatalogUpdate):
    """Update PC information"""
    try:
        pc = await pc_catalog_service.update_pc(pc_id, update_data)

        if not pc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PC not found"
            )

        return PCCatalog(**pc.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating PC {pc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update PC"
        )


@router.delete(
    "/catalog/{pc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete PC",
    description="Remove a PC from the catalog"
)
async def delete_pc(pc_id: str):
    """Delete PC from catalog"""
    try:
        success = await pc_catalog_service.delete_pc(pc_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PC not found"
            )

        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting PC {pc_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete PC"
        )