"""In-app notification service with SSE real-time broadcast and persistent storage."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update as sql_update

from app.models.notification import Notification
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# SSE subscriber registry: user_id -> list of asyncio.Queue
_sse_subscribers: dict[str, list[asyncio.Queue]] = {}


def subscribe_sse(user_id: str) -> asyncio.Queue:
    """Register an SSE listener queue for a connected user."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _sse_subscribers.setdefault(user_id, []).append(queue)
    logger.debug("SSE subscribed: user_id=%s (total listeners=%d)", user_id, len(_sse_subscribers[user_id]))
    return queue


def unsubscribe_sse(user_id: str, queue: asyncio.Queue) -> None:
    """Remove an SSE listener queue on client disconnect."""
    if user_id in _sse_subscribers:
        try:
            _sse_subscribers[user_id].remove(queue)
        except ValueError:
            pass
        if not _sse_subscribers[user_id]:
            del _sse_subscribers[user_id]
    logger.debug("SSE unsubscribed: user_id=%s", user_id)


def broadcast_to_user(user_id: str, payload: dict) -> int:
    """Push an event to all active SSE queues for a given user. Returns count of delivered queues."""
    queues = _sse_subscribers.get(user_id, [])
    delivered = 0
    for q in list(queues):
        try:
            q.put_nowait(payload)
            delivered += 1
        except asyncio.QueueFull:
            logger.warning("SSE queue full for user_id=%s; dropping real-time frame", user_id)
        except Exception as exc:
            logger.warning("Error pushing to SSE queue for user_id=%s: %s", user_id, exc)
    return delivered


async def _is_duplicate(
    db: AsyncSession,
    user_id: Optional[str],
    report_id: Optional[str],
    notification_type: str,
    window_seconds: int = 5,
) -> bool:
    """Check if an identical unread notification was recorded very recently."""
    if not user_id:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    stmt = (
        select(Notification.id)
        .where(
            Notification.user_id == user_id,
            Notification.report_id == report_id,
            Notification.notification_type == notification_type,
            Notification.created_at >= cutoff,
        )
        .limit(1)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None


def _resolve_action_url(notification_type: str, report_id: Optional[str], user_role: Optional[UserRole | str] = None) -> Optional[str]:
    """Determine client route for a notification click."""
    if not report_id:
        return None
    role_str = str(user_role.value if isinstance(user_role, UserRole) else user_role or "").lower()
    if role_str in ("coordinator", "admin"):
        return f"/coordinator/reports/{report_id}"
    elif role_str == "repair_team":
        return "/team/jobs"
    else:
        return f"/my-reports"


async def create_notification(
    db: AsyncSession,
    *,
    title: str,
    body: str,
    notification_type: str,
    user_id: Optional[str] = None,
    report_id: Optional[str] = None,
    recipient_email: Optional[str] = None,
    action_url: Optional[str] = None,
    user_role: Optional[UserRole | str] = None,
) -> Optional[Notification]:
    """Persist a single notification and broadcast to real-time subscribers."""
    # Deduplication check
    if user_id and await _is_duplicate(db, user_id, report_id, notification_type):
        logger.debug("Suppressed duplicate notification for user_id=%s, report_id=%s, type=%s", user_id, report_id, notification_type)
        return None

    notification = Notification(
        user_id=user_id,
        report_id=report_id,
        recipient_email=recipient_email,
        title=title,
        body=body,
        notification_type=notification_type,
    )
    db.add(notification)
    await db.flush()

    resolved_url = action_url or _resolve_action_url(notification_type, report_id, user_role)

    # Real-time SSE push
    if user_id:
        payload = {
            "id": notification.id,
            "title": title,
            "body": body,
            "type": notification_type,
            "report_id": report_id,
            "action_url": resolved_url,
            "created_at": notification.created_at.isoformat(),
        }
        broadcast_to_user(user_id, payload)

    return notification


async def notify_coordinators(
    db: AsyncSession,
    *,
    title: str,
    body: str,
    notification_type: str,
    report_id: Optional[str] = None,
    action_url: Optional[str] = None,
    exclude_user_id: Optional[str] = None,
) -> list[Notification]:
    """Persist notifications for all active coordinators and push to their SSE queues."""
    stmt = (
        select(User)
        .where(
            User.role.in_([UserRole.COORDINATOR, UserRole.ADMIN]),
            User.is_active == True,  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    coords = result.scalars().all()

    created: list[Notification] = []
    for coord in coords:
        if exclude_user_id and coord.id == exclude_user_id:
            continue
        n = await create_notification(
            db,
            title=title,
            body=body,
            notification_type=notification_type,
            user_id=coord.id,
            report_id=report_id,
            action_url=action_url or f"/coordinator/reports/{report_id}" if report_id else None,
            user_role=UserRole.COORDINATOR,
        )
        if n:
            created.append(n)
    return created


async def notify_team(
    db: AsyncSession,
    *,
    team_id: str,
    title: str,
    body: str,
    notification_type: str,
    report_id: Optional[str] = None,
    action_url: Optional[str] = None,
    exclude_user_id: Optional[str] = None,
) -> list[Notification]:
    """Persist notifications for all active members of a repair team and push via SSE."""
    stmt = (
        select(User)
        .where(
            User.team_id == team_id,
            User.is_active == True,  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    members = result.scalars().all()

    created: list[Notification] = []
    for member in members:
        if exclude_user_id and member.id == exclude_user_id:
            continue
        n = await create_notification(
            db,
            title=title,
            body=body,
            notification_type=notification_type,
            user_id=member.id,
            report_id=report_id,
            action_url=action_url or "/team/jobs",
            user_role=UserRole.REPAIR_TEAM,
        )
        if n:
            created.append(n)
    return created


async def notify_user(
    db: AsyncSession,
    *,
    user_id: Optional[str],
    title: str,
    body: str,
    notification_type: str,
    report_id: Optional[str] = None,
    recipient_email: Optional[str] = None,
    action_url: Optional[str] = None,
    user_role: Optional[UserRole | str] = None,
) -> Optional[Notification]:
    """Convenience helper to notify a specific user (citizen, coordinator, or crew member)."""
    if not user_id and not recipient_email:
        return None
    return await create_notification(
        db,
        title=title,
        body=body,
        notification_type=notification_type,
        user_id=user_id,
        report_id=report_id,
        recipient_email=recipient_email,
        action_url=action_url,
        user_role=user_role,
    )


async def get_notifications(
    db: AsyncSession,
    user_id: str,
    user_role: Optional[UserRole | str] = None,
    unread_only: bool = False,
    limit: int = 50,
) -> list[dict]:
    """Retrieve notifications for a user, adding dynamic action_url."""
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.is_read == False)  # noqa: E712
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(q)
    notifications = list(result.scalars().all())

    out = []
    for n in notifications:
        action_url = _resolve_action_url(n.notification_type, n.report_id, user_role)
        out.append({
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "notification_type": n.notification_type,
            "is_read": n.is_read,
            "report_id": n.report_id,
            "action_url": action_url,
            "created_at": n.created_at,
            "read_at": n.read_at,
        })
    return out


async def count_unread(db: AsyncSession, user_id: str) -> int:
    """Return count of unread notifications for a user."""
    stmt = (
        select(func.count(Notification.id))
        .where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def mark_read(db: AsyncSession, notification_id: str, user_id: str) -> Optional[Notification]:
    """Mark a single notification as read, enforcing user ownership."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
    return notification


async def mark_all_read(db: AsyncSession, user_id: str) -> int:
    """Mark all unread notifications for a user as read."""
    now = datetime.now(timezone.utc)
    res = await db.execute(
        sql_update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True, read_at=now)
    )
    return res.rowcount
