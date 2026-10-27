# RDD2022 Preprocessing & Quality Report (India)

## 1. Executive Summary
- **Dataset Subset:** RDD2022 — India
- **Official Citation:** Arya et al., CRDDC'22, IEEE Big Data 2022.
- **XML Annotations Scanned:** 10
- **Valid Image-Annotation Pairs:** 10
- **Total Valid Bounding Boxes:** 15
- **Validation Issues Filtered:** 0

## 2. Class Distribution (Official RDD Taxonomy)
| Class Code | Category | Count | Percentage |
|:---|:---|:---|:---|
| `D00` | Longitudinal Crack | 4 | 26.7% |
| `D10` | Transverse Crack | 3 | 20.0% |
| `D20` | Alligator Crack | 3 | 20.0% |
| `D40` | Pothole | 5 | 33.3% |

## 3. Split Allocation (Leakage-Free Sequence Partitioning)
- **Train Set (70%):** 10 images
- **Validation Set (15%):** 0 images
- **Test Set (15%):** 0 images

## 4. Configuration
- **Ultralytics YOLO YAML:** `ml/dataset/synthetic_samples/data.yaml`
- **Manifest:** `data/road_damage/splits/dataset_manifest_india.json`
