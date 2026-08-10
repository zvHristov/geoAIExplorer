from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class BBoxModel(BaseModel):
    """Bounding box in WGS84: [west, south, east, north]."""

    west: float = Field(..., ge=-180, le=180)
    south: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    north: float = Field(..., ge=-90, le=90)

    def as_list(self) -> list[float]:
        return [self.west, self.south, self.east, self.north]

    def centroid(self) -> tuple[float, float]:
        return ((self.west + self.east) / 2.0, (self.south + self.north) / 2.0)


class PolygonRequest(BaseModel):
    """GeoJSON Polygon coordinates [[[lon, lat], ...]]."""

    type: str = "Polygon"
    coordinates: list[list[list[float]]]


class StacSearchRequest(BaseModel):
    bbox: BBoxModel
    start_date: date
    end_date: date
    max_items: int = Field(default=10, ge=1, le=50)


class StacAssetInfo(BaseModel):
    collection: str
    item_id: str
    datetime: str | None
    cloud_cover: float | None
    bands: dict[str, str]
    bbox: list[float] | None = None


class StacSearchResponse(BaseModel):
    sentinel2: list[StacAssetInfo]
    landsat: list[StacAssetInfo]
    query: dict[str, Any]


class AnalysisRequest(BaseModel):
    polygon: PolygonRequest
    start_date: date
    end_date: date


class ScoreBreakdown(BaseModel):
    """Component contributions to the Heuristic Score (0–100)."""

    lst_anomaly: float = Field(description="Normalized LST anomaly contribution (weight 0.40)")
    fault_proximity: float = Field(description="Normalized fault proximity contribution (weight 0.25)")
    ndvi_stress: float = Field(description="Normalized NDVI stress contribution (weight 0.20)")
    distance_to_springs: float = Field(
        description="Normalized spring-distance contribution (weight 0.15)"
    )
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "lst_anomaly": 0.40,
            "fault_proximity": 0.25,
            "ndvi_stress": 0.20,
            "distance_to_springs": 0.15,
        }
    )


class AnalysisResult(BaseModel):
    run_id: str
    ndvi_mean: float | None
    lst_anomaly_c: float | None
    fault_proximity_m: float | None
    fault_proximity_pct: float | None
    spring_distance_m: float | None
    heuristic_score: float = Field(
        description="Heuristic Score 0–100 (weighted formula, NOT an AI/ML model)"
    )
    breakdown: ScoreBreakdown
    stac_items: dict[str, Any] | None = None
    notes: list[str] = Field(default_factory=list)
