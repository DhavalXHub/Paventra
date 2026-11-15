r"""
Isolated Batch YOLO Inference Module on Genuine RDD2022 Dataset.
Loads production checkpoint D:\Paventra\ml\weights\rdd2022_yolov8n.pt strictly READ-ONLY.
Executes inference on a representative batch of real road damage images.
Saves detection records as CSV & Parquet, and saves annotated visual previews.
"""
import os
import sys
import time
import json
import csv
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import torch

# Add experiment directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings

from ultralytics import YOLO


def run_yolo_batch_inference(sample_size=300):
    print("=" * 70)
    print("STARTING READ-ONLY YOLO BATCH INFERENCE ON RDD2022 IMAGES")
    print("=" * 70)
    
    t_start = time.perf_counter()
    
    # 1. Verify Checkpoint Baseline
    if not settings.YOLO_CHECKPOINT.exists():
        raise FileNotFoundError(f"Checkpoint not found at: {settings.YOLO_CHECKPOINT}")
        
    print(f"Loading YOLO model strictly READ-ONLY from: {settings.YOLO_CHECKPOINT}")
    model = YOLO(str(settings.YOLO_CHECKPOINT))
    model.eval()  # Set model to evaluation mode
    
    # Class mapping from model
    names_map = model.names
    print(f"Loaded YOLO Model classes: {names_map}")
    
    # 2. Select Representative Real Images
    train_images = sorted(list(settings.TRAIN_IMAGES_DIR.glob("*.jpg")))
    test_images = sorted(list(settings.TEST_IMAGES_DIR.glob("*.jpg")))
    
    # Mix: 200 from train (contains ground-truth damages), 100 from test (unlabelled real roads)
    train_sample_n = min(200, len(train_images))
    test_sample_n = min(100, len(test_images))
    selected_images = train_images[:train_sample_n] + test_images[:test_sample_n]
    
    total_images = len(selected_images)
    print(f"Processing representative batch of {total_images} real images ({train_sample_n} train, {test_sample_n} test)...")
    
    # Prepare preview directory
    settings.ANNOTATED_PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    
    detection_rows = []
    per_image_timings = []
    total_detections_count = 0
    images_with_detections = 0
    images_without_detections = 0
    saved_previews_count = 0
    
    # 3. Incremental Batch Inference
    for idx, img_path in enumerate(selected_images):
        img_id = img_path.stem
        t0 = time.perf_counter()
        
        # Inference mode: no gradient calculation, no optimizer, no training
        with torch.no_grad():
            results = model.predict(
                source=str(img_path),
                conf=0.20,
                device="cpu",
                verbose=False
            )
            
        inf_ms = round((time.perf_counter() - t0) * 1000, 2)
        per_image_timings.append(inf_ms)
        
        boxes = results[0].boxes if results and results[0].boxes is not None else []
        det_count = len(boxes)
        
        if det_count > 0:
            images_with_detections += 1
            total_detections_count += det_count
            
            # Save up to 10 annotated preview images
            if saved_previews_count < 10:
                annotated_img = results[0].plot()  # BGR numpy array
                from PIL import Image as PILImg
                preview_save_path = settings.ANNOTATED_PREVIEWS_DIR / f"annotated_{img_id}.jpg"
                # Convert BGR to RGB
                rgb_img = annotated_img[:, :, ::-1]
                PILImg.fromarray(rgb_img).save(preview_save_path)
                saved_previews_count += 1
                
            for box in boxes:
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                xyxy = box.xyxy[0].tolist()
                cls_name = names_map.get(cls_id, f"Class_{cls_id}")
                
                detection_rows.append({
                    "image_id": img_id,
                    "image_path": str(img_path),
                    "predicted_class": cls_name,
                    "class_id": cls_id,
                    "confidence": round(conf, 4),
                    "xmin": round(xyxy[0], 2),
                    "ymin": round(xyxy[1], 2),
                    "xmax": round(xyxy[2], 2),
                    "ymax": round(xyxy[3], 2),
                    "bbox_width": round(xyxy[2] - xyxy[0], 2),
                    "bbox_height": round(xyxy[3] - xyxy[1], 2),
                    "bbox_area": round((xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1]), 2),
                    "detection_count": det_count,
                    "inference_time_ms": inf_ms,
                    "processing_status": "SUCCESS_DETECTED",
                })
        else:
            images_without_detections += 1
            detection_rows.append({
                "image_id": img_id,
                "image_path": str(img_path),
                "predicted_class": "NO_DETECTION",
                "class_id": -1,
                "confidence": 0.0,
                "xmin": 0.0,
                "ymin": 0.0,
                "xmax": 0.0,
                "ymax": 0.0,
                "bbox_width": 0.0,
                "bbox_height": 0.0,
                "bbox_area": 0.0,
                "detection_count": 0,
                "inference_time_ms": inf_ms,
                "processing_status": "SUCCESS_ZERO_DETECTIONS",
            })
            
        if (idx + 1) % 50 == 0 or (idx + 1) == total_images:
            avg_so_far = round(sum(per_image_timings) / len(per_image_timings), 2)
            print(f"Processed [{idx+1}/{total_images}] images | Current Avg Latency: {avg_so_far} ms/image")
            
    total_batch_time = round(time.perf_counter() - t_start, 3)
    avg_inference_ms = round(sum(per_image_timings) / len(per_image_timings), 2)
    throughput_fps = round(total_images / max(total_batch_time, 0.001), 2)
    
    print("\n--- INFERENCE SUMMARY ---")
    print(f"Total Images Processed:       {total_images}")
    print(f"Images with Detections:       {images_with_detections} ({round(images_with_detections/total_images*100, 2)}%)")
    print(f"Images without Detections:    {images_without_detections} ({round(images_without_detections/total_images*100, 2)}%)")
    print(f"Total Defects Detected:       {total_detections_count}")
    print(f"Average Inference Latency:    {avg_inference_ms} ms/image")
    print(f"Throughput:                   {throughput_fps} images/second")
    print(f"Total Batch Processing Time:  {total_batch_time} seconds")
    print(f"Saved {saved_previews_count} annotated preview images to: {settings.ANNOTATED_PREVIEWS_DIR}")
    
    # 4. Save Detection Records to CSV & Parquet
    df_detections = pd.DataFrame(detection_rows)
    df_detections.to_csv(settings.YOLO_DETECTIONS_CSV, index=False)
    print(f"Saved detection records CSV to: {settings.YOLO_DETECTIONS_CSV}")
    
    df_detections.to_parquet(settings.YOLO_DETECTIONS_PARQUET, index=False)
    print(f"Saved detection records Parquet to: {settings.YOLO_DETECTIONS_PARQUET}")
    
    # 5. Class Breakdown of Predictions
    detected_df = df_detections[df_detections["predicted_class"] != "NO_DETECTION"]
    class_counts = detected_df["predicted_class"].value_counts().to_dict()
    avg_conf_by_class = detected_df.groupby("predicted_class")["confidence"].mean().round(4).to_dict()
    
    summary_data = {
        "model_path": str(settings.YOLO_CHECKPOINT),
        "device": "cpu",
        "batch_size_images": total_images,
        "images_with_detections": images_with_detections,
        "images_without_detections": images_without_detections,
        "total_detections": total_detections_count,
        "average_inference_ms": avg_inference_ms,
        "throughput_images_per_second": throughput_fps,
        "total_batch_time_seconds": total_batch_time,
        "classes_detected_count": class_counts,
        "average_confidence_by_class": avg_conf_by_class,
        "annotated_previews_saved": saved_previews_count,
    }
    
    # Generate YOLO_INFERENCE_REPORT.md
    gen_yolo_report(summary_data, class_counts, avg_conf_by_class)
    return summary_data


def gen_yolo_report(summary, class_counts, avg_conf):
    """Generate Markdown report for YOLO batch inference."""
    class_rows = "\n".join([
        f"| **{cls_name}** | {count:,} | {round(avg_conf.get(cls_name, 0.0) * 100, 2)}% |"
        for cls_name, count in class_counts.items()
    ])
    
    report_md = f"""# Read-Only YOLOv8n Batch Inference Report

**Deployed Checkpoint:** `{settings.YOLO_CHECKPOINT}`  
**Execution Mode:** Strictly Read-Only Inference (`torch.no_grad()`, `model.eval()`, zero weight updates)  
**Hardware Accelerator:** CPU (Intel/AMD x86_64)  
**Confidence Threshold:** `0.20`  
**Total Images Processed:** {summary['batch_size_images']:,} real road images  
**Images with Detected Defects:** {summary['images_with_detections']:,} ({round(summary['images_with_detections'] / summary['batch_size_images'] * 100, 2)}%)  
**Images without Detections:** {summary['images_without_detections']:,} ({round(summary['images_without_detections'] / summary['batch_size_images'] * 100, 2)}%)  
**Total Defect Objects Detected:** {summary['total_detections']:,}  
**Average Inference Latency:** {summary['average_inference_ms']} ms/image  
**Batch Throughput:** **{summary['throughput_images_per_second']} images/sec**  
**Total Batch Execution Time:** {summary['total_batch_time_seconds']} seconds  

---

## 1. Defect Category Distribution & Model Confidence

| Detected Class | Defect Count | Mean Model Confidence |
|---|---|---|
{class_rows}

---

## 2. Model Architecture & Deployment Protection

- **Model Type:** Ultralytics YOLOv8 Nano (`yolov8n`)
- **Classes Configured in Checkpoint:** `0: longitudinal_crack`, `1: transverse_crack`, `2: alligator_crack`, `3: pothole`
- **Integrity Guarantee:** Checkpoint weights were loaded directly from disk without modification, retraining, or fine-tuning.
- **Output Formats:**
  - Structured CSV: `{settings.YOLO_DETECTIONS_CSV}` ({summary['total_detections'] + summary['images_without_detections']} rows)
  - Columnar Parquet: `{settings.YOLO_DETECTIONS_PARQUET}`
  - Visual Detections: `{settings.ANNOTATED_PREVIEWS_DIR}` ({summary['annotated_previews_saved']} annotated images)
"""
    with open(settings.REPORTS_DIR / "YOLO_INFERENCE_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"Generated YOLO_INFERENCE_REPORT.md at: {settings.REPORTS_DIR / 'YOLO_INFERENCE_REPORT.md'}")


if __name__ == "__main__":
    run_yolo_batch_inference()
