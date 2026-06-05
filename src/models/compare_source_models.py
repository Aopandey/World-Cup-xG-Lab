from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.models.source_modeling import (
    add_row_metadata,
    clip_probability,
    evaluate_binary_classifier,
    evaluate_predictions_frame,
    metrics_by_group,
    plot_calibration_curves,
    write_metrics_report,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS_DIR = PROJECT_ROOT / "data" / "predictions"
ABLATION_DIR = PREDICTIONS_DIR / "feature_ablation"
REPORT_FILE = PROJECT_ROOT / "reports" / "source_model_comparison.csv"
CALIBRATION_FILE = PROJECT_ROOT / "reports" / "figures" / "source_model_calibration.png"

MODEL_PREDICTION_FILES = [
    {
        "label": "StatsBomb-only rich model",
        "model_name": "statsbomb_full_rich_features",
        "path": ABLATION_DIR / "statsbomb_full_rich_features_predictions.csv",
        "training_source": "StatsBomb",
        "feature_set": "rich_statsbomb",
    },
    {
        "label": "Understat-only model",
        "model_name": "understat_only_xgboost",
        "path": PREDICTIONS_DIR / "understat_xg_predictions.csv",
        "fallback_path": ABLATION_DIR / "understat_only_reduced_features_predictions.csv",
        "training_source": "Understat",
        "feature_set": "understat_reduced",
    },
    {
        "label": "Combined-source shared model",
        "model_name": "combined_source_xgboost",
        "path": PREDICTIONS_DIR / "combined_source_xg_predictions.csv",
        "fallback_path": ABLATION_DIR / "combined_source_shared_features_predictions.csv",
        "training_source": "StatsBomb + Understat",
        "feature_set": "shared_plus_data_source",
    },
]


def resolve_prediction_file(spec: dict) -> Path | None:
    """Pick the preferred prediction file, falling back to ablation predictions."""
    path = spec["path"]
    if path.exists():
        return path

    fallback = spec.get("fallback_path")
    if fallback and fallback.exists():
        return fallback

    return None


def add_model_rows(spec: dict, predictions: pd.DataFrame, rows: list[dict]) -> None:
    """Append overall and source-specific metrics for one model prediction file."""
    overall_metrics = evaluate_predictions_frame(predictions)
    rows.append(
        add_row_metadata(
            overall_metrics,
            model_label=spec["label"],
            model_name=spec["model_name"],
            training_source=spec["training_source"],
            test_source="overall",
            feature_set=spec["feature_set"],
            rows=len(predictions),
        )
    )

    if "data_source" in predictions.columns:
        grouped = metrics_by_group(predictions, "data_source")
        for _, group_row in grouped[grouped["group"] != "overall"].iterrows():
            rows.append(
                add_row_metadata(
                    {
                        "log_loss": group_row["log_loss"],
                        "brier_score": group_row["brier_score"],
                        "roc_auc": group_row["roc_auc"],
                        "accuracy_at_0_5": group_row["accuracy_at_0_5"],
                    },
                    model_label=spec["label"],
                    model_name=spec["model_name"],
                    training_source=spec["training_source"],
                    test_source=group_row["group"],
                    feature_set=spec["feature_set"],
                    rows=int(group_row["rows"]),
                )
            )


def add_understat_published_xg_benchmark(predictions: pd.DataFrame, rows: list[dict]) -> None:
    """Add Understat's published xG as a benchmark on the same Understat heldout rows."""
    if "source_xg" not in predictions.columns:
        return

    benchmark = predictions.dropna(subset=["source_xg"]).copy()
    if benchmark.empty or benchmark["actual_goal"].nunique() < 2:
        return

    benchmark["source_xg_probability"] = clip_probability(benchmark["source_xg"])
    metrics = evaluate_binary_classifier(
        benchmark["actual_goal"].astype(int),
        benchmark["source_xg_probability"].astype(float),
    )
    rows.append(
        add_row_metadata(
            metrics,
            model_label="Understat published xG benchmark",
            model_name="understat_published_xg",
            training_source="Understat published model",
            test_source="Understat",
            feature_set="external_benchmark_not_trained_here",
            rows=len(benchmark),
        )
    )


def main() -> None:
    """Compare StatsBomb-only, Understat-only, and combined-source xG model artifacts."""
    rows: list[dict] = []
    calibration_frames: list[tuple[str, pd.DataFrame]] = []
    missing_files: list[str] = []

    for spec in MODEL_PREDICTION_FILES:
        prediction_file = resolve_prediction_file(spec)
        if prediction_file is None:
            missing_files.append(spec["model_name"])
            continue

        predictions = pd.read_csv(prediction_file)
        add_model_rows(spec, predictions, rows)
        calibration_frames.append((spec["label"], predictions))

        if spec["model_name"] == "understat_only_xgboost":
            add_understat_published_xg_benchmark(predictions, rows)

    if not rows:
        raise SystemExit(
            "No source-model prediction files found. Run:\n"
            "python src/models/run_feature_ablation_experiments.py\n"
            "python src/models/train_understat_xg.py\n"
            "python src/models/train_combined_xg.py"
        )

    report = write_metrics_report(rows, REPORT_FILE)
    plot_calibration_curves(calibration_frames, CALIBRATION_FILE)

    print("Source Model Comparison")
    print("=" * 24)
    print(
        report[
            [
                "model_label",
                "training_source",
                "test_source",
                "log_loss",
                "brier_score",
                "roc_auc",
                "accuracy_at_0_5",
                "rows",
            ]
        ].to_string(index=False)
    )
    if missing_files:
        print("")
        print("Missing prediction files for:")
        for model_name in missing_files:
            print(f"- {model_name}")
    print(f"Saved report to: {REPORT_FILE}")
    print(f"Saved calibration plot to: {CALIBRATION_FILE}")


if __name__ == "__main__":
    main()

