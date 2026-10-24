"""
Paventra Machine Learning Inference Package.
"""
from ml.inference.detector import RoadDamageInferenceEngine, InferenceResult, Detection
from ml.inference.severity import estimate_damage_severity, SeverityAssessment

__all__ = [
    "RoadDamageInferenceEngine",
    "InferenceResult",
    "Detection",
    "estimate_damage_severity",
    "SeverityAssessment",
]
