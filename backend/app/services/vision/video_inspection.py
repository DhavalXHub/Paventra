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
from app.models.report import Report, ReportSource, ReportStatus, DamageType, SeverityLevel, LocationSource, MediaAsset
from app.services.vision.inference import detector, save_annotated_image
from app.services.prioritization.fuzzy_engine import compute_priority

logger = logging.getLogger(__name__)


def resolve_inspection_file_path(path_str: Optional[str]) -> Optional[Path]:
    """
    Resolves a stored inspection file path (video, GPS, frame) to a consistent absolute Path.
    Handles:
    - Absolute paths (if already absolute and exists)
    - Relative paths starting with 'uploads/inspections/' or 'uploads\\inspections\\'
    - Relative paths with just filename or subpaths
    - Both POSIX and Windows backslash separators
    - Fallbacks across settings.upload_path, backend root, and project root.
    """
    if not path_str or not str(path_str).strip():
        return None

    clean_str = str(path_str).strip()
    raw_path = Path(clean_str)

    if raw_path.is_absolute() and raw_path.exists():
        return raw_path.resolve()

    filename = raw_path.name
    upload_root = settings.upload_path.resolve()
    backend_root = Path(__file__).resolve().parent.parent.parent
    project_root = backend_root.parent

    # Candidate paths in order of preference
    candidates = [
        upload_root / "inspections" / filename,
        upload_root / clean_str.replace("uploads/", "").replace("uploads\\", ""),
        upload_root / clean_str,
        backend_root / clean_str,
        backend_root / "uploads" / "inspections" / filename,
        project_root / clean_str,
        project_root / "uploads" / "inspections" / filename,
        Path.cwd() / clean_str,
    ]

    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()
        except OSError:
            continue

    # Default to canonical destination path under upload_root / "inspections"
    return (upload_root / "inspections" / filename).resolve()


def validate_video_file(resolved_path: Optional[Path]) -> tuple[bool, Optional[str]]:
    """
    Validates that a video file exists, is non-empty, and has a minimum size for a media container.
    Returns (is_valid, error_reason).
    """
    if resolved_path is None or not resolved_path.exists():
        return False, f"Source video file not found at '{resolved_path}'"

    try:
        size = resolved_path.stat().st_size
    except OSError as e:
        return False, f"Could not access video file: {e}"

    if size == 0:
        return False, f"Invalid video file ({resolved_path.name}): file is empty (0 bytes)"

    # A valid video container (MP4, AVI, MOV) with headers requires at least 1 KB
    if size < 1024:
        return False, (
            f"Invalid video file ({resolved_path.name}): size is {size} bytes "
            f"(minimum 1024 bytes required for valid video container). File appears corrupted or incomplete."
        )

    return True, None


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
    if not gps_track_path:
        return []
    resolved = resolve_inspection_file_path(gps_track_path)
    if not resolved or not resolved.exists():
        return []
    
    try:
        with open(resolved, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception as e:
        logger.warning(f"Failed to parse GPS track file {resolved}: {e}")
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
        job.progress_percent = 0.0
        job.error_message = None
        await db.commit()

        # Step 1: Resolve filesystem path
        resolved_video_path = resolve_inspection_file_path(job.source_path)
        is_valid, validation_error = validate_video_file(resolved_video_path)
        if not is_valid:
            job.status = InspectionStatus.FAILED
            job.progress_percent = 0.0
            job.error_message = validation_error
            await db.commit()
            logger.error(f"Job {job_id} failed validation: {validation_error}")
            return

        gps_track = parse_gps_track(job.gps_track_path)
        frames_out_dir = settings.upload_path / "inspections" / f"job_{job.id}"
        frames_out_dir.mkdir(parents=True, exist_ok=True)

        cap = None
        try:
            cap = cv2.VideoCapture(str(resolved_video_path))
            if not cap.isOpened():
                job.status = InspectionStatus.FAILED
                job.progress_percent = 0.0
                job.error_message = (
                    f"OpenCV could not decode video container '{resolved_video_path.name}'. "
                    f"Format or codec may be unsupported or corrupted."
                )
                await db.commit()
                return

            # Successfully opened video
            job.progress_percent = 5.0
            await db.commit()

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            sample_step = max(1, job.frame_sample_rate)

            frame_idx = 0
            sampled_count = 0
            detections_found = 0
            reports_created = 0
            last_detection_time = -999.0  # For duplicate suppression (seconds)

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

                    # Relative web-friendly paths for frontend display
                    web_frame_path = f"uploads/inspections/job_{job.id}/{frame_filename}"

                    # Run inference
                    inf_result = detector.infer(str(frame_path), save_annotated=True)
                    annotated_path = None
                    web_annotated_path = None
                    if inf_result.annotated_image is not None:
                        ann_full_path = save_annotated_image(
                            inf_result.annotated_image, frames_out_dir, prefix=f"ann_{frame_idx:06d}"
                        )
                        if ann_full_path:
                            ann_name = Path(ann_full_path).name
                            web_annotated_path = f"uploads/inspections/job_{job.id}/{ann_name}"
                            annotated_path = str(ann_full_path)

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
                        frame_path=web_frame_path,
                        annotated_path=web_annotated_path or annotated_path,
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

                        # Attach MediaAsset to Report
                        photo_asset = MediaAsset(
                            report_id=report.id,
                            file_path=web_frame_path,
                            file_name=frame_filename,
                            mime_type="image/jpeg",
                            file_size_bytes=frame_path.stat().st_size if frame_path.exists() else 0,
                            asset_type="initial",
                            annotated_path=web_annotated_path or annotated_path,
                        )
                        db.add(photo_asset)
                        reports_created += 1

                frame_idx += 1
                if total_video_frames > 0:
                    pct = min(95.0, round((frame_idx / total_video_frames) * 100, 1))
                    if pct > job.progress_percent and (frame_idx % sample_step == 0 or frame_idx % 10 == 0):
                        job.progress_percent = pct
                        await db.commit()

        except Exception as e:
            logger.exception(f"Error processing inspection job {job.id}: {e}")
            job.status = InspectionStatus.FAILED
            job.error_message = f"Processing error at frame {frame_idx}: {str(e)}"
            await db.commit()
            return
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception as ex:
                    logger.warning(f"Error releasing video capture: {ex}")

        job.total_frames_sampled = sampled_count
        job.detections_count = detections_found
        job.reports_created = reports_created
        job.progress_percent = 100.0
        job.status = InspectionStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"Completed inspection job {job.id}: {sampled_count} frames, {detections_found} detections, {reports_created} reports created")
