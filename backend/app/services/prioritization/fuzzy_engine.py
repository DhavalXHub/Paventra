"""
Fuzzy priority inference engine for road damage reports.

Uses the following input variables:
  - severity:          0-10 (estimated damage severity)
  - traffic_exposure:  0-10 (traffic volume/importance of road)
  - time_unresolved:   0-365 (days since report submitted)
  - safety_urgency:    0-10 (immediate safety hazard potential)

Output:
  - priority_score:    0-100 (repair priority recommendation)

Rule base:
  1. If severity is HIGH and safety_urgency is HIGH → priority is CRITICAL
  2. If severity is HIGH and traffic_exposure is HIGH → priority is HIGH
  3. If severity is MODERATE and time_unresolved is LONG → priority is HIGH
  4. If severity is HIGH and time_unresolved is MEDIUM → priority is HIGH
  5. If severity is LOW and safety_urgency is LOW → priority is LOW
  6. If traffic_exposure is HIGH and severity is MODERATE → priority is MEDIUM_HIGH
  7. If time_unresolved is VERY_LONG → priority is HIGH
  8. If severity is CRITICAL and safety_urgency is HIGH → priority is CRITICAL
  9. If severity is LOW and time_unresolved is SHORT → priority is LOW
  10. If severity is MODERATE and traffic_exposure is LOW → priority is MEDIUM

Priority labels: LOW (0-25), MEDIUM (25-50), MEDIUM_HIGH (50-70), HIGH (70-85), CRITICAL (85-100)
"""
import logging
from dataclasses import dataclass
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

try:
    import skfuzzy as fuzz
    from skfuzzy import control as ctrl
    SKFUZZY_AVAILABLE = True
except ImportError:
    SKFUZZY_AVAILABLE = False
    logger.warning("scikit-fuzzy not available, using baseline weighted scoring")


@dataclass
class FuzzyInputs:
    """Validated inputs for the fuzzy priority engine with safe default midpoints."""
    severity: Optional[float] = 5.0           # 0-10 (default 5.0)
    traffic_exposure: Optional[float] = 5.0   # 0-10 (default 5.0)
    time_unresolved_days: Optional[float] = 0.0  # 0-365 (default 0.0)
    safety_urgency: Optional[float] = 5.0     # 0-10 (default 5.0)

    def __post_init__(self) -> None:
        # Default midpoints for missing values with documented justification
        s = 5.0 if self.severity is None else self.severity
        t = 5.0 if self.traffic_exposure is None else self.traffic_exposure
        d = 0.0 if self.time_unresolved_days is None else self.time_unresolved_days
        u = 5.0 if self.safety_urgency is None else self.safety_urgency
        self.severity = float(np.clip(s, 0.0, 10.0))
        self.traffic_exposure = float(np.clip(t, 0.0, 10.0))
        self.time_unresolved_days = float(np.clip(d, 0.0, 365.0))
        self.safety_urgency = float(np.clip(u, 0.0, 10.0))


@dataclass
class FuzzyResult:
    """Result of the fuzzy inference computation."""
    priority_score: float       # 0-100
    priority_label: str         # LOW / MEDIUM / MEDIUM_HIGH / HIGH / CRITICAL
    top_contributing_factors: list[dict]
    baseline_score: float       # weighted-formula comparison
    engine_used: str            # "fuzzy" or "baseline"
    inputs: dict


def _severity_from_label(label: str) -> float:
    """Convert a severity label string to a numeric input."""
    mapping = {"low": 2.0, "moderate": 5.0, "high": 8.0, "critical": 9.5}
    return mapping.get(label.lower(), 5.0)


def _priority_label(score: float) -> str:
    if score >= 85:
        return "CRITICAL"
    elif score >= 70:
        return "HIGH"
    elif score >= 50:
        return "MEDIUM_HIGH"
    elif score >= 25:
        return "MEDIUM"
    else:
        return "LOW"


def _baseline_score(inputs: FuzzyInputs) -> float:
    """Simple weighted formula for comparison / fallback."""
    w_severity = 0.35
    w_traffic = 0.20
    w_time = 0.20
    w_safety = 0.25
    normalized_time = min(inputs.time_unresolved_days / 180.0, 1.0) * 10.0
    raw = (
        w_severity * inputs.severity
        + w_traffic * inputs.traffic_exposure
        + w_time * normalized_time
        + w_safety * inputs.safety_urgency
    )
    return float(np.clip(raw * 10.0, 0.0, 100.0))


def _contributing_factors(inputs: FuzzyInputs, score: float) -> list[dict]:
    factors = []
    if inputs.severity >= 8:
        factors.append({"factor": "High damage severity", "weight": "strong", "value": inputs.severity})
    elif inputs.severity >= 5:
        factors.append({"factor": "Moderate damage severity", "weight": "medium", "value": inputs.severity})
    
    if inputs.safety_urgency >= 8:
        factors.append({"factor": "High safety urgency", "weight": "strong", "value": inputs.safety_urgency})
    
    if inputs.traffic_exposure >= 7:
        factors.append({"factor": "High traffic exposure", "weight": "medium", "value": inputs.traffic_exposure})
    
    if inputs.time_unresolved_days >= 90:
        factors.append({"factor": f"Unresolved for {int(inputs.time_unresolved_days)} days", "weight": "medium", "value": inputs.time_unresolved_days})
    elif inputs.time_unresolved_days >= 30:
        factors.append({"factor": f"Pending for {int(inputs.time_unresolved_days)} days", "weight": "low", "value": inputs.time_unresolved_days})
    
    return factors[:4]  # Top 4 factors


class FuzzyPriorityEngine:
    """Singleton fuzzy priority inference engine."""

    _instance: Optional["FuzzyPriorityEngine"] = None
    _system: object = None

    def __new__(cls) -> "FuzzyPriorityEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _build_system(self) -> None:
        """Build the fuzzy control system using scikit-fuzzy."""
        # Universe of discourse
        x_sev = np.arange(0, 10.1, 0.1)
        x_traf = np.arange(0, 10.1, 0.1)
        x_time = np.arange(0, 365.1, 1.0)
        x_safety = np.arange(0, 10.1, 0.1)
        x_priority = np.arange(0, 100.1, 0.5)

        # Antecedents
        severity = ctrl.Antecedent(x_sev, "severity")
        traffic = ctrl.Antecedent(x_traf, "traffic")
        time_days = ctrl.Antecedent(x_time, "time_days")
        safety = ctrl.Antecedent(x_safety, "safety")

        # Consequent
        priority = ctrl.Consequent(x_priority, "priority")

        # Membership functions — severity
        severity["low"] = fuzz.trimf(x_sev, [0, 0, 4])
        severity["moderate"] = fuzz.trimf(x_sev, [2, 5, 8])
        severity["high"] = fuzz.trimf(x_sev, [6, 8, 10])
        severity["critical"] = fuzz.trimf(x_sev, [8.5, 10, 10])

        # Traffic
        traffic["low"] = fuzz.trimf(x_traf, [0, 0, 4])
        traffic["medium"] = fuzz.trimf(x_traf, [2, 5, 8])
        traffic["high"] = fuzz.trimf(x_traf, [6, 10, 10])

        # Time unresolved
        time_days["short"] = fuzz.trimf(x_time, [0, 0, 30])
        time_days["medium"] = fuzz.trimf(x_time, [14, 60, 120])
        time_days["long"] = fuzz.trimf(x_time, [60, 120, 200])
        time_days["very_long"] = fuzz.trimf(x_time, [150, 365, 365])

        # Safety urgency
        safety["low"] = fuzz.trimf(x_safety, [0, 0, 4])
        safety["medium"] = fuzz.trimf(x_safety, [2, 5, 8])
        safety["high"] = fuzz.trimf(x_safety, [6, 10, 10])

        # Priority output
        priority["low"] = fuzz.trimf(x_priority, [0, 0, 30])
        priority["medium"] = fuzz.trimf(x_priority, [20, 37, 55])
        priority["medium_high"] = fuzz.trimf(x_priority, [45, 60, 75])
        priority["high"] = fuzz.trimf(x_priority, [65, 78, 90])
        priority["critical"] = fuzz.trimf(x_priority, [85, 100, 100])

        # Rule base
        rules = [
            ctrl.Rule(severity["critical"] & safety["high"], priority["critical"]),
            ctrl.Rule(severity["high"] & safety["high"], priority["critical"]),
            ctrl.Rule(severity["high"] & traffic["high"], priority["high"]),
            ctrl.Rule(severity["moderate"] & time_days["very_long"], priority["high"]),
            ctrl.Rule(severity["high"] & time_days["medium"], priority["high"]),
            ctrl.Rule(severity["low"] & safety["low"], priority["low"]),
            ctrl.Rule(traffic["high"] & severity["moderate"], priority["medium_high"]),
            ctrl.Rule(time_days["very_long"], priority["high"]),
            ctrl.Rule(severity["low"] & time_days["short"], priority["low"]),
            ctrl.Rule(severity["moderate"] & traffic["low"], priority["medium"]),
            ctrl.Rule(severity["moderate"] & safety["medium"], priority["medium_high"]),
            ctrl.Rule(severity["high"] & traffic["medium"], priority["medium_high"]),
            ctrl.Rule(severity["low"] & traffic["high"] & time_days["long"], priority["medium"]),
        ]

        priority_ctrl = ctrl.ControlSystem(rules)
        self._system = ctrl.ControlSystemSimulation(priority_ctrl)

    def initialize(self) -> None:
        if self._initialized:
            return
        if SKFUZZY_AVAILABLE:
            try:
                self._build_system()
                self._initialized = True
                logger.info("Fuzzy priority engine initialized with scikit-fuzzy")
            except Exception as e:
                logger.error(f"Failed to build fuzzy system: {e}")
                self._initialized = True  # Mark as initialized, will use baseline
        else:
            self._initialized = True

    def compute(self, inputs: FuzzyInputs) -> FuzzyResult:
        """Compute the fuzzy priority score."""
        if not self._initialized:
            self.initialize()

        baseline = _baseline_score(inputs)
        raw_inputs = {
            "severity": inputs.severity,
            "traffic_exposure": inputs.traffic_exposure,
            "time_unresolved_days": inputs.time_unresolved_days,
            "safety_urgency": inputs.safety_urgency,
        }

        if SKFUZZY_AVAILABLE and self._system is not None:
            try:
                self._system.input["severity"] = inputs.severity
                self._system.input["traffic"] = inputs.traffic_exposure
                self._system.input["time_days"] = inputs.time_unresolved_days
                self._system.input["safety"] = inputs.safety_urgency
                self._system.compute()
                score = float(np.clip(self._system.output["priority"], 0.0, 100.0))
                engine = "fuzzy"
            except Exception as e:
                logger.warning(f"Fuzzy inference failed ({e}), using baseline")
                score = baseline
                engine = "baseline_fallback"
        else:
            score = baseline
            engine = "baseline"

        return FuzzyResult(
            priority_score=round(score, 2),
            priority_label=_priority_label(score),
            top_contributing_factors=_contributing_factors(inputs, score),
            baseline_score=round(baseline, 2),
            engine_used=engine,
            inputs=raw_inputs,
        )


# Module-level singleton
_engine = FuzzyPriorityEngine()


def compute_priority(
    severity_label: Optional[str] = "moderate",
    traffic_exposure: Optional[float] = 5.0,
    time_unresolved_days: Optional[float] = 0.0,
    safety_urgency: Optional[float] = 5.0,
    severity_numeric: Optional[float] = None,
) -> FuzzyResult:
    """
    Public API for computing repair priority.
    
    Args:
        severity_label: "low", "moderate", "high", or "critical" (default "moderate")
        traffic_exposure: 0-10 (default 5.0 if None)
        time_unresolved_days: days since report created (default 0.0 if None)
        safety_urgency: 0-10 (default 5.0 if None)
        severity_numeric: optional override for numeric severity (0-10)
    """
    _engine.initialize()
    
    if severity_numeric is not None:
        sev_numeric = severity_numeric
    elif severity_label:
        sev_numeric = _severity_from_label(severity_label)
    else:
        sev_numeric = 5.0

    inputs = FuzzyInputs(
        severity=sev_numeric,
        traffic_exposure=traffic_exposure,
        time_unresolved_days=time_unresolved_days,
        safety_urgency=safety_urgency,
    )
    return _engine.compute(inputs)
