"""
Computer vision inference service using YOLOv8 for road damage detection.

Supported damage categories (standard road damage dataset mapping):
  Class 0 - Longitudinal Crack
  Class 1 - Transverse Crack
  Class 2 - Alligator Crack
  Class 3 - Pothole

Falls back gracefully when model weights are not configured.
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

DAMAGE_CLASS_MAP: dict[int, tuple[str, str, str]] = {
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
    bbox_xyxy: list[float]  # normalized [x1,y1,x2,y2]


@dataclass
class InferenceResult:
    detections: list[Detection] = field(default_factory=list)
    inference_ms: float = 0.0
    model_available: bool = True
    error: Optional[str] = None
    annotated_image: Optional[np.ndarray] = None
    image_width: int = 0
    image_height: int = 0

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


class RoadDamageDetector:
    """Singleton road damage detector. Loads model once on first use."""

    _instance: Optional["RoadDamageDetector"] = None
    _model = None
    _model_loaded: bool = False
    _load_attempted: bool = False

    def __new__(cls) -> "RoadDamageDetector":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _try_load_model(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True

        if not settings.MODEL_ENABLED:
            logger.info("CV model disabled via MODEL_ENABLED=false")
            return

        weights = settings.MODEL_WEIGHTS_PATH or "yolov8n.pt"
        try:
            from ultralytics import YOLO  # type: ignore
            logger.info(f"Loading YOLO model: {weights}")
            self._model = YOLO(weights)
            self._model_loaded = True
            logger.info("Road damage detection model loaded successfully")
        except Exception as exc:
            logger.error(f"Model load failed: {exc}")

    def is_available(self) -> bool:
        if not self._load_attempted:
            self._try_load_model()
        return self._model_loaded

    def infer(self, image_path: str, save_annotated: bool = True) -> InferenceResult:
        if not self._load_attempted:
            self._try_load_model()
        if not self._model_loaded:
            return InferenceResult(
                model_available=False,
                error="Model not configured. Set MODEL_ENABLED=true and MODEL_WEIGHTS_PATH.",
            )
        try:
            img = cv2.imread(image_path)
            if img is None:
                return InferenceResult(model_available=True, error=f"Cannot read image: {image_path}")
            h, w = img.shape[:2]

            t0 = time.perf_counter()
            results = self._model(
                image_path,
                conf=settings.MODEL_CONFIDENCE_THRESHOLD,
                device=settings.MODEL_DEVICE,
                verbose=False,
            )
            inference_ms = (time.perf_counter() - t0) * 1000

            detections: list[Detection] = []
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                for box in boxes:
                    cls_id = int(box.cls.item())
                    conf = float(box.conf.item())
                    xyxy = box.xyxy[0].tolist()
                    code, category, dtype = DAMAGE_CLASS_MAP.get(cls_id, (f"C{cls_id}", "unknown", "other"))
                    detections.append(Detection(
                        class_id=cls_id,
                        class_code=code,
                        damage_category=category,
                        damage_type=dtype,
                        confidence=round(conf, 4),
                        bbox_xyxy=[xyxy[0]/w, xyxy[1]/h, xyxy[2]/w, xyxy[3]/h],
                    ))

            annotated = None
            if save_annotated and results:
                try:
                    annotated = results[0].plot()
                except Exception:
                    pass

            return InferenceResult(
                detections=detections,
                inference_ms=round(inference_ms, 2),
                model_available=True,
                annotated_image=annotated,
                image_width=w,
                image_height=h,
            )
        except Exception as exc:
            logger.exception(f"Inference error: {exc}")
            return InferenceResult(model_available=True, error=str(exc))


def save_annotated_image(annotated: np.ndarray, output_dir: Path, prefix: str = "ann") -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
    output_path = output_dir / filename
    cv2.imwrite(str(output_path), annotated)
    return str(output_path)


detector = RoadDamageDetector()
