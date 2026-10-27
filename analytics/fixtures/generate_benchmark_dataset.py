"""
Generator for the Paventra Soft Computing Maintenance Benchmark Dataset.

Produces both CSV and JSON formats adhering strictly to docs/data_dictionary.md.
Combines computer vision distress detections, environmental/traffic context,
Mamdani fuzzy inference results, and baseline weighted scoring for academic comparison.
"""

import sys
import csv
import json
import uuid
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Ensure backend modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))
from app.services.prioritization.fuzzy_engine import compute_priority

CITIES = [
    {"name": "Mumbai", "center_lat": 19.0760, "center_lon": 72.8777, "roads": ["Western Express Hwy", "SV Road", "Link Road", "LBS Marg", "Ghatkopar Arterial"]},
    {"name": "Bengaluru", "center_lat": 12.9716, "center_lon": 77.5946, "roads": ["Outer Ring Road", "Hosur Road", "Bannerghatta Rd", "Indiranagar 100ft", "Whitefield Main Rd"]},
    {"name": "Delhi", "center_lat": 28.6139, "center_lon": 77.2090, "roads": ["Ring Road", "Mathura Road", "Vikas Marg", "GT Karnal Road", "MG Road"]},
    {"name": "Chennai", "center_lat": 13.0827, "center_lon": 80.2707, "roads": ["Anna Salai", "Poonamallee High Rd", "OMR IT Corridor", "GST Road", "ECR Scenic"]},
    {"name": "Ahmedabad", "center_lat": 23.0225, "center_lon": 72.5714, "roads": ["SG Highway", "Ashram Road", "Drive-In Road", "132ft Ring Road", "C.G. Road"]},
]

DAMAGE_SPECS = {
    "D40": {"name": "Pothole", "severity_base": 7.5, "base_area": (0.03, 0.16)},
    "D20": {"name": "Alligator Crack", "severity_base": 6.0, "base_area": (0.05, 0.25)},
    "D00": {"name": "Longitudinal Crack", "severity_base": 4.0, "base_area": (0.01, 0.08)},
    "D10": {"name": "Transverse Crack", "severity_base": 4.5, "base_area": (0.01, 0.10)},
}

STATUS_CHOICES = ["submitted", "verified", "assigned", "in_progress", "pending_verification", "resolved"]


def generate_benchmark_records(count: int = 250, seed: int = 101):
    random.seed(seed)
    now = datetime(2026, 10, 27, 10, 0, 0, tzinfo=timezone.utc)
    records = []

    for i in range(1, count + 1):
        report_id = str(uuid.uuid4())
        ref_suffix = f"{random.randint(10000000, 99999999):08X}"[:8]
        public_ref = f"PAV-{ref_suffix}"

        city = random.choice(CITIES)
        lat = round(city["center_lat"] + random.uniform(-0.08, 0.08), 6)
        lon = round(city["center_lon"] + random.uniform(-0.08, 0.08), 6)
        road = f"{random.choice(city['roads'])}, {city['name']}"

        cls_code = random.choices(["D40", "D20", "D00", "D10"], weights=[45, 25, 15, 15])[0]
        spec = DAMAGE_SPECS[cls_code]
        conf = round(random.uniform(0.55, 0.98), 3)

        min_a, max_a = spec["base_area"]
        area_ratio = round(random.uniform(min_a, max_a), 4)

        # Provisional severity score calculated from geometry + class
        provisional_sev = round(min(10.0, max(1.0, spec["severity_base"] + (area_ratio * 15.0) + random.uniform(-0.8, 0.8))), 1)

        # Verified severity (simulated coordinator check on subset)
        has_human_verification = random.random() < 0.40
        if has_human_verification:
            if provisional_sev >= 8.5:
                verified_sev = "critical"
            elif provisional_sev >= 6.5:
                verified_sev = "high"
            elif provisional_sev >= 4.0:
                verified_sev = "moderate"
            else:
                verified_sev = "low"
        else:
            verified_sev = None

        # Contextual variables
        traffic_source = random.choices(["sensor", "gis_road_class", "manual_entry", "estimated_default"], weights=[20, 45, 15, 20])[0]
        if traffic_source == "estimated_default":
            traffic = 5.0
        else:
            traffic = round(random.uniform(2.0, 9.8), 1)

        days_unresolved = round(random.expovariate(1 / 35.0), 1)
        days_unresolved = min(365.0, days_unresolved)

        # Safety urgency (elevated near schools / heavy traffic intersections)
        if "Highway" in road or "Ring Road" in road or cls_code == "D40":
            safety = round(min(10.0, random.uniform(5.5, 9.8)), 1)
        else:
            safety = round(random.uniform(1.5, 7.5), 1)

        duplicate_count = random.choices([0, 1, 2, 3, 5], weights=[60, 20, 10, 7, 3])[0]

        # Compute fuzzy inference priority and baseline weighted score
        fuzzy_res = compute_priority(
            traffic_exposure=traffic,
            time_unresolved_days=days_unresolved,
            safety_urgency=safety,
            severity_numeric=provisional_sev,
        )

        fuzzy_score = fuzzy_res.priority_score
        baseline_score = fuzzy_res.baseline_score
        decision_delta = round(fuzzy_score - baseline_score, 2)

        # Status and workflow progression
        status = random.choices(STATUS_CHOICES, weights=[35, 25, 15, 10, 5, 10])[0]
        created_at = (now - timedelta(days=days_unresolved)).isoformat()
        
        assigned_team_id = str(uuid.uuid4()) if status in ("assigned", "in_progress", "pending_verification", "resolved") else None
        assignment_ts = (now - timedelta(days=max(1.0, days_unresolved * 0.5))).isoformat() if assigned_team_id else None
        completion_ts = (now - timedelta(days=max(0.5, days_unresolved * 0.2))).isoformat() if status in ("pending_verification", "resolved") else None
        resolution_verified_at = (now - timedelta(days=0.1)).isoformat() if status == "resolved" else None

        records.append({
            "report_id": report_id,
            "public_ref": public_ref,
            "detection_class": cls_code,
            "class_description": spec["name"],
            "detection_confidence": conf,
            "bbox_area_ratio": area_ratio,
            "provisional_severity_score": provisional_sev,
            "human_verified_severity": verified_sev,
            "traffic_exposure_score": traffic,
            "traffic_provenance": traffic_source,
            "time_unresolved_days": days_unresolved,
            "safety_urgency_score": safety,
            "duplicate_report_count": duplicate_count,
            "latitude": lat,
            "longitude": lon,
            "road_segment": road,
            "status": status,
            "assigned_team_id": assigned_team_id,
            "assignment_timestamp": assignment_ts,
            "completion_timestamp": completion_ts,
            "resolution_verified_at": resolution_verified_at,
            "fuzzy_priority_score": fuzzy_score,
            "priority_label": fuzzy_res.priority_label,
            "baseline_weighted_score": baseline_score,
            "decision_delta": decision_delta,
            "top_factors": [f["factor"] for f in fuzzy_res.top_contributing_factors],
            "created_at": created_at,
        })

    return records


def main():
    records = generate_benchmark_records(count=250, seed=101)

    out_dir = Path("analytics/fixtures")
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "soft_computing_maintenance_benchmark.csv"
    json_path = out_dir / "soft_computing_maintenance_benchmark.json"

    # Write CSV
    fieldnames = list(records[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            row = dict(r)
            row["top_factors"] = " | ".join(r["top_factors"])
            writer.writerow(row)

    # Write JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"Generated {len(records)} benchmark records:")
    print(f"  CSV:  {csv_path} ({csv_path.stat().st_size} bytes)")
    print(f"  JSON: {json_path} ({json_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
