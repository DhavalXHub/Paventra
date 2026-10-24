"""
Video inspection processing service.
Extracts frames, performs road damage inference with YOLO, associates GPS if synchronized track is provided,
and deduplicates sequential observations to prevent duplicate repair cases.
"""
import os
import cv2
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.inspection import InspectionJob, InspectionFrame, InspectionStatus
from app.models.report import Report, ReportSource, ReportStatus, DamageType, SeverityLevel, LocationSource
from app.services.vision.inference import detector, save_annotated_image
from app.services.prioritization.fuzzy_engine import compute_priority

logger = logging.getLogger(__name__)


def parse_gps_track(gps_track_path: Optional[str]) -> List[Dict[str, Any]]:
    """
    Parses a synchronized GPS track file (JSON or CSV).
    Format expected:
    [
      {"timestamp_seconds": 0.0, "latitude": 28.6139, "longitude": 77.2090},
      {"timestamp_seconds": 1.0, "latitude": 28.6140, "longitude": 77.2092}
    ]
    Safeguard: If no GPS file is provided, exact coordinates are never inferred from pixels.
    """
    if not gps_track_path or not os.path.exists(gps_track_path):
        return []
    
    try:
        with open(gps_track_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception as e:
        logger.warning(f"Failed to parse GPS track file {gps_track_path}: {e}")
    return []


def find_interpolated_gps(gps_track: List[Dict[str, Any]], timestamp_sec: float) -> tuple[Optional[float], Optional[float]]:
    """Interpolates coordinates for a given video timestamp from synchronized GPS points."""
    if not gps_track:
        return None, None
    
    # Exact or closest timestamp match within 2.0s
    best_match = None
    min_diff = float("inf")
    for pt in gps_track:
        pt_time = pt.get("timestamp_seconds", 0.0)
        diff = abs(pt_time - timestamp_sec)
        if diff < min_diff:
            min_diff = diff
            best_match = pt
            
    if best_match and min_diff <= 2.0:
        return best_match.get("latitude"), best_match.get("longitude")
    return None, None


async def process_inspection_job_async(job_id: str, session_factory):
    """
    Runs video extraction, inference, deduplication, and observation creation.
    Can be run as a background task.
    """
    async with session_factory() as db:
        res = await db.execute(select(InspectionJob).where(InspectionJob.id == job_id))
        job = res.scalar_one_or_none()
        if not job:
            logger.error(f"InspectionJob {job_id} not found")
            return

        job.status = InspectionStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        job.progress_percent = 5.0
        await db.commit()

        video_path = job.source_path
        if not os.path.exists(video_path):
            job.status = InspectionStatus.FAILED
            job.error_message = f"Source media file not found: {video_path}"
            await db.commit()
            return

        gps_track = parse_gps_track(job.gps_track_path)
        frames_out_dir = Path(settings.UPLOAD_DIR) / "inspections" / f"job_{job.id}"
        frames_out_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            job.status = InspectionStatus.FAILED
            job.error_message = f"OpenCV could not open video: {video_path}"
            await db.commit()
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        sample_step = max(1, job.frame_sample_rate)

        frame_idx = 0
        sampled_count = 0
        detections_found = 0
        reports_created = 0
        last_detection_time = -999.0  # For duplicate suppression (seconds)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % sample_step == 0:
                    sampled_count += 1
                    timestamp_sec = round(frame_idx / fps, 2)
                    lat, lon = find_interpolated_gps(gps_track, timestamp_sec)

                    # Save extracted frame
                    frame_filename = f"frame_{frame_idx:06d}.jpg"
                    frame_path = frames_out_dir / frame_filename
                    cv2.imwrite(str(frame_path), frame)

                    # Run inference
                    inf_result = detector.infer(str(frame_path), save_annotated=True)
                    annotated_path = None
                    if inf_result.annotated_image is not None:
                        annotated_path = save_annotated_image(
                            inf_result.annotated_image, frames_out_dir, prefix=f"ann_{frame_idx:06d}"
                        )

                    is_duplicate = False
                    detections_list = [
                        {
                            "class_code": d.class_code,
                            "damage_type": d.damage_type,
                            "confidence": d.confidence,
                            "bbox": d.bbox_xyxy,
                        }
                        for d in inf_result.detections
                    ]

                    # Deduplication safeguard: suppress repeated detections within 3.0s window
                    if inf_result.detections:
                        detections_found += len(inf_result.detections)
                        if (timestamp_sec - last_detection_time) < 3.0:
                            is_duplicate = True
                        else:
                            last_detection_time = timestamp_sec

                    # Create InspectionFrame record
                    job_frame = InspectionFrame(
                        job_id=job.id,
                        frame_index=frame_idx,
                        frame_path=str(frame_path),
                        annotated_path=annotated_path,
                        timestamp_seconds=timestamp_sec,
                        latitude=lat,
                        longitude=lon,
                        detections=detections_list,
                        confidence=inf_result.max_confidence,
                        is_duplicate=is_duplicate,
                    )
                    db.add(job_frame)
                    await db.flush()

                    # If valid, non-duplicate road damage with sufficient confidence, create a Report
                    best_det = inf_result.best_detection
                    if best_det and not is_duplicate and best_det.confidence >= settings.MODEL_CONFIDENCE_THRESHOLD:
                        dtype_map = {
                            "pothole": DamageType.POTHOLE,
                            "crack": DamageType.CRACK,
                        }
                        dam_type = dtype_map.get(best_det.damage_type, DamageType.OTHER)
                        
                        sev_obj = inf_result.severity_assessment
                        sev = SeverityLevel.LOW
                        sev_numeric = None
                        if sev_obj:
                            sev_map = {
                                "low": SeverityLevel.LOW,
                                "moderate": SeverityLevel.MODERATE,
                                "high": SeverityLevel.HIGH,
                                "critical": SeverityLevel.CRITICAL,
                            }
                            sev = sev_map.get(sev_obj.level, SeverityLevel.MODERATE)
                            sev_numeric = sev_obj.score
                        elif best_det.confidence >= 0.75:
                            sev = SeverityLevel.HIGH
                        elif best_det.confidence >= 0.55:
                            sev = SeverityLevel.MODERATE

                        import secrets, string
                        ref = "INSP-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                        
                        pr = compute_priority(
                            severity_label=sev.value,
                            traffic_exposure=5.0,
                            time_unresolved_days=0.0,
                            safety_urgency=7.0 if sev == SeverityLevel.CRITICAL else (6.0 if sev == SeverityLevel.HIGH else 4.0),
                            severity_numeric=sev_numeric,
                        )

                        report = Report(
                            public_ref=ref,
                            source=ReportSource.INSPECTION,
                            status=ReportStatus.SUBMITTED,
                            description=f"Automated video inspection observation at t={timestamp_sec}s (Frame #{frame_idx}). Model confidence: {best_det.confidence:.2f}",
                            damage_type=dam_type,
                            severity=sev,
                            severity_is_estimated=True,
                            latitude=lat,
                            longitude=lon,
                            location_source=LocationSource.VIDEO_SYNC if (lat and lon) else LocationSource.UNKNOWN,
                            ai_confidence=best_det.confidence,
                            ai_damage_type=best_det.damage_type,
                            ai_inference_ms=inf_result.inference_ms,
                            ai_bounding_boxes={
                                "detections": detections_list,
                                "severity_estimation": {
                                    "level": sev_obj.level,
                                    "score": sev_obj.score,
                                    "method": sev_obj.method,
                                    "features": sev_obj.features,
                                    "confidence": sev_obj.confidence,
                                    "uncertainty": sev_obj.uncertainty,
                                    "review_required": sev_obj.review_required,
                                    "provisional": sev_obj.provisional,
                                    "disclaimer": sev_obj.disclaimer,
                                } if sev_obj else None,
                            },
                            priority_score=pr.priority_score,
                            priority_explanation={
                                "label": pr.priority_label,
                                "factors": pr.top_contributing_factors,
                                "engine": pr.engine_used,
                            },
                            inspection_frame_id=job_frame.id,
                        )
                        db.add(report)
                        await db.flush()
                        job_frame.report_id = report.id
                        reports_created += 1

                frame_idx += 1
                if total_video_frames > 0 and frame_idx % 60 == 0:
                    job.progress_percent = min(95.0, round((frame_idx / total_video_frames) * 100, 1))
                    await db.commit()

        except Exception as e:
            logger.exception(f"Error processing inspection job {job.id}: {e}")
            job.status = InspectionStatus.FAILED
            job.error_message = str(e)
            await db.commit()
            return
        finally:
            cap.release()

        job.total_frames_sampled = sampled_count
        job.detections_count = detections_found
        job.reports_created = reports_created
        job.progress_percent = 100.0
        job.status = InspectionStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"Completed inspection job {job.id}: {sampled_count} frames, {detections_found} detections, {reports_created} reports created")
