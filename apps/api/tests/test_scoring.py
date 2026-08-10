"""Unit tests for heuristic scoring (no network / raster I/O)."""

from app.services.scoring import (
    compute_heuristic_score,
    normalize_fault_proximity,
    normalize_lst_anomaly,
    normalize_ndvi_stress,
    normalize_spring_distance,
)


def test_normalize_ranges():
    assert normalize_lst_anomaly(8.0) == 1.0
    assert normalize_lst_anomaly(-2.0) == 0.0
    assert normalize_fault_proximity(0.0) == 1.0
    assert normalize_fault_proximity(25_000.0) == 0.0
    assert normalize_ndvi_stress(0.1) == 1.0
    assert normalize_ndvi_stress(0.8) == 0.0
    assert normalize_spring_distance(0.0) == 1.0
    assert normalize_spring_distance(50_000.0) == 0.0


def test_heuristic_score_bounds():
    score, breakdown = compute_heuristic_score(8.0, 0.0, 0.1, 0.0)
    assert 0 <= score <= 100
    assert breakdown.weights["lst_anomaly"] == 0.40
    assert score == 100.0


def test_heuristic_score_mid():
    score, _ = compute_heuristic_score(None, None, None, None)
    assert score == 0.0
