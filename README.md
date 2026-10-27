# Paventra — AI-Powered Civic Road Damage Intelligence & Repair Management Platform

> **An Integrated University & Enterprise Engineering Project Combining:**
> 1. **Computer Vision & Deep Learning:** YOLOv8 object detection trained on the official Road Damage Dataset 2022 (RDD2022).
> 2. **Soft Computing:** Mamdani Fuzzy Inference System (FIS) for explainable, non-linear severity and repair prioritization under uncertainty.
> 3. **Big Data Analytics:** Scalable spatial-temporal clustering and batch analytics with PySpark / reference Pandas numerical parity validation.
> 4. **Full-Stack Web GIS & Governance:** React 19, TypeScript, Vite, Tailwind CSS, Leaflet OpenStreetMap, FastAPI, and an immutable 7-stage state machine with photographic post-repair verification.

---

## 🌟 The Four Integrated Pillars

### 1. Computer Vision & RDD2022 Dataset Strategy
- **Official RDD2022 Benchmark:** Utilizes the official Crowdsensing-based Road Damage Dataset 2022 (Arya et al., IEEE Big Data 2022) with official Pascal VOC XML annotations.
- **Supported Damage Taxonomy:**
  - `D00`: Longitudinal cracks (linear cracks parallel to road centerline)
  - `D10`: Transverse cracks (linear cracks perpendicular to road centerline)
  - `D20`: Alligator cracks (interconnected fatigue / crocodile cracking network)
  - `D40`: Potholes (structural bowl-shaped depressions and cavities)
- **Automated Dataset Preparation Pipeline (`ml/dataset/prepare_rdd2022.py`):**
  - Download guidance & disk space safeguards.
  - Pascal VOC XML coordinate boundary validation (`0 <= xmin < xmax <= width`, `0 <= ymin < ymax <= height`).
  - Detection of corrupt files, zero-area boxes, and missing annotations.
  - Conversion to normalized Ultralytics YOLOv8 format (`classes.txt`, `images/`, `labels/`, `data.yaml`).
  - Sequence-aware, leakage-free train/val/test splitting (70/15/15) grouping contiguous dashcam sequences.
  - Automated generation of quality reports (`preprocessing_report.json`) and manifests (`dataset_manifest.json`).
  - Built-in synthetic sample generator (`--create-sample`) for automated testing and CI evaluation without requiring a 10 GB download.
- **Model Evaluation (`ml/evaluation/evaluate.py`):** Actually measures Precision, Recall, mAP@50, and mAP@50:95 on held-out test splits.

---

### 2. Soft Computing: Mamdani Fuzzy Inference System (FIS)
The central academic contribution is the **Soft Computing prioritization module**, which independently interprets uncertain damage dimensions and contextual road conditions:
- **Mamdani Min-Max Composition:** Uses triangular membership functions across continuous universes of discourse:
  1. **Damage Severity** ($0 - 10$): Low, Moderate, High, Critical (derived from 2D bounding box footprint & hazard index).
  2. **Traffic Exposure** ($0 - 10$): Low, Medium, High (derived from municipal GIS road hierarchies).
  3. **Time Unresolved** ($0 - 365$ days): Short, Medium, Long, Very Long (elapsed duration since inception).
  4. **Safety Urgency** ($0 - 10$): Low, Medium, High (immediate hazard to cyclists, two-wheelers, and pedestrians).
- **22 Complete Mamdani Rules:** Guaranteed 100% boundary space coverage (\(\sum \mu_i > 0\) for all possible inputs).
- **Centroid Defuzzification (Center of Gravity / COG):** Calculates continuous, explainable priority scores ($0 - 100$).
- **Academic Superiority Over Linear Sums:** Protects vulnerable road users by unconditionally escalating high-safety hazards to `CRITICAL` (85–100), whereas linear models dangerously dilute priorities in low-traffic zones.
- **Interactive Fuzzy Simulator in Coordinator Analytics (`/coordinator/analytics`):**
  - Real-time sliders for all 4 antecedents.
  - Academic test presets (School Zone Pothole, Neglected Rural Crack, Highway Fatigue, Suburban Minor Wear).
  - Side-by-side comparison against linear weighted baselines with decision delta ($\Delta = \text{Fuzzy} - \text{Linear}$).
  - Full display of linguistic membership degrees ($\mu \in [0.0, 1.0]$) and rule base specifications.
- **Tabular Maintenance Benchmark Dataset (`analytics/fixtures/soft_computing_maintenance_benchmark.csv`):** 250 empirical records with documented field provenance (`docs/data_dictionary.md`).

---

### 3. Big Data Analytics & Spatial-Temporal Hotspot Clustering
- **Offline Batch Analytics Pipeline (`analytics/jobs/road_damage_batch_analytics.py`):**
  - Analyzes road reports and maintenance decisions at scale.
  - Computes high-density spatial damage clusters ($0.01^\circ \approx 1.1\text{ km}$ grid centroids).
  - Calculates average repair turnaround durations, 90-day seasonal trends, and overdue cases (> 30 days).
  - Numerical parity validation between Apache PySpark and reference Pandas engines (`Parity Verified: True`).
- **Coordinator Analytics View:** Visualizes hotspot clusters, status breakdowns, and monthly intake trends.

---

### 4. Full-Stack Web GIS & Human-in-the-Loop Governance
- **Citizen Public Reporting (`/report`):**
  - Ride-hailing precision map picker (fixed center pin, smooth pan-to-adjust, Nominatim autocomplete).
  - Dual-mode access: Anonymous guest reporting with unguessable references (`PAV-XXXXXXXX`) & claim tokens, or authenticated citizen reporting (`/my-reports`).
  - AI preliminary screening with bounding boxes and honest offline notices.
- **Public Report Tracking (`/track/:ref`):** Citizens can follow live milestone progress and submit supplemental evidence without coordinator credentials.
- **Municipal Coordinator Command Center (`/coordinator`):**
  - Triage table with multi-attribute filtering, search, and pagination.
  - Interactive Leaflet GIS Map (`/coordinator/map`) with cluster pins.
  - Conservative duplicate report linking factoring Haversine distance, temporal decay, and image perceptual dHash similarity.
  - Method B Automated Survey Video Ingestion (`/coordinator/inspections`) with synchronized GPS telemetry interpolation.
  - Immutable audit trail logging every status change, actor, and justification.
- **Repair Team Operations Portal (`/team/jobs`):**
  - Field crew work orders with external map navigation links.
  - Work commencement (`ASSIGNED` $\rightarrow$ `IN_PROGRESS`).
  - Mandatory completion photographic evidence submission (`PENDING_VERIFICATION`).
- **Resolution Verification Safeguard:** The system **never** self-certifies a road as repaired. A coordinator must inspect the after-repair photo before advancing to `RESOLVED`.

---

## 🏗️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS v4, React Router 7, TanStack Query, Leaflet, Recharts, Lucide React |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, aiosqlite, SQLite / PostgreSQL PostGIS |
| **Security & Auth** | Google Identity Services (GIS), Bcrypt password hashing, JWT (python-jose), Role-Based Access Control (RBAC) |
| **Computer Vision** | OpenCV (`cv2`), PyTorch, Ultralytics YOLOv8n (RDD2022 weights) |
| **Soft Computing** | `scikit-fuzzy`, NumPy (22-rule Mamdani FIS, Centroid Defuzzification) |
| **Big Data Analytics** | Apache PySpark, Pandas |
| **Testing** | Pytest, pytest-asyncio, HTTPX, FastAPI TestClient |

---

## 🚀 Setup & Running Instructions (Windows PowerShell)

### Prerequisites
- Python 3.12+ installed and available on PATH.
- Node.js 18+ and npm installed.

### 1. Backend Server Setup
```powershell
# Navigate to backend directory
cd d:\Paventra\backend

# Seed database with coordinator, repair teams, and sample data
python -m app.seed

# Start the FastAPI server (pinned to port 8000)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Swagger Documentation: `http://127.0.0.1:8000/docs`
- Health check endpoint: `http://127.0.0.1:8000/api/health`
- Readiness check endpoint: `http://127.0.0.1:8000/api/ready`

### 2. Frontend Application Setup
```powershell
# In a second PowerShell window, navigate to frontend
cd d:\Paventra\frontend

# Start the Vite development server (pinned strictly to port 5173)
npm run dev -- --host 127.0.0.1 --port 5173
```
- Open browser at: `http://localhost:5173`

---

## 👥 Seeded User Accounts & Portals

| Role | Email | Password | Access / Portal |
|---|---|---|---|
| **Municipal Coordinator** | `coordinator@paventra.local` | `Paventra2024!` | `/coordinator` — Full management & triage |
| **Repair Team Alpha** | `team.alpha@paventra.local` | `TeamAlpha2024!` | `/team/jobs` — Work orders & evidence submission |
| **Citizen** | Self-register at `/register` | User-defined | `/my-reports` & `/report` |

*(Anonymous public reporting and tracking via reference code are also fully supported without registration).*

---

## 🧪 Comprehensive Automated Testing (49 Tests Passing)

Paventra features an extensive automated test suite covering all four pillars:

```powershell
cd d:\Paventra\backend
python -m pytest -v
```

### Test Suite Breakdown
- **API, Auth & State Machine (`tests/test_api.py` — 16 tests):** Server health, citizen upload, reference codes, geospatial range validation, RBAC enforcement, finite state machine transitions, duplicate bilateral linking, video inspection queue, repair team evidence submission, verified severity confirmation & priority recalculation, sliding-window rate limiting, and guest claim token claiming.
- **Duplicate Observation Intelligence (`tests/test_duplicate.py` — 8 tests):** Haversine distance weighting, temporal decay, same-type scoring, repeated video frame grouping, recurring multi-pass inspection matching, crowdsourced duplicate clustering, and perceptual dHash image similarity.
- **Soft Computing: Mamdani Fuzzy Engine (`tests/test_fuzzy.py` — 9 tests):** Input bounds clipping, critical hazard rules, low priority rules, deterministic weighted baseline scoring, top contributing factors explainability, safe missing-input midpoint defaults, time unresolved monotonic priority growth, 100% boundary space coverage, and academic narrative generation.
- **Geospatial Mathematics (`tests/test_geospatial.py` — 3 tests):** Latitude/longitude validation, Haversine known distance verification, radius search boundaries.
- **Method B Video Inspection Engine (`tests/test_video.py` — 5 tests):** Synchronized GPS tracklog JSON parsing, spatial-temporal coordinate interpolation within 2.0s windows, out-of-window GPS rejection (no coordinate fabrication), empty track handling.
- **Computer Vision & Severity Estimation (`tests/test_vision.py` — 8 tests):** RDD2022 4-class taxonomy mapping (`D00`, `D10`, `D20`, `D40`), YOLOv8 model loading, missing image path error handling, corrupt image rejection, visible area footprint severity scaling, elongation aspect ratio analysis, review-required triggers, and provisional optical disclaimers.

---

## 📁 Repository Structure

```
d:\Paventra\
├── analytics\
│   ├── fixtures\            # Soft computing tabular benchmark (CSV/JSON) & demo data
│   ├── jobs\                # PySpark / Pandas batch analytics pipeline
│   └── reports\             # Generated batch summary reports
├── backend\
│   ├── app\
│   │   ├── api\v1\          # FastAPI endpoints (auth, reports, inspections, teams, analytics)
│   │   ├── core\            # Config, security (Bcrypt/JWT), database setup
│   │   ├── models\          # SQLAlchemy 2.0 async domain models
│   │   ├── schemas\         # Pydantic v2 validation contracts
│   │   ├── services\        # CV inference, Mamdani fuzzy priority, video inspection, duplicates
│   │   └── main.py          # Application entrypoint & static mount
│   ├── tests\               # Pytest automated test suite (49 tests)
│   └── paventra.db          # SQLite database (repaired & integrity checked)
├── data\
│   └── road_damage\         # Documented RDD2022 dataset directory
│       ├── raw\             # Original downloaded archives & VOC XMLs
│       ├── processed\       # Converted Ultralytics YOLOv8 dataset & data.yaml
│       ├── splits\          # Leakage-free sequence-grouped split manifests
│       ├── reports\         # Preprocessing quality & class distribution reports
│       └── models\          # Local training checkpoints
├── docs\
│   ├── data_dictionary.md   # Field provenance, data types, and uncertainty handling
│   ├── dataset_guide.md     # Official RDD2022 setup, citation, and evaluation protocol
│   ├── soft_computing_specification.md # Mamdani FIS academic formulation & 22-rule base
│   ├── architecture.md      # Full-stack architectural specification
│   └── demo_script.md       # Step-by-step evaluator demonstration script
├── frontend\
│   ├── src\
│   │   ├── components\      # SoftComputingInspector, LocationPicker, Card, Badges
│   │   ├── pages\           # AnalyticsPage, ReportPage, TrackPage, DashboardPage, etc.
│   │   └── lib\             # API client, geocoding, constants
│   └── vite.config.ts       # Vite config with strictPort: 5173
└── ml\
    ├── dataset\             # RDD2022 dataset preparation & validation utility
    ├── evaluation\          # Model mAP/precision/recall evaluation tool
    ├── inference\           # YOLOv8 detector & 2D geometric severity module
    └── weights\             # Pretrained RDD2022 YOLOv8n weights
```
