"""STAC search endpoints — Sentinel-2 L2A (optical) + Landsat C2 L2 (thermal ST_B10)."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import StacSearchRequest, StacSearchResponse
from app.services import stac_client

router = APIRouter()


@router.post("/search", response_model=StacSearchResponse)
async def search_stac(req: StacSearchRequest):
    """
    Search Planetary Computer STAC for:
    - sentinel-2-l2a bands B02/B03/B04/B08 (NDVI only — no thermal)
    - landsat-c2-l2 band ST_B10 / lwir11 (Surface Temperature in Kelvin)
    """
    if req.start_date > req.end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    if req.bbox.west >= req.bbox.east or req.bbox.south >= req.bbox.north:
        raise HTTPException(status_code=400, detail="Invalid bbox")

    try:
        result = stac_client.search_all(req.bbox, req.start_date, req.end_date, req.max_items)
        return StacSearchResponse(
            sentinel2=result["sentinel2"],
            landsat=result["landsat"],
            query=result["query"],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"STAC search failed: {exc}") from exc
