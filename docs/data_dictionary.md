# Paventra Data Dictionary & Provenance Specification

## 1. Overview and Purpose
This document defines the formal schema, provenance standards, and measurement methodologies for all data attributes used across the **Paventra Road Damage Intelligence System**. 

Road distress management requires reconciling two fundamentally distinct types of data:
1. **Direct Optical Observations:** 2D bounding boxes, pixel ratios, and confidence scores emitted by the YOLOv8 computer vision model trained on RDD2022.
2. **Contextual & Soft Computing Variables:** Traffic density, road classifications, elapsed waiting time, safety hazards, and physical depth measurements that **cannot** be directly determined from standard RGB photographs.

---

## 2. Tabular Schema for Road Damage Reports & Prioritization

| Column Name | Data Type | Permissible Range | Acquisition / Calculation Method | Provenance & Source | Uncertainty & Limitations |
|:---|:---|:---|:---|:---|:---|
| `report_id` | String (UUIDv4) | 36-char UUID | Generated upon ingestion | System (`UUIDv4`) | None (deterministic key) |
| `public_ref` | String | `PAV-[A-Z0-9]{8}` | Unique human-readable code | System random base32 | None |
| `detection_class` | String | `D00`, `D10`, `D20`, `D40`, `unknown` | YOLOv8 object detection inference | `[INFERRED_2D_VISION]` | Subject to model classification error ($\tau \ge 0.35$). |
| `class_description` | String | Text label | Taxonomy lookup table | RDD2022 taxonomy | Descriptive |
| `detection_confidence` | Float | `0.000` to `1.000` | Softmax probability output from YOLOv8 | `[INFERRED_2D_VISION]` | Epistemic uncertainty of model feature matching. |
| `bbox_area_ratio` | Float | `0.0000` to `1.0000` | Normalized box area: $\frac{(x_2-x_1)(y_2-y_1)}{W \times H}$ | `[INFERRED_2D_VISION]` | 2D image plane only; perspective distortion affects camera angle. |
| `provisional_severity_score` | Float | `1.0` to `10.0` | Heuristic geometric footprint + class hazard index | `[INFERRED_2D_VISION]` | **Provisional estimate.** Ordinary 2D imagery cannot measure true volumetric cavity depth. |
| `human_verified_severity` | String (Nullable) | `low`, `moderate`, `high`, `critical`, `null` | Manual assessment by certified municipal coordinator | `[COORDINATOR_ENTRY]` | Overrides model provisional score once field-inspected. |
| `traffic_exposure_score` | Float | `0.0` to `10.0` | Municipal road hierarchy lookup or coordinator entry | `[MUNICIPAL_TELEMETRY]` or `[ESTIMATED_DEFAULT]` | Defaults to safe midpoint `5.0` if road census unavailable. |
| `traffic_provenance` | String | `sensor`, `gis_road_class`, `manual_entry`, `estimated_default` | Method of acquisition | System metadata | Transparently documents whether traffic is measured or assumed. |
| `time_unresolved_days` | Float | `0.0` to `365.0` | Elapsed duration: `(now() - created_at).days` | `[AUDIT_TIMESTAMPS]` | Temporal precision to seconds. |
| `safety_urgency_score` | Float | `0.0` to `10.0` | Proximity to school zones, pedestrian crossings, or high-speed arterials | `[GIS_BUFFER_SPATIAL]` or `[COORDINATOR_ENTRY]` | Evaluates impact hazard to two-wheelers and pedestrians. |
| `duplicate_report_count` | Integer | $\ge 0$ | Spatial-temporal clustering ($r \le 25\text{m}, \Delta t \le 14\text{d}$) | `[DEDUPLICATION_ENGINE]` | Prevents redundant work orders from multiple citizen uploads. |
| `latitude` | Float | `-90.0` to `+90.0` | Hardware GNSS / EXIF GPS / User Map Pin | `[CLIENT_GEOLOCATION]` | GPS horizontal accuracy reported in `location_accuracy_meters`. |
| `longitude` | Float | `-180.0` to `+180.0` | Hardware GNSS / EXIF GPS / User Map Pin | `[CLIENT_GEOLOCATION]` | Subject to urban canyon multi-path reflections. |
| `road_segment` | String | Text address | Reverse geocoded Nominatim / OSM highway tag | `[OSM_GEOCODING]` | Address hint; verified on map. |
| `status` | String | `submitted`, `under_review`, `verified`, `assigned`, `in_progress`, `pending_verification`, `resolved`, `rejected` | Finite State Machine workflow | `[WORKFLOW_ENGINE]` | Enforces immutable state transition audit history. |
| `assigned_team_id` | String (Nullable) | UUID | Municipal repair crew assignment | `[COORDINATOR_ENTRY]` | Foreign key to `repair_teams`. |
| `assignment_timestamp` | ISO8601 (Nullable) | UTC timestamp | Time coordinator dispatched crew | `[AUDIT_TIMESTAMPS]` | Audit tracked. |
| `completion_timestamp` | ISO8601 (Nullable) | UTC timestamp | Time crew submitted repair completion proof | `[REPAIR_CREW_ENTRY]` | Accompanied by mandatory photographic evidence. |
| `resolution_verified_at` | ISO8601 (Nullable) | UTC timestamp | Time coordinator reviewed after-repair photo and verified resolution | `[COORDINATOR_ENTRY]` | System **never** self-certifies resolution without coordinator review. |
| `fuzzy_priority_score` | Float | `0.0` to `100.0` | Mamdani Fuzzy Inference System defuzzified centroid | `[SOFT_COMPUTING_MAMDANI]` | Primary explainable decision support score. |
| `baseline_weighted_score` | Float | `0.0` to `100.0` | Linear weighted sum: $0.35 S + 0.20 T + 0.20 D + 0.25 U$ | `[BASELINE_REFERENCE]` | Academic control benchmark to demonstrate fuzzy non-linearity. |
| `decision_delta` | Float | `-100.0` to `+100.0` | `fuzzy_priority_score - baseline_weighted_score` | `[ANALYTIC_COMPARISON]` | Demonstrates edge-case elevation for critical safety hazards. |

---

## 3. Data Provenance & Safeguards Policy

### 3.1 2D Optical Inference Safeguard
> [!IMPORTANT]
> ordinary monocular RGB images cannot recover true depth, pothole cavity volume, or road sub-base structural failure.
> All computer vision outputs are strictly recorded as `provisional: true`. The UI and API must explicitly label bounding box area as visible surface distress footprint rather than true physical depth.

### 3.2 Human-in-the-Loop Governance
No road defect can transition to `resolved` without:
1. An uploaded post-repair photograph showing the sealed pavement surface.
2. Explicit coordinator review and verification in the Coordinator Portal.
3. An immutable entry in the `audit_events` and `report_status_history` tables recording the reviewer's ID, timestamp, and notes.

### 3.3 Default Values and Epistemic Uncertainty
When non-optical variables are missing:
- `traffic_exposure_score`: Defaults to neutral midpoint `5.0`, tagged as `traffic_provenance: estimated_default`.
- `safety_urgency_score`: Defaults to `5.0` unless nearby school/hospital POIs are intersected or set by coordinator.
- `time_unresolved_days`: Deterministically calculated from `created_at`.
All imputations are logged transparently in `fuzzy_priority_assessments`.
