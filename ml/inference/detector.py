"""
Paventra Road Damage Inference Detector.
Encapsulates Ultralytics YOLOv8 inference for Road Damage Detection (RDD).

Supported Classes (standard RDD2022 taxonomy):
  0: D00 - longitudinal_crack (crack)
  1: D10 - transverse_crack (crack)
  2: D20 - alligator_crack (crack)
  3: D40 - pothole (pothole)
"""
import os
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

import cv2
import numpy as np

from ml.inference.severity import estimate_damage_severity, SeverityAssessment

logger = logging.getLogger(__name__)

# Standard RDD2022 class mapping
RDD_CLASS_MAP: Dict[int, tuple[str, str, str]] = {
    0: ("D00", "longitudinal_crack", "crack"),
    1: ("D10", "transverse_crack", "crack"),
    2: ("D20", "alligator_crack", "crack"),
    3: ("D40", "pothole", "pothole"),
}


@dataclass
class Detection:
    class_id: int
    class_code: str
    damage_category: str
    damage_type: str
    confidence: float
    bbox_xyxy: List[float]  # normalized [x1, y1, x2, y2]


@dataclass
class InferenceResult:
    detections: List[Detection] = field(default_factory=list)
    inference_ms: float = 0.0
    model_available: bool = True
    error: Optional[str] = None
    annotated_image: Optional[np.ndarray] = None
    image_width: int = 0
    image_height: int = 0
    severity_assessment: Optional[SeverityAssessment] = None

    @property
    def best_detection(self) -> Optional[Detection]:
        if not self.detections:
            return None
        return max(self.detections, key=lambda d: d.confidence)

    @property
    def primary_damage_type(self) -> str:
        bd = self.best_detection
        return bd.damage_type if bd else "unknown"

    @property
    def max_confidence(self) -> Optional[float]:
        bd = self.best_detection
        return bd.confidence if bd else None


class RoadDamageInferenceEngine:
    """Loads YOLO road damage weights and performs structured inference."""

    def __init__(self, weights_path: Optional[str] = None, device: str = "cpu", conf_threshold: float = 0.35):
        self.weights_path = weights_path
        self.device = device
        self.conf_threshold = conf_threshold
        self._model = None
        self._load_attempted = False
        self._load_error: Optional[str] = None

    def _find_weights(self) -> Optional[str]:
        if self.weights_path and os.path.exists(self.weights_path):
            return self.weights_path

        # Candidate paths to locate weights
        candidates = [
            Path(__file__).resolve().parent.parent / "weights" / "rdd2022_yolov8n.pt",
            Path("d:/Paventra/ml/weights/rdd2022_yolov8n.pt"),
            Path("ml/weights/rdd2022_yolov8n.pt"),
            Path("../ml/weights/rdd2022_yolov8n.pt"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)

        try:
            from ml.weights.download_weights import download_rdd_weights
            downloaded = download_rdd_weights()
            if downloaded and os.path.exists(downloaded):
                return downloaded
        except Exception as e:
            logger.warning(f"Could not automatically download weights: {e}")
        return None

    def load_model(self) -> bool:
        if self._load_attempted:
            return self._model is not None
        self._load_attempted = True

        weights_file = self._find_weights()
        if not weights_file:
            self._load_error = "Model weights not found. Please provide valid RDD YOLO weights (.pt)."
            logger.warning(self._load_error)
            return False

        try:
            from ultralytics import YOLO
            logger.info(f"Loading Road Damage YOLO model from: {weights_file} (device: {self.device})")
            self._model = YOLO(weights_file)
            logger.info("Road damage model loaded successfully")
            return True
        except Exception as e:
            self._load_error = f"Failed to load YOLO weights ({weights_file}): {e}"
            logger.error(self._load_error)
            return False

    def is_available(self) -> bool:
        if not self._load_attempted:
            self.load_model()
        return self._model is not None

    def infer(self, image_path: str, save_annotated: bool = True) -> InferenceResult:
        """Runs road distress inference on an input image file."""
        if not self.is_available():
            return InferenceResult(
                model_available=False,
                error=self._load_error or "Model weights unavailable.",
            )

        if not os.path.exists(image_path):
            return InferenceResult(model_available=True, error=f"File not found: {image_path}")

        try:
            img = cv2.imread(image_path)
            if img is None:
                return InferenceResult(
                    model_available=True,
                    error=f"Unsupported format or corrupt image file: {image_path}"
                )
            h, w = img.shape[:2]
            if h < 10 or w < 10:
                return InferenceResult(
                    model_available=True,
                    error=f"Image dimensions too small ({w}x{h}) for CV inference."
                )

            t0 = time.perf_counter()
            results = self._model(
                image_path,
                conf=self.conf_threshold,
                device=self.device,
                verbose=False,
            )
            inference_ms = round((time.perf_counter() - t0) * 1000, 2)

            detections: List[Detection] = []
            dict_detections: List[Dict[str, Any]] = []

            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    cls_id = int(box.cls.item())
                    conf = float(box.conf.item())
                    xyxy = box.xyxy[0].tolist()
                    code, category, dtype = RDD_CLASS_MAP.get(
                        cls_id, (f"D{cls_id:02d}", "unknown_defect", "other")
                    )
                    normalized_bbox = [
                        round(xyxy[0] / w, 4),
                        round(xyxy[1] / h, 4),
                        round(xyxy[2] / w, 4),
                        round(xyxy[3] / h, 4),
                    ]
                    det = Detection(
                        class_id=cls_id,
                        class_code=code,
                        damage_category=category,
                        damage_type=dtype,
                        confidence=round(conf, 4),
                        bbox_xyxy=normalized_bbox,
                    )
                    detections.append(det)
                    dict_detections.append({
                        "class_code": code,
                        "damage_type": dtype,
                        "confidence": round(conf, 4),
                        "bbox": normalized_bbox,
                    })

            # Severity estimation based on measurable 2D geometric features
            severity = estimate_damage_severity(dict_detections, image_width=w, image_height=h)

            annotated = None
            if save_annotated and results:
                try:
                    annotated = results[0].plot()
                except Exception:
                    annotated = None

            return InferenceResult(
                detections=detections,
                inference_ms=inference_ms,
                model_available=True,
                annotated_image=annotated,
                image_width=w,
                image_height=h,
                severity_assessment=severity,
            )

        except Exception as exc:
            logger.exception(f"Inference execution failed on {image_path}: {exc}")
            return InferenceResult(model_available=True, error=str(exc))
