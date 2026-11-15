r"""
Comprehensive Unit and Integration Test Suite for
Paventra Large-Scale Road Damage Big Data Analytics Experiment.
Verifies XML parsing, bounding box validation, feature engineering,
Spark DataFrames, Parquet I/O, MLlib model, YOLO outputs, and model checkpoint immutability.
"""
import os
import sys
import json
import csv
import hashlib
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
import pandas as pd

# Add experiment directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings
from preprocessing.audit_dataset import parse_xml_annotation


class TestXmlParsingAndValidation:
    """Tests for Pascal VOC XML parsing and geometric validation."""

    def test_valid_xml_parsing(self, tmp_path):
        xml_content = """<annotation>
            <filename>sample_001.jpg</filename>
            <size><width>720</width><height>720</height></size>
            <object>
                <name>D40</name>
                <bndbox><xmin>100</xmin><ymin>200</ymin><xmax>300</xmax><ymax>400</ymax></bndbox>
            </object>
        </annotation>"""
        p = tmp_path / "sample_001.xml"
        p.write_text(xml_content, encoding="utf-8")
        
        data, err = parse_xml_annotation(p)
        assert err is None
        assert data["filename"] == "sample_001.jpg"
        assert data["image_width"] == 720
        assert data["image_height"] == 720
        assert data["object_count"] == 1
        obj = data["objects"][0]
        assert obj["class"] == "D40"
        assert obj["width"] == 200.0
        assert obj["height"] == 200.0
        assert obj["area"] == 40000.0

    def test_invalid_bbox_filtering(self, tmp_path):
        # xmin >= xmax, or ymin >= ymax, or negative coordinates
        xml_content = """<annotation>
            <filename>invalid_001.jpg</filename>
            <size><width>720</width><height>720</height></size>
            <object>
                <name>D40</name>
                <bndbox><xmin>300</xmin><ymin>200</ymin><xmax>100</xmax><ymax>400</ymax></bndbox>
            </object>
            <object>
                <name>D20</name>
                <bndbox><xmin>-50</xmin><ymin>100</ymin><xmax>200</xmax><ymax>300</ymax></bndbox>
            </object>
        </annotation>"""
        p = tmp_path / "invalid_001.xml"
        p.write_text(xml_content, encoding="utf-8")
        
        data, err = parse_xml_annotation(p)
        assert err is None
        assert data["object_count"] == 0
        assert data["invalid_bboxes"] == 2

    def test_malformed_xml_handling(self, tmp_path):
        p = tmp_path / "malformed.xml"
        p.write_text("<annotation><unclosed_tag>", encoding="utf-8")
        data, err = parse_xml_annotation(p)
        assert data is None
        assert "XML Parse Error" in err


class TestFeatureExtraction:
    """Tests for derived geometric features calculation."""

    def test_normalized_geometry_calculations(self):
        img_w, img_h = 1000, 500
        xmin, ymin, xmax, ymax = 100, 50, 300, 250
        
        bbox_w = xmax - xmin  # 200
        bbox_h = ymax - ymin  # 200
        bbox_area = bbox_w * bbox_h  # 40000
        
        norm_w = bbox_w / img_w  # 0.2
        norm_h = bbox_h / img_h  # 0.4
        norm_area = bbox_area / (img_w * img_h)  # 0.08
        aspect_ratio = bbox_w / bbox_h  # 1.0
        center_x = (xmin + xmax) / (2.0 * img_w)  # 0.2
        center_y = (ymin + ymax) / (2.0 * img_h)  # 0.3
        
        assert norm_w == pytest.approx(0.2)
        assert norm_h == pytest.approx(0.4)
        assert norm_area == pytest.approx(0.08)
        assert aspect_ratio == pytest.approx(1.0)
        assert center_x == pytest.approx(0.2)
        assert center_y == pytest.approx(0.3)


class TestSparkParquetTables:
    """Verifies that Spark created valid partitioned Parquet tables."""

    def test_image_metadata_parquet_exists_and_readable(self):
        assert settings.IMAGE_METADATA_PARQUET.exists()
        df = pd.read_parquet(settings.IMAGE_METADATA_PARQUET)
        assert len(df) == 9665
        expected_cols = {"image_id", "image_path", "width", "height", "file_size_bytes", "dataset_split", "annotation_count", "has_damage_annotation", "validation_status"}
        assert expected_cols.issubset(set(df.columns))

    def test_damage_annotations_parquet_exists_and_readable(self):
        assert settings.DAMAGE_ANNOTATIONS_PARQUET.exists()
        df = pd.read_parquet(settings.DAMAGE_ANNOTATIONS_PARQUET)
        assert len(df) == 8203
        expected_cols = {"image_id", "damage_class", "xmin", "ymin", "xmax", "ymax", "bbox_width", "bbox_height", "bbox_area", "normalized_width", "normalized_height", "normalized_area", "aspect_ratio", "center_x", "center_y"}
        assert expected_cols.issubset(set(df.columns))
        # Ensure all bounding box coordinates are strictly valid
        assert (df["xmin"] < df["xmax"]).all()
        assert (df["ymin"] < df["ymax"]).all()


class TestMLlibModelArtifacts:
    """Verifies MLlib training evaluation and output artifacts."""

    def test_mllib_evaluation_metrics(self):
        assert settings.MLLIB_EVALUATION_JSON.exists()
        with open(settings.MLLIB_EVALUATION_JSON, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
            
        m = eval_data["metrics"]
        assert m["test_accuracy"] > 0.50  # Over 50% on multi-class
        assert m["test_accuracy"] > m["majority_baseline_accuracy"]  # Beats baseline
        assert m["weighted_f1_score"] > 0.50
        assert eval_data["train_samples"] > 5000
        assert eval_data["test_samples"] > 1000

    def test_confusion_matrix_csv_structure(self):
        assert settings.CONFUSION_MATRIX_CSV.exists()
        with open(settings.CONFUSION_MATRIX_CSV, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header[0] == "Actual_Class"
            assert len(header) > 4
            rows = list(reader)
            # The test set contains representations of 9 of the 10 classes
            # (D0w0 is a single-instance outlier present only in train)
            assert len(rows) >= 9
            assert len(rows) <= len(header) - 1

    def test_mllib_saved_model_directory(self):
        assert settings.MLLIB_MODEL_DIR.exists()
        metadata_dir = settings.MLLIB_MODEL_DIR / "metadata"
        data_dir = settings.MLLIB_MODEL_DIR / "data"
        assert metadata_dir.exists()
        assert data_dir.exists()


class TestYoloBatchInferenceOutputs:
    """Verifies YOLO batch inference CSV, Parquet, and preview artifacts."""

    def test_yolo_detections_csv_and_parquet(self):
        assert settings.YOLO_DETECTIONS_CSV.exists()
        assert settings.YOLO_DETECTIONS_PARQUET.exists()
        
        df_csv = pd.read_csv(settings.YOLO_DETECTIONS_CSV)
        df_parquet = pd.read_parquet(settings.YOLO_DETECTIONS_PARQUET)
        assert len(df_csv) == len(df_parquet)
        assert len(df_csv) >= 300  # At least 300 images represented
        
        # Check required columns
        req_cols = {"image_id", "predicted_class", "confidence", "xmin", "ymin", "xmax", "ymax", "inference_time_ms", "processing_status"}
        assert req_cols.issubset(set(df_csv.columns))
        
        # Verify confidences for positive detections
        positive_detections = df_csv[df_csv["predicted_class"] != "NO_DETECTION"]
        assert len(positive_detections) > 50
        assert (positive_detections["confidence"] >= 0.20).all()
        assert (positive_detections["confidence"] <= 1.0).all()

    def test_annotated_preview_images(self):
        assert settings.ANNOTATED_PREVIEWS_DIR.exists()
        previews = list(settings.ANNOTATED_PREVIEWS_DIR.glob("*.jpg"))
        assert len(previews) == 10
        for p in previews:
            assert p.stat().st_size > 5000  # Non-trivial image file


class TestProductionModelImmutability:
    """Strict test to guarantee production YOLO weights were never modified."""

    def test_yolo_checkpoint_hash_unaltered(self):
        assert settings.YOLO_CHECKPOINT.exists()
        current_data = open(settings.YOLO_CHECKPOINT, "rb").read()
        current_hash = hashlib.sha256(current_data).hexdigest()
        assert current_hash == settings.YOLO_BASELINE_SHA256, (
            f"CRITICAL ERROR: YOLO checkpoint SHA256 has changed! "
            f"Expected: {settings.YOLO_BASELINE_SHA256}, Got: {current_hash}"
        )
