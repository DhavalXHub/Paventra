# Read-Only YOLOv8n Batch Inference Report

**Deployed Checkpoint:** `D:\Paventra\ml\weights\rdd2022_yolov8n.pt`  
**Execution Mode:** Strictly Read-Only Inference (`torch.no_grad()`, `model.eval()`, zero weight updates)  
**Hardware Accelerator:** CPU (Intel/AMD x86_64)  
**Confidence Threshold:** `0.20`  
**Total Images Processed:** 300 real road images  
**Images with Detected Defects:** 103 (34.33%)  
**Images without Detections:** 197 (65.67%)  
**Total Defect Objects Detected:** 149  
**Average Inference Latency:** 54.4 ms/image  
**Batch Throughput:** **18.12 images/sec**  
**Total Batch Execution Time:** 16.552 seconds  

---

## 1. Defect Category Distribution & Model Confidence

| Detected Class | Defect Count | Mean Model Confidence |
|---|---|---|
| **alligator_crack** | 64 | 47.28% |
| **pothole** | 52 | 42.02% |
| **longitudinal_crack** | 33 | 34.31% |

---

## 2. Model Architecture & Deployment Protection

- **Model Type:** Ultralytics YOLOv8 Nano (`yolov8n`)
- **Classes Configured in Checkpoint:** `0: longitudinal_crack`, `1: transverse_crack`, `2: alligator_crack`, `3: pothole`
- **Integrity Guarantee:** Checkpoint weights were loaded directly from disk without modification, retraining, or fine-tuning.
- **Output Formats:**
  - Structured CSV: `D:\Paventra\bda\experiments\large_scale_road_damage\outputs\yolo_detections.csv` (346 rows)
  - Columnar Parquet: `D:\Paventra\bda\experiments\large_scale_road_damage\outputs\yolo_detections.parquet`
  - Visual Detections: `D:\Paventra\bda\experiments\large_scale_road_damage\outputs\annotated_previews` (10 annotated images)
