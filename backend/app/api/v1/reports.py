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
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import get_db, get_current_user, get_optional_user, require_coordinator, require_team_or_above
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
    ReportClaimRequest, ReportClaimResponse, AssessmentOverrideRequest,
)
from app.services.vision.inference import detector
from app.services.prioritization.fuzzy_engine import compute_priority, _priority_label
from app.services.storage import storage_service
from app.services.vision.assessment_pipeline import (
    run_automatic_assessment, derive_traffic_exposure, derive_safety_urgency,
)
from app.services.notifications.service import create_notification
from app.services.duplicate_detection.detector import find_duplicate_candidates as _find_dupes
from app.services.geospatial.distance import validate_coordinates, haversine_distance
from app.services.media.validation import enforce_upload_size, safe_upload_name, validate_image_bytes
from app.core.rate_limiter import enforce_submission_rate_limit

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
    return safe_upload_name(original)


async def _run_ai_inference(image_path: str, report: Report, db: AsyncSession) -> None:
    """Background task: run CV inference and update report."""
    try:
        result = detector.infer(image_path)
        if result.model_available and not result.error:
            best = result.best_detection
            if best:
                report.ai_confidence = best.confidence
                report.ai_damage_type = best.damage_type
                report.ai_inference_ms = result.inference_ms

                # Grounded severity estimation from visible 2D geometry
                sev_obj = result.severity_assessment
                if sev_obj:
                    sev_map = {
                        "low": SeverityLevel.LOW,
                        "moderate": SeverityLevel.MODERATE,
                        "high": SeverityLevel.HIGH,
                        "critical": SeverityLevel.CRITICAL,
                    }
                    report.severity = sev_map.get(sev_obj.level, SeverityLevel.MODERATE)
                    report.severity_is_estimated = True
                elif best.confidence >= 0.75:
                    report.severity = SeverityLevel.HIGH
                    report.severity_is_estimated = True
                else:
                    report.severity = SeverityLevel.MODERATE
                    report.severity_is_estimated = True

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
                }
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
    request: Request,
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
    # Enforce dual-key rate limiting (IP and account/email)
    enforce_submission_rate_limit(
        request=request,
        submitter_email=submitter_email,
        current_user_id=current_user.id if current_user else None,
    )
    # Validate image
    content_type = image.content_type or ""
    if content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use JPEG, PNG or WebP.")

    content = await image.read()
    enforce_upload_size(content)
    validate_image_bytes(content)

    # Validate coordinates — never invent missing GPS
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=400, detail="Latitude and longitude must be provided together")
    if latitude is not None or longitude is not None:
        if not validate_coordinates(latitude, longitude):
            raise HTTPException(status_code=400, detail="Invalid coordinates")

    # Save file (hybrid: local disk for CV + persistent object storage when configured)
    safe_name = await _safe_filename(image.filename or "upload.jpg")
    accessible_url_or_path, safe_name = await storage_service.save_file(
        content=content,
        safe_filename=safe_name,
        folder="reports",
        content_type=content_type,
    )
    local_path = Path(settings.UPLOAD_DIR) / "reports" / safe_name

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

    # If guest submission, generate single-use claim token
    claim_token = secrets.token_urlsafe(32) if not current_user else None

    report = Report(
        public_ref=ref,
        source=ReportSource.CITIZEN,
        status=ReportStatus.SUBMITTED,
        submitter_id=current_user.id if current_user else None,
        submitter_email=submitter_email or (current_user.email if current_user else None),
        claim_token=claim_token,
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
        file_path=accessible_url_or_path,
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

    # Run automated Computer Vision and Mamdani Fuzzy Prioritization
    assessment_res = await run_automatic_assessment(report, str(local_path), db)
    await db.commit()

    ai_assessment = {
        "status": report.assessment_status,
        "damage_type": report.damage_type.value if report.damage_type else None,
        "confidence": report.ai_confidence,
        "severity_estimated": report.severity.value if report.severity else None,
        "priority_score": report.priority_score,
        "priority_label": (report.priority_explanation or {}).get("label"),
        "model_available": detector.is_available(),
        "disclaimer": (
            "Provisional 2D image-derived estimate based on visible surface distress area and geometry. "
            "Ordinary RGB photographs cannot measure true volumetric cavity depth or pavement sub-base integrity."
        ),
    }

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
        claim_token=claim_token,
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
        "latitude": report.latitude,
        "longitude": report.longitude,
        "address_hint": report.address_hint,
        "is_claimed": report.submitter_id is not None,
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
            raise HTTPException(status_code=400, detail="Unsupported file type. Use JPEG, PNG or WebP.")
        content = await image.read()
        enforce_upload_size(content)
        validate_image_bytes(content)

        safe_name = await _safe_filename(image.filename or "evidence.jpg")
        accessible_url_or_path, safe_name = await storage_service.save_file(
            content=content,
            safe_filename=safe_name,
            folder="reports",
            content_type=content_type,
        )

        media = MediaAsset(
            report_id=report.id,
            file_path=accessible_url_or_path,
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
@router.get("/mine", response_model=list[ReportListItem])
async def list_my_reports(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Allows authenticated citizens to view their own submitted reports."""
    q = select(Report).where(Report.submitter_id == current_user.id)
    if status:
        q = q.where(Report.status == status)
    q = q.order_by(Report.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return [ReportListItem.model_validate(r) for r in rows]


@router.post("/claim", response_model=ReportClaimResponse)
async def claim_report(
    request: Request,
    body: ReportClaimRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Claim an unassigned/guest report to link it to the authenticated citizen account."""
    # Rate-limit claims to prevent brute forcing
    enforce_submission_rate_limit(request=request, current_user_id=current_user.id)

    ref = body.public_ref.strip().upper()
    result = await db.execute(select(Report).where(Report.public_ref == ref))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report with reference '{ref}' not found")

    if report.submitter_id is not None:
        if report.submitter_id == current_user.id:
            return ReportClaimResponse(
                status="ok",
                message="This report is already linked to your account.",
                public_ref=report.public_ref,
                claimed_at=datetime.now(timezone.utc),
            )
        raise HTTPException(
            status_code=400,
            detail="This report has already been linked to another account.",
        )

    # Verification check: either valid claim_token OR matching verification_email OR current user email matches guest email
    verified = False
    if body.claim_token and report.claim_token and secrets.compare_digest(body.claim_token.strip(), report.claim_token):
        verified = True
    elif body.verification_email and report.submitter_email and body.verification_email.strip().lower() == report.submitter_email.strip().lower():
        verified = True
    elif report.submitter_email and current_user.email.strip().lower() == report.submitter_email.strip().lower():
        verified = True

    if not verified:
        raise HTTPException(
            status_code=400,
            detail="Verification failed. Please provide the single-use claim token or the email address submitted with the report.",
        )

    # Associate report to user and invalidate claim token (single-use)
    report.submitter_id = current_user.id
    report.claim_token = None

    # Record audit event
    audit = AuditEvent(
        action="REPORT_CLAIMED",
        actor_id=current_user.id,
        actor_email=current_user.email,
        resource_type="report",
        resource_id=report.id,
        details={
            "public_ref": report.public_ref,
            "claimed_by_email": current_user.email,
        },
    )
    db.add(audit)
    await db.commit()

    return ReportClaimResponse(
        status="ok",
        message=f"Report {report.public_ref} has been successfully linked to your account.",
        public_ref=report.public_ref,
        claimed_at=datetime.now(timezone.utc),
    )


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
    include_test_artifacts: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    q = select(Report)
    if not include_test_artifacts and not search:
        q = q.where(
            or_(
                Report.assessment_status != "AUTOMATED_TEST_ARTIFACT",
                Report.assessment_status.is_(None),
            )
        )
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
            or_(Report.public_ref.ilike(f"%{search}%"), Report.description.ilike(f"%{search}%"),
                Report.submitter_email.ilike(f"%{search}%"))
        )

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # ── Sorting strategy ────────────────────────────────────────────────────────
    # Bucket 0 (sort key 0): Actionable + has a valid priority score  → rank by score desc
    # Bucket 1 (sort key 1): Actionable + no valid score              → newest first
    # Bucket 2 (sort key 2): Non-actionable (RESOLVED / REJECTED)     → newest first
    #
    # This ensures:
    #   • Assessed high-priority hazards appear at the top.
    #   • Newly submitted genuine reports (not yet assessed) appear immediately
    #     below scored reports, not buried at position 400+.
    #   • Resolved/rejected reports stay at the bottom.
    # ────────────────────────────────────────────────────────────────────────────
    is_non_actionable = case(
        (Report.status.in_([ReportStatus.RESOLVED, ReportStatus.REJECTED]), 2),
        else_=case(
            (Report.priority_score.isnot(None), 0),
            else_=1,
        ),
    )
    q = q.order_by(
        is_non_actionable.asc(),
        # Within bucket 0 (scored): highest score first, deterministic tie-break
        case((is_non_actionable == 0, Report.priority_score), else_=None).desc().nulls_last(),
        # Within all buckets: newest first as secondary sort
        Report.created_at.desc(),
        Report.public_ref.asc(),
    ).offset((page - 1) * page_size).limit(page_size)

    rows = (await db.execute(q)).scalars().all()
    pages = max(1, (total + page_size - 1) // page_size)

    items = []
    for r in rows:
        item = ReportListItem.model_validate(r)
        if r.priority_explanation and isinstance(r.priority_explanation, dict) and "label" in r.priority_explanation:
            item.priority_label = r.priority_explanation["label"]
        elif r.priority_score is not None:
            item.priority_label = _priority_label(r.priority_score)
        items.append(item)

    return ReportListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


# ─── Coordinator: recent submissions ─────────────────────────────────────────

@router.get("/recent", response_model=list[ReportListItem])
async def list_recent_reports(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    """
    Returns the newest citizen submissions, ordered strictly by created_at desc.
    Ensures newly submitted reports are immediately prominent in the coordinator UI.
    """
    q = (
        select(Report)
        .where(
            or_(
                Report.assessment_status != "AUTOMATED_TEST_ARTIFACT",
                Report.assessment_status.is_(None),
            )
        )
        .order_by(Report.created_at.desc(), Report.public_ref.asc())
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()
    items = []
    for r in rows:
        item = ReportListItem.model_validate(r)
        if r.priority_explanation and isinstance(r.priority_explanation, dict) and "label" in r.priority_explanation:
            item.priority_label = r.priority_explanation["label"]
        elif r.priority_score is not None:
            item.priority_label = _priority_label(r.priority_score)
        items.append(item)
    return items


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
        .where(or_(Report.id == report_id, Report.public_ref == report_id.upper()))
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    out = ReportOut.model_validate(report)
    if report.assignment and report.assignment.team:
        out.assignment.team_name = report.assignment.team.name
    if report.priority_explanation and isinstance(report.priority_explanation, dict) and "label" in report.priority_explanation:
        out.priority_label = report.priority_explanation["label"]
    elif report.priority_score is not None:
        out.priority_label = _priority_label(report.priority_score)
    return out


# ─── Coordinator: status update ───────────────────────────────────────────────

@router.patch("/{report_id}/status", response_model=dict)
async def update_status(
    report_id: str,
    body: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    result = await db.execute(select(Report).where(or_(Report.id == report_id, Report.public_ref == report_id.upper())))
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

    if body.severity:
        try:
            if report.original_severity is None:
                report.original_severity = report.severity
            if report.original_priority_score is None:
                report.original_priority_score = report.priority_score
            report.severity = SeverityLevel(body.severity.lower())
            report.severity_is_estimated = False
            report.assessment_status = "OVERRIDDEN"
            report.override_reason = body.notes or body.reason or "Verified severity confirmation"
            created = report.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            days_unresolved = max(
                0.0,
                (datetime.now(timezone.utc) - created).total_seconds() / 86400.0,
            )
            traffic_score, _ = derive_traffic_exposure(report.address_hint)
            safety_score, _ = derive_safety_urgency(report.severity, report.damage_type, report.address_hint)
            pr = compute_priority(
                severity_label=report.severity.value,
                traffic_exposure=traffic_score,
                time_unresolved_days=days_unresolved,
                safety_urgency=safety_score,
            )
            report.priority_score = pr.priority_score
            report.priority_explanation = {
                "label": pr.priority_label,
                "score": pr.priority_score,
                "factors": pr.top_contributing_factors,
                "engine": pr.engine_used,
            }
        except Exception as exc:
            logger.warning(f"Failed to update verified severity: {exc}")

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


# ─── Coordinator: human override of assessment ───────────────────────────────

@router.post("/{report_id}/override", response_model=ReportOut)
async def override_assessment(
    report_id: str,
    body: AssessmentOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    result = await db.execute(
        select(Report)
        .options(
            selectinload(Report.media_assets),
            selectinload(Report.status_history),
            selectinload(Report.assignment).selectinload(RepairAssignment.team),
            selectinload(Report.priority_assessment),
        )
        .where(or_(Report.id == report_id, Report.public_ref == report_id.upper()))
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        new_sev = SeverityLevel(body.severity.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid severity level: {body.severity}")

    old_sev = report.severity
    old_priority = report.priority_score

    # Preserve original AI assessment values
    if report.original_severity is None:
        report.original_severity = old_sev
    if report.original_priority_score is None:
        report.original_priority_score = old_priority

    # Apply override
    report.severity = new_sev
    report.severity_is_estimated = False
    report.assessment_status = "OVERRIDDEN"
    report.override_reason = body.reason
    report.override_by_id = current_user.id
    report.override_at = datetime.now(timezone.utc)

    if body.damage_type:
        try:
            report.damage_type = DamageType(body.damage_type.lower())
        except ValueError:
            pass

    # Recalculate priority based on human-verified severity and actual elapsed days
    created = report.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    days_unresolved = max(0.0, (datetime.now(timezone.utc) - created).total_seconds() / 86400.0)

    traffic_score, traffic_prov = derive_traffic_exposure(report.address_hint)
    safety_score, safety_prov = derive_safety_urgency(report.severity, report.damage_type, report.address_hint)

    pr = compute_priority(
        severity_label=report.severity.value,
        traffic_exposure=traffic_score,
        time_unresolved_days=days_unresolved,
        safety_urgency=safety_score,
    )

    report.priority_score = pr.priority_score
    report.priority_explanation = {
        "label": pr.priority_label,
        "score": pr.priority_score,
        "factors": pr.top_contributing_factors,
        "engine": pr.engine_used,
        "inputs": pr.inputs,
        "baseline_score": pr.baseline_score,
        "override": {
            "overridden_by": current_user.email,
            "overridden_at": report.override_at.isoformat(),
            "reason": body.reason,
            "notes": body.notes,
            "original_severity": report.original_severity.value if report.original_severity else None,
            "original_priority_score": report.original_priority_score,
        },
    }

    # Record AuditEvent
    audit = AuditEvent(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="assessment_override",
        resource_type="report",
        resource_id=report.id,
        details={
            "from_severity": old_sev.value if old_sev else None,
            "to_severity": new_sev.value,
            "from_priority": old_priority,
            "to_priority": pr.priority_score,
            "reason": body.reason,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(report)

    out = ReportOut.model_validate(report)
    out.priority_label = pr.priority_label
    return out


# ─── Coordinator: backfill unassessed reports ────────────────────────────────

@router.post("/backfill-assessments", response_model=dict)
async def backfill_assessments(
    limit: int = Query(500, ge=1, le=1000),
    dry_run: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    """
    Controlled, idempotent backfill for existing unassessed reports.
    Executes automatic YOLO detection and Mamdani FIS on reports with photos,
    or flags them with honest NO_IMAGE / NO_DETECTIONS states.
    Preserves existing user reports, never fabricates evidence, never overwrites
    human overrides, and records an audit trail.
    Supports dry_run=True to preview counts without applying any changes.
    """
    res = await db.execute(
        select(Report)
        .options(selectinload(Report.media_assets))
        .where(
            and_(
                or_(
                    Report.assessment_status.is_(None),
                    Report.assessment_status == "PENDING",
                ),
                # Never overwrite human overrides
                Report.assessment_status != "OVERRIDDEN",
            )
        )
        .limit(limit)
    )
    reports_to_backfill = res.scalars().all()

    if dry_run:
        with_images = 0
        without_images = 0
        for rep in reports_to_backfill:
            has_valid_img = False
            for asset in rep.media_assets:
                cand = Path(settings.upload_path) / "reports" / asset.file_name
                if cand.exists() and cand.stat().st_size > 0:
                    has_valid_img = True
                    break
                elif Path(asset.file_path).exists() and Path(asset.file_path).stat().st_size > 0:
                    has_valid_img = True
                    break
            if has_valid_img:
                with_images += 1
            else:
                without_images += 1
        return {
            "status": "preview",
            "dry_run": True,
            "total_eligible": len(reports_to_backfill),
            "with_images_to_assess": with_images,
            "missing_or_no_image": without_images,
            "message": f"Preview: {len(reports_to_backfill)} eligible reports ({with_images} with valid photo, {without_images} with missing/no photo). No changes were written.",
        }

    assessed_count = 0
    no_image_count = 0
    no_detections_count = 0
    failed_count = 0

    for rep in reports_to_backfill:
        primary_asset = None
        for asset in rep.media_assets:
            if asset.asset_type in ("report_photo", "initial"):
                primary_asset = asset
                break
        if not primary_asset and rep.media_assets:
            primary_asset = rep.media_assets[0]

        img_path = None
        if primary_asset:
            candidate = Path(settings.upload_path) / "reports" / primary_asset.file_name
            if candidate.exists():
                img_path = str(candidate)
            elif Path(primary_asset.file_path).exists():
                img_path = primary_asset.file_path

        outcome = await run_automatic_assessment(rep, img_path, db)
        status = outcome.get("status")
        if status in ("COMPLETED", "REVIEW_REQUIRED"):
            assessed_count += 1
        elif status == "NO_IMAGE":
            no_image_count += 1
        elif status == "NO_DETECTIONS":
            no_detections_count += 1
        else:
            failed_count += 1

    audit = AuditEvent(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="backfill_assessments",
        resource_type="system",
        resource_id="reports",
        details={
            "total_processed": len(reports_to_backfill),
            "assessed": assessed_count,
            "no_image": no_image_count,
            "no_detections": no_detections_count,
            "failed": failed_count,
            "dry_run": False,
        },
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "dry_run": False,
        "total_processed": len(reports_to_backfill),
        "assessed": assessed_count,
        "no_image": no_image_count,
        "no_detections": no_detections_count,
        "failed": failed_count,
    }


# ─── Coordinator: assign team ─────────────────────────────────────────────────

@router.post("/{report_id}/assign", response_model=dict)
async def assign_report(
    report_id: str,
    body: AssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    result = await db.execute(select(Report).where(or_(Report.id == report_id, Report.public_ref == report_id.upper())))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status not in (ReportStatus.VERIFIED, ReportStatus.ASSIGNED):
        raise HTTPException(status_code=400, detail="Only VERIFIED or ASSIGNED reports can be assigned")

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
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "severity": r.severity.value if hasattr(r.severity, "value") else (str(r.severity) if r.severity else None),
            "damage_type": r.damage_type.value if hasattr(r.damage_type, "value") else str(r.damage_type),
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
        .where(or_(Report.id == report_id, Report.public_ref == report_id.upper()))
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
            "distinction_category": c.distinction_category,
            "recommendation": c.recommendation,
            "reasoning": c.match_evidence.get("reasoning", ""),
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
    r1 = await db.execute(select(Report).where(or_(Report.id == report_id, Report.public_ref == report_id.upper())))
    r2 = await db.execute(select(Report).where(or_(Report.id == duplicate_id, Report.public_ref == duplicate_id.upper())))
    rep1 = r1.scalar_one_or_none()
    rep2 = r2.scalar_one_or_none()
    if not rep1 or not rep2:
        raise HTTPException(status_code=404, detail="Report not found")

    # Check not already linked
    existing = await db.execute(
        select(DuplicateLink).where(
            DuplicateLink.primary_report_id == rep1.id,
            DuplicateLink.duplicate_report_id == rep2.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_linked"}

    link = DuplicateLink(
        primary_report_id=rep1.id,
        duplicate_report_id=rep2.id,
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
    current_user: User = Depends(require_team_or_above),
):
    """Upload completion evidence and mark report as pending verification."""
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.assignment))
        .where(or_(Report.id == report_id, Report.public_ref == report_id.upper()))
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status not in (ReportStatus.IN_PROGRESS, ReportStatus.ASSIGNED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit completion for report in status: {report.status.value}"
        )

    if photo is None:
        raise HTTPException(status_code=400, detail="After-repair photograph is required")

    photo_path = None
    if photo:
        content_type = photo.content_type or ""
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        if content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Unsupported completion photo type")
        content = await photo.read()
        enforce_upload_size(content)
        validate_image_bytes(content)
        safe_name = await _safe_filename(photo.filename or "completion.jpg")
        photo_path, safe_name = await storage_service.save_file(
            content=content,
            safe_filename=safe_name,
            folder="completions",
            content_type=content_type,
        )

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

