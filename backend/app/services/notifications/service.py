"""In-app notification service with SSE support."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.notification import Notification

logger = logging.getLogger(__name__)

# SSE subscriber registry: user_id -> list of asyncio.Queue
_sse_subscribers: dict[str, list[asyncio.Queue]] = {}


async def create_notification(
    db: AsyncSession,
    *,
    title: str,
    body: str,
    notification_type: str,
    user_id: Optional[str] = None,
    report_id: Optional[str] = None,
    recipient_email: Optional[str] = None,
) -> Notification:
    """Persist and broadcast a notification."""
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

    # Broadcast to SSE subscribers
    if user_id and user_id in _sse_subscribers:
        payload = {
            "id": notification.id,
            "title": title,
            "body": body,
            "type": notification_type,
            "report_id": report_id,
            "created_at": notification.created_at.isoformat(),
        }
        for queue in _sse_subscribers[user_id]:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    return notification


def subscribe_sse(user_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    _sse_subscribers.setdefault(user_id, []).append(queue)
    return queue


def unsubscribe_sse(user_id: str, queue: asyncio.Queue) -> None:
    if user_id in _sse_subscribers:
        try:
            _sse_subscribers[user_id].remove(queue)
        except ValueError:
            pass
        if not _sse_subscribers[user_id]:
            del _sse_subscribers[user_id]


async def get_notifications(
    db: AsyncSession,
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.is_read == False)  # noqa: E712
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def mark_read(db: AsyncSession, notification_id: str, user_id: str) -> Optional[Notification]:
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
