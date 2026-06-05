from __future__ import annotations

from pathlib import Path
from typing import Iterable

import joblib
import matplotlib
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from src.models.evaluate import evaluate_binary_classifier


RANDOM_STATE = 42
TARGET_COLUMN = "is_goal"

BASE_NUMERIC_FEATURES = [
    "shot_x",
    "shot_y",
    "distance_to_goal",
    "angle_to_goal",
    "minute",
    "period",
]

STATSBOMB_RICH_CATEGORICAL_FEATURES = [
    "body_part",
    "shot_type",
    "under_pressure",
    "play_pattern",
]

UNDERSTAT_CATEGORICAL_FEATURES = [
    "body_part",
    "shot_type",
    "play_pattern",
    "last_action",
    "home_away",
]

SHARED_CATEGORICAL_FEATURES = [
    "body_part",
    "shot_type",
    "play_pattern",
    "data_source",
]

REFERENCE_FEATURES = [
    *BASE_NUMERIC_FEATURES,
    *STATSBOMB_RICH_CATEGORICAL_FEATURES,
]

DEFAULT_XGBOOST_PARAMS = {
    "n_estimators": 200,
    "learning_rate": 0.05,
    "max_depth": 4,
    "subsample": 0.85,
    "colsample_bytree": 0.85,
    "eval_metric": "logloss",
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
    "tree_method": "hist",
}


def ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Ensure modeling columns exist, filling missing categorical-style columns with Unknown."""
    output = df.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = "Unknown"
    return output


def prepare_model_frame(
    df: pd.DataFrame,
    numeric_columns: list[str],
    categorical_columns: list[str],
) -> pd.DataFrame:
    """Prepare feature columns with safe numeric and categorical values."""
    required = [*numeric_columns, *categorical_columns, TARGET_COLUMN]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required model columns: {', '.join(missing)}")

    output = df.copy()
    for column in numeric_columns:
        output[column] = pd.to_numeric(output[column], errors="coerce")
        median = output[column].median()
        output[column] = output[column].fillna(0 if pd.isna(median) else median)

    for column in categorical_columns:
        output[column] = output[column].fillna("Unknown").astype(str)

    output[TARGET_COLUMN] = pd.to_numeric(output[TARGET_COLUMN], errors="coerce").fillna(0).astype(int)
    return output


def build_xgboost_pipeline(
    numeric_columns: list[str],
    categorical_columns: list[str],
    params: dict | None = None,
) -> Pipeline:
    """Create an XGBoost xG model pipeline with one-hot categorical preprocessing."""
    model_params = {**DEFAULT_XGBOOST_PARAMS, **(params or {})}
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", "passthrough", numeric_columns),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_columns),
        ]
    )
    model = XGBClassifier(**model_params)
    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )


def train_evaluate_save_model(
    df: pd.DataFrame,
    numeric_columns: list[str],
    categorical_columns: list[str],
    model_name: str,
    model_path: Path,
    predictions_path: Path,
    extra_prediction_columns: list[str] | None = None,
    params: dict | None = None,
) -> tuple[Pipeline, dict[str, float], pd.DataFrame]:
    """Train a model, save the pipeline and predictions, and return metrics."""
    model_frame = prepare_model_frame(df, numeric_columns, categorical_columns)
    feature_columns = [*numeric_columns, *categorical_columns]
    x = model_frame[feature_columns]
    y = model_frame[TARGET_COLUMN]

    x_train, x_test, y_train, y_test, metadata_train, metadata_test = train_test_split(
        x,
        y,
        model_frame,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    pipeline = build_xgboost_pipeline(numeric_columns, categorical_columns, params=params)
    pipeline.fit(x_train, y_train)
    predicted_xg = pipeline.predict_proba(x_test)[:, 1]
    metrics = evaluate_binary_classifier(y_test, predicted_xg)

    predictions = pd.DataFrame(
        {
            "actual_goal": y_test.astype(int).to_numpy(),
            "predicted_xg": predicted_xg,
            "model_name": model_name,
        }
    )

    for column in extra_prediction_columns or []:
        if column in metadata_test.columns:
            predictions[column] = metadata_test[column].to_numpy()

    model_path.parent.mkdir(parents=True, exist_ok=True)
    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)
    predictions.to_csv(predictions_path, index=False)

    metrics = {
        **metrics,
        "train_rows": float(len(x_train)),
        "test_rows": float(len(x_test)),
        "feature_count": float(len(feature_columns)),
    }
    return pipeline, metrics, predictions


def evaluate_predictions_frame(
    predictions: pd.DataFrame,
    probability_column: str = "predicted_xg",
) -> dict[str, float]:
    """Evaluate a saved predictions DataFrame."""
    return evaluate_binary_classifier(
        predictions["actual_goal"].astype(int),
        predictions[probability_column].astype(float),
    )


def metrics_by_group(
    predictions: pd.DataFrame,
    group_column: str,
    probability_column: str = "predicted_xg",
) -> pd.DataFrame:
    """Evaluate predictions overall and by a grouping column such as data_source."""
    rows = [
        {
            "group": "overall",
            "rows": len(predictions),
            **evaluate_predictions_frame(predictions, probability_column),
        }
    ]

    if group_column in predictions.columns:
        for group_value, group_df in predictions.groupby(group_column):
            if group_df["actual_goal"].nunique() < 2:
                continue
            rows.append(
                {
                    "group": group_value,
                    "rows": len(group_df),
                    **evaluate_predictions_frame(group_df, probability_column),
                }
            )

    return pd.DataFrame(rows)


def reference_feature_availability(feature_columns: list[str]) -> tuple[int, float]:
    """Compare a feature set against the StatsBomb-rich reference feature list."""
    available = len(set(feature_columns).intersection(REFERENCE_FEATURES))
    missing_pct = 1 - (available / len(REFERENCE_FEATURES))
    return available, missing_pct


def plot_calibration_curves(
    prediction_frames: list[tuple[str, pd.DataFrame]],
    save_path: Path,
    probability_column: str = "predicted_xg",
    n_bins: int = 10,
) -> None:
    """Save a calibration plot for one or more model prediction frames."""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 6))
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect calibration")

    for label, predictions in prediction_frames:
        if predictions.empty or predictions["actual_goal"].nunique() < 2:
            continue
        y_true = predictions["actual_goal"].astype(int)
        y_prob = predictions[probability_column].astype(float).clip(0, 1)
        fraction_of_positives, mean_predicted_value = calibration_curve(
            y_true,
            y_prob,
            n_bins=n_bins,
            strategy="quantile",
        )
        plt.plot(mean_predicted_value, fraction_of_positives, marker="o", label=label)

    plt.title("xG Model Calibration")
    plt.xlabel("Mean predicted xG")
    plt.ylabel("Observed goal rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=160)
    plt.close()


def add_row_metadata(metrics: dict[str, float], **metadata) -> dict:
    """Combine model metrics with report metadata."""
    return {**metadata, **metrics}


def write_metrics_report(rows: list[dict], output_path: Path) -> pd.DataFrame:
    """Write a metrics table and return it."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = pd.DataFrame(rows)
    report.to_csv(output_path, index=False)
    return report


def clip_probability(values: pd.Series) -> pd.Series:
    """Keep benchmark probability columns inside the valid 0-1 range."""
    return pd.to_numeric(values, errors="coerce").fillna(0).clip(0, 1)
