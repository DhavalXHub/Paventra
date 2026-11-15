# Apache Spark SQL YOLO Analytics Report

**Analytics Engine:** Apache Spark 4.2.0 SQL (`local[*]`)  
**Source Dataset:** YOLOv8n inference outputs (`yolo_detections.parquet`)  
**Total Images Audited:** 300 real road images  
**Execution Time:** 19.591 seconds  

---

## 1. Defect Category Frequencies & Proportions

```sql
SELECT predicted_class, COUNT(*) as detection_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct_of_detections
FROM yolo_detections
WHERE predicted_class != 'NO_DETECTION'
GROUP BY predicted_class ORDER BY detection_count DESC;
```

| Predicted Defect Category | Detections Count | Percentage of Defect Volume |
|---|---|---|
| **alligator_crack** | 64 | 42.95% |
| **pothole** | 52 | 34.9% |
| **longitudinal_crack** | 33 | 22.15% |

---

## 2. Confidence Statistical Dispersion by Class

```sql
SELECT predicted_class, COUNT(*) as object_count,
       ROUND(AVG(confidence), 4) as avg_confidence,
       ROUND(MIN(confidence), 4) as min_confidence,
       ROUND(MAX(confidence), 4) as max_confidence,
       ROUND(STDDEV(confidence), 4) as stddev_confidence
FROM yolo_detections WHERE predicted_class != 'NO_DETECTION'
GROUP BY predicted_class;
```

| Class | Objects | Mean Conf | Min Conf | Max Conf | StdDev |
|---|---|---|---|---|---|
| **alligator_crack** | 64 | 0.4728 | 0.2038 | 0.858 | 0.1981 |
| **pothole** | 52 | 0.4202 | 0.2025 | 0.8144 | 0.1874 |
| **longitudinal_crack** | 33 | 0.3431 | 0.2027 | 0.6013 | 0.1245 |

---

## 3. Confidence Interval Distribution

| Confidence Range | Detection Count | Share |
|---|---|---|
| `0.20 - 0.30` | 57 | 38.26% |
| `0.30 - 0.40` | 18 | 12.08% |
| `0.40 - 0.50` | 25 | 16.78% |
| `0.50 - 0.60` | 16 | 10.74% |
| `0.60 - 0.70` | 15 | 10.07% |
| `0.70 - 0.80` | 13 | 8.72% |
| `0.80 - 1.00` | 5 | 3.36% |

---

## 4. Coverage & Detection Density

- **Images with Positive Detections:** 103 (34.33%)
- **Images without Detections:** 197 (65.67%)
- **Predicted Bounding Box Area:** Mean: 48,364.65 px² | Median: 24,981.71 px²
- **Predicted Dimensions:** Mean Width: 263.6 px | Mean Height: 154.16 px

---

## 5. CPU Inference Latency Profile & Percentiles

```sql
SELECT ROUND(AVG(latency_ms), 2) as avg_ms,
       ROUND(PERCENTILE_APPROX(latency_ms, 0.50), 2) as p50_ms,
       ROUND(PERCENTILE_APPROX(latency_ms, 0.90), 2) as p90_ms,
       ROUND(PERCENTILE_APPROX(latency_ms, 0.99), 2) as p99_ms
FROM yolo_detections;
```

| Latency Metric | Measured Latency (ms) |
|---|---|
| **Mean Latency** | **54.4 ms** |
| **50th Percentile (p50 / Median)** | **46.25 ms** |
| **90th Percentile (p90)** | **49.42 ms** |
| **95th Percentile (p95)** | **50.85 ms** |
| **99th Percentile (p99)** | **58.14 ms** |
| **Min / Max Latency** | 39.34 ms / 2491.44 ms |
| **Effective Inference Throughput** | **18.38 images/sec** |
