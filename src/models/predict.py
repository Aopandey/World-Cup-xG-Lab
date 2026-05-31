from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_FILE = PROJECT_ROOT / "models" / "xgboost_xg_model.joblib"
FEATURES_FILE = PROJECT_ROOT / "data" / "features" / "shot_features.csv"
SHOTS_FILE = PROJECT_ROOT / "data" / "processed" / "shots.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "predictions" / "all_shots_xg.csv"

MODEL_FEATURE_COLUMNS = [
    "shot_x",
    "shot_y",
    "distance_to_goal",
    "angle_to_goal",
    "minute",
    "period",
    "body_part",
    "shot_type",
    "under_pressure",
    "play_pattern",
]

OUTPUT_COLUMNS = [
    "match_id",
    "team",
    "world_cup_team",
    "player",
    "position",
    "minute",
    "shot_x",
    "shot_y",
    "body_part",
    "shot_type",
    "play_pattern",
    "shot_outcome",
    "competition_name",
    "season_name",
    "match_date",
    "actual_goal",
    "predicted_xg",
    "xg_bucket",
]


def load_model(path: Path = MODEL_FILE):
    """Load the trained XGBoost xG model pipeline."""
    if not path.exists():
        raise FileNotFoundError(
            f"Model file not found: {path}. "
            "Run python src/models/train_xgboost.py first."
        )

    return joblib.load(path)


def load_features(path: Path = FEATURES_FILE) -> pd.DataFrame:
    """Load model-ready shot features."""
    if not path.exists():
        raise FileNotFoundError(
            f"Feature file not found: {path}. "
            "Run python src/features/build_features.py first."
        )

    return pd.read_csv(path)


def load_output_context(features: pd.DataFrame) -> pd.DataFrame:
    """Load richer shot columns for output when the processed shots table exists."""
    if SHOTS_FILE.exists():
        shots = pd.read_csv(SHOTS_FILE)

        if len(shots) == len(features):
            return shots.copy()

        print(
            "WARNING: data/processed/shots.csv row count does not match "
            "data/features/shot_features.csv. Using feature columns only."
        )

    return features.copy()


def add_xg_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """Add low, medium, and high xG buckets."""
    output = df.copy()
    output["xg_bucket"] = pd.cut(
        output["predicted_xg"],
        bins=[-float("inf"), 0.05, 0.20, float("inf")],
        labels=["low", "medium", "high"],
        right=False,
    )

    return output


def build_prediction_dataset(model, features: pd.DataFrame) -> pd.DataFrame:
    """Generate xG predictions and create a dashboard-friendly output table."""
    missing_features = [
        column for column in MODEL_FEATURE_COLUMNS if column not in features.columns
    ]

    if missing_features:
        raise ValueError(f"Missing model feature columns: {', '.join(missing_features)}")

    predicted_xg = model.predict_proba(features[MODEL_FEATURE_COLUMNS])[:, 1]
    output = load_output_context(features)
    output["predicted_xg"] = predicted_xg

    if "is_goal" in output.columns:
        output = output.rename(columns={"is_goal": "actual_goal"})

    output = add_xg_buckets(output)
    available_columns = [column for column in OUTPUT_COLUMNS if column in output.columns]

    return output[available_columns]


def main() -> None:
    """Apply the trained XGBoost xG model to all shots."""
    model = load_model()
    features = load_features()
    predictions = build_prediction_dataset(model, features)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUTPUT_FILE, index=False)

    print(f"Number of rows scored: {len(predictions):,}")
    print(f"Average predicted xG: {predictions['predicted_xg'].mean():.4f}")
    print(f"Saved predictions to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
