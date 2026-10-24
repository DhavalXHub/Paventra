# Model Card: YOLOv8 Road Damage Detection

## Model Overview
- **Model Name:** Paventra YOLOv8 Road Damage Detector
- **Architecture:** YOLOv8n / YOLOv8s (Ultralytics)
- **Task:** Multi-class Object Detection (Bounding Box)
- **Primary Domain:** Pavement distress and road surface anomaly detection
- **License:** AGPL-3.0 (Ultralytics) / Research & Civic Non-Commercial

## Intended Use
- **Primary Use:** AI-assisted pre-screening of road surface damage for municipal coordinators and citizen reports.
- **Out of Scope:** Autonomous structural certifications, post-repair warranty sign-off without human verification.

## Supported Classes
Mapped according to standard Road Damage Detection (RDD) dataset taxonomy:
| Class Code | Category | Description | Model Class ID |
|---|---|---|---|
| `D00` | `longitudinal_crack` | Longitudinal linear crack along wheel path | 0 |
| `D10` | `transverse_crack` | Transverse linear crack across pavement width | 1 |
| `D20` | `alligator_crack` | Fatigue / crocodile cracking network | 2 |
| `D40` | `pothole` | Pothole or structural surface cavity | 3 |

## Safeguards and Operational Constraints
1. **Never Infer Coordinates from Pixels:** GPS coordinates are ONLY attached via device GNSS hardware, synchronized GPX/NMEA telemetry, or explicit interactive map pin placement.
2. **Confidence Thresholding:** Minimum inference threshold is strictly enforced (default: $\tau = 0.40$). Detections below this threshold are rejected.
3. **No Safety Hazard Auto-Certification:** Model predictions are explicitly labeled as `severity_is_estimated: true`. A human municipal coordinator must verify any repair classification before municipal budget or crew dispatch.
4. **Duplicate Suppression:** Video frames are sampled and deduplicated within temporal/spatial buffers to prevent one road defect from generating dozens of redundant work orders.

## Evaluation Protocol
See `ml/evaluation/evaluate.py` to evaluate custom weights against held-out validation sets (e.g. RDD2022 / CRDDC).
Standard metrics measured:
- **Precision:** $\frac{TP}{TP + FP}$
- **Recall:** $\frac{TP}{TP + FN}$
- **mAP@50:** Mean Average Precision at IoU threshold 0.50
- **mAP@50:95:** Mean Average Precision across IoU thresholds 0.50 to 0.95
