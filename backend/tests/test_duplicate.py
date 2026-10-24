"""Unit tests for duplicate detection service."""
from datetime import datetime, timezone, timedelta
from app.services.duplicate_detection.detector import (
    find_duplicate_candidates, compute_similarity_score
)


def test_compute_similarity_score():
    # Exactly same location, same type, same day -> high similarity
    score = compute_similarity_score(
        distance_m=5.0,
        same_type=True,
        time_diff_days=0.5,
        distance_threshold=50.0,
        time_threshold=30.0,
    )
    assert score > 0.8


def test_far_apart_low_similarity():
    # Far apart (> 50m threshold)
    score = compute_similarity_score(
        distance_m=100.0,
        same_type=False,
        time_diff_days=40.0,
        distance_threshold=50.0,
        time_threshold=30.0,
    )
    assert score == 0.0


def test_find_duplicate_candidates():
    now = datetime.now(timezone.utc)
    existing = [
        {
            "id": "rpt-1",
            "public_ref": "PAV-11111111",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "damage_type": "pothole",
            "created_at": now - timedelta(days=2),
            "status": "submitted",
        },
        {
            "id": "rpt-2",
            "public_ref": "PAV-22222222",
            "latitude": 28.6139,  # Far away
            "longitude": 77.2090,
            "damage_type": "pothole",
            "created_at": now - timedelta(days=1),
            "status": "submitted",
        }
    ]

    # Report right next to rpt-1
    candidates = find_duplicate_candidates(
        new_report_lat=19.0761,
        new_report_lon=72.8777,
        new_report_type="pothole",
        new_report_created_at=now,
        existing_reports=existing,
        distance_threshold_m=50.0,
    )

    assert len(candidates) == 1
    assert candidates[0].public_ref == "PAV-11111111"
    assert candidates[0].same_damage_type is True
    assert candidates[0].distance_meters < 50.0
