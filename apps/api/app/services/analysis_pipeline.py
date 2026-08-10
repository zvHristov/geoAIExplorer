"""Orchestrates STAC fetch → raster metrics → PostGIS proximity → heuristic score."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import (
    AnalysisRequest,
    AnalysisResult,
    BBoxModel,
)
from app.services import geo_queries, raster_analysis, scoring, stac_client

logger = logging.getLogger(__name__)


def _bbox_from_polygon(coords: list[list[list[float]]]) -> BBoxModel:
    ring = coords[0]
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return BBoxModel(west=min(lons), south=min(lats), east=max(lons), north=max(lats))


def _centroid(coords: list[list[list[float]]]) -> tuple[float, float]:
    ring = coords[0]
    # Skip closing vertex if duplicated
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
    lon = sum(p[0] for p in pts) / len(pts)
    lat = sum(p[1] for p in pts) / len(pts)
    return lon, lat


async def run_analysis(session: AsyncSession, req: AnalysisRequest) -> AnalysisResult:
    notes: list[str] = []
    coords = req.polygon.coordinates
    bbox = _bbox_from_polygon(coords)
    lon, lat = _centroid(coords)
    run_id = str(uuid.uuid4())

    # 1. STAC search
    stac = stac_client.search_all(bbox, req.start_date, req.end_date, max_items=5)
    s2_items = stac["sentinel2"]
    ls_items = stac["landsat"]

    ndvi_mean: float | None = None
    lst_anomaly_c: float | None = None
    s2_used: str | None = None
    ls_used: str | None = None

    def _cloud_key(item: Any) -> float:
        return item.cloud_cover if item.cloud_cover is not None else 999.0

    # 2. NDVI — try Sentinel-2 scenes by ascending cloud cover until valid pixels
    if s2_items:
        s2_ordered = sorted(s2_items, key=_cloud_key)
        s2_scenes = [
            (item.item_id, item.bands["B04"], item.bands["B08"])
            for item in s2_ordered
            if "B04" in item.bands and "B08" in item.bands
        ]
        if s2_scenes:
            ndvi_mean, s2_used, ndvi_notes = raster_analysis.compute_ndvi_with_fallback(
                s2_scenes, coords
            )
            notes.extend(ndvi_notes)
            if ndvi_mean is not None and s2_used:
                notes.append(f"NDVI from Sentinel-2 item {s2_used}")
        else:
            notes.append("Sentinel-2 items missing B04/B08")
    else:
        notes.append("No Sentinel-2 L2A items found for bbox/time range")

    # 3. LST anomaly — try Landsat ST_B10 scenes by cloud cover (never Sentinel-2 thermal)
    if ls_items:
        ls_ordered = sorted(ls_items, key=_cloud_key)
        ls_scenes = [
            (item.item_id, item.bands["ST_B10"])
            for item in ls_ordered
            if "ST_B10" in item.bands
        ]
        if ls_scenes:
            lst_anomaly_c, ls_used, lst_notes = raster_analysis.compute_lst_anomaly_with_fallback(
                ls_scenes, coords
            )
            notes.extend(lst_notes)
            if lst_anomaly_c is not None and ls_used:
                notes.append(f"LST anomaly from Landsat ST_B10 item {ls_used}")
        else:
            notes.append("Landsat items missing ST_B10 / lwir11")
    else:
        notes.append("No Landsat C2 L2 items found for bbox/time range")

    # 4. Fault proximity + spring distance (PostGIS)
    fault_m = await geo_queries.nearest_fault_distance_m(session, lon, lat)
    spring_m, spring_name = await geo_queries.nearest_spring_distance_m(session, lon, lat)
    if spring_name:
        notes.append(f"Nearest thermal spring: {spring_name}")

    fault_pct = scoring.fault_proximity_pct(fault_m)
    heuristic_score, breakdown = scoring.compute_heuristic_score(
        lst_anomaly_c, fault_m, ndvi_mean, spring_m
    )

    # Persist run
    try:
        await session.execute(
            text(
                """
                INSERT INTO analysis_runs (
                    id, bbox, start_date, end_date,
                    ndvi_mean, lst_anomaly_c, fault_proximity_m, spring_distance_m,
                    score, breakdown
                ) VALUES (
                    CAST(:id AS uuid),
                    ST_MakeEnvelope(:west, :south, :east, :north, 4326),
                    :start_date, :end_date,
                    :ndvi, :lst, :fault, :spring,
                    :score, CAST(:breakdown AS jsonb)
                )
                """
            ),
            {
                "id": run_id,
                "west": bbox.west,
                "south": bbox.south,
                "east": bbox.east,
                "north": bbox.north,
                "start_date": req.start_date.isoformat(),
                "end_date": req.end_date.isoformat(),
                "ndvi": ndvi_mean,
                "lst": lst_anomaly_c,
                "fault": fault_m,
                "spring": spring_m,
                "score": heuristic_score,
                "breakdown": json.dumps(breakdown.model_dump()),
            },
        )
        await session.commit()
    except Exception as exc:
        logger.warning("Failed to persist analysis run: %s", exc)
        await session.rollback()
        notes.append("Analysis result not persisted (DB write failed)")

    return AnalysisResult(
        run_id=run_id,
        ndvi_mean=round(ndvi_mean, 4) if ndvi_mean is not None else None,
        lst_anomaly_c=round(lst_anomaly_c, 3) if lst_anomaly_c is not None else None,
        fault_proximity_m=round(fault_m, 1) if fault_m is not None else None,
        fault_proximity_pct=fault_pct,
        spring_distance_m=round(spring_m, 1) if spring_m is not None else None,
        heuristic_score=heuristic_score,
        breakdown=breakdown,
        stac_items={
            "sentinel2_count": len(s2_items),
            "landsat_count": len(ls_items),
            "sentinel2_best": s2_used,
            "landsat_best": ls_used,
        },
        notes=notes,
    )
