# Environment and Dependency Notes

**Experiment Path:** `D:\Paventra\bda\experiments\large_scale_road_damage`  
**Host Platform:** Windows 11 (64-bit AMD64)  

---

## 1. Runtime Versions Verified

- **Python Runtime:** Python `3.12.9` (64-bit MSC v.1942)
- **Apache Spark / PySpark:** PySpark `4.2.0`
- **Java Virtual Machine:** OpenJDK Temurin 17.0.20.1+1 (`D:\Paventra\bda\tools\jdk17\jdk-17.0.20.1+1`)
- **Hadoop Winutils:** Hadoop 3.3.6 winutils (`D:\Paventra\bda\tools\hadoop\bin\winutils.exe`)
- **PyTorch:** `2.11.0+cpu`
- **Ultralytics YOLO:** `8.4.185`
- **Pandas:** `2.3.2`
- **PyArrow:** `19.0.1`
- **Pillow:** `11.1.0`
- **scikit-fuzzy:** `0.5.0`

---

## 2. Configuration & Path Handling

To guarantee smooth PySpark execution on Windows across multi-threaded workers without hitting space-in-path quoting issues:
- `PYSPARK_PYTHON` is mapped to short path `C:\PROGRA~1\Python312\python.exe`.
- `JAVA_HOME` and `HADOOP_HOME` are explicitly injected in `config/settings.py` so any script or test runs self-contained without needing global Windows environment mutations.
