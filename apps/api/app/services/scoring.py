"""Heuristic scoring — transparent weighted formula, NOT a trained ML model."""

from __future__ import annotations

from app.models.schemas import ScoreBreakdown

WEIGHTS = {
    "lst_anomaly": 0.40,
    "fault_proximity": 0.25,
    "ndvi_stress": 0.20,
    "distance_to_springs": 0.15,
}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def normalize_lst_anomaly(anomaly_c: float | None) -> float:
    """
    Higher positive LST anomaly → higher geothermal interest.
    Maps roughly [-2°C, +8°C] → [0, 1].
    """
    if anomaly_c is None:
        return 0.0
    return _clamp01((anomaly_c + 2.0) / 10.0)


def normalize_fault_proximity(distance_m: float | None) -> float:
    """Closer to active fault → higher score. 0 m → 1, ≥25 km → 0."""
    if distance_m is None:
        return 0.0
    return _clamp01(1.0 - (distance_m / 25_000.0))


def normalize_ndvi_stress(ndvi_mean: float | None) -> float:
    """
    Vegetation stress / sparse cover can correlate with geothermal surface expression.
    Lower NDVI → higher stress score. NDVI 0.8 → 0, NDVI 0.1 → 1.
    """
    if ndvi_mean is None:
        return 0.0
    return _clamp01((0.8 - ndvi_mean) / 0.7)


def normalize_spring_distance(distance_m: float | None) -> float:
    """Closer to known thermal springs → higher score. 0 m → 1, ≥50 km → 0."""
    if distance_m is None:
        return 0.0
    return _clamp01(1.0 - (distance_m / 50_000.0))


def compute_heuristic_score(
    lst_anomaly_c: float | None,
    fault_proximity_m: float | None,
    ndvi_mean: float | None,
    spring_distance_m: float | None,
) -> tuple[float, ScoreBreakdown]:
    """
    score = 0.40*norm(lst_anomaly) + 0.25*norm(fault_proximity)
          + 0.20*norm(ndvi_stress) + 0.15*norm(distance_to_springs)

    Returns Heuristic Score in [0, 100] and per-component breakdown.
    """
    n_lst = normalize_lst_anomaly(lst_anomaly_c)
    n_fault = normalize_fault_proximity(fault_proximity_m)
    n_ndvi = normalize_ndvi_stress(ndvi_mean)
    n_spring = normalize_spring_distance(spring_distance_m)

    score_01 = (
        WEIGHTS["lst_anomaly"] * n_lst
        + WEIGHTS["fault_proximity"] * n_fault
        + WEIGHTS["ndvi_stress"] * n_ndvi
        + WEIGHTS["distance_to_springs"] * n_spring
    )
    score = round(score_01 * 100.0, 1)

    breakdown = ScoreBreakdown(
        lst_anomaly=round(n_lst * 100.0, 1),
        fault_proximity=round(n_fault * 100.0, 1),
        ndvi_stress=round(n_ndvi * 100.0, 1),
        distance_to_springs=round(n_spring * 100.0, 1),
        weights=dict(WEIGHTS),
    )
    return score, breakdown


def fault_proximity_pct(distance_m: float | None) -> float | None:
    """UI-friendly proximity percentage (100% = on fault, 0% = ≥25 km)."""
    if distance_m is None:
        return None
    return round(normalize_fault_proximity(distance_m) * 100.0, 1)
