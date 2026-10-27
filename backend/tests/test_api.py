"""Integration tests for FastAPI endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import io
import uuid

from PIL import Image

from app.main import app
from app.core.security import hash_password, create_access_token
from app.db.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.report import Report, ReportStatus, ReportSource, DamageType
from sqlalchemy import select


def _jpeg_bytes(size: int = 64) -> io.BytesIO:
    buf = io.BytesIO()
    Image.new("RGB", (size, size), (90, 90, 90)).save(buf, format="JPEG")
    buf.seek(0)
    return buf


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
        files = {"image": ("test_pothole.jpg", _jpeg_bytes(), "image/jpeg")}
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
        ev_img = _jpeg_bytes(48)
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
        files = {"image": ("bad.jpg", _jpeg_bytes(), "image/jpeg")}
        data = {
            "latitude": "999.0",  # Out of range
            "longitude": "72.8777",
        }
        res = await client.post("/api/v1/reports", data=data, files=files)
        assert res.status_code == 400


@pytest.mark.asyncio
async def test_invalid_image_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"image": ("notes.txt", b"this is not an image", "text/plain")}
        res = await client.post("/api/v1/reports", data={"latitude": "19.07", "longitude": "72.87"}, files=files)
        assert res.status_code == 400

        files = {"image": ("corrupt.jpg", b"not-a-real-jpeg", "image/jpeg")}
        res = await client.post("/api/v1/reports", data={"latitude": "19.07", "longitude": "72.87"}, files=files)
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
        comp_img = _jpeg_bytes(48)
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


@pytest.mark.asyncio
async def test_report_submission_rate_limiting(monkeypatch):
    """Verify that submitting reports beyond RATE_LIMIT_REPORTS_PER_HOUR returns 429 and changing email does not bypass IP rate limit."""
    from app.core.config import settings
    from app.core.rate_limiter import _memory_limiter
    _memory_limiter.clear()

    monkeypatch.setattr(settings, "RATE_LIMIT_REPORTS_PER_HOUR", 2)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Submit 1 (spammer1@example.com)
        f1 = {"image": ("p1.jpg", _jpeg_bytes().getvalue(), "image/jpeg")}
        d1 = {"latitude": "19.0760", "longitude": "72.8777", "submitter_email": "spammer1@example.com"}
        r1 = await client.post("/api/v1/reports", data=d1, files=f1)
        assert r1.status_code == 201

        # Submit 2 (spammer2@example.com - attempts bypass by changing email from same client IP)
        f2 = {"image": ("p2.jpg", _jpeg_bytes().getvalue(), "image/jpeg")}
        d2 = {"latitude": "19.0760", "longitude": "72.8777", "submitter_email": "spammer2@example.com"}
        r2 = await client.post("/api/v1/reports", data=d2, files=f2)
        assert r2.status_code == 201

        # Submit 3 (spammer3@example.com) -> Exceeds IP rate limit of 2/hour
        f3 = {"image": ("p3.jpg", _jpeg_bytes().getvalue(), "image/jpeg")}
        d3 = {"latitude": "19.0760", "longitude": "72.8777", "submitter_email": "spammer3@example.com"}
        r3 = await client.post("/api/v1/reports", data=d3, files=f3)
        assert r3.status_code == 429
        assert "Rate limit exceeded" in r3.json()["detail"]

    _memory_limiter.clear()


@pytest.mark.asyncio
async def test_auth_config_and_google_disabled_safeguard(monkeypatch):
    """Verify auth config discovery and unconfigured Google sign-in rejection."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_ENABLED", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Config discovery when disabled
        cfg_res = await client.get("/api/v1/auth/config")
        assert cfg_res.status_code == 200
        cfg = cfg_res.json()
        assert cfg["google_enabled"] is False

        # Google login when disabled returns 501
        g_res = await client.post("/api/v1/auth/google", json={"credential": "fake-google-id-token"})
        assert g_res.status_code == 501
        assert "not configured" in g_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_google_auth_validation_scenarios(monkeypatch):
    """Test full matrix of Google ID token validation: audience, issuer, expiry, verified email, new user, existing user, linking."""
    import time
    from app.core.config import settings
    import httpx

    test_client_id = "test-client-id-12345.apps.googleusercontent.com"
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", test_client_id)

    class MockResponse:
        def __init__(self, status_code: int, data: dict):
            self.status_code = status_code
            self._data = data

        def json(self):
            return self._data

    current_mock_resp = MockResponse(200, {})

    async def mock_get(self, url, params=None):
        return current_mock_resp

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Invalid token (Google tokeninfo returns 400)
        current_mock_resp = MockResponse(400, {"error": "invalid_token"})
        r = await client.post("/api/v1/auth/google", json={"credential": "bad-token"})
        assert r.status_code == 401
        assert "invalid or expired" in r.json()["detail"].lower()

        # 2. Audience mismatch
        current_mock_resp = MockResponse(200, {
            "iss": "accounts.google.com",
            "aud": "wrong-client-id",
            "email": "user@example.com",
            "email_verified": True,
            "sub": "sub-1",
        })
        r = await client.post("/api/v1/auth/google", json={"credential": "valid-token"})
        assert r.status_code == 401
        assert "audience" in r.json()["detail"].lower()

        # 3. Untrusted issuer
        current_mock_resp = MockResponse(200, {
            "iss": "https://malicious-issuer.com",
            "aud": test_client_id,
            "email": "user@example.com",
            "email_verified": True,
            "sub": "sub-1",
        })
        r = await client.post("/api/v1/auth/google", json={"credential": "valid-token"})
        assert r.status_code == 401
        assert "untrusted" in r.json()["detail"].lower()

        # 4. Unverified email
        current_mock_resp = MockResponse(200, {
            "iss": "https://accounts.google.com",
            "aud": test_client_id,
            "email": "user@example.com",
            "email_verified": False,
            "sub": "sub-1",
        })
        r = await client.post("/api/v1/auth/google", json={"credential": "valid-token"})
        assert r.status_code == 400
        assert "not verified" in r.json()["detail"].lower()

        # 5. Expired token
        current_mock_resp = MockResponse(200, {
            "iss": "https://accounts.google.com",
            "aud": test_client_id,
            "email": "user@example.com",
            "email_verified": True,
            "exp": str(int(time.time()) - 3600),
            "sub": "sub-1",
        })
        r = await client.post("/api/v1/auth/google", json={"credential": "valid-token"})
        assert r.status_code == 401
        assert "expired" in r.json()["detail"].lower()

        # 6. Controlled successful login: New Citizen User
        unique_sub = f"g_sub_{uuid.uuid4().hex[:8]}"
        unique_email = f"new_google_user_{uuid.uuid4().hex[:6]}@example.com"
        current_mock_resp = MockResponse(200, {
            "iss": "accounts.google.com",
            "aud": test_client_id,
            "email": unique_email,
            "email_verified": True,
            "name": "Google Tester",
            "exp": str(int(time.time()) + 3600),
            "sub": unique_sub,
        })
        r = await client.post("/api/v1/auth/google", json={"credential": "good-token"})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["role"] == "citizen"

        # 7. Controlled successful login: Existing Google User (same sub)
        r2 = await client.post("/api/v1/auth/google", json={"credential": "good-token"})
        assert r2.status_code == 200
        assert "access_token" in r2.json()

        # 8. Safe Account Linking: Email matches existing password user
        # User exists: test_citizen@paventra.local (password: CitizenPass123!)
        linking_sub = f"g_sub_{uuid.uuid4().hex[:8]}"
        current_mock_resp = MockResponse(200, {
            "iss": "accounts.google.com",
            "aud": test_client_id,
            "email": "test_citizen@paventra.local",
            "email_verified": True,
            "name": "Citizen Match",
            "exp": str(int(time.time()) + 3600),
            "sub": linking_sub,
        })
        # Attempt without linking confirmation -> 409 Conflict
        r_link1 = await client.post("/api/v1/auth/google", json={"credential": "good-token"})
        assert r_link1.status_code == 409
        assert "already exists" in r_link1.json()["detail"].lower()

        # Attempt with wrong password -> 401 Unauthorized
        r_link2 = await client.post("/api/v1/auth/google", json={
            "credential": "good-token",
            "link_existing": True,
            "password_for_linking": "WrongPassword!",
        })
        assert r_link2.status_code == 401
        assert "incorrect password" in r_link2.json()["detail"].lower()

        # Attempt with correct password -> 200 OK and linked!
        r_link3 = await client.post("/api/v1/auth/google", json={
            "credential": "good-token",
            "link_existing": True,
            "password_for_linking": "CitizenPass123!",
        })
        assert r_link3.status_code == 200
        assert "access_token" in r_link3.json()


@pytest.mark.asyncio
async def test_citizen_registration_prevents_privilege_escalation():
    """Verify self-registration cannot escalate to coordinator or admin."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"citizen_esc_{uuid.uuid4().hex[:6]}@example.com"
        reg_res = await client.post("/api/v1/auth/register", json={
            "email": unique_email,
            "full_name": "Hacker Attempt",
            "password": "SecurePassword123!",
            "role": "coordinator",  # attempted privilege escalation
        })
        assert reg_res.status_code == 201
        data = reg_res.json()
        assert data["role"] == "citizen"  # server enforced citizen role!


@pytest.mark.asyncio
async def test_guest_submission_claim_token_and_claiming():
    """Verify guest submissions generate claim tokens and can be securely claimed by a citizen."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Citizen login
        login_res = await client.post("/api/v1/auth/login", json={
            "email": "test_citizen@paventra.local",
            "password": "CitizenPass123!",
        })
        assert login_res.status_code == 200
        citizen_token = login_res.json()["access_token"]
        citizen_headers = {"Authorization": f"Bearer {citizen_token}"}

        # 2. Guest submits report
        f = {"image": ("pothole_guest.jpg", _jpeg_bytes().getvalue(), "image/jpeg")}
        d = {
            "latitude": "12.9716",
            "longitude": "77.5946",
            "damage_type": "pothole",
            "description": "Guest reported crater",
            "address_hint": "MG Road",
        }
        guest_res = await client.post("/api/v1/reports", data=d, files=f)
        assert guest_res.status_code == 201
        guest_data = guest_res.json()
        public_ref = guest_data["public_ref"]
        claim_token = guest_data.get("claim_token")
        assert claim_token is not None  # Guest got claim token!

        # 3. Public tracking returns status and is_claimed=False
        track_res = await client.get(f"/api/v1/reports/track/{public_ref}")
        assert track_res.status_code == 200
        track_data = track_res.json()
        assert track_data["is_claimed"] is False
        assert track_data["public_ref"] == public_ref
        assert "submitter_email" not in track_data  # Privacy check!

        # 4. Check that /reports/mine does NOT yet have this report
        mine_res = await client.get("/api/v1/reports/mine", headers=citizen_headers)
        assert mine_res.status_code == 200
        refs = [r["public_ref"] for r in mine_res.json()]
        assert public_ref not in refs

        # 5. Invalid claim attempt fails
        bad_claim = await client.post(
            "/api/v1/reports/claim",
            headers=citizen_headers,
            json={"public_ref": public_ref, "claim_token": "wrong-token"},
        )
        assert bad_claim.status_code == 400

        # 6. Valid claim attempt succeeds
        good_claim = await client.post(
            "/api/v1/reports/claim",
            headers=citizen_headers,
            json={"public_ref": public_ref, "claim_token": claim_token},
        )
        assert good_claim.status_code == 200
        assert good_claim.json()["status"] == "ok"

        # 7. Check that /reports/mine now includes this report
        mine_res2 = await client.get("/api/v1/reports/mine", headers=citizen_headers)
        assert mine_res2.status_code == 200
        refs2 = [r["public_ref"] for r in mine_res2.json()]
        assert public_ref in refs2

        # 8. Tracking now shows is_claimed=True
        track_res2 = await client.get(f"/api/v1/reports/track/{public_ref}")
        assert track_res2.status_code == 200
        assert track_res2.json()["is_claimed"] is True
