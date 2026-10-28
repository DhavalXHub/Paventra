"""
Database Migration Script: SQLite (paventra.db) -> PostgreSQL (Supabase / Neon).

Safely migrates:
  - Users (Preserves coordinator, citizen, and repair-team accounts and hashed passwords)
  - Repair Teams
  - Genuine Citizen Reports (Strictly excludes AUTOMATED_TEST_ARTIFACT records)
  - Media Assets
  - Report Status History
  - Duplicate Links

Preserves local SQLite paventra.db completely unchanged.
Usage:
  python backend/scripts/migrate_to_postgres.py "postgresql+asyncpg://postgres.[REF]:[PWD]@[HOST]:6543/postgres"
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.db.database import Base
from app.models.user import User
from app.models.team import RepairTeam
from app.models.report import Report, MediaAsset, ReportStatusHistory, DuplicateLink, RepairAssignment


async def migrate(target_url: str):
    if not target_url:
        print("ERROR: Target PostgreSQL URL is required.")
        print('Usage: python backend/scripts/migrate_to_postgres.py "postgresql+asyncpg://postgres:pass@host:5432/dbname"')
        sys.exit(1)

    # Normalize url if standard postgres:// was provided
    if target_url.startswith("postgres://"):
        target_url = target_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif target_url.startswith("postgresql://") and not target_url.startswith("postgresql+asyncpg://"):
        target_url = target_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    sqlite_db_path = backend_root / "paventra.db"
    if not sqlite_db_path.exists():
        print(f"ERROR: Local source database not found at {sqlite_db_path}")
        sys.exit(1)

    source_url = f"sqlite+aiosqlite:///{sqlite_db_path}"
    print(f"[1/5] Source SQLite database: {sqlite_db_path}")
    print(f"[2/5] Target PostgreSQL: {target_url.split('@')[-1] if '@' in target_url else 'target'}")

    src_engine = create_async_engine(source_url, echo=False)
    dst_engine = create_async_engine(target_url, echo=False, pool_pre_ping=True)

    SrcSession = async_sessionmaker(src_engine, class_=AsyncSession, expire_on_commit=False)
    DstSession = async_sessionmaker(dst_engine, class_=AsyncSession, expire_on_commit=False)

    print("[3/5] Creating table schema on PostgreSQL...")
    async with dst_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Schema created successfully on PostgreSQL.")

    print("[4/5] Reading genuine records from SQLite...")
    async with SrcSession() as src_db:
        # 1. Users
        users = (await src_db.execute(select(User))).scalars().all()
        # 2. Teams
        teams = (await src_db.execute(select(RepairTeam))).scalars().all()
        # 3. Reports (Excluding test artifacts)
        reports = (await src_db.execute(
            select(Report).where(
                (Report.assessment_status != "AUTOMATED_TEST_ARTIFACT") | (Report.assessment_status.is_(None))
            )
        )).scalars().all()
        valid_report_ids = {r.id for r in reports}

        # 4. Media assets for valid reports
        all_media = (await src_db.execute(select(MediaAsset))).scalars().all()
        media_assets = [m for m in all_media if m.report_id in valid_report_ids]

        # 5. Status history for valid reports
        all_history = (await src_db.execute(select(ReportStatusHistory))).scalars().all()
        history = [h for h in all_history if h.report_id in valid_report_ids]

        # 6. Assignments
        all_assignments = (await src_db.execute(select(RepairAssignment))).scalars().all()
        assignments = [a for a in all_assignments if a.report_id in valid_report_ids]

    print(f"Found genuine records to migrate:")
    print(f" - Users: {len(users)}")
    print(f" - Repair Teams: {len(teams)}")
    print(f" - Genuine Reports: {len(reports)}")
    print(f" - Media Assets: {len(media_assets)}")
    print(f" - Status History: {len(history)}")
    print(f" - Assignments: {len(assignments)}")

    print("[5/5] Writing records to target PostgreSQL...")
    async with DstSession() as dst_db:
        try:
            # Transfer Users
            for u in users:
                existing = await dst_db.get(User, u.id)
                if not existing:
                    dst_db.add(User(
                        id=u.id,
                        email=u.email,
                        hashed_password=u.hashed_password,
                        role=u.role,
                        is_active=u.is_active,
                        phone_number=u.phone_number,
                        created_at=u.created_at,
                    ))
            await dst_db.flush()

            # Transfer Teams
            for t in teams:
                existing = await dst_db.get(RepairTeam, t.id)
                if not existing:
                    dst_db.add(RepairTeam(
                        id=t.id,
                        name=t.name,
                        description=t.description,
                        contact_email=t.contact_email,
                        contact_phone=t.contact_phone,
                        is_active=t.is_active,
                        created_at=t.created_at,
                    ))
            await dst_db.flush()

            # Transfer Reports
            for r in reports:
                existing = await dst_db.get(Report, r.id)
                if not existing:
                    dst_db.add(Report(
                        id=r.id,
                        public_ref=r.public_ref,
                        source=r.source,
                        status=r.status,
                        submitter_id=r.submitter_id,
                        submitter_email=r.submitter_email,
                        claim_token=r.claim_token,
                        description=r.description,
                        damage_type=r.damage_type,
                        severity=r.severity,
                        severity_is_estimated=r.severity_is_estimated,
                        latitude=r.latitude,
                        longitude=r.longitude,
                        location_source=r.location_source,
                        location_accuracy_meters=r.location_accuracy_meters,
                        address_hint=r.address_hint,
                        ai_confidence=r.ai_confidence,
                        ai_damage_type=r.ai_damage_type,
                        ai_bounding_boxes=r.ai_bounding_boxes,
                        ai_inference_ms=r.ai_inference_ms,
                        priority_score=r.priority_score,
                        priority_explanation=r.priority_explanation,
                        assessment_status=r.assessment_status,
                        ai_model_name=r.ai_model_name,
                        ai_assessed_at=r.ai_assessed_at,
                        original_severity=r.original_severity,
                        original_priority_score=r.original_priority_score,
                        override_reason=r.override_reason,
                        override_by_id=r.override_by_id,
                        override_at=r.override_at,
                        review_reason=r.review_reason,
                        created_at=r.created_at,
                        updated_at=r.updated_at,
                    ))
            await dst_db.flush()

            # Transfer Media Assets
            for m in media_assets:
                existing = await dst_db.get(MediaAsset, m.id)
                if not existing:
                    dst_db.add(MediaAsset(
                        id=m.id,
                        report_id=m.report_id,
                        file_path=m.file_path,
                        file_name=m.file_name,
                        mime_type=m.mime_type,
                        file_size_bytes=m.file_size_bytes,
                        asset_type=m.asset_type,
                        annotated_path=m.annotated_path,
                        uploaded_at=m.uploaded_at,
                    ))

            # Transfer Status History
            for h in history:
                existing = await dst_db.get(ReportStatusHistory, h.id)
                if not existing:
                    dst_db.add(ReportStatusHistory(
                        id=h.id,
                        report_id=h.report_id,
                        from_status=h.from_status,
                        to_status=h.to_status,
                        changed_by_id=h.changed_by_id,
                        changed_by_email=h.changed_by_email,
                        reason=h.reason,
                        notes=h.notes,
                        changed_at=h.changed_at,
                    ))

            # Transfer Assignments
            for a in assignments:
                existing = await dst_db.get(RepairAssignment, a.id)
                if not existing:
                    dst_db.add(RepairAssignment(
                        id=a.id,
                        report_id=a.report_id,
                        team_id=a.team_id,
                        status=a.status,
                        assigned_at=a.assigned_at,
                        target_completion_date=a.target_completion_date,
                    ))

            await dst_db.commit()
            print("\nMigration completed successfully!")
            print(f"Total reports preserved in PostgreSQL: {len(reports)}")
        except Exception as e:
            await dst_db.rollback()
            print(f"\nMigration failed: {e}")
            raise


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TARGET_DATABASE_URL", "")
    asyncio.run(migrate(url))
