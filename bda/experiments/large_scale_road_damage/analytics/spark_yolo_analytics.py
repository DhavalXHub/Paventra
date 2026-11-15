r"""
Spark SQL Analytics on YOLO Batch Inference Outputs.
Reads yolo_detections.parquet and executes structured analytical queries.
Computes class frequencies, confidence distributions, spatial geometry,
and latency percentiles using Apache Spark.
"""
import os
import sys
import time
import json
from decimal import Decimal
from pathlib import Path

def convert_decimals(obj):
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(elem) for elem in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj

# Add experiment directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings

from pyspark.sql import SparkSession
import pyspark.sql.functions as F


def run_spark_yolo_analytics():
    print("=" * 70)
    print("STARTING SPARK SQL ANALYTICS ON YOLO DETECTIONS")
    print("=" * 70)
    
    t_start = time.perf_counter()
    
    # 1. Initialize SparkSession
    print("Initializing PySpark Session...")
    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("Paventra_Spark_YOLO_Analytics")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    
    # 2. Read YOLO Detections Parquet
    print(f"Reading YOLO detections from: {settings.YOLO_DETECTIONS_PARQUET}")
    df_yolo = spark.read.parquet(str(settings.YOLO_DETECTIONS_PARQUET))
    df_yolo.createOrReplaceTempView("yolo_detections")
    
    # Also read ground-truth damage annotations for comparison
    df_gt = spark.read.parquet(str(settings.DAMAGE_ANNOTATIONS_PARQUET))
    df_gt.createOrReplaceTempView("ground_truth_annotations")
    
    analytics_results = {}
    
    # Query 1: Detection counts by class
    q1 = spark.sql("""
        SELECT predicted_class, COUNT(*) as detection_count,
               ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct_of_detections
        FROM yolo_detections
        WHERE predicted_class != 'NO_DETECTION'
        GROUP BY predicted_class
        ORDER BY detection_count DESC
    """)
    analytics_results["detections_by_class"] = [row.asDict() for row in q1.collect()]
    
    # Query 2: Confidence statistics by predicted class
    q2 = spark.sql("""
        SELECT predicted_class,
               COUNT(*) as object_count,
               ROUND(AVG(confidence), 4) as avg_confidence,
               ROUND(MIN(confidence), 4) as min_confidence,
               ROUND(MAX(confidence), 4) as max_confidence,
               ROUND(STDDEV(confidence), 4) as stddev_confidence
        FROM yolo_detections
        WHERE predicted_class != 'NO_DETECTION'
        GROUP BY predicted_class
        ORDER BY avg_confidence DESC
    """)
    analytics_results["confidence_by_class"] = [row.asDict() for row in q2.collect()]
    
    # Query 3: Detections per image distribution
    q3 = spark.sql("""
        WITH distinct_images AS (
            SELECT image_id, FIRST(detection_count) as det_count
            FROM yolo_detections
            GROUP BY image_id
        )
        SELECT det_count as defects_per_image, COUNT(*) as image_count
        FROM distinct_images
        GROUP BY det_count
        ORDER BY defects_per_image
    """)
    analytics_results["detections_per_image_distribution"] = [row.asDict() for row in q3.collect()]
    
    # Query 4: Images with the highest number of detections
    q4 = spark.sql("""
        SELECT image_id, FIRST(detection_count) as total_detections,
               CONCAT_WS(', ', COLLECT_LIST(predicted_class)) as detected_classes,
               ROUND(AVG(confidence), 3) as mean_confidence
        FROM yolo_detections
        WHERE predicted_class != 'NO_DETECTION'
        GROUP BY image_id
        ORDER BY total_detections DESC
        LIMIT 10
    """)
    analytics_results["top_detected_images"] = [row.asDict() for row in q4.collect()]
    
    # Query 5: Distribution of confidence values in intervals
    q5 = spark.sql("""
        SELECT 
            CASE 
                WHEN confidence < 0.30 THEN '0.20 - 0.30'
                WHEN confidence < 0.40 THEN '0.30 - 0.40'
                WHEN confidence < 0.50 THEN '0.40 - 0.50'
                WHEN confidence < 0.60 THEN '0.50 - 0.60'
                WHEN confidence < 0.70 THEN '0.60 - 0.70'
                WHEN confidence < 0.80 THEN '0.70 - 0.80'
                ELSE '0.80 - 1.00'
            END as confidence_range,
            COUNT(*) as detection_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
        FROM yolo_detections
        WHERE predicted_class != 'NO_DETECTION'
        GROUP BY 1
        ORDER BY confidence_range
    """)
    analytics_results["confidence_histogram"] = [row.asDict() for row in q5.collect()]
    
    # Query 6: Bounding-box area distribution (predictions)
    q6 = spark.sql("""
        SELECT 
            ROUND(MIN(bbox_area), 2) as min_pred_area,
            ROUND(MAX(bbox_area), 2) as max_pred_area,
            ROUND(AVG(bbox_area), 2) as avg_pred_area,
            ROUND(PERCENTILE_APPROX(bbox_area, 0.5), 2) as median_pred_area,
            ROUND(AVG(bbox_width), 2) as avg_pred_width,
            ROUND(AVG(bbox_height), 2) as avg_pred_height
        FROM yolo_detections
        WHERE predicted_class != 'NO_DETECTION'
    """)
    analytics_results["prediction_bbox_area_stats"] = q6.collect()[0].asDict()
    
    # Query 7: Images with no detections vs with detections
    q7 = spark.sql("""
        WITH distinct_images AS (
            SELECT image_id, FIRST(detection_count) as det_count
            FROM yolo_detections
            GROUP BY image_id
        )
        SELECT 
            SUM(CASE WHEN det_count = 0 THEN 1 ELSE 0 END) as zero_detection_images,
            SUM(CASE WHEN det_count > 0 THEN 1 ELSE 0 END) as positive_detection_images,
            COUNT(*) as total_images,
            ROUND(SUM(CASE WHEN det_count = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as zero_detection_pct,
            ROUND(SUM(CASE WHEN det_count > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as positive_detection_pct
        FROM distinct_images
    """)
    analytics_results["detection_coverage"] = q7.collect()[0].asDict()
    
    # Query 8: Processing status breakdown
    q8 = spark.sql("""
        SELECT processing_status, COUNT(*) as record_count
        FROM yolo_detections
        GROUP BY processing_status
    """)
    analytics_results["processing_status"] = [row.asDict() for row in q8.collect()]
    
    # Query 9 & 10: Inference latency percentiles & throughput
    q9 = spark.sql("""
        WITH distinct_images AS (
            SELECT image_id, FIRST(inference_time_ms) as latency_ms
            FROM yolo_detections
            GROUP BY image_id
        )
        SELECT 
            COUNT(*) as total_images,
            ROUND(AVG(latency_ms), 2) as avg_latency_ms,
            ROUND(STDDEV(latency_ms), 2) as stddev_latency_ms,
            ROUND(PERCENTILE_APPROX(latency_ms, 0.50), 2) as p50_latency_ms,
            ROUND(PERCENTILE_APPROX(latency_ms, 0.90), 2) as p90_latency_ms,
            ROUND(PERCENTILE_APPROX(latency_ms, 0.95), 2) as p95_latency_ms,
            ROUND(PERCENTILE_APPROX(latency_ms, 0.99), 2) as p99_latency_ms,
            ROUND(MIN(latency_ms), 2) as min_latency_ms,
            ROUND(MAX(latency_ms), 2) as max_latency_ms,
            ROUND(1000.0 / AVG(latency_ms), 2) as estimated_images_per_second
        FROM distinct_images
    """)
    analytics_results["latency_percentiles"] = q9.collect()[0].asDict()
    
    total_query_time = round(time.perf_counter() - t_start, 3)
    
    final_output = {
        "analysis_type": "Spark SQL Analytics on YOLO Batch Inference Output",
        "spark_version": spark.version,
        "master": "local[*]",
        "execution_time_seconds": total_query_time,
        "results": analytics_results,
    }
    final_output = convert_decimals(final_output)
    
    with open(settings.SPARK_ANALYTICS_JSON, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)
    print(f"Saved Spark SQL analytics to: {settings.SPARK_ANALYTICS_JSON}")
    
    # Generate SPARK_YOLO_ANALYTICS.md
    gen_spark_yolo_report(final_output)
    
    spark.stop()
    print(f"Completed Spark SQL YOLO Analytics in {total_query_time}s.")
    return final_output


def gen_spark_yolo_report(data):
    """Generate Markdown report for Spark SQL YOLO Analytics."""
    res = data["results"]
    c_table = "\n".join([
        f"| **{row['predicted_class']}** | {row['detection_count']:,} | {row['pct_of_detections']}% |"
        for row in res["detections_by_class"]
    ])
    
    conf_table = "\n".join([
        f"| **{row['predicted_class']}** | {row['object_count']} | {row['avg_confidence']} | {row['min_confidence']} | {row['max_confidence']} | {row['stddev_confidence']} |"
        for row in res["confidence_by_class"]
    ])
    
    hist_table = "\n".join([
        f"| `{row['confidence_range']}` | {row['detection_count']} | {row['percentage']}% |"
        for row in res["confidence_histogram"]
    ])
    
    lat = res["latency_percentiles"]
    cov = res["detection_coverage"]
    area = res["prediction_bbox_area_stats"]
    
    report_md = f"""# Apache Spark SQL YOLO Analytics Report

**Analytics Engine:** Apache Spark {data['spark_version']} SQL (`local[*]`)  
**Source Dataset:** YOLOv8n inference outputs (`yolo_detections.parquet`)  
**Total Images Audited:** {cov['total_images']:,} real road images  
**Execution Time:** {data['execution_time_seconds']} seconds  

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
{c_table}

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
{conf_table}

---

## 3. Confidence Interval Distribution

| Confidence Range | Detection Count | Share |
|---|---|---|
{hist_table}

---

## 4. Coverage & Detection Density

- **Images with Positive Detections:** {cov['positive_detection_images']:,} ({cov['positive_detection_pct']}%)
- **Images without Detections:** {cov['zero_detection_images']:,} ({cov['zero_detection_pct']}%)
- **Predicted Bounding Box Area:** Mean: {area['avg_pred_area']:,} px² | Median: {area['median_pred_area']:,} px²
- **Predicted Dimensions:** Mean Width: {area['avg_pred_width']} px | Mean Height: {area['avg_pred_height']} px

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
| **Mean Latency** | **{lat['avg_latency_ms']} ms** |
| **50th Percentile (p50 / Median)** | **{lat['p50_latency_ms']} ms** |
| **90th Percentile (p90)** | **{lat['p90_latency_ms']} ms** |
| **95th Percentile (p95)** | **{lat['p95_latency_ms']} ms** |
| **99th Percentile (p99)** | **{lat['p99_latency_ms']} ms** |
| **Min / Max Latency** | {lat['min_latency_ms']} ms / {lat['max_latency_ms']} ms |
| **Effective Inference Throughput** | **{lat['estimated_images_per_second']} images/sec** |
"""
    with open(settings.REPORTS_DIR / "SPARK_YOLO_ANALYTICS.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"Generated SPARK_YOLO_ANALYTICS.md at: {settings.REPORTS_DIR / 'SPARK_YOLO_ANALYTICS.md'}")


if __name__ == "__main__":
    run_spark_yolo_analytics()
