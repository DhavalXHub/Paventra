# Paventra — AI-Powered Road Damage Intelligence and Repair Management Platform

Paventra is a civic road intelligence platform that allows citizens to report road damage, provides automated road inspection capabilities with computer vision, and empowers municipal coordinators to prioritize, assign, and verify repairs.

---

## Key Features

- **Citizen Reporting (Method A):** Instant photo capture/upload, geolocation retrieval with Leaflet map-pin fallback, automated AI pre-screening, immediate report reference generation, and status tracking without coordinator privileges.
- **Automatic Road Inspection (Method B):** Video frame extraction, YOLOv8 road distress classification (potholes, longitudinal/transverse cracks, alligator cracking), temporal deduplication, and synchronized GPS association.
- **Explainable Fuzzy Priority Engine:** Deterministic fuzzy inference system using `scikit-fuzzy` evaluating severity, traffic exposure, pending duration, and safety urgency into a 0-100 priority score with explainable contributing factors.
- **Coordinator Command Center:** Secure JWT authentication, interactive Leaflet OpenStreetMap with status-coded markers, search & multi-facet filtering, strict state machine transitions, and team dispatch with target completion dates.
- **Big Data Analytics:** Batch analytics pipeline aggregating spatial grid clusters, repair turnaround metrics, and citizen vs. automated inspection distributions with validation parity.

---

## Technology Stack

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, React Router 7, TanStack Query, Leaflet, Recharts, Lucide React.
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic, SQLite / PostgreSQL PostGIS.
- **Computer Vision:** PyTorch, OpenCV, Ultralytics YOLOv8.
- **Soft Computing:** `scikit-fuzzy`, NumPy.
- **Big Data Analytics:** PySpark, Pandas batch analytics.
- **Testing:** Pytest, pytest-asyncio, HTTPX.

---

## Setup & Running Instructions (Windows)

### 1. Backend Setup

```powershell
# 1. Open a PowerShell terminal
cd d:\Paventra\backend

# 2. Seed database with coordinator credentials & repair teams
python -m app.seed

# 3. Start the FastAPI server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Documentation is available at: `http://localhost:8000/api/docs`
- Health check: `http://localhost:8000/api/health`

### 2. Frontend Setup

```powershell
# 1. Open a second PowerShell terminal
cd d:\Paventra\frontend

# 2. Start the Vite development server
npm run dev
```
- Open your browser at `http://localhost:5173`

---

## Default Seeded Credentials

| Role | Email | Password |
|---|---|---|
| Municipal Coordinator | `coordinator@paventra.local` | `Paventra2024!` |

---

## Running Automated Tests

```powershell
cd d:\Paventra\backend
python -m pytest -v
```
All 16 unit and integration test suites will execute across API contracts, geospatial calculations, duplicate detection, and fuzzy logic.

---

## Running Big Data Batch Analytics

```powershell
python d:\Paventra\analytics\jobs\road_damage_batch_analytics.py
```
Executes batch aggregation over 150 labeled synthetic road reports, computes spatial grid clusters, and confirms numerical parity against reference calculations.
