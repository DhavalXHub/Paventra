# Paventra Demonstration Script (Fastest 3-Minute Walkthrough)

## Prerequisites
1. **Backend Server Running:**
   ```powershell
   cd d:\Paventra\backend
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Frontend Running:**
   ```powershell
   cd d:\Paventra\frontend
   npm run dev
   ```
3. Open browser at `http://localhost:5173`.

---

## Step 1: Citizen Road Damage Reporting (Method A)
1. Navigate to `http://localhost:5173/report`.
2. Notice the clean civic-tech UI.
3. Click **Upload image** and select any road image (e.g. pothole or crack).
4. Select damage category `Pothole` from the dropdown.
5. Click **Next: Confirm location**.
6. The interactive Leaflet OpenStreetMap appears. Click anywhere on the map to drop a pin.
7. Click **Review & Submit**.
8. Inspect the pre-submission review screen.
9. Click **Submit report**.
10. The report is saved, an instant AI preliminary assessment is returned, and a unique reference is generated (e.g. `PAV-XXXXXXXX`).
11. Click **Track status** to observe the real-time timeline for this complaint.

---

## Step 2: Coordinator Operations Workflow
1. Navigate to `http://localhost:5173/login`.
2. Log in using the seeded municipal credentials:
   - **Email:** `coordinator@paventra.local`
   - **Password:** `Paventra2024!`
3. View the **Dashboard**:
   - Total complaints, recent 7-day volume, overdue cases, high-severity unverified counts.
   - Interactive Recharts trend charts and status breakdown bars.
4. Click **Reports** in the left sidebar:
   - Search by reference or filter by status (`submitted`), severity, or damage type.
5. Click on the newly submitted report:
   - View uploaded evidence photograph.
   - Review AI confidence, bounding boxes, and Fuzzy Priority Score (0-100) with contributing factors.
6. Advance Status:
   - Select `Under Review` -> click **Apply**.
   - Select `Verified` -> click **Apply**.
7. Assign Repair Crew:
   - Notice the **Assign repair team** box now activates.
   - Select `Team Alpha` (or `Team Beta`), pick a target completion date, and click **Assign team**.
   - The status updates to `Assigned` and records the audit log event with timestamp.

---

## Step 3: Geospatial Map View
1. Click **Map** in the sidebar (`/coordinator/map`).
2. All reports with coordinates appear with status-colored SVG markers.
3. Click any marker to view its pop-up summary (reference ID, status badge, priority score, and damage type).

---

## Step 4: Big Data Batch Analytics
Run the reproducible batch analytics job in terminal:
```powershell
python d:\Paventra\analytics\jobs\road_damage_batch_analytics.py
```
Observe:
- 150 synthetic records loaded from explicit schema fixture.
- Spatial grid clustering ($0.01^\circ$ precision) highlights recurring damage hotspots.
- Calculation parity validation confirms identical metrics between PySpark and Reference engines (`Parity verified: True`).

---

## Step 5: Verification of Automated Tests
Run the pytest test suite:
```powershell
cd d:\Paventra\backend
python -m pytest -v
```
All 16 unit and integration tests execute and pass (`16 passed in ~2.7s`).
