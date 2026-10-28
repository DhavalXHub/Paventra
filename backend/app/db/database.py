"""Async SQLAlchemy engine and session factory."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables and apply backward-compatible schema enhancements."""
    async with engine.begin() as conn:
        from app.models import user, report, team, inspection, notification, audit  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

        def _migrate_sqlite_columns(sync_conn):
            from sqlalchemy import text
            res = sync_conn.execute(text("PRAGMA table_info(reports)"))
            existing = {row[1] for row in res.fetchall()}
            new_cols = [
                ("assessment_status", "VARCHAR(50) DEFAULT 'PENDING'"),
                ("ai_model_name", "VARCHAR(100)"),
                ("ai_assessed_at", "DATETIME"),
                ("original_severity", "VARCHAR(20)"),
                ("original_priority_score", "FLOAT"),
                ("override_reason", "TEXT"),
                ("override_by_id", "VARCHAR(36)"),
                ("override_at", "DATETIME"),
            ]
            for col_name, col_type in new_cols:
                if col_name not in existing:
                    sync_conn.execute(text(f"ALTER TABLE reports ADD COLUMN {col_name} {col_type}"))

        await conn.run_sync(_migrate_sqlite_columns)
