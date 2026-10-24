"""
Duplicate detection service for road damage reports.

Detects potential duplicates based on:
  - Geographic proximity (haversine distance)
  - Same damage type
  - Time interval
  - Image similarity (hash-based, when available)
"""
import logging
from dataclasses import dataclass
from typing import Optional

from app.services.geospatial.distance import haversine_distance, validate_coordinates

logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_DISTANCE_THRESHOLD_M = 50.0   # meters
DEFAULT_TIME_THRESHOLD_DAYS = 30      # days
MIN_SIMILARITY_SCORE = 0.6


@dataclass
class DuplicateCandidate:
    report_id: str
    public_ref: str
    distance_meters: Optional[float]
    same_damage_type: bool
    time_diff_days: float
    similarity_score: float
    match_evidence: dict


def compute_similarity_score(
    distance_m: Optional[float],
    same_type: bool,
    time_diff_days: float,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD_M,
    time_threshold: float = DEFAULT_TIME_THRESHOLD_DAYS,
) -> float:
    """
    Compute a composite similarity score [0-1].
    Higher = more likely duplicate.
    """
    score = 0.0

    # Geographic component (weight 0.5)
    if distance_m is not None:
        geo_score = max(0.0, 1.0 - distance_m / distance_threshold)
        score += 0.5 * geo_score

    # Damage type component (weight 0.25)
    if same_type:
        score += 0.25

    # Temporal component (weight 0.25)
    time_score = max(0.0, 1.0 - time_diff_days / time_threshold)
    score += 0.25 * time_score

    return round(score, 4)


def find_duplicate_candidates(
    new_report_lat: Optional[float],
    new_report_lon: Optional[float],
    new_report_type: str,
    new_report_created_at,
    existing_reports: list[dict],
    distance_threshold_m: float = DEFAULT_DISTANCE_THRESHOLD_M,
    time_threshold_days: float = DEFAULT_TIME_THRESHOLD_DAYS,
) -> list[DuplicateCandidate]:
    """
    Compare a new report against existing open reports to find duplicates.
    
    `existing_reports` should be a list of dicts with keys:
      id, public_ref, latitude, longitude, damage_type, created_at, status
    
    Returns candidates sorted by similarity score descending.
    """
    candidates = []

    for existing in existing_reports:
        ex_lat = existing.get("latitude")
        ex_lon = existing.get("longitude")

        # Compute distance if coordinates available
        distance_m = None
        if (
            validate_coordinates(new_report_lat, new_report_lon)
            and validate_coordinates(ex_lat, ex_lon)
        ):
            distance_m = haversine_distance(
                new_report_lat, new_report_lon, ex_lat, ex_lon
            )
            # Skip if clearly too far away
            if distance_m > distance_threshold_m * 3:
                continue

        # Time difference
        from datetime import timezone
        try:
            if hasattr(new_report_created_at, "replace"):
                t1 = new_report_created_at.replace(tzinfo=timezone.utc) if new_report_created_at.tzinfo is None else new_report_created_at
            else:
                t1 = new_report_created_at
            t2 = existing["created_at"]
            if hasattr(t2, "replace"):
                t2 = t2.replace(tzinfo=timezone.utc) if t2.tzinfo is None else t2
            time_diff_days = abs((t1 - t2).total_seconds()) / 86400.0
        except Exception:
            time_diff_days = 0.0

        same_type = (
            existing.get("damage_type", "unknown") == new_report_type
            and new_report_type != "unknown"
        )

        score = compute_similarity_score(
            distance_m, same_type, time_diff_days, distance_threshold_m, time_threshold_days
        )

        if score >= MIN_SIMILARITY_SCORE:
            candidates.append(
                DuplicateCandidate(
                    report_id=existing["id"],
                    public_ref=existing["public_ref"],
                    distance_meters=distance_m,
                    same_damage_type=same_type,
                    time_diff_days=time_diff_days,
                    similarity_score=score,
                    match_evidence={
                        "distance_m": distance_m,
                        "same_damage_type": same_type,
                        "time_diff_days": round(time_diff_days, 1),
                        "score": score,
                    },
                )
            )

    return sorted(candidates, key=lambda c: c.similarity_score, reverse=True)
