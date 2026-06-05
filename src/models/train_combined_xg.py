from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.models.source_modeling import (
    BASE_NUMERIC_FEATURES,
    SHARED_CATEGORICAL_FEATURES,
    add_row_metadata,
    metrics_by_group,
    plot_calibration_curves,
    train_evaluate_save_model,
    write_metrics_report,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_FILE = PROJECT_ROOT / "data" / "features" / "combined_shot_features.csv"
MODEL_FILE = PROJECT_ROOT / "models" / "combined_source_xg_model.joblib"
PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "combined_source_xg_predictions.csv"
REPORT_FILE = PROJECT_ROOT / "reports" / "combined_source_xg_model_report.csv"
CALIBRATION_FILE = PROJECT_ROOT / "reports" / "figures" / "combined_source_calibration.png"
MODEL_NAME = "combined_source_xgboost"


def load_features(path: Path = FEATURES_FILE) -> pd.DataFrame:
    """Load combined StatsBomb and Understat shot features."""
    if not path.exists():
        raise FileNotFoundError(
            f"Combined feature file not found: {path}. "
            "Run python src/features/build_combined_shot_features.py first."
        )
    return pd.read_csv(path, low_memory=False)


def main() -> None:
    """Train and evaluate a combined-source xG model."""
    features = load_features()
    _, metrics, predictions = train_evaluate_save_model(
        df=features,
        numeric_columns=BASE_NUMERIC_FEATURES,
        categorical_columns=SHARED_CATEGORICAL_FEATURES,
        model_name=MODEL_NAME,
        model_path=MODEL_FILE,
        predictions_path=PREDICTIONS_FILE,
        extra_prediction_columns=[
            "data_source",
            "player",
            "team",
            "league",
            "season",
            "source_xg",
        ],
    )

    rows = [
        add_row_metadata(
            metrics,
            model_name=MODEL_NAME,
            training_source="StatsBomb + Understat",
            evaluation_scope="heldout_combined_shots",
            uses_source_xg_as_feature=False,
        )
    ]
    grouped_metrics = metrics_by_group(predictions, "data_source")
    for _, row in grouped_metrics[grouped_metrics["group"] != "overall"].iterrows():
        rows.append(
            add_row_metadata(
                {
                    "log_loss": row["log_loss"],
                    "brier_score": row["brier_score"],
                    "roc_auc": row["roc_auc"],
                    "accuracy_at_0_5": row["accuracy_at_0_5"],
                    "train_rows": metrics["train_rows"],
                    "test_rows": row["rows"],
                    "feature_count": metrics["feature_count"],
                },
                model_name=MODEL_NAME,
                training_source="StatsBomb + Understat",
                evaluation_scope=f"heldout_{row['group']}_shots",
                uses_source_xg_as_feature=False,
            )
        )

    report = write_metrics_report(rows, REPORT_FILE)
    plot_calibration_curves([(MODEL_NAME, predictions)], CALIBRATION_FILE)

    print("Combined-source xG Model Metrics")
    print("=" * 35)
    print(report.to_string(index=False))
    print(f"Saved model to: {MODEL_FILE}")
    print(f"Saved predictions to: {PREDICTIONS_FILE}")
    print(f"Saved report to: {REPORT_FILE}")
    print(f"Saved calibration plot to: {CALIBRATION_FILE}")


if __name__ == "__main__":
    main()
