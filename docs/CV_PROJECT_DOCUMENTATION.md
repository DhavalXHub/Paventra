# PAVENTRA — COMPUTER VISION SUBSYSTEM TECHNICAL DOCUMENTATION
## Deep Learning Road Distress Detection, 2D Geometric Severity Estimation & Video Telemetry Pipeline
**Course Context:** Computer Vision Laboratory (B.Tech CSE AI-ML, AU-FEST, Adani University)  
**System Target:** Paventra — AI-Powered Civic Road Damage Intelligence and Repair Prioritization System  
**Workspace Root:** `D:\Paventra`  
**Document Version:** 1.0.0 (Audited Technical Baseline)  
**Date of Audit:** October 27, 2026  

---

## 1. PROJECT IDENTITY & SUBSYSTEM SCOPE

In the Paventra municipal intelligence architecture, the **Computer Vision (CV) Subsystem** acts as the primary perceptual layer. It bridges the physical roadway environment and the downstream computational governance pipelines (Soft Computing Mamdani Prioritization, Spatial Big Data Clustering, and Municipal Work-Order Lifecycle Management).

### Primary Responsibilities:
1. **Automated Visual Distress Identification:** Ingests monocular citizen smartphone photographs and vehicular survey video frames, identifying distress anomalies across the international **Road Damage Dataset 2022 (RDD2022)** taxonomy.
2. **2D Geometric Severity Estimation:** Derives quantitative distress severity scores ($1.0$ to $10.0$) using feature-grounded visible footprint area, elongation/aspect ratios, and defect density, rather than relying on ungrounded black-box heuristic guesses.
3. **Survey Video Telemetry & GPS Interpolation:** Samples dashcam survey frames, extracts bounding boxes, synchronizes video timestamps with GNSS tracklogs, and deduplicates consecutive frames to prevent maintenance ticket storms.
4. **Perceptual Image Hashing:** Computes 64-bit difference hashes (dHash) to evaluate image-level duplicate similarity under lighting and minor viewpoint variations.
5. **Human-in-the-Loop Governance:** Enforces strict epistemic boundaries: monocular RGB imagery cannot measure 3D cavity depth or subgrade compaction. Every CV output is flagged `provisional: true` with mandatory coordinator verification prior to resource allocation.

---

## 2. REPOSITORY ARCHITECTURE & SOURCE FILE INVENTORY

The Computer Vision implementation in `D:\Paventra` is organized into distinct modular components across the `ml/`, `backend/`, and `frontend/` directories:

```
D:\Paventra
├── ml/
│   ├── weights/
│   │   ├── download_weights.py       # Automated Hugging Face checkpoint download utility
│   │   └── rdd2022_yolov8n.pt        # Verified pretrained YOLOv8n checkpoint (6,251,050 bytes)
│   ├── inference/
│   │   ├── detector.py               # RoadDamageInferenceEngine (YOLO wrapper, bbox normalization)
│   │   ├── severity.py               # estimate_damage_severity (2D geometric footprint engine)
│   │   └── __init__.py               # Package exports
│   ├── dataset/
│   │   └── prepare_rdd2022.py        # Pascal VOC XML validator, YOLO converter & sample generator
│   ├── evaluation/
│   │   └── evaluate.py               # mAP@50, mAP@50-95, precision/recall evaluation harness
│   └── model_cards/
│       └── yolov8_road_damage.md     # Governance, operating constraints, class taxonomy
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── vision/
│   │   │   │   ├── inference.py      # RoadDamageDetector singleton, app-level service wrapper
│   │   │   │   └── video_inspection.py # Video frame extraction, deduplication & GPS interpolation
│   │   │   └── duplicate_detection/
│   │   │       └── detector.py       # Perceptual image hashing (dHash) and Hamming similarity
│   │   ├── api/v1/
│   │   │   ├── reports.py            # Synchronous & background AI inference on report submission
│   │   │   └── misc.py               # Video inspection job endpoints
│   │   └── models/
│   │       ├── report.py             # Report entity with ai_confidence, ai_bounding_boxes
│   │       └── inspection.py         # InspectionJob and InspectionFrame database models
│   └── tests/
│       ├── test_vision.py            # 8 unit tests: model loading, validation guards, severity scaling
│       ├── test_video.py             # 5 unit tests: GPS interpolation, window tolerance, fallbacks
│       └── test_duplicate.py         # 8 unit tests: dHash similarity, Haversine, duplicate tiers
└── frontend/
    └── src/
        └── pages/
            └── ReportDetailPage.tsx  # Triage UI: Confidence bar, inference latency, severity pill
```

---

## 3. MODEL PROVENANCE, WEIGHTS & INFERENCE ENGINE

### 3.1 Model Checkpoint Provenance
* **Weights File:** `ml/weights/rdd2022_yolov8n.pt`
* **File Size:** $6,251,050$ bytes (~$6.25\text{ MB}$)
* **Architecture:** Ultralytics YOLOv8n (Nano detection variant, PyTorch backbone)
* **Model Task:** `detect` (Bounding Box Object Detection)
* **Download Source:** Hugging Face Model Hub (`dronefreak/rdd2022-yolov8n`), retrieved via `huggingface_hub.hf_hub_download` in `ml/weights/download_weights.py`.
* **Training Status (Audited Truth):** The weights are a **pretrained checkpoint** trained on the external RDD2022 multi-country dataset. The model was **not** trained from scratch or fine-tuned locally within this repository due to local hardware constraints (CPU execution). No synthetic training metrics are fabricated.

### 3.2 Checkpoint Metadata & Class Vocabulary
Verified directly by inspecting the PyTorch checkpoint (`YOLO(weights_file).names`):
```python
{
    0: 'longitudinal_crack',
    1: 'transverse_crack',
    2: 'alligator_crack',
    3: 'pothole'
}
```

### 3.3 Engine Architecture & Lifecycle (`ml/inference/detector.py`)
The `RoadDamageInferenceEngine` manages model discovery, GPU/CPU device mapping, threshold enforcement, and inference execution:
1. **Dynamic Path Discovery (`_find_weights`):** Searches `ml/weights/rdd2022_yolov8n.pt`, local subdirectories, and absolute fallback paths.
2. **Lazy Initialization (`load_model`):** Imports `ultralytics.YOLO` only when required, capturing and reporting initialization errors gracefully if dependencies are missing.
3. **Execution Parameterization:**
   * Default Confidence Threshold: $\tau = 0.35$ (Configurable in `app.core.config.settings.MODEL_CONFIDENCE_THRESHOLD`).
   * Device: `cpu` (or `cuda:0` if configured).
   * Inference Mode: `verbose=False` to avoid polluting web server stdout.

---

## 4. RDD2022 ROAD DAMAGE TAXONOMY & GROUND TRUTH MAPPING

The subsystem strictly adheres to the official taxonomy established by the IEEE Big Data Crowdsensing-based Road Damage Detection Challenge (CRDDC'22 / RDD2022, Arya et al., 2022):

| Class ID | RDD Code | Category Name | Internal Type | Structural Engineering Description |
|:---:|:---:|:---|:---:|:---|
| **0** | `D00` | `longitudinal_crack` | `crack` | Linear crack parallel to the road centerline, caused by paving seam fatigue or subgrade settlement along wheel paths. |
| **1** | `D10` | `transverse_crack` | `crack` | Linear crack perpendicular to the road centerline, induced by thermal shrinkage or base-layer reflection. |
| **2** | `D20` | `alligator_crack` | `crack` | Interconnected network of fatigue cracks resembling crocodile skin, indicating structural base failure under cyclic axle loads. |
| **3** | `D40` | `pothole` | `pothole` | Bowl-shaped localized depression or structural void in the asphalt mat resulting from trapped water penetration and freeze-thaw stripping. |

*Verification Anchor:* Implemented in `RDD_CLASS_MAP` within `ml/inference/detector.py` (lines 26–31) and asserted in unit tests in `backend/tests/test_vision.py` (`test_rdd_class_mapping`).

---

## 5. IMAGE PREPROCESSING, VALIDATION & INFERENCE PIPELINE

### 5.1 Input Validation Safeguards
Ordinary web-submitted images frequently suffer from corruption, network truncation, or invalid formatting. Before passing images to YOLO tensors, `detector.py` enforces three production validation gates:
1. **File Existence Gate:** Verifies `os.path.exists(image_path)`. If missing, returns `InferenceResult(model_available=True, error="File not found: ...")` without crashing.
2. **Format & Integrity Gate:** Attempts OpenCV decoding via `cv2.imread(image_path)`. If decoding fails (e.g. truncated bytes, non-image format), returns `InferenceResult(error="Unsupported format or corrupt image file")`.
3. **Dimension Bounds Gate:** Checks `h < 10 or w < 10`. Microscopic thumbnails are rejected (`error="Image dimensions too small (...) for CV inference"`).

### 5.2 Preprocessing & YOLO Tensor Transformation
* **Image Resizing:** Inputs are processed through Ultralytics' internal letterboxing algorithm, maintaining aspect ratios by padding borders to $640 \times 640$.
* **Color Space:** BGR (OpenCV default) is transformed to RGB format.
* **Normalization:** Pixel uint8 values $[0, 255]$ are normalized to floating-point $[0.0, 1.0]$.

### 5.3 Postprocessing & Coordinate Normalization
Raw YOLO detection output boxes $[x_1, y_1, x_2, y_2]$ in absolute pixel coordinates are normalized against image dimensions $(w, h)$:
$$x_{1,\text{norm}} = \frac{x_1}{w}, \quad y_{1,\text{norm}} = \frac{y_1}{h}, \quad x_{2,\text{norm}} = \frac{x_2}{w}, \quad y_{2,\text{norm}} = \frac{y_2}{h}$$
Every bounding box coordinate is rounded to 4 decimal places, creating a resolution-independent representation for frontend responsive rendering.

---

## 6. EXPLAINABLE 2D GEOMETRIC SEVERITY ESTIMATION

### 6.1 Scientific Motivation & The Monocular Limit
Standard object detection models produce only categorical classes and bounding boxes; they do not output maintenance severity. However, attempting to calculate true physical distress volume ($m^3$) or depth ($mm$) from uncalibrated 2D RGB smartphone photography is an ill-posed inverse problem:
* Camera focal length ($f$), sensor pitch, and ground-plane mounting angles ($\theta$) are unknown.
* Shadows, rainwater puddles, and dark asphalt obscure optical contrast.
* Monocular imagery has zero sensitivity along the optical $z$-axis (depth).

To solve this, Paventra implements a **feature-grounded 2D geometric severity engine** (`ml/inference/severity.py`), deriving explainable severity from measurable surface properties while explicitly marking the output as provisional.

### 6.2 Mathematical Formulation
The severity estimation algorithm evaluates four geometric features:
1. **Total Visible Damaged Area Ratio ($A_{\text{ratio}}$):**
   $$A_{\text{ratio}} = \min\left(1.0, \, \sum_{i=1}^{N} (x_{2,i} - x_{1,i}) \cdot (y_{2,i} - y_{1,i})\right)$$
   $$\text{Area Percentage} = A_{\text{ratio}} \times 100\%$$
2. **Distress Elongation / Aspect Ratio ($R_{\text{aspect}}$):**
   $$R_{\text{aspect}} = \frac{\max(\text{box\_w}, \text{box\_h})}{\max(10^{-4}, \min(\text{box\_w}, \text{box\_h}))}$$
3. **Hazard Category Base Scoring:**
   * **Pothole (`D40`):** Sudden high-impact suspension hazard:
     $$S_{\text{base}} = \begin{cases} 3.5 \ (\text{LOW}) & \text{if } A_{\text{ratio}} < 0.02 \ (2\%) \\ 6.0 \ (\text{MOD}) & \text{if } 0.02 \le A_{\text{ratio}} < 0.06 \\ 8.0 \ (\text{HIGH}) & \text{if } 0.06 \le A_{\text{ratio}} < 0.12 \\ 9.5 \ (\text{CRIT}) & \text{if } A_{\text{ratio}} \ge 0.12 \ (12\%) \end{cases}$$
   * **Crack (`D00`, `D10`, `D20`):** Progressive fatigue and water ingress hazard:
     $$S_{\text{base}} = \begin{cases} 2.5 \ (\text{LOW}) & \text{if } A_{\text{ratio}} < 0.03 \text{ and } R_{\text{aspect}} < 4.0 \\ 5.0 \ (\text{MOD}) & \text{if } A_{\text{ratio}} < 0.08 \text{ or } R_{\text{aspect}} \ge 4.0 \\ 7.5 \ (\text{HIGH}) & \text{otherwise} \end{cases}$$
4. **Multi-Defect Compound Penalty:**
   $$S_{\text{final}} = \min(10.0, \, S_{\text{base}} + \min(1.2, \, (N - 1) \times 0.4))$$

### 6.3 Mandatory Review Triggers (`review_required`)
To guarantee civic safety, human review is flagged as mandatory (`review_required = True`) when:
* Model confidence is marginal ($c_{\max} < 0.60$).
* Distress area falls within ambiguous classification boundaries ($[1.8\%, 2.5\%]$, $[5.5\%, 6.5\%]$, $[11.5\%, 12.5\%]$).
* Scene contains $>2$ distinct distress clusters.
* Computed severity reaches `HIGH` or `CRITICAL`.

---

## 7. VIDEO TELEMETRY & SPATIAL-TEMPORAL GPS INTERPOLATION

### 7.1 Architecture of Video Inspection Service (`backend/app/services/vision/video_inspection.py`)
For municipal driving surveys (Method B), Paventra processes continuous video tracks (MP4/AVI) using OpenCV:
1. **Video Ingestion:** `cap = cv2.VideoCapture(video_path)` extracts frame rate ($fps$) and total frame count.
2. **Frame Sampling:** Implements frame decimation via `sample_step = max(1, job.frame_sample_rate)` (default: 1 frame every 15 frames $\approx 2.0\text{ FPS}$ at $30\text{ FPS}$).
3. **Temporal Mapping:** Timestamp for frame index $k$ is calculated as $t_k = \text{round}(k / fps, 2)$ seconds.

### 7.2 Synchronized GPS Tracklog Interpolation
To associate road defects with geographic coordinates without guessing, Paventra ingests a synchronized GPS telemetry file (JSON tracklog):
* **Format:** `[{"timestamp_seconds": float, "latitude": float, "longitude": float}, ...]`
* **Nearest-Neighbor Temporal Matching (`find_interpolated_gps`):**
  Identifies tracklog point $p^*$ minimizing $|t_{p^*} - t_k|$.
* **Strict 2.0-Second Boundary Window:**
  $$\text{If } |t_{p^*} - t_k| \le 2.0\text{ s} \implies (\text{lat}_{p^*}, \text{lon}_{p^*})$$
  $$\text{If } |t_{p^*} - t_k| > 2.0\text{ s} \implies (\text{None}, \text{None})$$
* **Negative Location Safeguard:** If no synchronized track is supplied, coordinates are recorded as `None` with `LocationSource.UNKNOWN`. **Coordinates are never hallucinated from image pixels.**

### 7.3 Duplicate Observation Suppression (Window Decay)
In high-frame-rate vehicular surveys, a single pothole is visible across multiple consecutive frames. To prevent flooding municipal databases with dozens of duplicate tickets for one physical hole:
* Consecutive frame detections occurring within $3.0\text{ seconds}$ of the last recorded defect are flagged `is_duplicate = True`.
* Duplicate frames are stored in the `InspectionFrame` database table for audit trails, but are suppressed from creating redundant `Report` tickets.

---

## 8. PERCEPTUAL IMAGE HASHING (dHash) FOR DUPLICATE DETECTION

### 8.1 Mathematical Difference Hashing (`backend/app/services/duplicate_detection/detector.py`)
To identify crowdsourced citizen duplicate reports submitted for the same pothole from slightly different angles, Paventra computes a 64-bit Difference Hash (dHash):
1. **Grayscale Decoding:** Decodes image in single-channel format (`cv2.IMREAD_GRAYSCALE`).
2. **Area Downsampling:** Resizes image to $9 \times 8$ pixels using area interpolation:
   $$I_{\text{down}} = \text{cv2.resize}(I_{\text{gray}}, (9, 8), \text{interpolation}=\text{cv2.INTER\_AREA})$$
3. **Horizontal Gradient Computation:**
   Evaluates adjacent column intensity differences:
   $$D(y, x) = \begin{cases} 1 & \text{if } I_{\text{down}}(y, x+1) > I_{\text{down}}(y, x) \\ 0 & \text{otherwise} \end{cases} \quad \forall y \in [0, 7], x \in [0, 7]$$
4. **Hex Bit-Packing:** Compresses the resulting $8 \times 8 = 64$ boolean values into a 16-character hexadecimal string via `np.packbits(diff).tobytes().hex()`.

### 8.2 Hamming Distance Similarity
The perceptual similarity between two hashes $H_1, H_2$ is computed via normalized bitwise XOR:
$$D_{\text{Hamming}} = \sum_{b=1}^{64} (H_1[b] \oplus H_2[b])$$
$$\text{Similarity}_{\text{image}} = \max\left(0.0, \, 1.0 - \frac{D_{\text{Hamming}}}{64.0}\right)$$
* Identical images: $D_{\text{Hamming}} = 0 \implies \text{Similarity} = 1.0000$.
* Minor brightness/noise variations: $D_{\text{Hamming}} \le 3 \implies \text{Similarity} \ge 0.9531$.
* Dissimilar images: $D_{\text{Hamming}} \approx 32 \implies \text{Similarity} \approx 0.5000$.

---

## 9. INTEGRATION WITH SOFT COMPUTING PRIORITIZATION ENGINE

The Computer Vision subsystem does not make repair decisions in isolation. Instead, its optical measurements directly feed the **Mamdani Fuzzy Inference System (FIS)** (`backend/app/services/prioritization/fuzzy_engine.py`):

```
+---------------------------------------+
|  Monocular RGB Input Image / Frame   |
+---------------------------------------+
                   |
                   v
+---------------------------------------+
|  YOLOv8 Inference Engine              |
|  - Class: D00, D10, D20, D40          |
|  - Confidence: c in [0.35, 1.0]        |
|  - Bounding Boxes: [x1, y1, x2, y2]   |
+---------------------------------------+
                   |
                   v
+---------------------------------------+
|  2D Severity Estimator (severity.py)  |
|  - Footprint area percentage          |
|  - Max elongation aspect ratio        |
|  - Output Score: S in [1.0, 10.0]     |
|  - Level: LOW, MODERATE, HIGH, CRIT   |
+---------------------------------------+
                   |
                   | S (Severity Score)
                   v
+---------------------------------------+
|  23-Rule Mamdani FIS (fuzzy_engine.py)| <--- Traffic Exposure (T)
|  - Evaluates non-linear compound risk | <--- Waiting Duration (D)
|  - Centroid defuzzification over 201  | <--- Safety Urgency (U)
|  - Output Priority Score: P in [0,100]|
+---------------------------------------+
                   |
                   v
+---------------------------------------+
|  Municipal Triage Queue & Work Orders |
+---------------------------------------+
```

### Direct Coupling Parameters:
* **Severity Input ($S$):** The numeric score ($S \in [1.0, 10.0]$) generated by `estimate_damage_severity` is passed directly as `severity_numeric` into `compute_priority()`.
* **Linguistic Level:** The discrete category (`low`, `moderate`, `high`, `critical`) initializes the antecedent membership functions ($\mu_{\text{low}}, \mu_{\text{moderate}}, \mu_{\text{high}}, \mu_{\text{critical}}$).
* **Linear Dilution Prevention:** When the CV engine identifies a critical pothole ($S = 9.9$), the Fuzzy Engine elevates the priority to High/Critical even if traffic volume is light, preventing linear weighted sum suppression.

---

## 10. FRONTEND USER INTERFACE INTEGRATION

In the municipal triage portal (`frontend/src/pages/ReportDetailPage.tsx`), CV inferences are rendered in an interactive card:
1. **Detected Distress Label:** Displays the primary defect class (e.g., `pothole`, `crack`) with capitalized styling.
2. **Model Confidence Bar:** Visual percentage progress bar (`report.ai_confidence * 100%`).
3. **Inference Latency Badge:** Displays processing time in milliseconds (e.g., `542ms`).
4. **Provisional Warning Pill:** Displays an amber `<AlertTriangle />` pill labeled **"Provisional"**, alerting coordinators that optical estimates must be physically verified.
5. **Severity Estimate Box:** Shows the estimated level (e.g., `CRITICAL (9.9/10)`), footprint area percentage, and distress elongation ratio.
6. **Review Required Flag:** Highlights tickets with high uncertainty or severe damage with an amber "Review Required" badge.

---

## 11. AUTOMATED TEST SUITE & EMPIRICAL VERIFICATION

The vision subsystem is validated by **21 dedicated automated tests** passing with zero failures:

```powershell
cd D:\Paventra\backend
python -m pytest tests/test_vision.py tests/test_video.py tests/test_duplicate.py -v
```

### Verified Test Breakdown:
* **`tests/test_vision.py` (8 passed in 21.36s):**
  1. `test_rdd_class_mapping`: Asserts standard 4-class RDD2022 mappings (`D00`, `D10`, `D20`, `D40`).
  2. `test_cv_engine_available_with_rdd_weights`: Confirms checkpoint loading and engine readiness.
  3. `test_invalid_image_path_returns_clean_error`: Confirms missing image handling without crashes.
  4. `test_corrupt_or_empty_image_handling`: Confirms non-image binary rejection.
  5. `test_image_dimensions_too_small`: Confirms rejection of sub-10px images.
  6. `test_severity_estimation_pothole_scaling`: Verifies area ratio scaling ($<2\% \to \text{low}$, $>12\% \to \text{critical}$).
  7. `test_severity_estimation_crack_geometry`: Verifies aspect ratio elongation triggers moderate/high severity.
  8. `test_severity_review_required_and_disclaimer`: Validates review triggers and disclaimer strings.
* **`tests/test_video.py` (5 passed):**
  1. `test_parse_gps_track_valid`: Validates JSON telemetry extraction.
  2. `test_parse_gps_track_missing_or_corrupt`: Validates corrupt GPS track tolerance.
  3. `test_find_interpolated_gps_within_window`: Confirms coordinate matching within 2.0s window.
  4. `test_find_interpolated_gps_out_of_window_returns_none`: Confirms coordinate suppression beyond 2.0s.
  5. `test_find_interpolated_gps_empty_track`: Confirms safe fallback on empty GPS logs.
* **`tests/test_duplicate.py` (8 passed):**
  1. `test_image_perceptual_hash_similarity`: Confirms identical hashes give $1.0$, 1-bit difference gives $>0.95$, and inverted hashes give $0.0$.
  2. `test_compute_similarity_score`, `test_far_apart_low_similarity`, etc.: Validates composite multi-factor deduplication.

---

## 12. EMPIRICAL BENCHMARK EXPERIMENT ON REAL ROAD DISTRESS

To provide genuine experimental data for the Computer Vision laboratory report, inference was executed directly against sample distress images:

### Experiment 1: Synthetic RDD2022 Sample Verification (`India_000001.jpg`)
* **Input Image:** $600 \times 600 \times 3$ RGB road image containing synthesized pothole voids and crack lines.
* **Inference Latency:** $6,895.74\text{ ms}$ (CPU execution).
* **Detections Identified:**
  1. `D40` (`pothole`): Confidence = **$0.6018$** (60.18%), Bounding Box = `[0.3457, 0.5382, 0.6384, 0.7954]`
  2. `D40` (`pothole`): Confidence = **$0.5766$** (57.66%), Bounding Box = `[0.0667, 0.1536, 0.2106, 0.8147]`
* **Severity Output:** Level = **`CRITICAL`**, Score = **$9.9 / 10.0$**, `review_required = True`.

### Experiment 2: Pothole with Rainwater Obstruction (`deep-road-pothole-filled-with-rainwater.webp`)
* **Input Image:** `sample-test/deep-road-pothole-filled-with-rainwater.webp` ($62,946\text{ bytes}$).
* **Execution Outcome:** $0$ detections at $\tau = 0.35$ and $\tau = 0.10$.
* **Failure Analysis:** Standing water creates specular reflections and eliminates texture gradients of the asphalt crater lip, causing the pretrained detector to fail. This demonstrates a documented real-world CV edge case: water-filled cavities require LiDAR or multispectral sensing.

---

## 13. RDD2022 DATASET PREPROCESSING UTILITY (`ml/dataset/prepare_rdd2022.py`)

For reproducible training or evaluation on the full 47,000-image dataset, Paventra includes a standalone preprocessing pipeline:
1. **Pascal VOC XML Parsing:** Scans multi-country subsets (`India`, `Japan`, `Czech`, `Norway`, `United_States`, `China`).
2. **Coordinate Validation:** Checks boundary bounds ($0 \le x_{\min} < x_{\max} \le W$) and rejects zero-area boxes.
3. **Sequence-Aware Partitioning:** Groups images by dashcam sequence IDs, splitting $70\%$ train, $15\%$ validation, and $15\%$ test to prevent temporal frame leakage between splits.
4. **Ultralytics YAML Generation:** Exports formatted `data.yaml` descriptors for model training.
5. **Synthetic Sample Generator (`--create-sample`):** Generates 10 valid VOC XML image pairs with realistic textured asphalt for CI/CD test automation without downloading 10GB archives.

---

## 14. DOCUMENTED LIMITATIONS & ETHICAL GOVERNANCE

1. **Depth Inaccessibility:** 2D monocular cameras cannot estimate vertical depth ($z$-displacement). High-severity predictions indicate large visual footprint area, not necessarily deep sub-base collapse.
2. **Environmental Occlusions:** Rainwater, mud, tree canopy shadows, and vehicle tire tracks can suppress confidence or cause false negatives.
3. **CPU Execution Latency:** Inference on CPU requires $6$–$10$ seconds per high-resolution frame. Real-time edge video processing ($>15\text{ FPS}$) requires dedicated tensor hardware (e.g. NVIDIA Jetson / TensorRT).
4. **Pretrained Generalization:** The Hugging Face checkpoint was trained on international roads; novel domestic asphalt patterns or unmarked speed bumps may exhibit domain shift.

---

## 15. REQUIREMENTS COMPLIANCE & UNRESOLVED ITEMS

* **Available Code & Tests:** Fully audited, functional, and passing in `D:\Paventra`.
* **Unresolved Requirement:** The specific Computer Vision course assignment rubric or mini-project proposal template was not present as a separate file inside `D:\Paventra`. Once the official rubric is provided, a final 1:1 compliance matrix can be compiled for academic submission.
