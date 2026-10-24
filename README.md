# Paventra — AI-Powered Civic Road Damage Intelligence & Repair Management Platform

Paventra is an enterprise-grade civic road intelligence and repair operations platform. It bridges citizens, municipal coordinators, and field repair crews through computer vision damage detection, explainable fuzzy logic prioritization, synchronized GPS video survey ingestion, and an end-to-end status lifecycle.

---

## 🌟 Key Capabilities

### 1. Citizen Reporting & Tracking (Method A)
- **Mobile-First Capture:** Photo upload or camera capture with client-side image validation and preview.
- **Geospatial Precision:** Browser GPS geolocation retrieval with interactive Leaflet OpenStreetMap pin drop and address search fallback.
- **Truthful AI Preliminary Screening:** Automated road distress classification (potholes, cracks) with bounding box visualization. If the AI model is offline, Paventra truthfully displays an honest offline notice without fabricating predictions.
- **Instant Tracking Reference:** Unique unguessable reference codes (e.g., `PAV-XXXXXXXX`) generated upon submission.
- **Public Tracking Timeline:** Citizens can track live progress (`/track/:ref`) through each milestone without needing coordinator credentials.
- **Supplemental Evidence Submission:** Citizens can upload additional follow-up photographs directly to their active complaint.
- **Citizen Self-Service Portal:** Citizens can register (`/register`), log in, and view all their submitted reports in a unified dashboard (`/my-reports`).

### 2. Repair Team Operations Portal (`/team/jobs`)
- **Field Crew Work Orders:** Authenticated view for repair teams showing assigned work orders, target completion dates, locations with one-click external map navigation, and original citizen damage photos.
- **On-Site Work Commencement:** Field crews mark work as active (`ASSIGNED` $\rightarrow$ `IN_PROGRESS`) upon arrival.
- **Completion Evidence Submission:** Teams upload completion evidence photos and post-repair notes, moving the case to `PENDING_VERIFICATION` for coordinator sign-off.

### 3. Municipal Coordinator Command Center (`/coordinator`)
- **Executive Operations Dashboard:** Real-time counts of active complaints, 7-day intake trends, overdue cases, unverified high-severity items, and status distribution charts.
- **Multi-Faceted Report Triage:** Full-text search and filtering by status, severity, source (`citizen` vs. `inspection`), and road damage classification with server-side pagination.
- **Strict State Machine Workflow:** Server-enforced role transitions:
  $$\text{SUBMITTED} \rightarrow \text{UNDER\_REVIEW} \rightarrow \text{VERIFIED} \rightarrow \text{ASSIGNED} \rightarrow \text{IN\_PROGRESS} \rightarrow \text{PENDING\_VERIFICATION} \rightarrow \text{RESOLVED}$$
  *(plus documented rejection and rework loops)*.
- **Verified Severity Confirmation:** Coordinators can confirm or adjust the AI's preliminary severity during verification, which automatically triggers a real-time recalculation of the fuzzy priority score.
- **Team Assignment & Reassignment:** Assign or reassign repair crews (Team Alpha, Beta, Gamma) with target completion deadlines and dispatch notes.
- **Geographic Duplicate Review & Linking:** Conservative duplicate detection factoring Haversine distance, temporal delta, damage category, and image similarity with coordinator one-click linking.
- **Interactive Geospatial Map (`/coordinator/map`):** Full-screen Leaflet OpenStreetMap displaying status-colored markers, priority tooltips, and deep-links to report details.
- **Comprehensive Audit Trail:** Immutable chronologically ordered history logging every status modification, actor, timestamp, and justification.
- **Real-Time Notification Center & SSE Stream:** In-app notification center backed by Server-Sent Events (`/api/v1/notifications/stream`) with individual and bulk mark-read actions.

### 4. Method B Automated Road Survey Video Ingestion (`/coordinator/inspections`)
- **Survey Video Upload:** Ingest high-definition road survey video recordings (`.mp4`).
- **Synchronized GPS Track Ingestion:** Ingest time-stamped JSON GPS tracklogs with automatic spatial-temporal interpolation for extracted frames.
- **Configurable Frame Sampling:** Extracts inspection frames at user-specified intervals (1–10 FPS).
- **Temporal Deduplication:** 3-second temporal suppression prevents redundant records for the same defect across adjacent frames.
- **Automated High-Confidence Report Creation:** Detections meeting high-confidence thresholds automatically generate official road damage reports attributed to `INSPECTION` source.
- **Frame Inspection Gallery:** Interactive modal to review all extracted frames and bounding box detections.

### 5. Explainable Fuzzy Priority Engine (`scikit-fuzzy`)
- Deterministic Mamdani fuzzy inference system evaluating:
  1. **Severity** ($0 - 10$): Damage magnitude and hazard level.
  2. **Traffic Exposure** ($0 - 10$): Road volume and classification.
  3. **Time Unresolved** ($0 - 365$ days): Days pending repair.
  4. **Safety Urgency** ($0 - 10$): Immediate risk to motorists and cyclists.
- Outputs defuzzified priority score ($0 - 100$) and categorizes into `CRITICAL`, `HIGH`, `MEDIUM_HIGH`, `MEDIUM`, or `LOW`.
- Provides transparent **contributing factors** explaining the score drivers.
- Benchmarked against a deterministic baseline linear weighted score with logged delta.

### 6. Big Data Batch Analytics (PySpark & Pandas)
- Reproducible batch job running over 150 synthetic records (`analytics/jobs/road_damage_batch_analytics.py`).
- Computes $0.01^\circ$ spatial grid cluster hotspots, 90-day seasonal trends, turnaround times, and method distribution.
- Includes automatic numerical parity validation between PySpark and reference engines (`Parity Verified: True`).

---

## 🏗️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS v4, React Router 7, TanStack Query, Leaflet, Recharts, Lucide React |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, aiosqlite, SQLite / PostgreSQL PostGIS |
| **Security & Auth** | Direct Bcrypt password hashing, JWT (python-jose), Role-Based Access Control (RBAC) |
| **Computer Vision** | OpenCV (`cv2`), PyTorch, Ultralytics YOLOv8 |
| **Soft Computing** | `scikit-fuzzy`, NumPy |
| **Big Data Analytics** | Apache PySpark, Pandas |
| **Testing** | Pytest, pytest-asyncio, HTTPX |

---

## 🚀 Setup & Running Instructions (Windows PowerShell)

### Prerequisites
- Python 3.12+ installed and available on PATH.
- Node.js 18+ and npm installed.

### 1. Backend Server Setup

```powershell
# Navigate to the backend directory
cd d:\Paventra\backend

# Seed database with coordinator, repair teams, and repair crew account
python -m app.seed

# Start the FastAPI server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Documentation (Swagger UI): `http://127.0.0.1:8000/docs`
- Health check endpoint: `http://127.0.0.1:8000/api/health`

### 2. Frontend Application Setup

```powershell
# Open a second PowerShell terminal and navigate to the frontend directory
cd d:\Paventra\frontend

# Start the Vite development server
npm run dev
```
- Open browser at: `http://localhost:5173`

---

## 👥 Seeded User Accounts & Roles

| Role | Email | Password | Access / Portal |
|---|---|---|---|
| **Municipal Coordinator** | `coordinator@paventra.local` | `Paventra2024!` | `/coordinator` — Full management & triage |
| **Repair Team Alpha** | `team.alpha@paventra.local` | `TeamAlpha2024!` | `/team/jobs` — Field work orders & completion |
| **Citizen** | Self-register at `/register` | User-defined | `/my-reports` & `/report` |

*(Anonymous public reporting and tracking via reference code are also fully supported without registration).*

---

## 🧪 Automated Testing

Paventra features a comprehensive 41-test automated suite verifying computer vision inference, 2D geometric severity estimation, video inspection interpolation, duplicate intelligence across all 4 operational scenarios, fuzzy logic rule engines, and API state machine transitions:

```powershell
cd d:\Paventra\backend
python -m pytest -v
```

### Test Suite Summary (41/41 Passing)
- **API & Workflow Contracts (`tests/test_api.py` — 10 tests):** Server health, citizen upload & unguessable reference codes, geospatial range validation, RBAC enforcement, finite state machine transitions, duplicate bilateral linking, video inspection job queue, citizen reports isolation, repair team work order completion, verified severity confirmation & priority recalculation.
- **Duplicate Report & Observation Intelligence (`tests/test_duplicate.py` — 8 tests):** Haversine distance weighting, temporal decay, same-type scoring, repeated consecutive video frame grouping, recurring multi-pass inspection defect matching, crowdsourced citizen duplicate clustering, nearby distinct defect separation, and perceptual dHash image similarity.
- **Soft Computing: Fuzzy Priority Engine (`tests/test_fuzzy.py` — 7 tests):** Input bounds clipping, critical hazard rules, low priority rules, deterministic weighted baseline scoring, top contributing factors explainability, safe missing-input midpoint defaults, and time unresolved monotonic priority growth.
- **Geospatial Geometry (`tests/test_geospatial.py` — 3 tests):** Latitude/longitude validation, Haversine known distance verification, radius search boundaries.
- **Method B Video Inspection Engine (`tests/test_video.py` — 5 tests):** Synchronized GPS tracklog JSON parsing, corrupt file recovery, spatial-temporal coordinate interpolation within 2.0s windows, out-of-window GPS rejection (no coordinate fabrication), empty track handling.
- **Computer Vision & Severity Estimation (`tests/test_vision.py` — 8 tests):** RDD2022 4-class taxonomy mapping (`D00`, `D10`, `D20`, `D40`), YOLOv8 model loading, missing image path error handling, corrupt image rejection, minimum dimension bounds validation, visible area footprint severity scaling, elongation aspect ratio analysis, review-required triggers, and provisional optical disclaimers.
- `test_compute_similarity_score`, `test_far_apart_low_similarity`, `test_find_duplicate_candidates`: Duplicate scoring algorithms.
- `test_fuzzy_input_clipping`, `test_critical_priority_rule`, `test_low_priority_scenario`, `test_baseline_score_calculation`, `test_contributing_factors_explanation`: Fuzzy priority engine mechanics.
- `test_validate_coordinates`, `test_haversine_known_distance`, `test_coordinates_within_radius`: Geospatial math formulas.

---

## 📊 Running Big Data Batch Analytics

Execute the batch aggregation pipeline:

```powershell
python d:\Paventra\analytics\jobs\road_damage_batch_analytics.py
```
- Aggregates 150 records across spatial grid clusters and repair turnaround metrics.
- Validates numerical parity between PySpark and reference engines (`Parity Verified: True`).

---

## 📁 Repository Structure

```
d:\Paventra\
├── backend\
│   ├── app\
│   │   ├── api\v1\          # FastAPI endpoints (auth, reports, inspections, teams, etc.)
│   │   ├── core\            # Config, security (Bcrypt/JWT), database setup
│   │   ├── models\          # SQLAlchemy 2.0 async domain models
│   │   ├── schemas\         # Pydantic v2 validation contracts
│   │   ├── services\        # CV inference, fuzzy priority, video inspection, duplicates
│   │   ├── main.py          # Application entrypoint & static mount
│   │   └── seed.py          # Database seeder script
│   ├── tests\               # Pytest test suite (21 tests)
│   ├── uploads\             # Stored media evidence and inspection frames
│   └── paventra.db          # SQLite database
├── frontend\
│   ├── src\
│   │   ├── api\             # Axios HTTP client & API route wrappers
│   │   ├── components\      # Reusable UI (Map, Badge, Button, Card, FormElements)
│   │   ├── layouts\         # CoordinatorLayout with responsive navigation & SSE
│   │   ├── pages\           # ReportPage, TrackPage, DashboardPage, TeamJobsPage, etc.
│   │   └── types\           # Shared TypeScript domain contracts
├── analytics\
│   └── jobs\                # PySpark / Pandas batch analytics scripts
└── docs\                    # System architecture & demonstration walkthrough
```
