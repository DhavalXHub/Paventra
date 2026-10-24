"""Integration tests for FastAPI endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import io

from app.main import app
from app.core.security import hash_password, create_access_token
from app.db.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.report import Report, ReportStatus, ReportSource, DamageType
from sqlalchemy import select


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Create test coordinator
        coord = await db.execute(select(User).where(User.email == "test_coord@paventra.local"))
        if not coord.scalar_one_or_none():
            db.add(User(
                email="test_coord@paventra.local",
                full_name="Test Coord",
                hashed_password=hash_password("CoordPass123!"),
                role=UserRole.COORDINATOR,
            ))
        # Create test citizen
        citizen = await db.execute(select(User).where(User.email == "test_citizen@paventra.local"))
        if not citizen.scalar_one_or_none():
            db.add(User(
                email="test_citizen@paventra.local",
                full_name="Test Citizen",
                hashed_password=hash_password("CitizenPass123!"),
                role=UserRole.CITIZEN,
            ))
        await db.commit()


@pytest.mark.asyncio
async def test_health_and_readiness():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        ready_r = await client.get("/api/ready")
        assert ready_r.status_code == 200
        assert ready_r.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_citizen_report_submission_and_tracking():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fake_image = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100)
        files = {"image": ("test_pothole.jpg", fake_image, "image/jpeg")}
        data = {
            "description": "Large pothole near city center",
            "damage_type": "pothole",
            "latitude": "19.0760",
            "longitude": "72.8777",
            "location_source": "gps",
            "address_hint": "Main Street junction",
        }

        # 1. Citizen submits report
        res = await client.post("/api/v1/reports", data=data, files=files)
        assert res.status_code == 201
        res_json = res.json()
        assert "public_ref" in res_json
        pub_ref = res_json["public_ref"]
        assert pub_ref.startswith("PAV-")

        # 2. Public tracking check
        track_res = await client.get(f"/api/v1/reports/track/{pub_ref}")
        assert track_res.status_code == 200
        track_json = track_res.json()
        assert track_json["public_ref"] == pub_ref
        assert track_json["status"] == "submitted"
        assert len(track_json["history"]) >= 1


@pytest.mark.asyncio
async def test_invalid_coordinates_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fake_image = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 50)
        files = {"image": ("bad.jpg", fake_image, "image/jpeg")}
        data = {
            "latitude": "999.0",  # Out of range
            "longitude": "72.8777",
        }
        res = await client.post("/api/v1/reports", data=data, files=files)
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_coordinator_authorization_protection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Without auth header -> 401
        res = await client.get("/api/v1/reports")
        assert res.status_code == 401

        # With Citizen role token -> 403 Forbidden
        async with AsyncSessionLocal() as db:
            c_res = await db.execute(select(User).where(User.email == "test_citizen@paventra.local"))
            citizen = c_res.scalar_one()
            citizen_token = create_access_token(citizen.id)

        res_citizen = await client.get(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {citizen_token}"}
        )
        assert res_citizen.status_code == 403


@pytest.mark.asyncio
async def test_coordinator_workflow_state_transitions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            coord_res = await db.execute(select(User).where(User.email == "test_coord@paventra.local"))
            coord = coord_res.scalar_one()
            coord_token = create_access_token(coord.id)

            # Create a test report
            rpt = Report(
                public_ref="PAV-TESTFLOW",
                source=ReportSource.CITIZEN,
                status=ReportStatus.SUBMITTED,
                damage_type=DamageType.POTHOLE,
            )
            db.add(rpt)
            await db.commit()
            await db.refresh(rpt)
            report_id = rpt.id

        headers = {"Authorization": f"Bearer {coord_token}"}

        # Valid transition: SUBMITTED -> UNDER_REVIEW
        r1 = await client.patch(
            f"/api/v1/reports/{report_id}/status",
            json={"status": "under_review", "notes": "Checking CCTV evidence"},
            headers=headers,
        )
        assert r1.status_code == 200
        assert r1.json()["status"] == "under_review"

        # Invalid transition: UNDER_REVIEW -> RESOLVED (cannot jump straight to resolved!)
        r_bad = await client.patch(
            f"/api/v1/reports/{report_id}/status",
            json={"status": "resolved"},
            headers=headers,
        )
        assert r_bad.status_code == 400

        # Valid transition: UNDER_REVIEW -> VERIFIED
        r2 = await client.patch(
            f"/api/v1/reports/{report_id}/status",
            json={"status": "verified"},
            headers=headers,
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "verified"
