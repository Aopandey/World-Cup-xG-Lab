from __future__ import annotations

from pathlib import Path
import sys

import joblib
import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.models.source_modeling import (
    BASE_NUMERIC_FEATURES,
    UNDERSTAT_CATEGORICAL_FEATURES,
    prepare_model_frame,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_FILE = PROJECT_ROOT / "models" / "understat_xg_model.joblib"
FEATURES_FILE = PROJECT_ROOT / "data" / "features" / "understat_model_features.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "predictions" / "all_understat_shots_xg.csv"
MODEL_NAME = "experimental_understat_xg_model"


def load_model():
    """Load the trained experimental Understat xG pipeline."""
    if not MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Understat model not found: {MODEL_FILE}. "
            "Run python src/models/train_understat_xg.py first."
        )
    return joblib.load(MODEL_FILE)


def load_features() -> pd.DataFrame:
    """Load standardized Understat shot features."""
    if not FEATURES_FILE.exists():
        raise FileNotFoundError(
            f"Understat feature file not found: {FEATURES_FILE}. "
            "Run python src/data/build_understat_shot_features.py first."
        )
    return pd.read_csv(FEATURES_FILE, low_memory=False)


def build_prediction_output(features: pd.DataFrame, predicted_xg) -> pd.DataFrame:
    """Create a dashboard-friendly all-shot Understat prediction table."""
    keep_columns = [
        "data_source",
        "source_shot_id",
        "match_id",
        "player",
        "team",
        "opponent",
        "competition",
        "league",
        "season",
        "match_date",
        "minute",
        "period",
        "shot_x",
        "shot_y",
        "distance_to_goal",
        "angle_to_goal",
        "body_part",
        "shot_type",
        "play_pattern",
        "last_action",
        "home_away",
        "is_goal",
        "source_xg",
    ]
    available_columns = [column for column in keep_columns if column in features.columns]
    output = features[available_columns].copy()
    output = output.rename(columns={"is_goal": "actual_goal"})
    output["predicted_xg"] = predicted_xg
    output["model_name"] = MODEL_NAME
    return output


def main() -> None:
    """Apply the experimental Understat xG model to every Understat shot."""
    model = load_model()
    features = load_features()
    model_frame = prepare_model_frame(
        features,
        BASE_NUMERIC_FEATURES,
        UNDERSTAT_CATEGORICAL_FEATURES,
    )
    predicted_xg = model.predict_proba(
        model_frame[BASE_NUMERIC_FEATURES + UNDERSTAT_CATEGORICAL_FEATURES]
    )[:, 1]
    output = build_prediction_output(features, predicted_xg)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_FILE, index=False)

    print(f"Saved all-shot Understat xG predictions to: {OUTPUT_FILE}")
    print(f"Rows: {len(output):,}")
    print(f"Average experimental xG: {output['predicted_xg'].mean():.4f}")
    if "source_xg" in output.columns:
        print(f"Average Understat source xG: {pd.to_numeric(output['source_xg'], errors='coerce').mean():.4f}")


if __name__ == "__main__":
    main()

