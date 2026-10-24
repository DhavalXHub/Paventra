"""
Computer vision inference service using YOLOv8 for road damage detection.

Supported damage categories (standard RDD2022 taxonomy):
  Class 0 - Longitudinal Crack (D00)
  Class 1 - Transverse Crack (D10)
  Class 2 - Alligator Crack (D20)
  Class 3 - Pothole (D40)

Features:
  - Real inference using pre-trained RDD2022 YOLOv8 weights when configured.
  - Transparent fallback when model weights are not configured.
  - Explainable 2D geometric severity estimation (area ratio, elongation, distress hazard).
  - Production image validation (dimensions, formats, corrupt file guards).
"""
import sys
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

import cv2
import numpy as np

# Ensure root workspace is in sys.path so ml.inference can be imported
workspace_root = str(Path(__file__).resolve().parent.parent.parent.parent.parent)
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from app.core.config import settings

try:
    from ml.inference.detector import RoadDamageInferenceEngine, Detection, InferenceResult
    from ml.inference.severity import SeverityAssessment, estimate_damage_severity
    ML_MODULE_AVAILABLE = True
except Exception as e:
    ML_MODULE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import ml.inference: {e}")

logger = logging.getLogger(__name__)

DAMAGE_CLASS_MAP: dict[int, tuple[str, str, str]] = {
    0: ("D00", "longitudinal_crack", "crack"),
    1: ("D10", "transverse_crack", "crack"),
    2: ("D20", "alligator_crack", "crack"),
    3: ("D40", "pothole", "pothole"),
}


if not ML_MODULE_AVAILABLE:
    @dataclass
    class Detection:
        class_id: int
        class_code: str
        damage_category: str
        damage_type: str
        confidence: float
        bbox_xyxy: list[float]  # normalized [x1,y1,x2,y2]

    @dataclass
    class SeverityAssessment:
        level: str
        score: float
        method: str
        features: dict
        confidence: float
        uncertainty: float
        review_required: bool
        provisional: bool = True
        disclaimer: str = ""

    @dataclass
    class InferenceResult:
        detections: list[Detection] = field(default_factory=list)
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


class RoadDamageDetector:
    """Singleton road damage detector. Delegates to RoadDamageInferenceEngine."""

    _instance: Optional["RoadDamageDetector"] = None
    _engine: Optional[Any] = None

    def __new__(cls) -> "RoadDamageDetector":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._engine = None
        return cls._instance

    def _get_engine(self):
        if self._engine is None and ML_MODULE_AVAILABLE:
            weights = settings.MODEL_WEIGHTS_PATH or None
            device = settings.MODEL_DEVICE or "cpu"
            conf = settings.MODEL_CONFIDENCE_THRESHOLD or 0.35
            self._engine = RoadDamageInferenceEngine(
                weights_path=weights, device=device, conf_threshold=conf
            )
        return self._engine

    def is_available(self) -> bool:
        if not settings.MODEL_ENABLED:
            return False
        eng = self._get_engine()
        return eng.is_available() if eng else False

    def infer(self, image_path: str, save_annotated: bool = True) -> InferenceResult:
        if not settings.MODEL_ENABLED:
            return InferenceResult(
                model_available=False,
                error="Model disabled via MODEL_ENABLED=false. Configure MODEL_ENABLED=true and weights.",
            )

        eng = self._get_engine()
        if not eng or not eng.is_available():
            err_msg = eng._load_error if eng else "ML inference engine unavailable."
            return InferenceResult(
                model_available=False,
                error=err_msg,
            )

        return eng.infer(image_path, save_annotated=save_annotated)


def save_annotated_image(annotated: np.ndarray, output_dir: Path, prefix: str = "ann") -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
    output_path = output_dir / filename
    cv2.imwrite(str(output_path), annotated)
    return str(output_path)


detector = RoadDamageDetector()
