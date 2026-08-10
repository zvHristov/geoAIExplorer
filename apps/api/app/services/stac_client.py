"""Microsoft Planetary Computer STAC client for Sentinel-2 L2A and Landsat C2 L2."""

from __future__ import annotations

from datetime import date
from typing import Any

import planetary_computer as pc
import pystac_client

from app.config import settings
from app.models.schemas import BBoxModel, StacAssetInfo

# Sentinel-2 optical bands for NDVI (NOT thermal — S2 has no thermal channel)
S2_BANDS = {
    "B02": "blue",
    "B03": "green",
    "B04": "red",
    "B08": "nir",
}

# Landsat Collection 2 Level-2 Surface Temperature (Kelvin, atmosphere-corrected)
LANDSAT_THERMAL_BAND = "lwir11"  # ST_B10 asset key on PC often as "lwir11" or "ST_B10"


def _open_catalog() -> pystac_client.Client:
    modifiers = []
    if settings.pc_subscription_key:
        # Signed access when a subscription key is configured
        pass
    return pystac_client.Client.open(
        settings.stac_api_url,
        modifier=pc.sign_inplace,
    )


def _cloud_cover(item: Any) -> float | None:
    props = item.properties or {}
    for key in ("eo:cloud_cover", "landsat:cloud_cover_land", "cloud_cover"):
        if key in props and props[key] is not None:
            return float(props[key])
    return None


def _resolve_asset_href(item: Any, keys: list[str]) -> str | None:
    for key in keys:
        asset = item.assets.get(key)
        if asset is not None:
            href = asset.href
            try:
                return pc.sign(href)
            except Exception:
                return href
    return None


def search_sentinel2(bbox: BBoxModel, start: date, end: date, max_items: int = 10) -> list[StacAssetInfo]:
    """Search sentinel-2-l2a for optical bands B02/B03/B04/B08 within bbox + time range."""
    catalog = _open_catalog()
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox.as_list(),
        datetime=f"{start.isoformat()}/{end.isoformat()}",
        query={"eo:cloud_cover": {"lt": settings.max_cloud_cover}},
        max_items=max_items,
    )
    results: list[StacAssetInfo] = []
    for item in search.items():
        bands: dict[str, str] = {}
        for band_key in S2_BANDS:
            href = _resolve_asset_href(item, [band_key])
            if href:
                bands[band_key] = href
        if not {"B04", "B08"}.issubset(bands.keys()):
            continue
        results.append(
            StacAssetInfo(
                collection="sentinel-2-l2a",
                item_id=item.id,
                datetime=item.datetime.isoformat() if item.datetime else None,
                cloud_cover=_cloud_cover(item),
                bands=bands,
                bbox=list(item.bbox) if item.bbox else None,
            )
        )
    return results


def search_landsat(bbox: BBoxModel, start: date, end: date, max_items: int = 10) -> list[StacAssetInfo]:
    """
    Search landsat-c2-l2 for Surface Temperature band ST_B10 (Kelvin).
    Do NOT use Sentinel-2 for thermal — it has no thermal channel.
    """
    catalog = _open_catalog()
    search = catalog.search(
        collections=["landsat-c2-l2"],
        bbox=bbox.as_list(),
        datetime=f"{start.isoformat()}/{end.isoformat()}",
        query={"eo:cloud_cover": {"lt": settings.max_cloud_cover}},
        max_items=max_items,
    )
    results: list[StacAssetInfo] = []
    for item in search.items():
        # Planetary Computer Landsat C2 L2 uses "lwir11" for ST_B10 surface temperature
        href = _resolve_asset_href(item, ["lwir11", "ST_B10", "st_b10", "thermal"])
        if not href:
            continue
        results.append(
            StacAssetInfo(
                collection="landsat-c2-l2",
                item_id=item.id,
                datetime=item.datetime.isoformat() if item.datetime else None,
                cloud_cover=_cloud_cover(item),
                bands={"ST_B10": href},
                bbox=list(item.bbox) if item.bbox else None,
            )
        )
    return results


def search_all(bbox: BBoxModel, start: date, end: date, max_items: int = 10) -> dict[str, Any]:
    s2 = search_sentinel2(bbox, start, end, max_items)
    ls = search_landsat(bbox, start, end, max_items)
    return {
        "sentinel2": s2,
        "landsat": ls,
        "query": {
            "bbox": bbox.as_list(),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "stac_api": settings.stac_api_url,
            "collections": ["sentinel-2-l2a", "landsat-c2-l2"],
            "note": "Thermal from Landsat ST_B10 only; Sentinel-2 used solely for NDVI (B04/B08).",
        },
    }
