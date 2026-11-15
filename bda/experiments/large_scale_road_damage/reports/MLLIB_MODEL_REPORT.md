# Spark MLlib Supervised Model Training Report

**Algorithm:** Apache Spark MLlib `RandomForestClassifier`  
**Task:** Supervised Multi-class Classification of Road Damage Types from Bounding-Box Geometry  
**Split Strategy:** Grouped split by `image_id` (80% Train, 20% Test, Seed 42) to eliminate data leakage  
**Training Samples:** 6,703 bounding boxes  
**Test Samples:** 1,500 bounding boxes  
**Training Duration:** 5.316 seconds  

---

## 1. Classification Performance Metrics

| Evaluation Metric | MLlib Random Forest Model | Simple Majority-Class Baseline (`D40`) | Delta / Improvement |
|---|---|---|---|
| **Accuracy** | **65.47%** | 38.20% | **+27.27%** |
| **Weighted Precision** | **0.6216** | - | - |
| **Weighted Recall** | **0.6547** | - | - |
| **Weighted F1-Score** | **0.6318** | - | - |

> **Scientific Honesty & Methodology Explanation:**  
> This MLlib model operates strictly on geometric and spatial features (`normalized_width`, `normalized_height`, `normalized_area`, `aspect_ratio`, `center_x`, `center_y`) derived from bounding boxes, rather than raw image pixel tensors.  
> It proves that geometric spatial footprints alone possess significant discriminative power to distinguish longitudinal cracks (high aspect ratio, narrow width) from potholes (compact, circular/elliptical area) and fatigue alligator cracks (wide area footprint). It achieves a substantial **+27.27% accuracy gain** over predicting the majority class.

---

## 2. Feature Importance Analysis

| Geometric Feature | Gini Importance Weight |
|---|---|
| `normalized_height` | 0.2888 |
| `aspect_ratio` | 0.2389 |
| `normalized_width` | 0.1732 |
| `normalized_area` | 0.1317 |
| `center_x` | 0.1074 |
| `center_y` | 0.0599 |

---

## 3. Multiclass Confusion Matrix (Held-out Test Set)

| Actual_Class | Pred_D40 | Pred_D20 | Pred_D00 | Pred_D44 | Pred_D01 | Pred_D10 | Pred_D43 | Pred_D11 | Pred_D50 | Pred_D0w0 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
D40 | 458 | 75 | 19 | 21 | 0 | 0 | 0 | 0 | 0
D20 | 47 | 288 | 25 | 6 | 0 | 0 | 1 | 1 | 0
D00 | 44 | 29 | 175 | 38 | 0 | 0 | 0 | 0 | 0
D44 | 73 | 19 | 57 | 55 | 0 | 0 | 0 | 0 | 0
D01 | 4 | 2 | 20 | 7 | 0 | 0 | 0 | 0 | 0
D10 | 7 | 2 | 0 | 0 | 0 | 2 | 1 | 1 | 0
D43 | 2 | 8 | 0 | 0 | 0 | 1 | 1 | 0 | 0
D11 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 3 | 0
D50 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0

---

## 4. Model Architecture & Hyperparameters

- **Number of Decision Trees:** 50
- **Max Tree Depth:** 8
- **Random Seed:** 42
- **Features Vector Assembly:** `VectorAssembler` across 6 continuous geometric columns
- **Label Encoding:** `StringIndexer` with alphabetical class preservation
- **Saved Model Location:** `D:\Paventra\bda\experiments\large_scale_road_damage\outputs\mllib_rf_model`
