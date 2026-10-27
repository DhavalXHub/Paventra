# Official Dataset Guide: Road Damage Dataset 2022 (RDD2022)

**Project:** Paventra — Road Damage Intelligence & Prioritization System  
**Dataset Reference:** RDD2022 (CRDDC'22 Benchmark)  
**Primary Subsets:** India, Japan, Czech Republic, Norway, United States, China  

---

## 1. Official Dataset Citation & Provenance

The primary computer vision dataset utilized by Paventra is the **Road Damage Dataset 2022 (RDD2022)**, released as part of the Crowdsensing-based Road Damage Detection Challenge (CRDDC'22).

### Academic Citation
```bibtex
@inproceedings{arya2022crddc,
  author    = {Deeksha Arya and Hiroya Maeda and Sanjay Kumar Ghosh and Durga Toshniwal and Alexandre Mraz and Takehiro Kashiyama and Yoshihide Sekimoto},
  title     = {Crowdsensing-based Road Damage Detection Challenge 2022 (CRDDC'22)},
  booktitle = {2022 IEEE International Conference on Big Data (Big Data)},
  pages     = {6271--6280},
  year      = {2022},
  doi       = {10.6084/m9.figshare.21431547.v1}
}
```

### Official Links
- **Dataset Information:** [https://crddc2022.sekilab.global/data/](https://crddc2022.sekilab.global/data/)
- **Figshare Archive:** [https://doi.org/10.6084/m9.figshare.21431547.v1](https://doi.org/10.6084/m9.figshare.21431547.v1)
- **Official Repository:** [https://github.com/sekilab/RoadDamageDetector](https://github.com/sekilab/RoadDamageDetector)

---

## 2. Supported Distress Taxonomy

RDD2022 defines four standard damage categories evaluated in the international challenge:

| Class Code | Category | Description | Model Class ID |
|:---|:---|:---|:---:|
| `D00` | Longitudinal Crack | Linear crack running parallel to road centerline | `0` |
| `D10` | Transverse Crack | Linear crack running perpendicular to road centerline | `1` |
| `D20` | Alligator Crack | Interconnected network of fatigue / crocodile cracking | `2` |
| `D40` | Pothole | Structural bowl-shaped cavity or depression in asphalt | `3` |

---

## 3. Recommended Directory Organization

Paventra structures dataset assets under `data/road_damage/`:

```
data/road_damage/
├── raw/                      # Original downloaded archives & unpacked Pascal VOC files
│   ├── India/
│   │   ├── images/           # Raw .jpg files
│   │   └── annotations/xmls/ # Pascal VOC XML files
│   └── .gitkeep
├── processed/                # Validated, converted Ultralytics YOLOv8 dataset
│   ├── images/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   ├── labels/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   └── data.yaml             # Ultralytics dataset configuration
├── splits/                   # Reproducible sequence-grouped split manifests
│   └── dataset_manifest_india.json
├── reports/                  # Preprocessing quality & class distribution reports
│   ├── preprocessing_report_india.json
│   └── preprocessing_report_india.md
└── models/                   # Local training checkpoints and weights
```

> [!NOTE]
> Large raw archives, processed images, and heavy weights (`.pt`) are excluded from Git via `.gitignore` to maintain a lightweight, reproducible repository.

---

## 4. Dataset Preparation Pipeline

Paventra provides a production-grade dataset conversion utility at `ml/dataset/prepare_rdd2022.py`.

### 4.1 Step 1: Download Official Subset
1. Navigate to the Figshare repository: [https://doi.org/10.6084/m9.figshare.21431547.v1](https://doi.org/10.6084/m9.figshare.21431547.v1)
2. Download `India.tar.gz` (~1.6 GB) for domestic pavement conditions, or other subsets (`Japan.tar.gz`, `Czech.tar.gz`, etc.).
3. Extract the archive into:
   ```
   data/road_damage/raw/India/
   ```

### 4.2 Step 2: Run the Preparation & Conversion Tool
Run the conversion pipeline to parse Pascal VOC XML annotations, validate coordinates, enforce class taxonomy, and output YOLOv8 format:

```bash
python ml/dataset/prepare_rdd2022.py --source-dir data/road_damage/raw/India --country India
```

#### Pipeline Operations:
1. **Disk Space Verification:** Confirms available storage before processing.
2. **XML Parsing & Validation:** Checks coordinate boundaries (`0 <= xmin < xmax <= width`, `0 <= ymin < ymax <= height`) and flags missing, empty, or inverted bounding boxes.
3. **Format Normalization:** Converts absolute coordinates to normalized YOLO centers:
   \[
   x_{\text{center}} = \frac{x_{\min} + x_{\max}}{2 \cdot W}, \quad w = \frac{x_{\max} - x_{\min}}{W}
   \]
4. **Leakage-Free Splitting:** Groups continuous camera sequences (by image ID prefix) to prevent near-duplicate dashcam frames from appearing in both train and test splits (default: 70% Train, 15% Val, 15% Test).
5. **Quality Reporting:** Emits `preprocessing_report_india.json` and markdown summaries.

### 4.3 Quickstart: Synthetic Sample Generator for Testing & CI
To test the pipeline without downloading a multi-gigabyte dataset:
```bash
python ml/dataset/prepare_rdd2022.py --create-sample --country India
```
This automatically generates 10 verified sample images with corresponding Pascal VOC XML annotations representing all 4 distress classes (`D00`, `D10`, `D20`, `D40`), validates them, and produces a complete, working `data/road_damage/processed/data.yaml`.

---

## 5. Model Evaluation Protocol

To evaluate detection performance against held-out validation sets:

```bash
python ml/evaluation/evaluate.py --weights ml/weights/rdd2022_yolov8n.pt --data data/road_damage/processed/data.yaml --device cpu
```

Metrics actually evaluated and logged:
- **Precision:** \(\frac{\text{TP}}{\text{TP} + \text{FP}}\)
- **Recall:** \(\frac{\text{TP}}{\text{TP} + \text{FN}}\)
- **mAP@50:** Mean Average Precision at IoU = 0.50
- **mAP@50-95:** Mean Average Precision across IoU thresholds \([0.50, 0.95]\)
