"""Unit tests for the Fuzzy Priority Inference Engine."""
import pytest
from app.services.prioritization.fuzzy_engine import (
    compute_priority, FuzzyInputs, FuzzyPriorityEngine, _baseline_score
)


def test_fuzzy_input_clipping():
    inputs = FuzzyInputs(
        severity=15.0,           # exceeds 10
        traffic_exposure=-2.0,   # below 0
        time_unresolved_days=500.0,  # exceeds 365
        safety_urgency=8.0,
    )
    assert inputs.severity == 10.0
    assert inputs.traffic_exposure == 0.0
    assert inputs.time_unresolved_days == 365.0
    assert inputs.safety_urgency == 8.0


def test_critical_priority_rule():
    # Rule: If severity is HIGH and safety_urgency is HIGH -> CRITICAL (score >= 85)
    result = compute_priority(
        severity_label="critical",
        traffic_exposure=8.0,
        time_unresolved_days=10.0,
        safety_urgency=9.0,
        severity_numeric=9.5,
    )
    assert result.priority_score >= 80.0
    assert result.priority_label in ("HIGH", "CRITICAL")
    assert len(result.top_contributing_factors) > 0


def test_low_priority_scenario():
    # Rule: If severity is LOW and safety_urgency is LOW -> LOW
    result = compute_priority(
        severity_label="low",
        traffic_exposure=2.0,
        time_unresolved_days=2.0,
        safety_urgency=1.0,
        severity_numeric=1.5,
    )
    assert result.priority_score <= 40.0
    assert result.priority_label in ("LOW", "MEDIUM")


def test_baseline_score_calculation():
    inputs = FuzzyInputs(
        severity=5.0,
        traffic_exposure=5.0,
        time_unresolved_days=0.0,
        safety_urgency=5.0,
    )
    score = _baseline_score(inputs)
    assert 30.0 <= score <= 70.0


def test_contributing_factors_explanation():
    result = compute_priority(
        severity_label="high",
        traffic_exposure=9.0,
        time_unresolved_days=95.0,
        safety_urgency=8.5,
    )
    factor_names = [f["factor"] for f in result.top_contributing_factors]
    assert any("severity" in name.lower() for name in factor_names)
    assert any("traffic" in name.lower() for name in factor_names)


def test_missing_input_defaults():
    """Verify that None values for optional inputs are handled with safe midpoints."""
    result = compute_priority(
        severity_label=None,
        traffic_exposure=None,
        time_unresolved_days=None,
        safety_urgency=None,
    )
    assert 25.0 <= result.priority_score <= 75.0
    assert result.inputs["severity"] == 5.0
    assert result.inputs["traffic_exposure"] == 5.0
    assert result.inputs["time_unresolved_days"] == 0.0
    assert result.inputs["safety_urgency"] == 5.0


def test_time_unresolved_monotonic_increase():
    """Increasing unresolved duration (holding other factors constant) must raise or preserve priority."""
    r_day0 = compute_priority(severity_label="moderate", traffic_exposure=5.0, time_unresolved_days=0.0)
    r_day30 = compute_priority(severity_label="moderate", traffic_exposure=5.0, time_unresolved_days=30.0)
    r_day180 = compute_priority(severity_label="moderate", traffic_exposure=5.0, time_unresolved_days=180.0)

    assert r_day30.priority_score >= r_day0.priority_score
    assert r_day180.priority_score >= r_day30.priority_score
