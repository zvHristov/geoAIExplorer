from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analysis, health, stac

app = FastAPI(
    title="GeoAI Explorer API",
    description=(
        "Geothermal potential analysis via Sentinel-2 NDVI, Landsat LST anomaly, "
        "fault proximity and thermal-spring distance. Scores are transparent "
        "heuristics — not trained ML models."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(stac.router, prefix="/api/stac", tags=["stac"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
