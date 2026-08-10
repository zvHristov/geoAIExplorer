"""Raster analysis: NDVI from Sentinel-2, LST anomaly from Landsat ST_B10."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import rasterio
from rasterio.mask import mask as rio_mask
from rasterio.warp import transform_geom
from shapely.geometry import mapping, shape
from shapely.ops import transform as shp_transform
import pyproj

from app.config import settings

logger = logging.getLogger(__name__)

# Landsat Collection 2 Level-2 ST scale (Kelvin): DN * 0.00341802 + 149.0
LANDSAT_ST_SCALE = 0.00341802
LANDSAT_ST_OFFSET = 149.0
LANDSAT_ST_FILL = 0


def _polygon_geojson(coords: list[list[list[float]]]) -> dict[str, Any]:
    return {"type": "Polygon", "coordinates": coords}


def _read_masked(href: str, polygon_coords: list[list[list[float]]]) -> tuple[np.ndarray, dict]:
    """Read and mask a COG/GeoTIFF by polygon; returns float array and profile."""
    geom = _polygon_geojson(polygon_coords)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_PROTOCOLS="https"):
        with rasterio.open(href) as src:
            geom_proj = transform_geom("EPSG:4326", src.crs, geom)
            out_image, out_transform = rio_mask(src, [geom_proj], crop=True, filled=False)
            profile = src.profile.copy()
            profile.update(
                {
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                }
            )
            data = out_image[0].astype(np.float64)
            if np.ma.is_masked(data):
                data = np.ma.filled(data, np.nan)
            return data, profile


def compute_ndvi(red_href: str, nir_href: str, polygon_coords: list[list[list[float]]]) -> float | None:
    """
    NDVI = (NIR - RED) / (NIR + RED) from Sentinel-2 B08 / B04.
    Returns mean NDVI over the polygon, or None if insufficient valid pixels.
    """
    try:
        red, _ = _read_masked(red_href, polygon_coords)
        nir, _ = _read_masked(nir_href, polygon_coords)
    except Exception as exc:
        logger.warning("NDVI read failed: %s", exc)
        return None

    # Align shapes if slight crop differences
    h = min(red.shape[0], nir.shape[0])
    w = min(red.shape[1], nir.shape[1])
    red = red[:h, :w]
    nir = nir[:h, :w]

    # Sentinel-2 L2A reflectance is often scaled by 10000
    if np.nanmax(red) > 1.5 or np.nanmax(nir) > 1.5:
        red = red / 10000.0
        nir = nir / 10000.0

    denom = nir + red
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - red) / denom
    ndvi = np.where(np.isfinite(ndvi) & (denom != 0), ndvi, np.nan)
    valid = ndvi[~np.isnan(ndvi)]
    if valid.size == 0:
        return None
    return float(np.nanmean(valid))


def _dn_to_kelvin(dn: np.ndarray) -> np.ndarray:
    kelvin = dn.astype(np.float64) * LANDSAT_ST_SCALE + LANDSAT_ST_OFFSET
    kelvin = np.where((dn == LANDSAT_ST_FILL) | ~np.isfinite(dn) | (dn < 1), np.nan, kelvin)
    # Plausible Earth ST range ~250–350 K
    kelvin = np.where((kelvin >= 250) & (kelvin <= 360), kelvin, np.nan)
    return kelvin


def compute_lst_anomaly(
    st_b10_href: str,
    polygon_coords: list[list[list[float]]],
    radius_m: float | None = None,
) -> float | None:
    """
    LST anomaly (°C) = LST_pixel_mean - local_mean_LST within radius (default 5 km).
    Surface Temperature from Landsat ST_B10 (Kelvin, atmosphere-corrected).
    """
    radius_m = radius_m or settings.lst_anomaly_radius_m
    try:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_PROTOCOLS="https"):
            with rasterio.open(st_b10_href) as src:
                poly = shape(_polygon_geojson(polygon_coords))
                centroid = poly.centroid

                # Project to local azimuthal equidistant (meters) for buffer
                project = pyproj.Transformer.from_crs(
                    "EPSG:4326",
                    f"+proj=aeqd +lat_0={centroid.y} +lon_0={centroid.x} +datum=WGS84",
                    always_xy=True,
                ).transform
                project_back = pyproj.Transformer.from_crs(
                    f"+proj=aeqd +lat_0={centroid.y} +lon_0={centroid.x} +datum=WGS84",
                    "EPSG:4326",
                    always_xy=True,
                ).transform

                poly_m = shp_transform(project, poly)
                buffer_m = poly_m.centroid.buffer(radius_m)
                buffer_wgs = shp_transform(project_back, buffer_m)

                geom_aoi = transform_geom("EPSG:4326", src.crs, mapping(poly))
                geom_buf = transform_geom("EPSG:4326", src.crs, mapping(buffer_wgs))

                aoi_img, _ = rio_mask(src, [geom_aoi], crop=True, filled=False)
                buf_img, _ = rio_mask(src, [geom_buf], crop=True, filled=False)

                aoi_k = _dn_to_kelvin(np.ma.filled(aoi_img[0], np.nan))
                buf_k = _dn_to_kelvin(np.ma.filled(buf_img[0], np.nan))

                aoi_valid = aoi_k[np.isfinite(aoi_k)]
                buf_valid = buf_k[np.isfinite(buf_k)]
                if aoi_valid.size == 0 or buf_valid.size == 0:
                    return None

                lst_aoi = float(np.nanmean(aoi_valid))
                lst_local = float(np.nanmean(buf_valid))
                anomaly_k = lst_aoi - lst_local
                return anomaly_k  # Kelvin delta == Celsius delta
    except Exception as exc:
        logger.warning("LST anomaly failed for %s: %s", st_b10_href[:80], exc)
        return None


def compute_lst_anomaly_with_fallback(
    scenes: list[tuple[str, str]],
    polygon_coords: list[list[list[float]]],
    radius_m: float | None = None,
) -> tuple[float | None, str | None, list[str]]:
    """
    Try LST anomaly across Landsat scenes in order until one yields valid pixels.

    Args:
        scenes: list of (item_id, st_b10_href), already sorted (e.g. by cloud cover).
        polygon_coords: AOI polygon rings.
        radius_m: local mean radius (default 5 km).

    Returns:
        (anomaly_c, used_item_id, attempt_notes)
    """
    notes: list[str] = []
    if not scenes:
        return None, None, ["No Landsat ST_B10 scenes to try"]

    for idx, (item_id, href) in enumerate(scenes, start=1):
        logger.info("LST attempt %d/%d item=%s", idx, len(scenes), item_id)
        value = compute_lst_anomaly(href, polygon_coords, radius_m=radius_m)
        if value is not None:
            if idx > 1:
                notes.append(
                    f"LST: skipped {idx - 1} scene(s) with cloud/nodata over AOI; "
                    f"used Landsat item {item_id}"
                )
            return value, item_id, notes
        notes.append(f"LST: scene {item_id} returned no valid pixels (cloud/nodata edge)")

    notes.append(f"LST anomaly failed for all {len(scenes)} Landsat scene(s)")
    return None, None, notes


def compute_ndvi_with_fallback(
    scenes: list[tuple[str, str, str]],
    polygon_coords: list[list[list[float]]],
) -> tuple[float | None, str | None, list[str]]:
    """
    Try NDVI across Sentinel-2 scenes in order until one yields valid pixels.

    Args:
        scenes: list of (item_id, red_href, nir_href), sorted e.g. by cloud cover.
    """
    notes: list[str] = []
    if not scenes:
        return None, None, ["No Sentinel-2 scenes to try"]

    for idx, (item_id, red, nir) in enumerate(scenes, start=1):
        logger.info("NDVI attempt %d/%d item=%s", idx, len(scenes), item_id)
        value = compute_ndvi(red, nir, polygon_coords)
        if value is not None:
            if idx > 1:
                notes.append(
                    f"NDVI: skipped {idx - 1} scene(s) with no valid pixels; "
                    f"used Sentinel-2 item {item_id}"
                )
            return value, item_id, notes
        notes.append(f"NDVI: scene {item_id} returned no valid pixels")

    notes.append(f"NDVI failed for all {len(scenes)} Sentinel-2 scene(s)")
    return None, None, notes
