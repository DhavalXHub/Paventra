"""
Evaluation script for YOLO road damage detection models.
Measures Precision, Recall, and mAP metrics on a held-out dataset.
Safeguard: Never claims metrics that have not been actually measured.
"""
import argparse
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ModelEvaluation")


def evaluate_model(weights_path: str, data_yaml_path: str, device: str = "cpu"):
    """
    Evaluates Ultralytics YOLO model on a validation dataset specified in data.yaml.
    """
    if not os.path.exists(weights_path):
        logger.error(f"Model weights file not found: {weights_path}")
        logger.info("To test inference evaluation, supply valid weights (.pt) or export dataset in YOLO format.")
        sys.exit(1)

    if not os.path.exists(data_yaml_path):
        logger.error(f"Dataset descriptor YAML not found: {data_yaml_path}")
        sys.exit(1)

    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("Ultralytics library is not installed. Run: pip install ultralytics")
        sys.exit(1)

    logger.info(f"Loading weights from {weights_path}...")
    model = YOLO(weights_path)

    logger.info(f"Running validation on {data_yaml_path} using device: {device}...")
    metrics = model.val(data=data_yaml_path, device=device, split="val", verbose=True)

    print("\n" + "="*50)
    print("EVALUATION METRICS RESULTS (ACTUALLY MEASURED):")
    print(f"  Precision: {metrics.box.mp:.4f}")
    print(f"  Recall:    {metrics.box.mr:.4f}")
    print(f"  mAP@50:    {metrics.box.map50:.4f}")
    print(f"  mAP@50-95: {metrics.box.map:.4f}")
    print("="*50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate YOLO road damage detector.")
    parser.add_argument("--weights", type=str, default="yolov8n.pt", help="Path to .pt model weights")
    parser.add_argument("--data", type=str, default="ml/evaluation/sample_data.yaml", help="Path to dataset yaml")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu, cuda:0)")
    args = parser.parse_args()

    evaluate_model(args.weights, args.data, args.device)
