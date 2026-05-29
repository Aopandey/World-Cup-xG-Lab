from pathlib import Path
import sys

import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.models.evaluate import evaluate_binary_classifier


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS_DIR = PROJECT_ROOT / "data" / "predictions"
REPORT_FILE = PROJECT_ROOT / "reports" / "model_comparison.csv"

PREDICTION_FILES = [
    "baseline_predictions.csv",
    "xgboost_predictions.csv",
]


def load_prediction_file(path: Path) -> pd.DataFrame:
    """Load one model prediction file and validate required columns."""
    predictions = pd.read_csv(path)
    required_columns = ["actual_goal", "predicted_xg", "model_name"]
    missing_columns = [
        column for column in required_columns if column not in predictions.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{path} is missing required columns: {', '.join(missing_columns)}"
        )

    return predictions


def compare_models(predictions_dir: Path = PREDICTIONS_DIR) -> pd.DataFrame:
    """Calculate model metrics from saved prediction files."""
    rows = []

    for file_name in PREDICTION_FILES:
        prediction_file = predictions_dir / file_name

        if not prediction_file.exists():
            print(f"WARNING: Prediction file not found: {prediction_file}")
            continue

        predictions = load_prediction_file(prediction_file)
        model_name = predictions["model_name"].iloc[0]
        metrics = evaluate_binary_classifier(
            predictions["actual_goal"],
            predictions["predicted_xg"],
        )

        rows.append(
            {
                "model_name": model_name,
                "prediction_file": file_name,
                **metrics,
            }
        )

    if not rows:
        raise FileNotFoundError(
            f"No supported prediction files were found in {predictions_dir}."
        )

    comparison = pd.DataFrame(rows)
    return comparison.sort_values("log_loss", ascending=True).reset_index(drop=True)


def main() -> None:
    """Print and save model comparison metrics."""
    comparison = compare_models()

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(REPORT_FILE, index=False)

    print("Model Comparison")
    print("=" * 16)
    print(comparison.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print(f"\nSaved model comparison to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
