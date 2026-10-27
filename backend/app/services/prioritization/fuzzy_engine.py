"""
Fuzzy Priority Inference Engine for Road Damage Reports.

Academic Foundation:
  Mamdani-type Fuzzy Inference System (FIS) utilizing:
    - Min-Max composition (Mamdani implication)
    - Triangular membership functions for linguistic modeling of uncertainty
    - Centroid Defuzzification (Center of Gravity / COG)
    - 22-Rule complete rule base covering all boundary combinations

Inputs (Universes of Discourse):
  - severity:              [0.0, 10.0]  (estimated damage severity)
  - traffic_exposure:      [0.0, 10.0]  (traffic volume / highway classification)
  - time_unresolved_days:  [0.0, 365.0] (days since report submitted)
  - safety_urgency:        [0.0, 10.0]  (immediate pedestrian / two-wheeler hazard)

Output:
  - priority_score:        [0.0, 100.0] (repair priority recommendation)

Tiers:
  - LOW:         0  - 25
  - MEDIUM:      25 - 50
  - MEDIUM_HIGH: 50 - 70
  - HIGH:        70 - 85
  - CRITICAL:    85 - 100
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
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
    severity: Optional[float] = 5.0
    traffic_exposure: Optional[float] = 5.0
    time_unresolved_days: Optional[float] = 0.0
    safety_urgency: Optional[float] = 5.0

    def __post_init__(self) -> None:
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
    """Result of the fuzzy inference computation with academic explainability."""
    priority_score: float
    priority_label: str
    top_contributing_factors: List[Dict[str, Any]]
    baseline_score: float
    engine_used: str
    inputs: Dict[str, float]
    membership_activations: Optional[Dict[str, Dict[str, float]]] = None
    fired_rules: Optional[List[Dict[str, Any]]] = None
    explanation_narrative: Optional[str] = None


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
    """Simple weighted linear formula for comparative academic benchmarking."""
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


def _calculate_tri_membership(x: float, a: float, b: float, c: float) -> float:
    """Evaluates triangular membership function at point x, supporting shoulder extensions."""
    if a == b and x <= a:
        return 1.0
    if b == c and x >= c:
        return 1.0
    if x <= a or x >= c:
        return 0.0
    if a < x <= b:
        return (x - a) / (b - a) if b != a else 1.0
    if b < x < c:
        return (c - x) / (c - b) if c != b else 1.0
    return 0.0


def evaluate_all_memberships(inputs: FuzzyInputs) -> Dict[str, Dict[str, float]]:
    """Evaluates exact membership degrees for all linguistic terms."""
    s = inputs.severity
    t = inputs.traffic_exposure
    d = inputs.time_unresolved_days
    u = inputs.safety_urgency

    return {
        "severity": {
            "low": round(_calculate_tri_membership(s, 0.0, 0.0, 4.0), 3),
            "moderate": round(_calculate_tri_membership(s, 2.0, 5.0, 8.0), 3),
            "high": round(_calculate_tri_membership(s, 6.0, 8.0, 10.0), 3),
            "critical": round(_calculate_tri_membership(s, 8.5, 10.0, 10.0), 3),
        },
        "traffic": {
            "low": round(_calculate_tri_membership(t, 0.0, 0.0, 4.0), 3),
            "medium": round(_calculate_tri_membership(t, 2.0, 5.0, 8.0), 3),
            "high": round(_calculate_tri_membership(t, 6.0, 10.0, 10.0), 3),
        },
        "time_days": {
            "short": round(_calculate_tri_membership(d, 0.0, 0.0, 30.0), 3),
            "medium": round(_calculate_tri_membership(d, 14.0, 60.0, 120.0), 3),
            "long": round(_calculate_tri_membership(d, 60.0, 120.0, 200.0), 3),
            "very_long": round(_calculate_tri_membership(d, 150.0, 365.0, 365.0), 3),
        },
        "safety": {
            "low": round(_calculate_tri_membership(u, 0.0, 0.0, 4.0), 3),
            "medium": round(_calculate_tri_membership(u, 2.0, 5.0, 8.0), 3),
            "high": round(_calculate_tri_membership(u, 6.0, 10.0, 10.0), 3),
        },
    }


def _contributing_factors(inputs: FuzzyInputs, score: float) -> List[Dict[str, Any]]:
    factors = []
    if inputs.severity >= 8.5:
        factors.append({"factor": "Critical damage extent", "weight": "strong", "value": inputs.severity})
    elif inputs.severity >= 6.5:
        factors.append({"factor": "High damage severity", "weight": "strong", "value": inputs.severity})
    elif inputs.severity >= 4.5:
        factors.append({"factor": "Moderate damage severity", "weight": "medium", "value": inputs.severity})

    if inputs.safety_urgency >= 7.5:
        factors.append({"factor": "High safety / pedestrian hazard", "weight": "strong", "value": inputs.safety_urgency})

    if inputs.traffic_exposure >= 7.0:
        factors.append({"factor": "Heavy traffic exposure", "weight": "medium", "value": inputs.traffic_exposure})

    if inputs.time_unresolved_days >= 90:
        factors.append({"factor": f"Unresolved for {int(inputs.time_unresolved_days)} days", "weight": "medium", "value": inputs.time_unresolved_days})
    elif inputs.time_unresolved_days >= 30:
        factors.append({"factor": f"Pending for {int(inputs.time_unresolved_days)} days", "weight": "low", "value": inputs.time_unresolved_days})

    return factors[:4]


def _generate_narrative(inputs: FuzzyInputs, fuzzy_score: float, baseline_score: float) -> str:
    """Generates an academic explainability narrative explaining the soft computing advantage."""
    delta = fuzzy_score - baseline_score
    label = _priority_label(fuzzy_score)

    narrative = f"The Mamdani Fuzzy Inference System assigned a priority score of {fuzzy_score:.1f}/100 ({label}). "

    if delta > 10.0:
        narrative += (
            f"The fuzzy score is significantly higher than the linear baseline ({baseline_score:.1f}/100, +{delta:.1f} pts) "
            "because the non-linear fuzzy rule base escalated priority due to compounding risk factors "
            "(e.g., severe localized hazard or prolonged unaddressed exposure) that linear weighted sums dilute."
        )
    elif delta < -10.0:
        narrative += (
            f"The fuzzy score is lower than the linear baseline ({baseline_score:.1f}/100, {delta:.1f} pts) "
            "because the fuzzy inference system safely subdued priority for low-severity distress despite moderate traffic, "
            "preventing premature crew dispatch for minor non-structural cosmetic wear."
        )
    else:
        narrative += (
            f"The fuzzy assessment closely correlates with the linear baseline ({baseline_score:.1f}/100) "
            "reflecting balanced, moderate road distress under standard municipal operating conditions."
        )

    return narrative


class FuzzyPriorityEngine:
    """Singleton Mamdani fuzzy priority inference engine."""

    _instance: Optional["FuzzyPriorityEngine"] = None
    _control_system: Any = None
    _initialized: bool = False

    def __new__(cls) -> "FuzzyPriorityEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _build_system(self) -> None:
        """Constructs the 22-rule Mamdani fuzzy control system using scikit-fuzzy."""
        x_sev = np.arange(0, 10.1, 0.1)
        x_traf = np.arange(0, 10.1, 0.1)
        x_time = np.arange(0, 365.1, 1.0)
        x_safety = np.arange(0, 10.1, 0.1)
        x_priority = np.arange(0, 100.1, 0.5)

        severity = ctrl.Antecedent(x_sev, "severity")
        traffic = ctrl.Antecedent(x_traf, "traffic")
        time_days = ctrl.Antecedent(x_time, "time_days")
        safety = ctrl.Antecedent(x_safety, "safety")
        priority = ctrl.Consequent(x_priority, "priority")

        # Membership functions
        severity["low"] = fuzz.trimf(x_sev, [0, 0, 4])
        severity["moderate"] = fuzz.trimf(x_sev, [2, 5, 8])
        severity["high"] = fuzz.trimf(x_sev, [6, 8, 10])
        severity["critical"] = fuzz.trimf(x_sev, [8.5, 10, 10])

        traffic["low"] = fuzz.trimf(x_traf, [0, 0, 4])
        traffic["medium"] = fuzz.trimf(x_traf, [2, 5, 8])
        traffic["high"] = fuzz.trimf(x_traf, [6, 10, 10])

        time_days["short"] = fuzz.trimf(x_time, [0, 0, 30])
        time_days["medium"] = fuzz.trimf(x_time, [14, 60, 120])
        time_days["long"] = fuzz.trimf(x_time, [60, 120, 200])
        time_days["very_long"] = fuzz.trimf(x_time, [150, 365, 365])

        safety["low"] = fuzz.trimf(x_safety, [0, 0, 4])
        safety["medium"] = fuzz.trimf(x_safety, [2, 5, 8])
        safety["high"] = fuzz.trimf(x_safety, [6, 10, 10])

        priority["low"] = fuzz.trimf(x_priority, [0, 0, 30])
        priority["medium"] = fuzz.trimf(x_priority, [20, 37, 55])
        priority["medium_high"] = fuzz.trimf(x_priority, [45, 60, 75])
        priority["high"] = fuzz.trimf(x_priority, [65, 78, 90])
        priority["critical"] = fuzz.trimf(x_priority, [85, 100, 100])

        rules = [
            # Critical Hazards
            ctrl.Rule(severity["critical"] & safety["high"], priority["critical"]),
            ctrl.Rule(severity["critical"] & safety["medium"], priority["critical"]),
            ctrl.Rule(severity["critical"] & safety["low"], priority["high"]),
            ctrl.Rule(severity["high"] & safety["high"], priority["critical"]),

            # High Priority Conditions
            ctrl.Rule(severity["high"] & traffic["high"], priority["high"]),
            ctrl.Rule(severity["high"] & traffic["medium"], priority["high"]),
            ctrl.Rule(severity["high"] & traffic["low"], priority["medium_high"]),
            ctrl.Rule(severity["moderate"] & safety["high"], priority["high"]),
            ctrl.Rule(severity["moderate"] & time_days["very_long"], priority["high"]),
            ctrl.Rule(severity["moderate"] & time_days["long"] & traffic["high"], priority["high"]),

            # Medium-High Conditions
            ctrl.Rule(traffic["high"] & severity["moderate"], priority["medium_high"]),
            ctrl.Rule(severity["moderate"] & safety["medium"], priority["medium_high"]),
            ctrl.Rule(severity["low"] & safety["high"], priority["medium_high"]),

            # Medium Conditions
            ctrl.Rule(severity["moderate"] & traffic["medium"], priority["medium"]),
            ctrl.Rule(severity["moderate"] & traffic["low"], priority["medium"]),
            ctrl.Rule(severity["low"] & time_days["very_long"], priority["medium"]),
            ctrl.Rule(severity["low"] & traffic["high"] & time_days["long"], priority["medium"]),

            # Low Conditions
            ctrl.Rule(severity["low"] & safety["low"], priority["low"]),
            ctrl.Rule(severity["low"] & time_days["short"], priority["low"]),
            ctrl.Rule(severity["low"] & traffic["medium"], priority["low"]),
            ctrl.Rule(severity["low"] & traffic["low"], priority["low"]),

            # Escalation Fallbacks
            ctrl.Rule(safety["high"] & traffic["high"], priority["high"]),
            ctrl.Rule(time_days["very_long"] & traffic["high"], priority["high"]),
        ]

        self._control_system = ctrl.ControlSystem(rules)
        logger.info("Built Mamdani fuzzy priority control system with 23 complete rules.")

    def initialize(self) -> None:
        if self._initialized:
            return
        if SKFUZZY_AVAILABLE:
            try:
                self._build_system()
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to build fuzzy system: {e}")
                self._initialized = True
        else:
            self._initialized = True

    def compute(self, inputs: FuzzyInputs) -> FuzzyResult:
        """Computes the defuzzified priority score using Mamdani inference."""
        if not self._initialized:
            self.initialize()

        baseline = _baseline_score(inputs)
        raw_inputs = {
            "severity": inputs.severity,
            "traffic_exposure": inputs.traffic_exposure,
            "time_unresolved_days": inputs.time_unresolved_days,
            "safety_urgency": inputs.safety_urgency,
        }

        memberships = evaluate_all_memberships(inputs)
        score = baseline
        engine = "baseline"

        if SKFUZZY_AVAILABLE and self._control_system is not None:
            try:
                # Instantiate fresh simulation per invocation for thread safety
                sim = ctrl.ControlSystemSimulation(self._control_system)
                sim.input["severity"] = inputs.severity
                sim.input["traffic"] = inputs.traffic_exposure
                sim.input["time_days"] = inputs.time_unresolved_days
                sim.input["safety"] = inputs.safety_urgency
                sim.compute()
                score = float(np.clip(sim.output["priority"], 0.0, 100.0))
                engine = "fuzzy_mamdani"
            except Exception as e:
                logger.warning(f"Fuzzy inference failed ({e}), using baseline fallback")
                score = baseline
                engine = "baseline_fallback"

        narrative = _generate_narrative(inputs, score, baseline)

        return FuzzyResult(
            priority_score=round(score, 2),
            priority_label=_priority_label(score),
            top_contributing_factors=_contributing_factors(inputs, score),
            baseline_score=round(baseline, 2),
            engine_used=engine,
            inputs=raw_inputs,
            membership_activations=memberships,
            explanation_narrative=narrative,
        )


_engine = FuzzyPriorityEngine()


def compute_priority(
    severity_label: Optional[str] = "moderate",
    traffic_exposure: Optional[float] = 5.0,
    time_unresolved_days: Optional[float] = 0.0,
    safety_urgency: Optional[float] = 5.0,
    severity_numeric: Optional[float] = None,
) -> FuzzyResult:
    """Public API for computing repair priority."""
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
