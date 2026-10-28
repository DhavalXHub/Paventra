"""
Automated testing for Automatic Damage Assessment & Priority Workflow.
Verifies:
1. Automatic CV + FIS priority on report submission.
2. Honest assessment states (COMPLETED, REVIEW_REQUIRED, NO_IMAGE, NO_DETECTIONS).
3. Coordinator cannot arbitrarily overwrite score on status change.
4. Human override preserves original AI score, requires reason, and creates audit trail.
5. Report list sorting: actionable items sorted by priority score descending with tie-breakers.
6. Non-coordinator role protection on override.
"""
import pytest
import io
import uuid
from datetime import datetime, timezone, timedelta
from PIL import Image
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.security import hash_password, create_access_token
from app.db.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.report import Report, ReportStatus, ReportSource, DamageType, SeverityLevel
from app.models.audit import AuditEvent


def _make_test_image(size: int = 120, color=(128, 64, 32)) -> io.BytesIO:
    buf = io.BytesIO()
    img = Image.new("RGB", (size, size), color)
    buf.name = "test_damage.jpg"
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


@pytest.fixture(autouse=True)
async def ensure_test_users():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Coordinator
        coord_res = await db.execute(select(User).where(User.email == "auto_coord@paventra.local"))
        if not coord_res.scalar_one_or_none():
            db.add(User(
                email="auto_coord@paventra.local",
                full_name="Auto Assessment Coordinator",
                hashed_password=hash_password("CoordPass123!"),
                role=UserRole.COORDINATOR,
            ))
        # Citizen
        cit_res = await db.execute(select(User).where(User.email == "auto_cit@paventra.local"))
        if not cit_res.scalar_one_or_none():
            db.add(User(
                email="auto_cit@paventra.local",
                full_name="Auto Assessment Citizen",
                hashed_password=hash_password("CitizenPass123!"),
                role=UserRole.CITIZEN,
            ))
        await db.commit()


@pytest.mark.asyncio
async def test_automatic_assessment_pipeline_on_submission():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        image_buf = _make_test_image()
        files = {"image": ("pothole_survey.jpg", image_buf, "image/jpeg")}
        data = {
            "latitude": "19.0760",
            "longitude": "72.8777",
            "address_hint": "Western Express Highway Near Bandra Flyover",
            "description": "Deep asphalt distress observed on express corridor",
        }

        res = await client.post("/api/v1/reports", data=data, files=files)
        assert res.status_code == 201
        res_data = res.json()
        assert "public_ref" in res_data
        pub_ref = res_data["public_ref"]

        # Fetch report from DB
        async with AsyncSessionLocal() as db:
            rep_res = await db.execute(select(Report).where(Report.public_ref == pub_ref))
            report = rep_res.scalar_one()

            # Assessment status must be honestly recorded
            assert report.assessment_status in ("COMPLETED", "REVIEW_REQUIRED", "NO_DETECTIONS", "PENDING_MODEL")
            assert report.ai_model_name is not None
            assert "RDD2022" in report.ai_model_name
            assert report.ai_assessed_at is not None

            # If detections were found, priority score must be automatically computed
            if report.severity:
                assert report.priority_score is not None
                assert 0.0 <= report.priority_score <= 100.0
                assert report.original_priority_score == report.priority_score
                assert report.original_severity == report.severity
                assert report.severity_is_estimated is True


@pytest.mark.asyncio
async def test_status_update_does_not_arbitrarily_overwrite_score():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            coord_res = await db.execute(select(User).where(User.email == "auto_coord@paventra.local"))
            coord = coord_res.scalar_one()
            coord_token = create_access_token(coord.id)

            # Create report with established score
            rpt = Report(
                public_ref=f"PAV-{uuid.uuid4().hex[:8].upper()}",
                source=ReportSource.CITIZEN,
                status=ReportStatus.SUBMITTED,
                damage_type=DamageType.POTHOLE,
                severity=SeverityLevel.MODERATE,
                priority_score=52.4,
                assessment_status="COMPLETED",
            )
            db.add(rpt)
            await db.commit()
            await db.refresh(rpt)
            rep_id = rpt.id

        headers = {"Authorization": f"Bearer {coord_token}"}

        # Transition status to UNDER_REVIEW
        r1 = await client.patch(
            f"/api/v1/reports/{rep_id}/status",
            json={"status": "under_review", "notes": "Checking field video"},
            headers=headers,
        )
        assert r1.status_code == 200

        # Verify priority score is unchanged
        async with AsyncSessionLocal() as db:
            rep_res = await db.execute(select(Report).where(Report.id == rep_id))
            refreshed = rep_res.scalar_one()
            assert refreshed.status == ReportStatus.UNDER_REVIEW
            assert refreshed.priority_score == 52.4
            assert refreshed.severity == SeverityLevel.MODERATE


@pytest.mark.asyncio
async def test_human_override_workflow_with_audit_trail():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            coord_res = await db.execute(select(User).where(User.email == "auto_coord@paventra.local"))
            coord = coord_res.scalar_one()
            coord_token = create_access_token(coord.id)

            # Seed report with initial AI assessment
            rpt = Report(
                public_ref=f"PAV-{uuid.uuid4().hex[:8].upper()}",
                source=ReportSource.CITIZEN,
                status=ReportStatus.SUBMITTED,
                damage_type=DamageType.POTHOLE,
                severity=SeverityLevel.LOW,
                original_severity=SeverityLevel.LOW,
                priority_score=28.0,
                original_priority_score=28.0,
                assessment_status="COMPLETED",
                severity_is_estimated=True,
            )
            db.add(rpt)
            await db.commit()
            await db.refresh(rpt)
            rep_id = rpt.id

        headers = {"Authorization": f"Bearer {coord_token}"}

        # Coordinator applies human override with required reason
        override_payload = {
            "severity": "critical",
            "damage_type": "pothole",
            "reason": "On-site inspection reveals deep sub-base hollow causing high risk for two-wheelers",
        }
        res = await client.post(f"/api/v1/reports/{rep_id}/override", json=override_payload, headers=headers)
        assert res.status_code == 200
        data = res.json()

        assert data["severity"] == "critical"
        assert data["severity_is_estimated"] is False
        assert data["assessment_status"] == "OVERRIDDEN"
        assert data["original_severity"] == "low"
        assert data["original_priority_score"] == 28.0
        # Priority score must be recalculated to critical tier (>= 85 or high)
        assert data["priority_score"] > 28.0

        # Verify AuditEvent was logged
        async with AsyncSessionLocal() as db:
            audit_res = await db.execute(
                select(AuditEvent)
                .where(AuditEvent.resource_id == rep_id)
                .where(AuditEvent.action == "assessment_override")
            )
            audit = audit_res.scalar_one_or_none()
            assert audit is not None
            assert audit.actor_email == "auto_coord@paventra.local"
            assert "critical" in str(audit.details)


@pytest.mark.asyncio
async def test_non_coordinator_cannot_override_assessment():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            cit_res = await db.execute(select(User).where(User.email == "auto_cit@paventra.local"))
            citizen = cit_res.scalar_one()
            cit_token = create_access_token(citizen.id)

            rpt = Report(
                public_ref=f"PAV-{uuid.uuid4().hex[:8].upper()}",
                source=ReportSource.CITIZEN,
                status=ReportStatus.SUBMITTED,
                damage_type=DamageType.POTHOLE,
                severity=SeverityLevel.LOW,
            )
            db.add(rpt)
            await db.commit()
            await db.refresh(rpt)
            rep_id = rpt.id

        headers = {"Authorization": f"Bearer {cit_token}"}
        res = await client.post(
            f"/api/v1/reports/{rep_id}/override",
            json={"severity": "critical", "reason": "Citizen tries to escalate"},
            headers=headers,
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_report_list_actionable_sorting_by_priority():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            coord_res = await db.execute(select(User).where(User.email == "auto_coord@paventra.local"))
            coord = coord_res.scalar_one()
            coord_token = create_access_token(coord.id)

            prefix = uuid.uuid4().hex[:4].upper()
            # 1. Actionable High Priority
            r_high = Report(
                public_ref=f"PAV-{prefix}HI",
                source=ReportSource.CITIZEN,
                status=ReportStatus.SUBMITTED,
                priority_score=92.5,
                damage_type=DamageType.POTHOLE,
            )
            # 2. Actionable Moderate Priority
            r_med = Report(
                public_ref=f"PAV-{prefix}MD",
                source=ReportSource.CITIZEN,
                status=ReportStatus.VERIFIED,
                priority_score=61.0,
                damage_type=DamageType.POTHOLE,
            )
            # 3. Resolved (Non-actionable, even with high score)
            r_res = Report(
                public_ref=f"PAV-{prefix}RS",
                source=ReportSource.CITIZEN,
                status=ReportStatus.RESOLVED,
                priority_score=95.0,
                damage_type=DamageType.POTHOLE,
            )
            db.add_all([r_high, r_med, r_res])
            await db.commit()

        headers = {"Authorization": f"Bearer {coord_token}"}
        res = await client.get(f"/api/v1/reports?search={prefix}", headers=headers)
        assert res.status_code == 200
        items = res.json()["items"]

        # Actionable 92.5 should appear BEFORE actionable 61.0
        # And resolved 95.0 should be placed at the end because it is non-actionable
        refs = [item["public_ref"] for item in items]
        assert f"PAV-{prefix}HI" in refs
        assert f"PAV-{prefix}MD" in refs
        assert f"PAV-{prefix}RS" in refs

        idx_hi = refs.index(f"PAV-{prefix}HI")
        idx_md = refs.index(f"PAV-{prefix}MD")
        idx_rs = refs.index(f"PAV-{prefix}RS")

        assert idx_hi < idx_md, "Higher priority actionable report must appear before lower priority"
        assert idx_md < idx_rs, "Actionable reports must appear before resolved non-actionable reports"


@pytest.mark.asyncio
async def test_backfill_assessments_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            coord_res = await db.execute(select(User).where(User.email == "auto_coord@paventra.local"))
            coord = coord_res.scalar_one()
            coord_token = create_access_token(coord.id)

        headers = {"Authorization": f"Bearer {coord_token}"}
        res = await client.post("/api/v1/reports/backfill-assessments?limit=20", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "total_processed" in data
        assert "assessed" in data
        assert "no_image" in data
