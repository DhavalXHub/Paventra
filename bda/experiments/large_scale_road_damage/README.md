# Large-Scale Road Damage Big Data Analytics Experiment

**Academic Subsystem of Paventra Road Damage Intelligence Platform**  
**Location:** `D:\Paventra\bda\experiments\large_scale_road_damage\`  
**Engine:** Apache Spark 4.2.0 (`local[*]`), Spark SQL, MLlib, Ultralytics YOLOv8n  
**Dataset:** Official CRDDC 2022 (RDD2022) Multi-national Road Damage Dataset  

---

## 1. Project Overview & Objective

This isolated experiment provides an academically defensible, end-to-end Big Data Analytics (BDA) pipeline for large-scale road damage intelligence. It pairs:
1. **Big Data Processing:** Apache Spark ingestion of 9,665 real road damage images and 8,203 Pascal VOC XML annotations into partitioned Snappy Parquet tables.
2. **Supervised Machine Learning:** PySpark MLlib `RandomForestClassifier` trained on 6 continuous geometric features, outperforming majority-class baseline by **+27.27% accuracy**.
3. **Computer Vision Inference:** Ultralytics YOLOv8n batch inference on genuine road pavement captures with latency percentiles and throughput profiling.
4. **Benchmarking & Scalability:** Comprehensive empirical comparison between Python Pandas and Apache Spark SQL on identical aggregation tasks.

---

## 2. Directory Structure

```
large_scale_road_damage/
├── README.md                          # Master documentation & execution instructions
├── requirements-notes.md              # Runtime & environment dependencies
├── config/
│   └── settings.py                    # Centralized environment, paths & constants
├── preprocessing/
│   └── audit_dataset.py               # Comprehensive dataset audit & checksums
├── spark/
│   └── spark_pipeline.py              # Ingestion, schema definition & Parquet creation
├── mllib/
│   └── train_mllib_classifier.py      # MLlib RandomForest training & evaluation
├── inference/
│   └── batch_yolo_inference.py        # Read-only YOLOv8n batch inference
├── analytics/
│   └── spark_yolo_analytics.py        # Spark SQL analytics on YOLO predictions
├── experiments/
│   └── performance_benchmarks.py      # Pandas vs Spark & batch scaling benchmarks
├── tests/
│   └── test_bda_experiment.py         # 12 automated unit & integration tests
├── outputs/                           # Machine-readable Parquet, JSON, and CSVs
│   ├── dataset_summary.json
│   ├── processing_summary.json
│   ├── image_metadata.parquet/
│   ├── damage_annotations.parquet/
│   ├── mllib_evaluation.json
│   ├── confusion_matrix.csv
│   ├── mllib_rf_model/
│   ├── yolo_detections.csv
│   ├── yolo_detections.parquet
│   ├── spark_analytics.json
│   ├── benchmark_results.json
│   └── annotated_previews/            # 10 preview images with bounding boxes
└── reports/                           # Academic markdown evaluation reports
    ├── DATASET_AUDIT.md
    ├── ARCHITECTURE.md
    ├── SPARK_PIPELINE.md
    ├── MLLIB_MODEL_REPORT.md
    ├── YOLO_INFERENCE_REPORT.md
    ├── SPARK_YOLO_ANALYTICS.md
    ├── PERFORMANCE_BENCHMARK.md
    ├── TEST_REPORT.md
    ├── SYSTEM_INTEGRITY_REPORT.md
    └── EXECUTION_SUMMARY.md
```

---

## 3. Exact Reproduction Commands

Run these sequential PowerShell commands from the repository root (`D:\Paventra`):

```powershell
# 1. Audit Dataset Integrity & Structure
python bda/experiments/large_scale_road_damage/preprocessing/audit_dataset.py

# 2. Run Apache Spark Ingestion & Parquet Partitioning
python bda/experiments/large_scale_road_damage/spark/spark_pipeline.py

# 3. Train & Evaluate PySpark MLlib Classifier
python bda/experiments/large_scale_road_damage/mllib/train_mllib_classifier.py

# 4. Execute Read-Only YOLOv8 Batch Inference
python bda/experiments/large_scale_road_damage/inference/batch_yolo_inference.py

# 5. Run Spark SQL Analytics on Detection Outputs
python bda/experiments/large_scale_road_damage/analytics/spark_yolo_analytics.py

# 6. Execute Empirical Performance Benchmarks (Pandas vs Spark)
python bda/experiments/large_scale_road_damage/experiments/performance_benchmarks.py

# 7. Run Automated Regression & Integrity Tests
python -m pytest bda/experiments/large_scale_road_damage/tests/test_bda_experiment.py -v
```
