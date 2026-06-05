from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.features.build_combined_shot_features import (
    COMBINED_FEATURES_FILE,
    STATSBOMB_FEATURES_FILE,
    build_combined_features,
)
from src.data.build_understat_shot_features import OUTPUT_FILE as UNDERSTAT_FEATURES_FILE
from src.models.source_modeling import (
    BASE_NUMERIC_FEATURES,
    SHARED_CATEGORICAL_FEATURES,
    STATSBOMB_RICH_CATEGORICAL_FEATURES,
    UNDERSTAT_CATEGORICAL_FEATURES,
    add_row_metadata,
    plot_calibration_curves,
    reference_feature_availability,
    train_evaluate_save_model,
    write_metrics_report,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREDICTIONS_DIR = PROJECT_ROOT / "data" / "predictions" / "feature_ablation"
REPORT_FILE = PROJECT_ROOT / "reports" / "feature_missingness_experiment.csv"
CALIBRATION_FILE = PROJECT_ROOT / "reports" / "figures" / "feature_missingness_calibration.png"

EXPERIMENT_XGBOOST_PARAMS = {
    "n_estimators": 140,
    "learning_rate": 0.06,
    "max_depth": 4,
}


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    dataset_name: str
    training_source: str
    numeric_columns: list[str]
    categorical_columns: list[str]
    description: str


EXPERIMENTS = [
    ExperimentConfig(
        name="statsbomb_full_rich_features",
        dataset_name="statsbomb",
        training_source="StatsBomb",
        numeric_columns=BASE_NUMERIC_FEATURES,
        categorical_columns=STATSBOMB_RICH_CATEGORICAL_FEATURES,
        description="StatsBomb rich event feature set with geometry, body part, shot type, pressure, and play pattern.",
    ),
    ExperimentConfig(
        name="statsbomb_geometry_only",
        dataset_name="statsbomb",
        training_source="StatsBomb",
        numeric_columns=BASE_NUMERIC_FEATURES,
        categorical_columns=[],
        description="Only shot location, distance, angle, minute, and period.",
    ),
    ExperimentConfig(
        name="statsbomb_understat_style_reduced",
        dataset_name="statsbomb",
        training_source="StatsBomb",
        numeric_columns=BASE_NUMERIC_FEATURES,
        categorical_columns=["body_part", "shot_type", "play_pattern"],
        description="StatsBomb rows reduced to the kind of context Understat generally has.",
    ),
    ExperimentConfig(
        name="understat_only_reduced_features",
        dataset_name="understat",
        training_source="Understat",
        numeric_columns=BASE_NUMERIC_FEATURES,
        categorical_columns=UNDERSTAT_CATEGORICAL_FEATURES,
        description="Understat shot-level model with lighter shot context and no pressure feature.",
    ),
    ExperimentConfig(
        name="combined_source_shared_features",
        dataset_name="combined",
        training_source="StatsBomb + Understat",
        numeric_columns=BASE_NUMERIC_FEATURES,
        categorical_columns=SHARED_CATEGORICAL_FEATURES,
        description="Combined source model using only harmonized shared features plus data_source.",
    ),
]


def ensure_feature_files() -> None:
    """Build standardized feature files if they are not present yet."""
    if STATSBOMB_FEATURES_FILE.exists() and UNDERSTAT_FEATURES_FILE.exists() and COMBINED_FEATURES_FILE.exists():
        return

    statsbomb_features, understat_features, combined_features = build_combined_features()
    STATSBOMB_FEATURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    statsbomb_features.to_csv(STATSBOMB_FEATURES_FILE, index=False)
    understat_features.to_csv(UNDERSTAT_FEATURES_FILE, index=False)
    combined_features.to_csv(COMBINED_FEATURES_FILE, index=False)


def load_datasets() -> dict[str, pd.DataFrame]:
    """Load feature datasets for all experiments."""
    ensure_feature_files()
    return {
        "statsbomb": pd.read_csv(STATSBOMB_FEATURES_FILE, low_memory=False),
        "understat": pd.read_csv(UNDERSTAT_FEATURES_FILE, low_memory=False),
        "combined": pd.read_csv(COMBINED_FEATURES_FILE, low_memory=False),
    }


def run_experiment(config: ExperimentConfig, dataset: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Train one ablation experiment and return report row plus predictions."""
    feature_columns = [*config.numeric_columns, *config.categorical_columns]
    reference_available, reference_missing_pct = reference_feature_availability(feature_columns)
    model_path = PROJECT_ROOT / "models" / f"{config.name}.joblib"
    predictions_path = PREDICTIONS_DIR / f"{config.name}_predictions.csv"

    _, metrics, predictions = train_evaluate_save_model(
        df=dataset,
        numeric_columns=config.numeric_columns,
        categorical_columns=config.categorical_columns,
        model_name=config.name,
        model_path=model_path,
        predictions_path=predictions_path,
        extra_prediction_columns=[
            "data_source",
            "player",
            "team",
            "league",
            "season",
            "source_xg",
        ],
        params=EXPERIMENT_XGBOOST_PARAMS,
    )

    row = add_row_metadata(
        metrics,
        model_name=config.name,
        training_source=config.training_source,
        dataset_name=config.dataset_name,
        evaluation_scope="heldout_same_source_split",
        actual_feature_count=len(feature_columns),
        reference_features_available=reference_available,
        reference_features_missing_pct=reference_missing_pct,
        predictions_file=str(predictions_path.relative_to(PROJECT_ROOT)),
        description=config.description,
    )
    return row, predictions


def main() -> None:
    """Run feature-richness and missing-context xG experiments."""
    datasets = load_datasets()
    rows: list[dict] = []
    calibration_frames: list[tuple[str, pd.DataFrame]] = []

    for config in EXPERIMENTS:
        print(f"Running experiment: {config.name}")
        row, predictions = run_experiment(config, datasets[config.dataset_name])
        rows.append(row)
        calibration_frames.append((config.name, predictions))

    report = write_metrics_report(rows, REPORT_FILE)
    plot_calibration_curves(calibration_frames, CALIBRATION_FILE)

    print("")
    print("Feature Missingness Experiment")
    print("=" * 32)
    display_columns = [
        "model_name",
        "training_source",
        "actual_feature_count",
        "reference_features_missing_pct",
        "log_loss",
        "brier_score",
        "roc_auc",
        "accuracy_at_0_5",
    ]
    print(report[display_columns].to_string(index=False))
    print(f"Saved report to: {REPORT_FILE}")
    print(f"Saved calibration plot to: {CALIBRATION_FILE}")


if __name__ == "__main__":
    main()
