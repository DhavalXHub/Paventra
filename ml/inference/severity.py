"""
Severity Estimation Module for Road Distress Detections.

Separates road damage detection from severity assessment.
Estimates severity using documented measurable 2D geometric features:
  - Visible damaged area ratio (bounding box footprint / total image area)
  - Distress elongation & aspect ratio (max dimension / min dimension)
  - Damage category hazard index (pothole vs alligator crack vs linear cracks)
  - Multi-defect density in the camera field-of-view

Safeguards:
  - Explicitly flags all image-derived estimates as provisional.
  - Transparently returns the calculation method, evidence features, and uncertainty.
  - Flags ambiguous cases as `review_required: true`.
  - Never claims to measure true volumetric depth or structural subgrade integrity from ordinary 2D RGB imagery.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class SeverityAssessment:
    level: str                  # "low", "moderate", "high", "critical"
    score: float                # 1.0 to 10.0
    method: str                 # "visible_damaged_area_and_geometry"
    features: Dict[str, Any]    # measurable supporting evidence
    confidence: float           # 0.0 to 1.0
    uncertainty: float          # 0.0 to 1.0
    review_required: bool       # Flag for coordinator review
    provisional: bool = True    # Always true for 2D optical estimation
    disclaimer: str = (
        "Provisional 2D image-derived estimate based on visible surface distress area and geometry. "
        "Ordinary RGB photographs cannot measure true volumetric cavity depth or pavement sub-base integrity."
    )


def estimate_damage_severity(
    detections: List[Dict[str, Any]],
    image_width: int,
    image_height: int,
) -> Optional[SeverityAssessment]:
    """
    Computes an explainable, feature-grounded severity assessment from detected road distress.

    Args:
        detections: List of detection dicts with 'bbox' ([x1, y1, x2, y2] normalized), 'class_code', 'damage_type', 'confidence'.
        image_width: Pixel width of input image.
        image_height: Pixel height of input image.

    Returns:
        SeverityAssessment or None if no detections are present.
    """
    if not detections or image_width <= 0 or image_height <= 0:
        return None

    # 1. Calculate individual and total visible damaged area ratio
    total_area_ratio = 0.0
    max_area_ratio = 0.0
    max_aspect_ratio = 1.0
    best_conf = 0.0
    primary_category = "unknown"

    for det in detections:
        bbox = det.get("bbox", [0, 0, 0, 0])
        x1, y1, x2, y2 = bbox
        box_w = max(0.0, x2 - x1)
        box_h = max(0.0, y2 - y1)
        area = box_w * box_h
        total_area_ratio += area
        if area > max_area_ratio:
            max_area_ratio = area
            primary_category = det.get("damage_type", "unknown")
            conf = det.get("confidence", 0.5)
            if conf > best_conf:
                best_conf = conf

        # Aspect ratio (elongation)
        min_dim = max(1e-4, min(box_w, box_h))
        aspect = max(box_w, box_h) / min_dim
        if aspect > max_aspect_ratio:
            max_aspect_ratio = aspect

    # Clamp total area ratio to 1.0
    total_area_ratio = min(1.0, total_area_ratio)
    area_percent = round(total_area_ratio * 100, 2)

    # 2. Base severity calculation by damage type and visible footprint
    # Distress type hazard weights:
    # - Pothole: high sudden impact hazard to vehicle suspension and two-wheelers.
    # - Alligator crack: progressive fatigue failure of asphalt mat.
    # - Longitudinal / Transverse: early-stage reflection or joint cracking.
    if primary_category == "pothole":
        if total_area_ratio < 0.02:      # < 2% of image
            base_score = 3.5
            level = "low"
        elif total_area_ratio < 0.06:    # 2% - 6% of image
            base_score = 6.0
            level = "moderate"
        elif total_area_ratio < 0.12:    # 6% - 12% of image
            base_score = 8.0
            level = "high"
        else:                            # > 12% of image
            base_score = 9.5
            level = "critical"
    elif primary_category == "crack" or "crack" in primary_category:
        if total_area_ratio < 0.03 and max_aspect_ratio < 4.0:
            base_score = 2.5
            level = "low"
        elif total_area_ratio < 0.08 or max_aspect_ratio >= 4.0:
            base_score = 5.0
            level = "moderate"
        else:
            base_score = 7.5
            level = "high"
    else:  # surface deterioration / other
        if total_area_ratio < 0.05:
            base_score = 3.0
            level = "low"
        else:
            base_score = 5.5
            level = "moderate"

    # Multi-defect adjustment (each additional defect adds 0.4 up to +1.2)
    multi_defect_bonus = min(1.2, max(0, len(detections) - 1) * 0.4)
    final_score = min(10.0, round(base_score + multi_defect_bonus, 2))

    # Recalculate level after multi-defect adjustment
    if final_score >= 8.5:
        level = "critical"
    elif final_score >= 7.0:
        level = "high"
    elif final_score >= 4.5:
        level = "moderate"
    else:
        level = "low"

    # 3. Determine if human coordinator review is required
    # Review is required if:
    # - Confidence is marginal (< 0.60)
    # - Area is near class boundaries (e.g. 1.8% - 2.2% or 5.5% - 6.5%)
    # - Multiple distinct defects detected
    boundary_ambiguity = (
        (0.018 <= total_area_ratio <= 0.025) or
        (0.055 <= total_area_ratio <= 0.065) or
        (0.115 <= total_area_ratio <= 0.125)
    )
    review_required = bool(
        best_conf < 0.60 or
        boundary_ambiguity or
        len(detections) > 2 or
        level in ["high", "critical"]
    )

    features = {
        "visible_area_percent": area_percent,
        "max_bounding_box_area_ratio": round(max_area_ratio, 4),
        "max_aspect_ratio": round(max_aspect_ratio, 2),
        "detections_count": len(detections),
        "primary_damage_type": primary_category,
        "boundary_ambiguity": boundary_ambiguity,
    }

    uncertainty = round(max(0.05, 1.0 - best_conf), 4)

    return SeverityAssessment(
        level=level,
        score=final_score,
        method="visible_damaged_area_and_geometry",
        features=features,
        confidence=round(best_conf, 4),
        uncertainty=uncertainty,
        review_required=review_required,
        provisional=True,
    )
