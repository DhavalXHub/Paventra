"""Reports API — citizen submission + coordinator management."""
import logging
import mimetypes
import re
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import get_db, get_current_user, get_optional_user, require_coordinator
from app.models.user import User, UserRole
from app.models.report import (
    Report, MediaAsset, ReportStatusHistory, RepairAssignment,
    FuzzyPriorityAssessment, DuplicateLink,
    ReportStatus, ReportSource, LocationSource, DamageType, SeverityLevel,
)
from app.models.team import RepairTeam
from app.models.audit import AuditEvent
from app.schemas.schemas import (
    ReportOut, ReportListItem, ReportListResponse, StatusUpdateRequest,
    AssignRequest, SubmitConfirmation, CompletionRequest,
)
from app.services.vision.inference import detector
from app.services.prioritization.fuzzy_engine import compute_priority
from app.services.notifications.service import create_notification
from app.services.duplicate_detection.detector import find_duplicate_candidates as _find_dupes
from app.services.geospatial.distance import validate_coordinates, haversine_distance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])

# Valid status transitions
VALID_TRANSITIONS: dict[ReportStatus, list[ReportStatus]] = {
    ReportStatus.SUBMITTED: [ReportStatus.UNDER_REVIEW, ReportStatus.REJECTED],
    ReportStatus.UNDER_REVIEW: [ReportStatus.VERIFIED, ReportStatus.REJECTED],
    ReportStatus.VERIFIED: [ReportStatus.ASSIGNED, ReportStatus.REJECTED],
    ReportStatus.ASSIGNED: [ReportStatus.IN_PROGRESS, ReportStatus.REJECTED],
    ReportStatus.IN_PROGRESS: [ReportStatus.PENDING_VERIFICATION, ReportStatus.ASSIGNED],
    ReportStatus.PENDING_VERIFICATION: [ReportStatus.RESOLVED, ReportStatus.IN_PROGRESS],
    ReportStatus.REJECTED: [ReportStatus.UNDER_REVIEW],
    ReportStatus.RESOLVED: [],
}


def _generate_ref() -> str:
    chars = string.ascii_uppercase + string.digits
    return "PAV-" + "".join(secrets.choice(chars) for _ in range(8))


async def _safe_filename(original: str) -> str:
    ext = Path(original).suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi"}
    if ext not in allowed:
        ext = ".jpg"
    return f"{secrets.token_hex(16)}{ext}"


async def _run_ai_inference(image_path: str, report: Report, db: AsyncSession) -> None:
    """Background task: run CV inference and update report."""
    try:
        result = detector.infer(image_path)
        if result.model_available and not result.error:
            best = result.best_detection
            if best:
                report.ai_confidence = best.confidence
                report.ai_damage_type = best.damage_type
                report.ai_bounding_boxes = {
                    "detections": [
                        {
                            "class_code": d.class_code,
                            "damage_type": d.damage_type,
                            "confidence": d.confidence,
                            "bbox": d.bbox_xyxy,
                        }
                        for d in result.detections
                    ]
                }
                report.ai_inference_ms = result.inference_ms
                # Infer severity from confidence
                if best.confidence >= 0.8:
                    report.severity = SeverityLevel.HIGH
                elif best.confidence >= 0.6:
                    report.severity = SeverityLevel.MODERATE
                else:
                    report.severity = SeverityLevel.LOW
                # Map damage type
                dtype_map = {
                    "pothole": DamageType.POTHOLE,
                    "crack": DamageType.CRACK,
                }
                report.damage_type = dtype_map.get(best.damage_type, DamageType.OTHER)
        await db.commit()
    except Exception as exc:
        logger.error(f"Background AI inference failed: {exc}")


# ─── Public: citizen submit ───────────────────────────────────────────────────

@router.post("", response_model=SubmitConfirmation, status_code=201)
async def submit_report(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    description: Optional[str] = Form(None),
    damage_type: str = Form("unknown"),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    location_source: str = Form("unknown"),
    location_accuracy_meters: Optional[float] = Form(None),
    address_hint: Optional[str] = Form(None),
    submitter_email: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    # Validate image
    content_type = image.content_type or ""
    if content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")

    content = await image.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    # Validate coordinates
    if latitude is not None or longitude is not None:
        if not validate_coordinates(latitude, longitude):
            raise HTTPException(status_code=400, detail="Invalid coordinates")

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR) / "reports"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = await _safe_filename(image.filename or "upload.jpg")
    file_path = upload_dir / safe_name
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Map damage_type string to enum
    try:
        dt_enum = DamageType(damage_type)
    except ValueError:
        dt_enum = DamageType.UNKNOWN

    # Map location_source
    try:
        ls_enum = LocationSource(location_source)
    except ValueError:
        ls_enum = LocationSource.UNKNOWN

    # Generate unique ref
    for _ in range(10):
        ref = _generate_ref()
        existing = await db.execute(select(Report).where(Report.public_ref == ref))
        if not existing.scalar_one_or_none():
            break

    report = Report(
        public_ref=ref,
        source=ReportSource.CITIZEN,
        status=ReportStatus.SUBMITTED,
        submitter_id=current_user.id if current_user else None,
        submitter_email=submitter_email or (current_user.email if current_user else None),
        description=description,
        damage_type=dt_enum,
        latitude=latitude,
        longitude=longitude,
        location_source=ls_enum,
        location_accuracy_meters=location_accuracy_meters,
        address_hint=address_hint,
    )
    db.add(report)
    await db.flush()

    # Save media asset
    media = MediaAsset(
        report_id=report.id,
        file_path=str(file_path),
        file_name=safe_name,
        mime_type=content_type,
        file_size_bytes=len(content),
        asset_type="report_photo",
    )
    db.add(media)

    # Initial status history
    history = ReportStatusHistory(
        report_id=report.id,
        from_status=None,
        to_status=ReportStatus.SUBMITTED.value,
        changed_by_id=current_user.id if current_user else None,
        changed_by_email=submitter_email or (current_user.email if current_user else "anonymous"),
    )
    db.add(history)
    await db.flush()

    # Run AI inference synchronously (fast) if model available
    ai_assessment = None
    if detector.is_available():
        result = detector.infer(str(file_path))
        if result.model_available and not result.error and result.best_detection:
            best = result.best_detection
            report.ai_confidence = best.confidence
            report.ai_damage_type = best.damage_type
            report.ai_inference_ms = result.inference_ms
            report.ai_bounding_boxes = {
                "detections": [
                    {"class_code": d.class_code, "damage_type": d.damage_type,
                     "confidence": d.confidence, "bbox": d.bbox_xyxy}
                    for d in result.detections
                ]
            }
            if best.confidence >= 0.8:
                report.severity = SeverityLevel.HIGH
            elif best.confidence >= 0.6:
                report.severity = SeverityLevel.MODERATE
            else:
                report.severity = SeverityLevel.LOW
            dtype_map = {"pothole": DamageType.POTHOLE, "crack": DamageType.CRACK}
            report.damage_type = dtype_map.get(best.damage_type, dt_enum)
            ai_assessment = {
                "damage_type": best.damage_type,
                "confidence": best.confidence,
                "severity_estimated": report.severity.value if report.severity else None,
                "model_available": True,
                "disclaimer": (
                    "This is an AI-estimated assessment. Confidence and severity "
                    "are predictions only and must be verified by a coordinator."
                ),
            }
        elif not result.model_available:
            ai_assessment = {"model_available": False, "message": result.error}
    else:
        ai_assessment = {
            "model_available": False,
            "message": "AI model not configured. Report will be manually reviewed.",
        }

    # Compute fuzzy priority
    if report.severity:
        days_unresolved = 0.0
        try:
            pr = compute_priority(
                severity_label=report.severity.value,
                time_unresolved_days=days_unresolved,
            )
            report.priority_score = pr.priority_score
            report.priority_explanation = {
                "label": pr.priority_label,
                "factors": pr.top_contributing_factors,
                "engine": pr.engine_used,
            }
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
        except Exception as exc:
            logger.warning(f"Fuzzy priority computation failed: {exc}")

    await db.commit()

    # Notification for submitter
    if current_user:
        try:
            await create_notification(
                db,
                user_id=current_user.id,
                report_id=report.id,
                title="Report received",
                body=f"Your road damage report {ref} has been submitted and is under review.",
                notification_type="report_submitted",
            )
            await db.commit()
        except Exception:
            pass

    return SubmitConfirmation(
        public_ref=ref,
        report_id=report.id,
        status=ReportStatus.SUBMITTED.value,
        ai_assessment=ai_assessment,
        message=f"Report {ref} submitted successfully. You can track its status using this reference.",
    )


# ─── Public: status tracking ──────────────────────────────────────────────────

@router.get("/track/{public_ref}", response_model=dict)
async def track_report(public_ref: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.status_history))
        .where(Report.public_ref == public_ref.upper())
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    history = [
        {"status": h.to_status, "changed_at": h.changed_at.isoformat(), "notes": h.notes}
        for h in sorted(report.status_history, key=lambda h: h.changed_at)
    ]
    return {
        "public_ref": report.public_ref,
        "status": report.status.value,
        "damage_type": report.damage_type.value,
        "severity": report.severity.value if report.severity else None,
        "created_at": report.created_at.isoformat(),
        "updated_at": report.updated_at.isoformat(),
        "resolved_at": report.resolved_at.isoformat() if report.resolved_at else None,
        "review_reason": report.review_reason,
        "history": history,
    }


@router.post("/track/{public_ref}/evidence", response_model=dict)
async def submit_additional_evidence(
    public_ref: str,
    notes: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """Allows citizens to provide additional evidence/photos for their report."""
    result = await db.execute(
        select(Report).where(Report.public_ref == public_ref.upper())
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status in (ReportStatus.RESOLVED, ReportStatus.REJECTED):
        raise HTTPException(status_code=400, detail="Cannot attach evidence to closed reports")

    media_id = None
    if image:
        content_type = image.content_type or ""
        if content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type}")
        content = await image.read()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="File exceeds maximum allowed upload size")

        upload_dir = Path(settings.UPLOAD_DIR) / "reports"
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = await _safe_filename(image.filename or "evidence.jpg")
        file_path = upload_dir / safe_name
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        media = MediaAsset(
            report_id=report.id,
            file_path=str(file_path),
            file_name=safe_name,
            mime_type=content_type,
            file_size_bytes=len(content),
            asset_type="additional_evidence",
        )
        db.add(media)
        await db.flush()
        media_id = media.id

    if notes or image:
        audit = AuditEvent(
            actor_id=report.submitter_id,
            actor_email=report.submitter_email or "citizen",
            action="additional_evidence_submitted",
            resource_type="report",
            resource_id=report.id,
            details={"notes": notes, "media_id": media_id},
        )
        db.add(audit)
        await db.commit()

    return {"status": "ok", "message": "Additional evidence attached successfully"}


# ─── Citizen: list my own reports ─────────────────────────────────────────────

@router.get("/my", response_model=list[ReportListItem])
async def list_my_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allows authenticated citizens to view their own submitted reports."""
    q = select(Report).where(
        or_(
            Report.submitter_id == current_user.id,
            Report.submitter_email == current_user.email,
        )
    ).order_by(Report.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return [ReportListItem.model_validate(r) for r in rows]


# ─── Coordinator: list reports ────────────────────────────────────────────────

@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    damage_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    q = select(Report)
    if status:
        q = q.where(Report.status == status)
    if source:
        q = q.where(Report.source == source)
    if severity:
        q = q.where(Report.severity == severity)
    if damage_type:
        q = q.where(Report.damage_type == damage_type)
    if search:
        q = q.where(
            or_(Report.public_ref.ilike(f"%{search}%"), Report.description.ilike(f"%{search}%"))
        )

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    pages = max(1, (total + page_size - 1) // page_size)

    return ReportListResponse(
        items=[ReportListItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ─── Coordinator: report detail ───────────────────────────────────────────────

@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    result = await db.execute(
        select(Report)
        .options(
            selectinload(Report.media_assets),
            selectinload(Report.status_history),
            selectinload(Report.assignment).selectinload(RepairAssignment.team),
            selectinload(Report.priority_assessment),
        )
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    out = ReportOut.model_validate(report)
    if report.assignment and report.assignment.team:
        out.assignment.team_name = report.assignment.team.name
    return out


# ─── Coordinator: status update ───────────────────────────────────────────────

@router.patch("/{report_id}/status", response_model=dict)
async def update_status(
    report_id: str,
    body: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        new_status = ReportStatus(body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown status: {body.status}")

    allowed = VALID_TRANSITIONS.get(report.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Transition {report.status.value} → {new_status.value} is not allowed",
        )

    if new_status == ReportStatus.REJECTED and not body.reason:
        raise HTTPException(status_code=400, detail="Rejection requires a reason")

    old_status = report.status
    report.status = new_status
    report.reviewed_by_id = current_user.id
    report.reviewed_at = datetime.now(timezone.utc)
    if body.reason:
        report.review_reason = body.reason
    if new_status == ReportStatus.RESOLVED:
        report.resolved_at = datetime.now(timezone.utc)

    history = ReportStatusHistory(
        report_id=report.id,
        from_status=old_status.value,
        to_status=new_status.value,
        changed_by_id=current_user.id,
        changed_by_email=current_user.email,
        reason=body.reason,
        notes=body.notes,
    )
    db.add(history)

    audit = AuditEvent(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="status_change",
        resource_type="report",
        resource_id=report.id,
        details={"from": old_status.value, "to": new_status.value, "reason": body.reason},
    )
    db.add(audit)

    # Notify submitter if they have an account
    if report.submitter_id:
        try:
            await create_notification(
                db,
                user_id=report.submitter_id,
                report_id=report.id,
                title=f"Report {report.public_ref} updated",
                body=f"Your report status changed to {new_status.value.replace('_', ' ').title()}.",
                notification_type="status_change",
            )
        except Exception:
            pass

    await db.commit()
    return {"public_ref": report.public_ref, "status": new_status.value}


# ─── Coordinator: assign team ─────────────────────────────────────────────────

@router.post("/{report_id}/assign", response_model=dict)
async def assign_report(
    report_id: str,
    body: AssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != ReportStatus.VERIFIED:
        raise HTTPException(status_code=400, detail="Only VERIFIED reports can be assigned")

    team_result = await db.execute(select(RepairTeam).where(RepairTeam.id == body.team_id, RepairTeam.is_active == True))  # noqa: E712
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found or inactive")

    # Remove existing assignment if any
    existing_assign = await db.execute(select(RepairAssignment).where(RepairAssignment.report_id == report_id))
    existing = existing_assign.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.flush()

    assignment = RepairAssignment(
        report_id=report_id,
        team_id=body.team_id,
        assigned_by_id=current_user.id,
        target_date=body.target_date,
        notes=body.notes,
    )
    db.add(assignment)

    old_status = report.status
    report.status = ReportStatus.ASSIGNED
    history = ReportStatusHistory(
        report_id=report.id,
        from_status=old_status.value,
        to_status=ReportStatus.ASSIGNED.value,
        changed_by_id=current_user.id,
        changed_by_email=current_user.email,
        notes=f"Assigned to team: {team.name}",
    )
    db.add(history)

    audit = AuditEvent(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="assign",
        resource_type="report",
        resource_id=report_id,
        details={"team_id": body.team_id, "team_name": team.name},
    )
    db.add(audit)
    await db.commit()

    return {"report_id": report_id, "team": team.name, "status": ReportStatus.ASSIGNED.value}


# ─── Map endpoint (public summary for map display) ────────────────────────────

@router.get("/map/markers", response_model=list[dict])
async def get_map_markers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    result = await db.execute(
        select(
            Report.id, Report.public_ref, Report.status, Report.severity,
            Report.damage_type, Report.latitude, Report.longitude,
            Report.priority_score, Report.created_at,
        ).where(
            Report.latitude.isnot(None),
            Report.longitude.isnot(None),
        )
    )
    rows = result.all()
    return [
        {
            "id": r.id,
            "public_ref": r.public_ref,
            "status": str(r.status),
            "severity": str(r.severity) if r.severity else None,
            "damage_type": str(r.damage_type),
            "lat": r.latitude,
            "lon": r.longitude,
            "priority_score": r.priority_score,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


# ─── Duplicate candidates ────────────────────────────────────────────────────

@router.get("/{report_id}/duplicates", response_model=list[dict])
async def get_duplicate_candidates(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    """Return potential duplicate reports for coordinator review."""
    result = await db.execute(
        select(Report)
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Fetch other open reports to compare against
    candidates_q = await db.execute(
        select(Report).where(
            Report.id != report_id,
            Report.status.in_([
                ReportStatus.SUBMITTED, ReportStatus.UNDER_REVIEW,
                ReportStatus.VERIFIED, ReportStatus.ASSIGNED, ReportStatus.IN_PROGRESS,
            ])
        ).limit(500)
    )
    other_reports = candidates_q.scalars().all()

    existing = [
        {
            "id": r.id,
            "public_ref": r.public_ref,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "damage_type": r.damage_type.value if r.damage_type else "unknown",
            "created_at": r.created_at,
            "status": r.status.value,
        }
        for r in other_reports
    ]

    dupes = _find_dupes(
        new_report_lat=report.latitude,
        new_report_lon=report.longitude,
        new_report_type=report.damage_type.value if report.damage_type else "unknown",
        new_report_created_at=report.created_at,
        existing_reports=existing,
    )

    return [
        {
            "id": c.report_id,
            "public_ref": c.public_ref,
            "distance_meters": c.distance_meters,
            "similarity_score": c.similarity_score,
            "same_damage_type": c.same_damage_type,
            "time_diff_days": round(c.time_diff_days, 1),
        }
        for c in dupes
    ]


@router.post("/{report_id}/duplicates/link", response_model=dict)
async def link_duplicate(
    report_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    """Mark another report as a duplicate of this one."""
    duplicate_id = body.get("duplicate_id")
    if not duplicate_id:
        raise HTTPException(status_code=400, detail="duplicate_id required")

    # Verify both exist
    r1 = await db.execute(select(Report).where(Report.id == report_id))
    r2 = await db.execute(select(Report).where(Report.id == duplicate_id))
    if not r1.scalar_one_or_none() or not r2.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Report not found")

    # Check not already linked
    existing = await db.execute(
        select(DuplicateLink).where(
            DuplicateLink.primary_report_id == report_id,
            DuplicateLink.duplicate_report_id == duplicate_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_linked"}

    link = DuplicateLink(
        primary_report_id=report_id,
        duplicate_report_id=duplicate_id,
        confirmed=True,
        confirmed_by_id=current_user.id,
    )
    db.add(link)

    audit = AuditEvent(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="duplicate_link",
        resource_type="report",
        resource_id=report_id,
        details={"duplicate_id": duplicate_id},
    )
    db.add(audit)
    await db.commit()
    return {"status": "linked", "primary": report_id, "duplicate": duplicate_id}


# ─── Completion evidence upload ───────────────────────────────────────────────

@router.post("/{report_id}/completion", response_model=dict)
async def submit_completion(
    report_id: str,
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    """Upload completion evidence and mark report as pending verification."""
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.assignment))
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status not in (ReportStatus.IN_PROGRESS, ReportStatus.ASSIGNED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit completion for report in status: {report.status.value}"
        )

    photo_path = None
    if photo:
        content_type = photo.content_type or ""
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        if content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Unsupported completion photo type")
        content = await photo.read()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="File too large")
        upload_dir = Path(settings.UPLOAD_DIR) / "completions"
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = await _safe_filename(photo.filename or "completion.jpg")
        file_path = upload_dir / safe_name
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        photo_path = str(file_path)

        # Save as media asset
        media = MediaAsset(
            report_id=report_id,
            file_path=photo_path,
            file_name=safe_name,
            mime_type=content_type,
            file_size_bytes=len(content),
            asset_type="completion_photo",
        )
        db.add(media)

    if report.assignment:
        if notes:
            report.assignment.completion_notes = notes
        if photo_path:
            report.assignment.completion_photo_path = photo_path

    old_status = report.status
    report.status = ReportStatus.PENDING_VERIFICATION
    history = ReportStatusHistory(
        report_id=report.id,
        from_status=old_status.value,
        to_status=ReportStatus.PENDING_VERIFICATION.value,
        changed_by_id=current_user.id,
        changed_by_email=current_user.email,
        notes=notes or "Completion evidence submitted",
    )
    db.add(history)

    audit = AuditEvent(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="completion_submitted",
        resource_type="report",
        resource_id=report_id,
        details={"has_photo": photo_path is not None, "notes": notes},
    )
    db.add(audit)
    await db.commit()
    return {"status": ReportStatus.PENDING_VERIFICATION.value, "photo_uploaded": photo_path is not None}

