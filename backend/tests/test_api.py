"""Integration tests for FastAPI endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import io
import uuid

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

        # 3. Citizen submits additional evidence
        ev_img = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 50)
        ev_res = await client.post(
            f"/api/v1/reports/track/{pub_ref}/evidence",
            data={"notes": "Pothole depth has increased after rain"},
            files={"image": ("extra.jpg", ev_img, "image/jpeg")},
        )
        assert ev_res.status_code == 200
        assert ev_res.json()["status"] == "ok"


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
            unique_ref = f"PAV-{uuid.uuid4().hex[:8].upper()}"
            rpt = Report(
                public_ref=unique_ref,
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


@pytest.mark.asyncio
async def test_duplicate_candidates_and_linking():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            coord_res = await db.execute(select(User).where(User.email == "test_coord@paventra.local"))
            coord = coord_res.scalar_one()
            coord_token = create_access_token(coord.id)

            r1 = Report(
                public_ref=f"PAV-{uuid.uuid4().hex[:8].upper()}",
                source=ReportSource.CITIZEN,
                status=ReportStatus.SUBMITTED,
                damage_type=DamageType.POTHOLE,
                latitude=19.0760,
                longitude=72.8777,
            )
            r2 = Report(
                public_ref=f"PAV-{uuid.uuid4().hex[:8].upper()}",
                source=ReportSource.CITIZEN,
                status=ReportStatus.SUBMITTED,
                damage_type=DamageType.POTHOLE,
                latitude=19.0761,
                longitude=72.8778,
            )
            db.add_all([r1, r2])
            await db.commit()
            await db.refresh(r1)
            await db.refresh(r2)
            id1, id2 = r1.id, r2.id

        headers = {"Authorization": f"Bearer {coord_token}"}
        dup_res = await client.get(f"/api/v1/reports/{id1}/duplicates", headers=headers)
        assert dup_res.status_code == 200
        dups = dup_res.json()
        assert any(d["id"] == id2 for d in dups)

        # Link duplicate
        link_res = await client.post(
            f"/api/v1/reports/{id1}/duplicates/link",
            json={"duplicate_id": id2},
            headers=headers,
        )
        assert link_res.status_code == 200
        assert link_res.json()["status"] == "linked"


@pytest.mark.asyncio
async def test_method_b_inspection_creation_and_listing():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            coord_res = await db.execute(select(User).where(User.email == "test_coord@paventra.local"))
            coord = coord_res.scalar_one()
            coord_token = create_access_token(coord.id)

        headers = {"Authorization": f"Bearer {coord_token}"}
        fake_video = io.BytesIO(b"fake_video_bytes")
        files = {"media_file": ("road_survey.mp4", fake_video, "video/mp4")}
        data = {"sample_rate": "15", "notes": "Sector 4 survey run"}

        res = await client.post("/api/v1/inspections", data=data, files=files, headers=headers)
        assert res.status_code == 201
        job_data = res.json()
        assert "id" in job_data
        assert job_data["status"] == "queued"
        job_id = job_data["id"]

        list_res = await client.get("/api/v1/inspections", headers=headers)
        assert list_res.status_code == 200
        jobs = list_res.json()
        assert any(j["id"] == job_id for j in jobs)


@pytest.mark.asyncio
async def test_citizen_my_reports_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            cit_res = await db.execute(select(User).where(User.email == "test_citizen@paventra.local"))
            citizen = cit_res.scalar_one()
            cit_token = create_access_token(citizen.id)

            rpt = Report(
                public_ref=f"PAV-{uuid.uuid4().hex[:8].upper()}",
                source=ReportSource.CITIZEN,
                status=ReportStatus.SUBMITTED,
                damage_type=DamageType.POTHOLE,
                submitter_id=citizen.id,
                submitter_email=citizen.email,
            )
            db.add(rpt)
            await db.commit()
            await db.refresh(rpt)
            ref = rpt.public_ref

        headers = {"Authorization": f"Bearer {cit_token}"}
        res = await client.get("/api/v1/reports/my", headers=headers)
        assert res.status_code == 200
        my_reports = res.json()
        assert any(r["public_ref"] == ref for r in my_reports)


@pytest.mark.asyncio
async def test_repair_team_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from app.models.team import RepairTeam
        from app.models.report import RepairAssignment

        async with AsyncSessionLocal() as db:
            coord_res = await db.execute(select(User).where(User.email == "test_coord@paventra.local"))
            coord = coord_res.scalar_one()
            coord_token = create_access_token(coord.id)

            # Ensure team exists
            team_res = await db.execute(select(RepairTeam).where(RepairTeam.name == "Test Team"))
            team = team_res.scalar_one_or_none()
            if not team:
                team = RepairTeam(name="Test Team", description="Test Crew")
                db.add(team)
                await db.flush()

            # Create test repair team user
            t_user_res = await db.execute(select(User).where(User.email == "test_team_user@paventra.local"))
            team_user = t_user_res.scalar_one_or_none()
            if not team_user:
                team_user = User(
                    email="test_team_user@paventra.local",
                    full_name="Team User",
                    hashed_password=hash_password("TeamPass123!"),
                    role=UserRole.REPAIR_TEAM,
                    team_id=team.id,
                )
                db.add(team_user)
                await db.flush()
            team_token = create_access_token(team_user.id)

            # Create report and assign
            rpt = Report(
                public_ref=f"PAV-{uuid.uuid4().hex[:8].upper()}",
                source=ReportSource.CITIZEN,
                status=ReportStatus.VERIFIED,
                damage_type=DamageType.POTHOLE,
            )
            db.add(rpt)
            await db.flush()

            assignment = RepairAssignment(
                report_id=rpt.id,
                team_id=team.id,
                assigned_by_id=coord.id,
                notes="Patch pothole ASAP",
            )
            db.add(assignment)
            rpt.status = ReportStatus.ASSIGNED
            await db.commit()
            rep_id = rpt.id

        # 1. Team views assigned jobs
        team_headers = {"Authorization": f"Bearer {team_token}"}
        jobs_res = await client.get("/api/v1/teams/my-jobs", headers=team_headers)
        assert jobs_res.status_code == 200
        jobs = jobs_res.json()
        assert any(j["report_id"] == rep_id for j in jobs)

        # 2. Team starts work
        start_res = await client.patch(f"/api/v1/teams/jobs/{rep_id}/start", headers=team_headers)
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "in_progress"

        # 3. Team uploads completion evidence
        comp_img = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 50)
        comp_res = await client.post(
            f"/api/v1/reports/{rep_id}/completion",
            data={"notes": "Pothole filled and leveled"},
            files={"photo": ("completed.jpg", comp_img, "image/jpeg")},
            headers=team_headers,
        )
        assert comp_res.status_code == 200
        assert comp_res.json()["status"] == "pending_verification"


@pytest.mark.asyncio
async def test_verified_severity_and_analytics_serialization():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            coord_res = await db.execute(select(User).where(User.email == "test_coord@paventra.local"))
            coord = coord_res.scalar_one()
            coord_token = create_access_token(coord.id)

            rpt = Report(
                public_ref=f"PAV-{uuid.uuid4().hex[:8].upper()}",
                source=ReportSource.CITIZEN,
                status=ReportStatus.UNDER_REVIEW,
                damage_type=DamageType.POTHOLE,
                latitude=19.0760,
                longitude=72.8777,
            )
            db.add(rpt)
            await db.commit()
            await db.refresh(rpt)
            rep_id = rpt.id

        headers = {"Authorization": f"Bearer {coord_token}"}

        # Verify with explicit field severity
        v_res = await client.patch(
            f"/api/v1/reports/{rep_id}/status",
            json={"status": "verified", "severity": "high", "notes": "Confirmed large crater"},
            headers=headers,
        )
        assert v_res.status_code == 200

        # Check detail reflects verified severity and priority
        detail_res = await client.get(f"/api/v1/reports/{rep_id}", headers=headers)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["severity"] == "high"
        assert detail["severity_is_estimated"] is False
        assert detail["priority_score"] is not None

        # Verify analytics serialization does NOT contain class reprs like "ReportStatus."
        summary_res = await client.get("/api/v1/analytics/summary", headers=headers)
        assert summary_res.status_code == 200
        summary = summary_res.json()
        for k in summary["by_status"].keys():
            assert not k.startswith("ReportStatus.")
        for k in summary["by_source"].keys():
            assert not k.startswith("ReportSource.")

        # Verify map markers serialization does NOT contain class reprs
        map_res = await client.get("/api/v1/reports/map/markers", headers=headers)
        assert map_res.status_code == 200
        markers = map_res.json()
        for m in markers:
            assert not m["status"].startswith("ReportStatus.")
