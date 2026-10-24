"""Unit tests for duplicate detection service across all four operational scenarios."""
from datetime import datetime, timezone, timedelta
from app.services.duplicate_detection.detector import (
    find_duplicate_candidates,
    compute_similarity_score,
    compute_image_perceptual_hash,
    compute_image_similarity_from_hashes,
    classify_duplicate_relationship,
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


def test_repeated_video_frame_candidate():
    """Scenario 1: Repeated video frames within 30 seconds should be classified as repeated_video_frame."""
    dist_cat, rec, reason = classify_duplicate_relationship(
        source_new="inspection",
        source_ex="inspection",
        distance_m=4.0,
        same_type=True,
        time_diff_days=0.0001,  # ~8.6 seconds
    )
    assert dist_cat == "repeated_video_frame"
    assert rec == "auto_link"
    assert "Consecutive survey frames" in reason


def test_multi_pass_inspection_candidate():
    """Scenario 2: Recurring defect found across different inspection runs/dates at the same location."""
    dist_cat, rec, reason = classify_duplicate_relationship(
        source_new="inspection",
        source_ex="inspection",
        distance_m=12.0,
        same_type=True,
        time_diff_days=14.0,  # 2 weeks later
    )
    assert dist_cat == "multi_pass_inspection"
    assert rec == "review"
    assert "Recurring defect" in reason


def test_crowdsourced_citizen_duplicate():
    """Scenario 3: Multiple citizens reporting the same defect nearby."""
    dist_cat, rec, reason = classify_duplicate_relationship(
        source_new="citizen",
        source_ex="citizen",
        distance_m=10.0,
        same_type=True,
        time_diff_days=1.5,
    )
    assert dist_cat == "crowdsourced_duplicate"
    assert rec in ["review", "auto_link"]


def test_nearby_distinct_defect_kept_separate():
    """Scenario 4: Different defects along the same road (e.g. pothole next to a crack) must be kept separate."""
    dist_cat, rec, reason = classify_duplicate_relationship(
        source_new="citizen",
        source_ex="citizen",
        distance_m=15.0,
        same_type=False,  # e.g. crack vs pothole
        time_diff_days=0.5,
    )
    assert dist_cat == "nearby_distinct_defect"
    assert rec == "keep_separate"
    assert "Different defect category" in reason


def test_image_perceptual_hash_similarity():
    """Verify perceptual hash comparison behaves consistently on identical vs modified hashes."""
    # Identical 64-bit hex hashes -> similarity = 1.0
    h1 = "ffff0000ffff0000"
    h2 = "ffff0000ffff0000"
    sim = compute_image_similarity_from_hashes(h1, h2)
    assert sim == 1.0

    # 1 bit difference -> 63/64 = 0.9844
    h3 = "ffff0000ffff0001"
    sim2 = compute_image_similarity_from_hashes(h1, h3)
    assert sim2 > 0.95

    # Completely inverted -> similarity = 0.0
    h4 = "0000ffff0000ffff"
    sim3 = compute_image_similarity_from_hashes(h1, h4)
    assert sim3 == 0.0
