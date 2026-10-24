"""Teams, notifications, analytics, and audit API routes."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import json

from app.core.deps import get_db, get_current_user, require_coordinator
from app.models.user import User
from app.models.team import RepairTeam
from app.models.audit import AuditEvent
from app.schemas.schemas import TeamCreate, TeamOut, NotificationOut, AnalyticsSummary, TrendPoint
from app.services.notifications.service import (
    create_notification, get_notifications, mark_read, subscribe_sse, unsubscribe_sse
)
from app.services.analytics.summary import get_summary_stats, get_trends

logger = logging.getLogger(__name__)

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
