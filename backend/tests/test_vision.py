"""
Comprehensive test suite for Computer Vision & Severity Estimation.
Validates:
  - RDD2022 model loading and class mapping.
  - Image validation (missing, corrupt, dimension bounds).
  - Feature-grounded 2D geometric severity estimation.
  - Transparent provisional disclaimers and review-required triggers.
"""
import os
import cv2
import numpy as np
import pytest

from ml.inference.detector import RoadDamageInferenceEngine, RDD_CLASS_MAP
from ml.inference.severity import estimate_damage_severity, SeverityAssessment
from app.services.vision.inference import detector


def test_rdd_class_mapping():
    """Verify standard RDD2022 4-class taxonomy."""
    assert RDD_CLASS_MAP[0] == ("D00", "longitudinal_crack", "crack")
    assert RDD_CLASS_MAP[1] == ("D10", "transverse_crack", "crack")
    assert RDD_CLASS_MAP[2] == ("D20", "alligator_crack", "crack")
    assert RDD_CLASS_MAP[3] == ("D40", "pothole", "pothole")


def test_cv_engine_available_with_rdd_weights():
    """Verify that RoadDamageInferenceEngine finds weights and initializes."""
    engine = RoadDamageInferenceEngine()
    assert engine.is_available() is True


def test_invalid_image_path_returns_clean_error():
    """Missing files should return a structured error without crashing."""
    engine = RoadDamageInferenceEngine()
    res = engine.infer("non_existent_file_path_12345.jpg")
    assert res.model_available is True
    assert "File not found" in (res.error or "")


def test_corrupt_or_empty_image_handling(tmp_path):
    """Empty or non-image files should return format error."""
    corrupt_file = tmp_path / "corrupt.jpg"
    corrupt_file.write_bytes(b"not an image file content")
    
    engine = RoadDamageInferenceEngine()
    res = engine.infer(str(corrupt_file))
    assert res.model_available is True
    assert "Unsupported format or corrupt image" in (res.error or "")


def test_image_dimensions_too_small(tmp_path):
    """Images smaller than 10x10 pixels should be rejected gracefully."""
    small_file = tmp_path / "tiny.jpg"
    tiny_img = np.zeros((5, 5, 3), dtype=np.uint8)
    cv2.imwrite(str(small_file), tiny_img)

    engine = RoadDamageInferenceEngine()
    res = engine.infer(str(small_file))
    assert res.model_available is True
    assert "too small" in (res.error or "")


def test_severity_estimation_pothole_scaling():
    """Verify pothole area ratio scales severity accurately."""
    # Small pothole (< 2% area)
    detections_small = [
        {"bbox": [0.4, 0.4, 0.48, 0.48], "damage_type": "pothole", "confidence": 0.85}
    ]
    sev_small = estimate_damage_severity(detections_small, image_width=640, image_height=640)
    assert sev_small is not None
    assert sev_small.level == "low"
    assert sev_small.score < 4.5

    # Large severe pothole (> 12% area)
    detections_large = [
        {"bbox": [0.2, 0.2, 0.6, 0.6], "damage_type": "pothole", "confidence": 0.90}
    ]
    sev_large = estimate_damage_severity(detections_large, image_width=640, image_height=640)
    assert sev_large is not None
    assert sev_large.level == "critical"
    assert sev_large.score >= 8.5
    assert sev_large.provisional is True


def test_severity_estimation_crack_geometry():
    """Verify aspect ratio and elongation influence crack severity."""
    # Highly elongated linear crack spanning the road
    detections_linear = [
        {"bbox": [0.1, 0.45, 0.9, 0.50], "damage_type": "crack", "confidence": 0.82}
    ]
    sev = estimate_damage_severity(detections_linear, image_width=640, image_height=640)
    assert sev is not None
    assert sev.features["max_aspect_ratio"] >= 4.0
    assert sev.level in ["moderate", "high"]


def test_severity_review_required_and_disclaimer():
    """Ambiguous or marginal detections must trigger review_required flag and carry disclaimer."""
    # Marginal confidence (0.50) triggers review
    detections = [
        {"bbox": [0.4, 0.4, 0.45, 0.45], "damage_type": "pothole", "confidence": 0.50}
    ]
    sev = estimate_damage_severity(detections, image_width=640, image_height=640)
    assert sev is not None
    assert sev.review_required is True
    assert "Provisional 2D image-derived estimate" in sev.disclaimer
    assert "depth" in sev.disclaimer.lower()
