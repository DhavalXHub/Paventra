"""Analytics summary queries."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.report import Report, ReportStatus, SeverityLevel

logger = logging.getLogger(__name__)


async def get_summary_stats(db: AsyncSession) -> dict[str, Any]:
    total_q = await db.execute(select(func.count(Report.id)))
    total = total_q.scalar() or 0

    status_q = await db.execute(
        select(Report.status, func.count(Report.id)).group_by(Report.status)
    )
    by_status = {str(row[0]): row[1] for row in status_q.all()}

    source_q = await db.execute(
        select(Report.source, func.count(Report.id)).group_by(Report.source)
    )
    by_source = {str(row[0]): row[1] for row in source_q.all()}

    sev_q = await db.execute(
        select(Report.severity, func.count(Report.id)).group_by(Report.severity)
    )
    by_severity = {str(row[0]): row[1] for row in sev_q.all()}

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_q = await db.execute(
        select(func.count(Report.id)).where(Report.created_at >= week_ago)
    )
    recent_7d = recent_q.scalar() or 0

    overdue_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    overdue_q = await db.execute(
        select(func.count(Report.id)).where(
            Report.status.in_([ReportStatus.ASSIGNED, ReportStatus.IN_PROGRESS]),
            Report.created_at < overdue_cutoff,
        )
    )
    overdue = overdue_q.scalar() or 0

    high_sev_q = await db.execute(
        select(func.count(Report.id)).where(
            Report.severity.in_([SeverityLevel.HIGH, SeverityLevel.CRITICAL]),
            Report.status == ReportStatus.SUBMITTED,
        )
    )
    high_sev_unverified = high_sev_q.scalar() or 0

    return {
        "total_reports": total,
        "by_status": by_status,
        "by_source": by_source,
        "by_severity": by_severity,
        "recent_7_days": recent_7d,
        "overdue_count": overdue,
        "high_severity_unverified": high_sev_unverified,
    }


async def get_trends(db: AsyncSession, days: int = 30) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = await db.execute(
        select(
            func.date(Report.created_at).label("date"),
            func.count(Report.id).label("count"),
        )
        .where(Report.created_at >= since)
        .group_by(func.date(Report.created_at))
        .order_by(func.date(Report.created_at))
    )
    return [{"date": str(row.date), "count": row.count} for row in q.all()]
