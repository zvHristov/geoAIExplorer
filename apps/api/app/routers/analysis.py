from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import AnalysisRequest, AnalysisResult
from app.services import geo_queries
from app.services.analysis_pipeline import run_analysis

router = APIRouter()


@router.post("/run", response_model=AnalysisResult)
async def analyze(req: AnalysisRequest, session: AsyncSession = Depends(get_db)):
    """
    Full geothermal heuristic analysis for a drawn polygon:
    NDVI (S2), LST anomaly (Landsat ST_B10), fault proximity, spring distance → Heuristic Score.
    """
    if req.start_date > req.end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    if not req.polygon.coordinates or not req.polygon.coordinates[0]:
        raise HTTPException(status_code=400, detail="Polygon coordinates required")

    try:
        return await run_analysis(session, req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


@router.get("/layers/springs")
async def springs(session: AsyncSession = Depends(get_db)):
    return await geo_queries.list_springs(session)


@router.get("/layers/faults")
async def faults(session: AsyncSession = Depends(get_db)):
    return await geo_queries.list_faults_geojson(session)
