"""
Script to download verified RDD2022 Road Damage Detection YOLOv8 model weights.
License: AGPL-3.0 (Ultralytics & RDD2022 academic benchmark)
"""
import os
import shutil
from pathlib import Path

def download_rdd_weights():
    target_dir = Path(__file__).resolve().parent
    target_file = target_dir / "rdd2022_yolov8n.pt"

    if target_file.exists() and target_file.stat().st_size > 1_000_000:
        print(f"Weights already present at: {target_file} ({target_file.stat().st_size} bytes)")
        return str(target_file)

    try:
        from huggingface_hub import hf_hub_download
        print("Downloading RDD2022 YOLOv8n weights from Hugging Face (dronefreak/rdd2022-yolov8n)...")
        cached_path = hf_hub_download(repo_id="dronefreak/rdd2022-yolov8n", filename="best.pt")
        shutil.copyfile(cached_path, str(target_file))
        print(f"Successfully downloaded and saved weights to: {target_file}")
        return str(target_file)
    except Exception as e:
        print(f"Failed to download weights: {e}")
        return None

if __name__ == "__main__":
    download_rdd_weights()
