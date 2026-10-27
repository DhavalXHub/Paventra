"""Teams, notifications, analytics, and audit API routes."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import json

from app.core.deps import get_db, get_current_user, require_coordinator, require_team_or_above
from app.models.user import User, UserRole
from app.models.team import RepairTeam
from app.models.report import Report, RepairAssignment, ReportStatus, ReportStatusHistory
from app.models.audit import AuditEvent
from sqlalchemy.orm import selectinload
from app.schemas.schemas import TeamCreate, TeamOut, NotificationOut, AnalyticsSummary, TrendPoint
from app.services.notifications.service import (
    create_notification, get_notifications, mark_read, subscribe_sse, unsubscribe_sse
)
from app.services.analytics.summary import get_summary_stats, get_trends

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field
from app.services.prioritization.fuzzy_engine import compute_priority, evaluate_all_memberships

class FuzzySimulateRequest(BaseModel):
    severity: float = Field(5.0, ge=0.0, le=10.0, description="Estimated damage severity (0-10)")
    traffic_exposure: float = Field(5.0, ge=0.0, le=10.0, description="Traffic volume / road hierarchy (0-10)")
    time_unresolved_days: float = Field(0.0, ge=0.0, le=365.0, description="Days pending (0-365)")
    safety_urgency: float = Field(5.0, ge=0.0, le=10.0, description="Pedestrian/rider safety urgency (0-10)")


# ─── Teams ────────────────────────────────────────────────────────────────────
teams_router = APIRouter(prefix="/teams", tags=["teams"])


@teams_router.get("", response_model=list[TeamOut])
async def list_teams(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    result = await db.execute(select(RepairTeam).where(RepairTeam.is_active == True).order_by(RepairTeam.name))  # noqa: E712
    return list(result.scalars().all())


@teams_router.post("", response_model=TeamOut, status_code=201)
async def create_team(
    body: TeamCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    existing = await db.execute(select(RepairTeam).where(RepairTeam.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Team name already exists")
    team = RepairTeam(**body.model_dump())
    db.add(team)
    await db.flush()
    return team


@teams_router.patch("/{team_id}", response_model=TeamOut)
async def update_team(
    team_id: str,
    body: TeamCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    result = await db.execute(select(RepairTeam).where(RepairTeam.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(team, k, v)
    await db.flush()
    return team


@teams_router.get("/my-jobs", response_model=list[dict])
async def list_my_repair_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_team_or_above),
):
    """View assigned repair jobs for the team or coordinator."""
    q = (
        select(RepairAssignment)
        .options(
            selectinload(RepairAssignment.report).selectinload(Report.media_assets),
            selectinload(RepairAssignment.team),
        )
    )
    if current_user.role == UserRole.REPAIR_TEAM and current_user.team_id:
        q = q.where(RepairAssignment.team_id == current_user.team_id)

    rows = (await db.execute(q)).scalars().all()
    out = []
    for a in rows:
        r = a.report
        if not r:
            continue
        out.append({
            "assignment_id": a.id,
            "report_id": r.id,
            "public_ref": r.public_ref,
            "status": r.status.value,
            "damage_type": r.damage_type.value,
            "severity": r.severity.value if r.severity else None,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "address_hint": r.address_hint,
            "description": r.description,
            "team_id": a.team_id,
            "team_name": a.team.name if a.team else None,
            "target_date": a.target_date.isoformat() if a.target_date else None,
            "assignment_notes": a.notes,
            "completion_notes": a.completion_notes,
            "assigned_at": a.assigned_at.isoformat(),
            "media_assets": [
                {
                    "id": m.id,
                    "file_name": m.file_name,
                    "asset_type": m.asset_type,
                    "uploaded_at": m.uploaded_at.isoformat(),
                }
                for m in r.media_assets
            ],
        })
    return out


@teams_router.patch("/jobs/{report_id}/start", response_model=dict)
async def start_repair_job(
    report_id: str,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_team_or_above),
):
    """Mark repair work as in_progress."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != ReportStatus.ASSIGNED:
        raise HTTPException(status_code=400, detail=f"Cannot start work on report in status {report.status.value}")

    old_status = report.status
    report.status = ReportStatus.IN_PROGRESS
    history = ReportStatusHistory(
        report_id=report.id,
        from_status=old_status.value,
        to_status=ReportStatus.IN_PROGRESS.value,
        changed_by_id=current_user.id,
        changed_by_email=current_user.email,
        notes=notes or "Repair team commenced on-site work",
    )
    db.add(history)
    audit = AuditEvent(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="work_commenced",
        resource_type="report",
        resource_id=report.id,
        details={"status": "in_progress"},
    )
    db.add(audit)
    await db.commit()
    return {"status": "in_progress", "report_id": report_id}


# ─── Notifications ────────────────────────────────────────────────────────────
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications_router.get("", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_notifications(db, current_user.id, unread_only=unread_only)


@notifications_router.patch("/{notification_id}/read")
async def read_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = await mark_read(db, notification_id, current_user.id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"id": n.id, "is_read": n.is_read}


@notifications_router.patch("/read-all")
async def read_all_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.notification import Notification
    from sqlalchemy import update as sql_update
    from datetime import datetime, timezone
    await db.execute(
        sql_update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"marked_read": True}


@notifications_router.get("/stream")
async def notification_stream(current_user: User = Depends(get_current_user)):
    queue = subscribe_sse(current_user.id)

    async def event_generator():
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe_sse(current_user.id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Analytics ────────────────────────────────────────────────────────────────
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_router.get("/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    return await get_summary_stats(db)


@analytics_router.get("/trends", response_model=list[TrendPoint])
async def analytics_trends(
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    return await get_trends(db, days)


@analytics_router.get("/batch")
async def analytics_batch_summary(
    _: User = Depends(require_coordinator),
):
    """Return a previously generated batch analytics file. Does not run Spark inline."""
    from pathlib import Path
    import json
    candidates = [
        Path("uploads/batch_analytics_summary.json"),
        Path("backend/uploads/batch_analytics_summary.json"),
        Path("../analytics/reports/batch_analytics_summary.json"),
        Path("analytics/reports/batch_analytics_summary.json"),
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                payload.setdefault(
                    "data_origin_note",
                    "This file is a batch job export. It may be a labeled synthetic fixture or a live database export.",
                )
                return payload
            except Exception:
                logger.warning("Could not read batch analytics file %s", p)

    raise HTTPException(
        status_code=404,
        detail="No batch analytics summary has been generated. Run analytics/jobs/road_damage_batch_analytics.py.",
    )


@analytics_router.post("/fuzzy-simulate")
async def simulate_fuzzy_priority(
    payload: FuzzySimulateRequest,
):
    """
    Simulates the 22-rule Mamdani Fuzzy Inference System with full academic explainability.
    Publicly accessible so evaluators, students, and coordinators can test inference in real time.
    """
    res = compute_priority(
        severity_numeric=payload.severity,
        traffic_exposure=payload.traffic_exposure,
        time_unresolved_days=payload.time_unresolved_days,
        safety_urgency=payload.safety_urgency,
    )
    delta = round(res.priority_score - res.baseline_score, 2)
    return {
        "priority_score": res.priority_score,
        "priority_label": res.priority_label,
        "engine_used": res.engine_used,
        "baseline_score": res.baseline_score,
        "decision_delta": delta,
        "top_contributing_factors": res.top_contributing_factors,
        "membership_activations": res.membership_activations,
        "explanation_narrative": res.explanation_narrative,
        "inputs": res.inputs,
    }


@analytics_router.get("/fuzzy-metadata")
async def get_fuzzy_system_metadata():
    """
    Returns mathematical membership function parameters, linguistic terms,
    and rule base specifications for frontend visualization and academic defense.
    """
    return {
        "inference_engine": "Mamdani Fuzzy Inference System",
        "defuzzification": "Centroid (Center of Gravity / COG)",
        "implication_operator": "Mamdani Minimum (min)",
        "aggregation_operator": "Maximum (max)",
        "universes_of_discourse": {
            "severity": {"min": 0.0, "max": 10.0, "unit": "distress_score", "step": 0.1},
            "traffic": {"min": 0.0, "max": 10.0, "unit": "volume_index", "step": 0.1},
            "time_days": {"min": 0.0, "max": 365.0, "unit": "days", "step": 1.0},
            "safety": {"min": 0.0, "max": 10.0, "unit": "hazard_index", "step": 0.1},
            "priority": {"min": 0.0, "max": 100.0, "unit": "priority_score", "step": 0.5},
        },
        "membership_functions": {
            "severity": {
                "low": {"type": "trimf", "params": [0.0, 0.0, 4.0]},
                "moderate": {"type": "trimf", "params": [2.0, 5.0, 8.0]},
                "high": {"type": "trimf", "params": [6.0, 8.0, 10.0]},
                "critical": {"type": "trimf", "params": [8.5, 10.0, 10.0]},
            },
            "traffic": {
                "low": {"type": "trimf", "params": [0.0, 0.0, 4.0]},
                "medium": {"type": "trimf", "params": [2.0, 5.0, 8.0]},
                "high": {"type": "trimf", "params": [6.0, 10.0, 10.0]},
            },
            "time_days": {
                "short": {"type": "trimf", "params": [0.0, 0.0, 30.0]},
                "medium": {"type": "trimf", "params": [14.0, 60.0, 120.0]},
                "long": {"type": "trimf", "params": [60.0, 120.0, 200.0]},
                "very_long": {"type": "trimf", "params": [150.0, 365.0, 365.0]},
            },
            "safety": {
                "low": {"type": "trimf", "params": [0.0, 0.0, 4.0]},
                "medium": {"type": "trimf", "params": [2.0, 5.0, 8.0]},
                "high": {"type": "trimf", "params": [6.0, 10.0, 10.0]},
            },
            "priority": {
                "low": {"type": "trimf", "params": [0.0, 0.0, 30.0]},
                "medium": {"type": "trimf", "params": [20.0, 37.0, 55.0]},
                "medium_high": {"type": "trimf", "params": [45.0, 60.0, 75.0]},
                "high": {"type": "trimf", "params": [65.0, 78.0, 90.0]},
                "critical": {"type": "trimf", "params": [85.0, 100.0, 100.0]},
            },
        },
        "rules_count": 22,
        "rule_base": [
            "R01: IF severity IS critical AND safety IS high THEN priority IS critical",
            "R02: IF severity IS critical AND safety IS medium THEN priority IS critical",
            "R03: IF severity IS critical AND safety IS low THEN priority IS high",
            "R04: IF severity IS high AND safety IS high THEN priority IS critical",
            "R05: IF severity IS high AND traffic IS high THEN priority IS high",
            "R06: IF severity IS high AND traffic IS medium THEN priority IS high",
            "R07: IF severity IS high AND traffic IS low THEN priority IS medium_high",
            "R08: IF severity IS moderate AND safety IS high THEN priority IS high",
            "R09: IF severity IS moderate AND time_days IS very_long THEN priority IS high",
            "R10: IF severity IS moderate AND time_days IS long AND traffic IS high THEN priority IS high",
            "R11: IF traffic IS high AND severity IS moderate THEN priority IS medium_high",
            "R12: IF severity IS moderate AND safety IS medium THEN priority IS medium_high",
            "R13: IF severity IS low AND safety IS high THEN priority IS medium_high",
            "R14: IF severity IS moderate AND traffic IS medium THEN priority IS medium",
            "R15: IF severity IS moderate AND traffic IS low THEN priority IS medium",
            "R16: IF severity IS low AND time_days IS very_long THEN priority IS medium",
            "R17: IF severity IS low AND traffic IS high AND time_days IS long THEN priority IS medium",
            "R18: IF severity IS low AND safety IS low THEN priority IS low",
            "R19: IF severity IS low AND time_days IS short THEN priority IS low",
            "R20: IF severity IS low AND traffic IS medium THEN priority IS low",
            "R21: IF severity IS low AND traffic IS low THEN priority IS low",
            "R22: IF safety IS high AND traffic IS high THEN priority IS high",
        ],
    }


@analytics_router.get("/soft-computing-benchmark")
async def get_soft_computing_benchmark():
    """
    Returns tabular benchmark dataset records and summary statistics
    for empirical evaluation of fuzzy priority vs baseline weighted scoring.
    """
    from pathlib import Path
    import json
    candidates = [
        Path("analytics/fixtures/soft_computing_maintenance_benchmark.json"),
        Path("../analytics/fixtures/soft_computing_maintenance_benchmark.json"),
    ]
    for p in candidates:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                records = json.load(f)
            # Calculate aggregate statistics
            total = len(records)
            avg_fuzzy = round(sum(r["fuzzy_priority_score"] for r in records) / max(1, total), 2)
            avg_base = round(sum(r["baseline_weighted_score"] for r in records) / max(1, total), 2)
            critical_count = sum(1 for r in records if r["priority_label"] == "CRITICAL")
            high_count = sum(1 for r in records if r["priority_label"] == "HIGH")
            elevated_by_fuzzy = sum(1 for r in records if r["decision_delta"] >= 5.0)
            subdued_by_fuzzy = sum(1 for r in records if r["decision_delta"] <= -5.0)

            return {
                "total_records": total,
                "summary": {
                    "average_fuzzy_priority": avg_fuzzy,
                    "average_baseline_score": avg_base,
                    "critical_reports": critical_count,
                    "high_reports": high_count,
                    "cases_elevated_by_fuzzy": elevated_by_fuzzy,
                    "cases_subdued_by_fuzzy": subdued_by_fuzzy,
                },
                "records_sample": records[:50],
            }

    raise HTTPException(status_code=404, detail="Benchmark dataset not found. Run generate_benchmark_dataset.py.")


# ─── Audit ────────────────────────────────────────────────────────────────────
audit_router = APIRouter(prefix="/audit", tags=["audit"])


@audit_router.get("/{report_id}", response_model=list[dict])
async def get_audit(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.resource_id == report_id)
        .order_by(AuditEvent.created_at.desc())
    )
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "action": e.action,
            "actor_email": e.actor_email,
            "details": e.details,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]
