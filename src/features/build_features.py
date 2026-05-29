from pathlib import Path
import sys

import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.features.geometry import calculate_angle_to_goal, calculate_distance_to_goal


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHOTS_FILE = PROJECT_ROOT / "data" / "processed" / "shots.csv"
FEATURES_FILE = PROJECT_ROOT / "data" / "features" / "shot_features.csv"

NUMERIC_FEATURES = [
    "shot_x",
    "shot_y",
    "distance_to_goal",
    "angle_to_goal",
    "minute",
    "period",
]

CATEGORICAL_FEATURES = [
    "body_part",
    "shot_type",
    "under_pressure",
    "play_pattern",
]

TARGET_COLUMN = "is_goal"
MODEL_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET_COLUMN]


def add_geometry_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add shot distance and goal angle features."""
    features = df.copy()
    features["distance_to_goal"] = features.apply(
        lambda row: calculate_distance_to_goal(row["shot_x"], row["shot_y"]),
        axis=1,
    )
    features["angle_to_goal"] = features.apply(
        lambda row: calculate_angle_to_goal(row["shot_x"], row["shot_y"]),
        axis=1,
    )

    return features


def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Fill categorical values with Unknown and numeric values with medians."""
    features = df.copy()

    for column in CATEGORICAL_FEATURES:
        features[column] = features[column].fillna("Unknown")

    for column in NUMERIC_FEATURES:
        features[column] = pd.to_numeric(features[column], errors="coerce")
        features[column] = features[column].fillna(features[column].median())

    return features


def build_feature_dataset(shots: pd.DataFrame) -> pd.DataFrame:
    """Create the final modeling feature dataset from processed shots."""
    missing_columns = [
        column for column in ["shot_x", "shot_y", *CATEGORICAL_FEATURES, "minute", "period", TARGET_COLUMN]
        if column not in shots.columns
    ]

    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    features = add_geometry_features(shots)
    features = features[MODEL_COLUMNS].copy()
    features = fill_missing_values(features)

    return features


def main() -> None:
    """Build and save model-ready shot features."""
    if not SHOTS_FILE.exists():
        raise SystemExit(
            f"Processed shots file not found: {SHOTS_FILE}\n"
            "Run python src/data/ingest_statsbomb.py first."
        )

    shots = pd.read_csv(SHOTS_FILE)
    features = build_feature_dataset(shots)

    FEATURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(FEATURES_FILE, index=False)

    print(f"Number of rows: {len(features):,}")
    print(f"Number of features: {len(features.columns) - 1:,}")
    print(f"Target goal rate: {features[TARGET_COLUMN].mean():.2%}")
    print(f"Saved output path: {FEATURES_FILE}")


if __name__ == "__main__":
    main()
