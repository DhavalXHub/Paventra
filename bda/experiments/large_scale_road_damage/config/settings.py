r"""
Centralized Configuration for Large Scale Road Damage Big Data Analytics Experiment.
Isolated in D:\Paventra\bda\experiments\large_scale_road_damage.
"""
from pathlib import Path
import os
import sys

# Base directories
EXPERIMENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = EXPERIMENT_DIR.parent.parent.parent

# Big Data tools
JAVA_HOME = PROJECT_ROOT / "bda" / "tools" / "jdk17" / "jdk-17.0.20.1+1"
HADOOP_HOME = PROJECT_ROOT / "bda" / "tools" / "hadoop"

# Python executable (use 8.3 short path if available to prevent space issues in Spark worker)
SHORT_PYTHON = "C:/PROGRA~1/Python312/python.exe"
PYTHON_EXE = SHORT_PYTHON if os.path.exists(SHORT_PYTHON) else sys.executable

# Ensure Spark / Java environment variables are set
os.environ["JAVA_HOME"] = str(JAVA_HOME)
os.environ["HADOOP_HOME"] = str(HADOOP_HOME)
os.environ["PYSPARK_PYTHON"] = PYTHON_EXE
os.environ["PYSPARK_DRIVER_PYTHON"] = PYTHON_EXE

# Path augmentation
java_bin = str(JAVA_HOME / "bin")
hadoop_bin = str(HADOOP_HOME / "bin")
current_path = os.environ.get("PATH", "")
if java_bin not in current_path:
    os.environ["PATH"] = f"{java_bin};{hadoop_bin};{current_path}"

# Raw Dataset paths
DATASET_BASE = PROJECT_ROOT / "bda" / "dataset" / "raw"
DATASET_ZIP = DATASET_BASE / "RDD2022_released_through_CRDDC2022.zip"
INDIA_DIR = DATASET_BASE / "India"
TRAIN_IMAGES_DIR = INDIA_DIR / "train" / "images"
TRAIN_XMLS_DIR = INDIA_DIR / "train" / "annotations" / "xmls"
TEST_IMAGES_DIR = INDIA_DIR / "test" / "images"

# YOLO Model Checkpoint (READ-ONLY)
YOLO_CHECKPOINT = PROJECT_ROOT / "ml" / "weights" / "rdd2022_yolov8n.pt"
YOLO_BASELINE_SHA256 = "d1c3536d8e4a873b7ff251d1cb81c0047100f06c86f92e08596de2d618618a3e"

# Experiment Outputs & Reports
OUTPUTS_DIR = EXPERIMENT_DIR / "outputs"
REPORTS_DIR = EXPERIMENT_DIR / "reports"
LOGS_DIR = EXPERIMENT_DIR / "logs"

# Output Parquet & Data Paths
IMAGE_METADATA_PARQUET = OUTPUTS_DIR / "image_metadata.parquet"
DAMAGE_ANNOTATIONS_PARQUET = OUTPUTS_DIR / "damage_annotations.parquet"
PROCESSING_SUMMARY_JSON = OUTPUTS_DIR / "processing_summary.json"
DATASET_SUMMARY_JSON = OUTPUTS_DIR / "dataset_summary.json"

MLLIB_MODEL_DIR = OUTPUTS_DIR / "mllib_rf_model"
MLLIB_EVALUATION_JSON = OUTPUTS_DIR / "mllib_evaluation.json"
CONFUSION_MATRIX_CSV = OUTPUTS_DIR / "confusion_matrix.csv"

YOLO_DETECTIONS_PARQUET = OUTPUTS_DIR / "yolo_detections.parquet"
YOLO_DETECTIONS_CSV = OUTPUTS_DIR / "yolo_detections.csv"
ANNOTATED_PREVIEWS_DIR = OUTPUTS_DIR / "annotated_previews"

SPARK_ANALYTICS_JSON = OUTPUTS_DIR / "spark_analytics.json"
BENCHMARK_RESULTS_JSON = OUTPUTS_DIR / "benchmark_results.json"

# RDD2022 Official Class Taxonomy
RDD_CLASSES = {
    "D00": "Longitudinal Crack",
    "D10": "Transverse Crack",
    "D20": "Alligator Crack",
    "D40": "Pothole",
}
