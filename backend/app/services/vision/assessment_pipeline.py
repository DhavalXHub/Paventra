"""
Automatic road-damage assessment and prioritization pipeline.
Integrates YOLOv8 object detection with Mamdani Fuzzy Inference System.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.report import Report, DamageType, SeverityLevel, FuzzyPriorityAssessment
from app.services.vision.inference import detector
from app.services.prioritization.fuzzy_engine import compute_priority

logger = logging.getLogger(__name__)

MODEL_VERSION = "RDD2022-YOLOv8n / Mamdani-FIS-23"


def derive_traffic_exposure(address_hint: Optional[str]) -> Tuple[float, str]:
    """
    Derives traffic exposure score from municipal GIS / road classification hint if available.
    Documented default: safe neutral midpoint 5.0 with 'estimated_default'.
    """
    if not address_hint:
        return 5.0, "estimated_default"

    addr_lower = address_hint.lower()
    if any(k in addr_lower for k in ["expressway", "highway", "arterial", "flyover", "ring road", "main road"]):
        return 8.5, "road_class_arterial"
    elif any(k in addr_lower for k in ["avenue", "marg", "junction", "circle", "link road"]):
        return 7.0, "road_class_collector"
    elif any(k in addr_lower for k in ["lane", "gali", "colony", "residential", "street"]):
        return 3.5, "road_class_local"
    return 5.0, "estimated_default"


def derive_safety_urgency(severity: SeverityLevel, damage_type: DamageType, address_hint: Optional[str]) -> Tuple[float, str]:
    """
    Derives safety urgency based on damage hazard and pedestrian/cyclist proximity.
    Potholes and critical failures have heightened sudden impact hazard.
    """
    addr_lower = (address_hint or "").lower()
    is_pedestrian_zone = any(k in addr_lower for k in ["school", "hospital", "market", "crossing", "station", "temple"])

    if severity == SeverityLevel.CRITICAL:
        base_urgency = 8.5 if is_pedestrian_zone else 7.5
    elif severity == SeverityLevel.HIGH:
        base_urgency = 7.5 if is_pedestrian_zone else 6.5
    elif severity == SeverityLevel.MODERATE:
        base_urgency = 6.0 if is_pedestrian_zone else 5.0
    else:
        base_urgency = 4.0 if is_pedestrian_zone else 3.0

    provenance = "poi_proximity_elevated" if is_pedestrian_zone else "damage_hazard_derived"
    return base_urgency, provenance


async def run_automatic_assessment(
    report: Report,
    image_path: Optional[str],
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Executes the full automated assessment workflow:
    1. Validates image presence and accessibility.
    2. Runs YOLO road-damage detector.
    3. Derives 2D geometric severity (distress footprint, aspect ratio, hazard index).
    4. Computes Mamdani fuzzy priority score.
    5. Persists assessment metadata and FuzzyPriorityAssessment record.
    """
    now = datetime.now(timezone.utc)
    report.ai_model_name = MODEL_VERSION
    report.ai_assessed_at = now

    # Safeguard 1: No image provided
    if not image_path:
        report.assessment_status = "NO_IMAGE"
        report.priority_explanation = {
            "status": "NO_IMAGE",
            "message": "No photograph provided with report. Automated Computer Vision assessment unavailable.",
            "review_required": True,
        }
        return {"status": "NO_IMAGE"}

    path_obj = Path(image_path)
    if not path_obj.exists() or path_obj.stat().st_size == 0:
        report.assessment_status = "NO_IMAGE"
        report.priority_explanation = {
            "status": "NO_IMAGE",
            "message": f"Photograph file '{path_obj.name}' is missing or empty.",
            "review_required": True,
        }
        return {"status": "NO_IMAGE"}

    # Safeguard 2: Model availability
    if not detector.is_available():
        report.assessment_status = "PENDING_MODEL"
        report.priority_explanation = {
            "status": "PENDING_MODEL",
            "message": "Computer vision model is not loaded or configured. Awaiting model availability.",
            "review_required": True,
        }
        return {"status": "PENDING_MODEL"}

    # Run YOLOv8 detection
    result = detector.infer(str(path_obj))
    if result.error:
        report.assessment_status = "FAILED"
        report.priority_explanation = {
            "status": "FAILED",
            "message": f"Computer vision inference error: {result.error}",
            "review_required": True,
        }
        return {"status": "FAILED"}

    report.ai_inference_ms = result.inference_ms

    # Safeguard 3: No detections found above threshold
    if not result.detections:
        report.assessment_status = "NO_DETECTIONS"
        # ai_confidence stays None — zero detections means no AI confidence to report
        report.ai_confidence = None
        report.ai_damage_type = None  # Model did not detect any category
        report.ai_bounding_boxes = {"detections": []}
        # damage_type remains as citizen-provided value (or UNKNOWN) — not overwritten by AI
        report.priority_explanation = {
            "status": "NO_DETECTIONS",
            "message": "No road distress detected above confidence threshold (0.40). Requires manual verification.",
            "review_required": True,
        }
        return {"status": "NO_DETECTIONS"}

    best = result.best_detection
    report.ai_confidence = best.confidence
    report.ai_damage_type = best.damage_type

    # Map YOLO class to DamageType
    dtype_map = {
        "pothole": DamageType.POTHOLE,
        "crack": DamageType.CRACK,
    }
    report.damage_type = dtype_map.get(best.damage_type, DamageType.OTHER)

    # Severity estimation from 2D geometry
    sev_obj = result.severity_assessment
    sev_numeric = None
    if sev_obj:
        sev_map = {
            "low": SeverityLevel.LOW,
            "moderate": SeverityLevel.MODERATE,
            "high": SeverityLevel.HIGH,
            "critical": SeverityLevel.CRITICAL,
        }
        report.severity = sev_map.get(sev_obj.level, SeverityLevel.MODERATE)
        report.severity_is_estimated = True
        report.original_severity = report.severity
        sev_numeric = sev_obj.score
    elif best.confidence >= 0.75:
        report.severity = SeverityLevel.HIGH
        report.severity_is_estimated = True
        report.original_severity = report.severity
        sev_numeric = 7.5
    else:
        report.severity = SeverityLevel.MODERATE
        report.severity_is_estimated = True
        report.original_severity = report.severity
        sev_numeric = 5.0

    report.ai_bounding_boxes = {
        "detections": [
            {
                "class_code": d.class_code,
                "damage_type": d.damage_type,
                "confidence": d.confidence,
                "bbox": d.bbox_xyxy,
            }
            for d in result.detections
        ],
        "severity_estimation": {
            "level": sev_obj.level if sev_obj else report.severity.value,
            "score": sev_obj.score if sev_obj else sev_numeric,
            "method": sev_obj.method if sev_obj else "geometric_heuristic",
            "features": sev_obj.features if sev_obj else {},
            "confidence": sev_obj.confidence if sev_obj else best.confidence,
            "uncertainty": sev_obj.uncertainty if sev_obj else 0.2,
            "review_required": sev_obj.review_required if sev_obj else False,
            "provisional": True,
            "disclaimer": (
                "Provisional 2D image-derived estimate based on visible surface distress area and geometry. "
                "Ordinary RGB photographs cannot measure true volumetric cavity depth or pavement sub-base integrity."
            ),
        },
    }

    # Set assessment status
    if sev_obj and sev_obj.review_required:
        report.assessment_status = "REVIEW_REQUIRED"
    else:
        report.assessment_status = "COMPLETED"

    # Soft Computing Mamdani FIS Prioritization
    created = report.created_at or now
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    days_unresolved = max(0.0, (now - created).total_seconds() / 86400.0)

    traffic_score, traffic_prov = derive_traffic_exposure(report.address_hint)
    safety_score, safety_prov = derive_safety_urgency(report.severity, report.damage_type, report.address_hint)

    pr = compute_priority(
        severity_label=report.severity.value,
        traffic_exposure=traffic_score,
        time_unresolved_days=days_unresolved,
        safety_urgency=safety_score,
        severity_numeric=sev_numeric,
    )

    report.priority_score = pr.priority_score
    report.original_priority_score = pr.priority_score
    report.priority_explanation = {
        "label": pr.priority_label,
        "score": pr.priority_score,
        "factors": pr.top_contributing_factors,
        "engine": pr.engine_used,
        "inputs": pr.inputs,
        "baseline_score": pr.baseline_score,
        "provenance": {
            "traffic_exposure": traffic_prov,
            "safety_urgency": safety_prov,
            "days_unresolved": round(days_unresolved, 2),
        },
    }

    # Persist or update FuzzyPriorityAssessment
    existing_assessment_res = await db.execute(
        select(FuzzyPriorityAssessment).where(FuzzyPriorityAssessment.report_id == report.id)
    )
    assessment = existing_assessment_res.scalar_one_or_none()
    if not assessment:
        assessment = FuzzyPriorityAssessment(
            report_id=report.id,
            severity_input=pr.inputs["severity"],
            traffic_exposure_input=pr.inputs["traffic_exposure"],
            time_unresolved_days=pr.inputs["time_unresolved_days"],
            safety_urgency_input=pr.inputs["safety_urgency"],
            priority_score=pr.priority_score,
            priority_label=pr.priority_label,
            top_contributing_factors=pr.top_contributing_factors,
            baseline_score=pr.baseline_score,
        )
        db.add(assessment)
    else:
        assessment.severity_input = pr.inputs["severity"]
        assessment.traffic_exposure_input = pr.inputs["traffic_exposure"]
        assessment.time_unresolved_days = pr.inputs["time_unresolved_days"]
        assessment.safety_urgency_input = pr.inputs["safety_urgency"]
        assessment.priority_score = pr.priority_score
        assessment.priority_label = pr.priority_label
        assessment.top_contributing_factors = pr.top_contributing_factors
        assessment.baseline_score = pr.baseline_score
        assessment.computed_at = now

    return {
        "status": report.assessment_status,
        "damage_type": report.damage_type.value,
        "confidence": report.ai_confidence,
        "severity": report.severity.value,
        "priority_score": report.priority_score,
        "priority_label": pr.priority_label,
    }
