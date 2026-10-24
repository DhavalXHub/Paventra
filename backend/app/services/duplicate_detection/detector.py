"""
Duplicate detection service for road damage reports and video observations.

Evaluates multi-source evidence:
  - Geographic distance (Haversine formula)
  - Time delta (days/seconds)
  - Damage category & distress type
  - Report status & resolution history
  - Perceptual image similarity (dHash / Hamming distance)

Explicitly distinguishes four operational scenarios:
  1. Repeated video-frame observations of one defect (consecutive frames)
  2. Multiple inspection observations of the same defect (recurring across survey runs)
  3. Multiple citizen complaints about the same defect (crowdsourced duplicate reports)
  4. Different nearby defects that must remain separate (e.g. adjacent crack and pothole)
"""
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import cv2
import numpy as np

from app.services.geospatial.distance import haversine_distance, validate_coordinates

logger = logging.getLogger(__name__)

# Configurable thresholds
DEFAULT_DISTANCE_THRESHOLD_M = 50.0   # meters
DEFAULT_TIME_THRESHOLD_DAYS = 30.0    # days
MIN_SIMILARITY_SCORE = 0.60


@dataclass
class DuplicateCandidate:
    report_id: str
    public_ref: str
    distance_meters: Optional[float]
    same_damage_type: bool
    time_diff_days: float
    similarity_score: float
    match_evidence: dict = field(default_factory=dict)
    distinction_category: str = "crowdsourced_duplicate"
    recommendation: str = "review"  # "auto_link", "review", "keep_separate"


def compute_image_perceptual_hash(image_path: Optional[str]) -> Optional[str]:
    """
    Computes a 64-bit difference hash (dHash) for an image.
    Resizes image to 9x8 grayscale and computes horizontal gradient sign.
    """
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        resized = cv2.resize(img, (9, 8), interpolation=cv2.INTER_AREA)
        diff = resized[:, 1:] > resized[:, :-1]
        return bytes(np.packbits(diff)).hex()
    except Exception as e:
        logger.debug(f"Could not compute perceptual hash for {image_path}: {e}")
        return None


def compute_image_similarity_from_hashes(
    hash1: Optional[str], hash2: Optional[str]
) -> Optional[float]:
    """
    Computes normalized Hamming similarity between two 64-bit hex perceptual hashes.
    Returns 0.0 (completely dissimilar) to 1.0 (identical images).
    """
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return None
    try:
        b1 = bytes.fromhex(hash1)
        b2 = bytes.fromhex(hash2)
        hamming_dist = sum(bin(x ^ y).count("1") for x, y in zip(b1, b2))
        return round(max(0.0, 1.0 - (hamming_dist / 64.0)), 4)
    except Exception:
        return None


def compute_similarity_score(
    distance_m: Optional[float],
    same_type: bool,
    time_diff_days: float,
    image_similarity: Optional[float] = None,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD_M,
    time_threshold: float = DEFAULT_TIME_THRESHOLD_DAYS,
) -> float:
    """
    Compute a composite similarity score [0-1].
    Higher = more likely duplicate.
    Incorporates image similarity when available.
    """
    # Geographic component
    geo_score = 0.0
    if distance_m is not None:
        geo_score = max(0.0, 1.0 - (distance_m / distance_threshold))

    # Damage type component
    type_score = 1.0 if same_type else 0.0

    # Temporal component
    time_score = max(0.0, 1.0 - (time_diff_days / time_threshold))

    if image_similarity is not None:
        # Weights: 40% geo, 20% type, 15% time, 25% image
        score = (
            0.40 * geo_score +
            0.20 * type_score +
            0.15 * time_score +
            0.25 * image_similarity
        )
    else:
        # Standard weights: 50% geo, 25% type, 25% time
        score = (
            0.50 * geo_score +
            0.25 * type_score +
            0.25 * time_score
        )

    return round(float(np.clip(score, 0.0, 1.0)), 4)


def classify_duplicate_relationship(
    source_new: str,
    source_ex: str,
    distance_m: Optional[float],
    same_type: bool,
    time_diff_days: float,
    image_similarity: Optional[float] = None,
) -> tuple[str, str, str]:
    """
    Distinguishes the four distinct duplicate/defect operational scenarios.

    Returns:
        (distinction_category, recommendation, reasoning)
    """
    # Scenario 4: Different nearby defects that must remain separate
    if not same_type and (distance_m is not None and distance_m <= 60.0):
        return (
            "nearby_distinct_defect",
            "keep_separate",
            "Different defect category situated nearby along the same roadway corridor; should remain independent."
        )

    # Scenario 1: Repeated video-frame observations of one defect
    # Both from inspection and within 30 seconds (or distance <= 8m)
    if source_new == "inspection" and source_ex == "inspection":
        time_diff_seconds = time_diff_days * 86400.0
        if time_diff_seconds <= 30.0 or (distance_m is not None and distance_m <= 8.0):
            return (
                "repeated_video_frame",
                "auto_link",
                "Consecutive survey frames capturing the same defect in the same pass (temporal delta <= 30s)."
            )
        else:
            # Scenario 2: Multiple inspection observations across survey runs
            return (
                "multi_pass_inspection",
                "review",
                "Recurring defect observed across distinct inspection passes at the same coordinates."
            )

    # Scenario 3: Multiple citizen complaints about the same defect
    if source_new == "citizen" and source_ex == "citizen":
        if distance_m is not None and distance_m <= 25.0 and same_type:
            rec = "auto_link" if (image_similarity and image_similarity >= 0.75) else "review"
            return (
                "crowdsourced_duplicate",
                rec,
                "Multiple citizen reports submitted for the same road defect in close spatial proximity."
            )

    # Default cross-source (Citizen vs Inspection)
    return (
        "crowdsourced_duplicate",
        "review",
        "Potential match between citizen report and inspection survey defect."
    )


def find_duplicate_candidates(
    new_report_lat: Optional[float],
    new_report_lon: Optional[float],
    new_report_type: str,
    new_report_created_at,
    existing_reports: List[Dict[str, Any]],
    new_report_source: str = "citizen",
    new_report_image_hash: Optional[str] = None,
    distance_threshold_m: float = DEFAULT_DISTANCE_THRESHOLD_M,
    time_threshold_days: float = DEFAULT_TIME_THRESHOLD_DAYS,
) -> List[DuplicateCandidate]:
    """
    Compare a new report against existing open reports to identify duplicates.

    Args:
        new_report_lat, new_report_lon: Coordinates of report under evaluation.
        new_report_type: Damage category string.
        new_report_created_at: Datetime object.
        existing_reports: List of dicts representing existing reports.
        new_report_source: "citizen" | "inspection"
        new_report_image_hash: Optional 64-bit hex perceptual hash.
        distance_threshold_m: Search radius in meters.
        time_threshold_days: Temporal window in days.

    Returns:
        Candidates sorted by similarity score descending.
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
            # Skip if clearly outside 3x distance threshold
            if distance_m > distance_threshold_m * 3.0:
                continue

        # Time difference in days
        try:
            if hasattr(new_report_created_at, "replace"):
                t1 = (
                    new_report_created_at.replace(tzinfo=timezone.utc)
                    if new_report_created_at.tzinfo is None
                    else new_report_created_at
                )
            else:
                t1 = new_report_created_at
            t2 = existing.get("created_at")
            if hasattr(t2, "replace"):
                t2 = t2.replace(tzinfo=timezone.utc) if t2.tzinfo is None else t2
            time_diff_days = abs((t1 - t2).total_seconds()) / 86400.0
        except Exception:
            time_diff_days = 0.0

        ex_type = existing.get("damage_type", "unknown")
        same_type = (ex_type == new_report_type and new_report_type != "unknown")

        # Image similarity
        ex_hash = existing.get("image_hash")
        img_sim = None
        if new_report_image_hash and ex_hash:
            img_sim = compute_image_similarity_from_hashes(new_report_image_hash, ex_hash)

        # Composite similarity score
        score = compute_similarity_score(
            distance_m=distance_m,
            same_type=same_type,
            time_diff_days=time_diff_days,
            image_similarity=img_sim,
            distance_threshold=distance_threshold_m,
            time_threshold=time_threshold_days,
        )

        ex_source = existing.get("source", "citizen")
        dist_cat, rec, reason = classify_duplicate_relationship(
            source_new=new_report_source,
            source_ex=ex_source,
            distance_m=distance_m,
            same_type=same_type,
            time_diff_days=time_diff_days,
            image_similarity=img_sim,
        )

        # Candidate thresholding
        if score >= MIN_SIMILARITY_SCORE or dist_cat == "repeated_video_frame":
            candidates.append(
                DuplicateCandidate(
                    report_id=existing.get("id", ""),
                    public_ref=existing.get("public_ref", ""),
                    distance_meters=round(distance_m, 2) if distance_m is not None else None,
                    same_damage_type=same_type,
                    time_diff_days=round(time_diff_days, 2),
                    similarity_score=score,
                    match_evidence={
                        "distance_m": round(distance_m, 2) if distance_m is not None else None,
                        "same_damage_type": same_type,
                        "time_diff_days": round(time_diff_days, 2),
                        "image_similarity": img_sim,
                        "score": score,
                        "distinction_category": dist_cat,
                        "recommendation": rec,
                        "reasoning": reason,
                    },
                    distinction_category=dist_cat,
                    recommendation=rec,
                )
            )

    return sorted(candidates, key=lambda c: c.similarity_score, reverse=True)
