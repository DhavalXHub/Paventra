"""
Independent Verification and Audit Script for Paventra Soft Computing Prioritization.
Audits the benchmark dataset, recomputes all statistical metrics, checks CSV/JSON parity,
re-runs the actual fuzzy engine, and tests theoretical guarantees and edge cases.
"""

import sys
import csv
import json
import math
from pathlib import Path
import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))
from app.services.prioritization.fuzzy_engine import (
    compute_priority,
    FuzzyInputs,
    _baseline_score,
    _priority_label,
    _engine,
    SKFUZZY_AVAILABLE
)

def run_audit():
    csv_path = Path("analytics/fixtures/soft_computing_maintenance_benchmark.csv")
    json_path = Path("analytics/fixtures/soft_computing_maintenance_benchmark.json")

    print("=" * 80)
    print("PAVENTRA SOFT COMPUTING BENCHMARK AUDIT & VERIFICATION")
    print("=" * 80)

    # 1. Inspect Files
    if not csv_path.exists() or not json_path.exists():
        print("ERROR: Benchmark files missing!")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        csv_records = list(csv.DictReader(f))

    with open(json_path, "r", encoding="utf-8") as f:
        json_records = json.load(f)

    print(f"CSV record count:  {len(csv_records)}")
    print(f"JSON record count: {len(json_records)}")

    # Check uniqueness
    csv_ids = [r["report_id"] for r in csv_records]
    csv_refs = [r["public_ref"] for r in csv_records]
    print(f"Unique CSV report_ids:  {len(set(csv_ids))} / {len(csv_records)}")
    print(f"Unique CSV public_refs: {len(set(csv_refs))} / {len(csv_records)}")

    # Check CSV vs JSON parity
    parity_mismatches = 0
    for i, (cr, jr) in enumerate(zip(csv_records, json_records)):
        if cr["report_id"] != jr["report_id"]:
            parity_mismatches += 1
        if float(cr["fuzzy_priority_score"]) != float(jr["fuzzy_priority_score"]):
            parity_mismatches += 1
        if float(cr["baseline_weighted_score"]) != float(jr["baseline_weighted_score"]):
            parity_mismatches += 1
    print(f"CSV vs JSON parity mismatches: {parity_mismatches}")

    # 2. Recompute scores using actual fuzzy engine on each record
    recomputed_fuzzy = []
    recomputed_baseline = []
    recompute_fuzzy_diffs = []
    recompute_base_diffs = []

    stored_fuzzy = [float(r["fuzzy_priority_score"]) for r in csv_records]
    stored_baseline = [float(r["baseline_weighted_score"]) for r in csv_records]
    stored_delta = [float(r["decision_delta"]) for r in csv_records]

    for r in csv_records:
        s = float(r["provisional_severity_score"])
        t = float(r["traffic_exposure_score"])
        d = float(r["time_unresolved_days"])
        u = float(r["safety_urgency_score"])

        res = compute_priority(
            traffic_exposure=t,
            time_unresolved_days=d,
            safety_urgency=u,
            severity_numeric=s
        )

        recomputed_fuzzy.append(res.priority_score)
        recomputed_baseline.append(res.baseline_score)

        recompute_fuzzy_diffs.append(abs(res.priority_score - float(r["fuzzy_priority_score"])))
        recompute_base_diffs.append(abs(res.baseline_score - float(r["baseline_weighted_score"])))

    max_fuzzy_diff = max(recompute_fuzzy_diffs)
    max_base_diff = max(recompute_base_diffs)
    print(f"Max difference between stored and recomputed fuzzy score:    {max_fuzzy_diff:.6f}")
    print(f"Max difference between stored and recomputed baseline score: {max_base_diff:.6f}")

    # 3. Calculate Summary Statistics
    def stats(arr):
        n = len(arr)
        mean_val = float(np.mean(arr))
        median_val = float(np.median(arr))
        min_val = float(np.min(arr))
        max_val = float(np.max(arr))
        std_sample = float(np.std(arr, ddof=1)) # sample std dev
        std_pop = float(np.std(arr, ddof=0))    # population std dev
        return {
            "n": n,
            "mean": mean_val,
            "median": median_val,
            "min": min_val,
            "max": max_val,
            "std_sample": std_sample,
            "std_pop": std_pop
        }

    fz_stats = stats(stored_fuzzy)
    bs_stats = stats(stored_baseline)

    print("\n--- STATISTICAL RECOMPUTATION ---")
    print(f"Fuzzy Priority Score:")
    print(f"  Mean:            {fz_stats['mean']:.4f} (Report claimed: 72.18)")
    print(f"  Median:          {fz_stats['median']:.4f}")
    print(f"  Min:             {fz_stats['min']:.4f} (Report claimed: 36.49)")
    print(f"  Max:             {fz_stats['max']:.4f} (Report claimed: 94.95)")
    print(f"  Std Dev (sample ddof=1):     {fz_stats['std_sample']:.4f}")
    print(f"  Std Dev (population ddof=0): {fz_stats['std_pop']:.4f} (Report claimed: 13.42)")

    print(f"\nLinear Baseline Score:")
    print(f"  Mean:            {bs_stats['mean']:.4f} (Report claimed: 58.30)")
    print(f"  Median:          {bs_stats['median']:.4f}")
    print(f"  Min:             {bs_stats['min']:.4f} (Report claimed: 27.18)")
    print(f"  Max:             {bs_stats['max']:.4f} (Report claimed: 85.35)")
    print(f"  Std Dev (sample ddof=1):     {bs_stats['std_sample']:.4f}")
    print(f"  Std Dev (population ddof=0): {bs_stats['std_pop']:.4f} (Report claimed: 11.87)")

    # 4. Deltas & Escalations
    # delta = fuzzy - baseline
    deltas = [f - b for f, b in zip(stored_fuzzy, stored_baseline)]
    esc_pos = [d for d in deltas if d >= 5.0]
    align = [d for d in deltas if abs(d) < 5.0]
    esc_neg = [d for d in deltas if d <= -5.0]

    print(f"\nDecision Deltas (Fuzzy - Baseline):")
    print(f"  Delta >= +5.0 (Escalated): {len(esc_pos)} ({len(esc_pos)/len(deltas)*100:.2f}%) (Report claimed: 212, 84.8%)")
    print(f"  |Delta| < 5.0 (Aligned):   {len(align)} ({len(align)/len(deltas)*100:.2f}%) (Report claimed: 36, 14.4%)")
    print(f"  Delta <= -5.0 (Subdued):   {len(esc_neg)} ({len(esc_neg)/len(deltas)*100:.2f}%) (Report claimed: 2, 0.8%)")

    # 5. Priority Tiers
    def get_tier(score):
        if score >= 85: return "CRITICAL"
        elif score >= 70: return "HIGH"
        elif score >= 50: return "MEDIUM_HIGH"
        elif score >= 25: return "MEDIUM"
        else: return "LOW"

    fz_tiers = {}
    bs_tiers = {}
    for f, b in zip(stored_fuzzy, stored_baseline):
        tf = get_tier(f)
        tb = get_tier(b)
        fz_tiers[tf] = fz_tiers.get(tf, 0) + 1
        bs_tiers[tb] = bs_tiers.get(tb, 0) + 1

    print("\nPriority Tiers Distribution:")
    for tier in ["CRITICAL", "HIGH", "MEDIUM_HIGH", "MEDIUM", "LOW"]:
        fc = fz_tiers.get(tier, 0)
        bc = bs_tiers.get(tier, 0)
        print(f"  {tier:<12}: Fuzzy = {fc:3d} ({fc/len(deltas)*100:5.1f}%) | Baseline = {bc:3d} ({bc/len(deltas)*100:5.1f}%)")

    # 6. Safety Urgency Analysis (Investigate "100% safety guarantee" claim)
    # The report claimed: "In 100% of high safety-hazard scenarios (U >= 8.0), the Mamdani FIS guaranteed a priority score >= 78.0"
    high_u_records = [r for r in csv_records if float(r["safety_urgency_score"]) >= 8.0]
    high_u_scores = [float(r["fuzzy_priority_score"]) for r in high_u_records]
    print(f"\nBenchmark records with U >= 8.0: {len(high_u_records)}")
    if high_u_scores:
        print(f"  Min fuzzy score for U >= 8.0 in benchmark: {min(high_u_scores):.2f}")
        print(f"  Mean fuzzy score for U >= 8.0 in benchmark: {np.mean(high_u_scores):.2f}")
        print(f"  Max fuzzy score for U >= 8.0 in benchmark: {max(high_u_scores):.2f}")
        below_78 = [s for s in high_u_scores if s < 78.0]
        print(f"  Number of benchmark records with U >= 8.0 having score < 78.0: {len(below_78)}")

    # 7. Stress Testing General Mathematical Guarantee:
    # What if severity is low (S=1.0), traffic is low (T=1.0), time is short (D=0.0), but safety is high (U=9.0)?
    print("\n--- GENERAL MATHEMATICAL STRESS TEST (OUTSIDE BENCHMARK) ---")
    test_cases = [
        {"name": "Low Sev, Low Traf, Short Time, High Safety", "s": 1.0, "t": 1.0, "d": 0.0, "u": 9.0},
        {"name": "Low Sev, Low Traf, Short Time, Critical Safety", "s": 1.0, "t": 1.0, "d": 0.0, "u": 10.0},
        {"name": "Critical Sev, Low Traf, Short Time, Low Safety", "s": 9.5, "t": 1.0, "d": 0.0, "u": 1.0},
        {"name": "Critical Sev, Low Traf, Short Time, High Safety", "s": 9.5, "t": 1.0, "d": 0.0, "u": 9.5},
        {"name": "Moderate Sev, High Safety, Low Traf, Short Time", "s": 5.0, "t": 1.0, "d": 0.0, "u": 9.0},
        {"name": "Low Sev, Low Traf, Very Long Time, Low Safety", "s": 1.0, "t": 1.0, "d": 250.0, "u": 1.0},
        {"name": "All Minimum Inputs (0, 0, 0, 0)", "s": 0.0, "t": 0.0, "d": 0.0, "u": 0.0},
        {"name": "All Maximum Inputs (10, 10, 365, 10)", "s": 10.0, "t": 10.0, "d": 365.0, "u": 10.0},
        {"name": "Midpoint Defaults (5, 5, 0, 5)", "s": 5.0, "t": 5.0, "d": 0.0, "u": 5.0},
    ]

    for tc in test_cases:
        res = compute_priority(
            severity_numeric=tc["s"],
            traffic_exposure=tc["t"],
            time_unresolved_days=tc["d"],
            safety_urgency=tc["u"]
        )
        print(f"Scenario: {tc['name']}")
        print(f"  Inputs: S={tc['s']}, T={tc['t']}, D={tc['d']}, U={tc['u']}")
        print(f"  Fuzzy: {res.priority_score:.2f} ({res.priority_label}) | Baseline: {res.baseline_score:.2f} | Delta: {res.priority_score - res.baseline_score:+.2f}")
        print(f"  Top factors: {[f['factor'] for f in res.top_contributing_factors]}")

if __name__ == "__main__":
    run_audit()
