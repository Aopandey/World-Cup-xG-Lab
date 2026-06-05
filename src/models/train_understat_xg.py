from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.models.source_modeling import (
    BASE_NUMERIC_FEATURES,
    UNDERSTAT_CATEGORICAL_FEATURES,
    add_row_metadata,
    clip_probability,
    evaluate_binary_classifier,
    metrics_by_group,
    train_evaluate_save_model,
    write_metrics_report,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_FILE = PROJECT_ROOT / "data" / "features" / "understat_model_features.csv"
MODEL_FILE = PROJECT_ROOT / "models" / "understat_xg_model.joblib"
PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "understat_xg_predictions.csv"
REPORT_FILE = PROJECT_ROOT / "reports" / "understat_xg_model_report.csv"
MODEL_NAME = "understat_only_xgboost"


def load_features(path: Path = FEATURES_FILE) -> pd.DataFrame:
    """Load Understat shot features."""
    if not path.exists():
        raise FileNotFoundError(
            f"Understat feature file not found: {path}. "
            "Run python src/data/build_understat_shot_features.py first."
        )
    return pd.read_csv(path)


def benchmark_understat_source_xg(predictions: pd.DataFrame) -> dict[str, float] | None:
    """Evaluate Understat's own source_xg on the same test rows, if available."""
    if "source_xg" not in predictions.columns:
        return None

    benchmark = predictions.dropna(subset=["source_xg"]).copy()
    if benchmark.empty:
        return None

    benchmark["understat_source_xg"] = clip_probability(benchmark["source_xg"])
    return evaluate_binary_classifier(
        benchmark["actual_goal"].astype(int),
        benchmark["understat_source_xg"].astype(float),
    )


def main() -> None:
    """Train and evaluate an Understat-only xG model."""
    features = load_features()
    _, metrics, predictions = train_evaluate_save_model(
        df=features,
        numeric_columns=BASE_NUMERIC_FEATURES,
        categorical_columns=UNDERSTAT_CATEGORICAL_FEATURES,
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
            training_source="Understat",
            evaluation_scope="heldout_understat_shots",
            uses_source_xg_as_feature=False,
        )
    ]

    source_xg_metrics = benchmark_understat_source_xg(predictions)
    if source_xg_metrics:
        rows.append(
            add_row_metadata(
                source_xg_metrics,
                train_rows=float("nan"),
                test_rows=float(len(predictions.dropna(subset=["source_xg"]))),
                feature_count=0.0,
                model_name="understat_published_xg_benchmark",
                training_source="Understat",
                evaluation_scope="same_heldout_understat_shots",
                uses_source_xg_as_feature=False,
            )
        )

    report = write_metrics_report(rows, REPORT_FILE)

    print("Understat-only xG Model Metrics")
    print("=" * 32)
    print(report.to_string(index=False))
    print("")
    print("Metrics by source")
    print(metrics_by_group(predictions, "data_source").to_string(index=False))
    print(f"Saved model to: {MODEL_FILE}")
    print(f"Saved predictions to: {PREDICTIONS_FILE}")
    print(f"Saved report to: {REPORT_FILE}")


if __name__ == "__main__":
    main()

