from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.data.build_understat_shot_features import (
    OUTPUT_FILE as UNDERSTAT_FEATURES_FILE,
    STANDARD_COLUMNS,
    load_understat_shot_files,
    standardize_understat_shots,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATSBOMB_SHOTS_FILE = PROJECT_ROOT / "data" / "processed" / "shots.csv"
STATSBOMB_FEATURES_FILE = PROJECT_ROOT / "data" / "features" / "statsbomb_model_features.csv"
COMBINED_FEATURES_FILE = PROJECT_ROOT / "data" / "features" / "combined_shot_features.csv"
REPORT_FILE = PROJECT_ROOT / "reports" / "combined_shot_feature_report.txt"


def calculate_distance_to_goal_vectorized(shot_x: pd.Series, shot_y: pd.Series) -> pd.Series:
    """Calculate Euclidean distance to the StatsBomb goal center at x=120, y=40."""
    return np.sqrt((120 - shot_x) ** 2 + (40 - shot_y) ** 2)


def calculate_angle_to_goal_vectorized(shot_x: pd.Series, shot_y: pd.Series) -> pd.Series:
    """Calculate visible angle to goalposts at y=36 and y=44, returned in radians."""
    distance_to_upper_post = np.sqrt((120 - shot_x) ** 2 + (44 - shot_y) ** 2)
    distance_to_lower_post = np.sqrt((120 - shot_x) ** 2 + (36 - shot_y) ** 2)
    goal_width = 8
    denominator = 2 * distance_to_upper_post * distance_to_lower_post
    cosine_angle = (
        (distance_to_upper_post**2 + distance_to_lower_post**2 - goal_width**2)
        / denominator.replace(0, np.nan)
    )
    return np.arccos(cosine_angle.clip(-1, 1))


def standardize_statsbomb_shots(shots: pd.DataFrame) -> pd.DataFrame:
    """Convert processed StatsBomb shots into the shared xG modeling schema."""
    required_columns = [
        "match_id",
        "team",
        "player",
        "minute",
        "shot_x",
        "shot_y",
        "body_part",
        "shot_type",
        "is_goal",
        "under_pressure",
        "play_pattern",
        "period",
    ]
    missing = [column for column in required_columns if column not in shots.columns]
    if missing:
        raise ValueError(f"Missing StatsBomb shot columns: {', '.join(missing)}")

    output = pd.DataFrame(index=shots.index)
    output["data_source"] = "StatsBomb"
    output["source_shot_id"] = shots["match_id"].astype(str) + "-" + shots.index.astype(str)
    output["match_id"] = shots["match_id"].astype(str)
    output["player"] = shots["player"].fillna("Unknown")
    output["team"] = shots["team"].fillna("Unknown")
    output["opponent"] = np.where(
        shots.get("home_team", pd.Series(index=shots.index)).eq(shots["team"]),
        shots.get("away_team", pd.Series("Unknown", index=shots.index)),
        shots.get("home_team", pd.Series("Unknown", index=shots.index)),
    )
    output["competition"] = shots.get("competition_name", pd.Series("StatsBomb Open Data", index=shots.index)).fillna(
        "StatsBomb Open Data"
    )
    output["league"] = output["competition"]
    output["season"] = shots.get("season_name", pd.Series("Unknown", index=shots.index)).fillna("Unknown")
    output["match_date"] = shots.get("match_date", pd.Series(pd.NA, index=shots.index))
    output["minute"] = pd.to_numeric(shots["minute"], errors="coerce")
    output["period"] = pd.to_numeric(shots["period"], errors="coerce").fillna(0).astype(int)
    output["shot_x"] = pd.to_numeric(shots["shot_x"], errors="coerce")
    output["shot_y"] = pd.to_numeric(shots["shot_y"], errors="coerce")
    output["distance_to_goal"] = calculate_distance_to_goal_vectorized(output["shot_x"], output["shot_y"])
    output["angle_to_goal"] = calculate_angle_to_goal_vectorized(output["shot_x"], output["shot_y"])
    output["body_part"] = shots["body_part"].fillna("Unknown")
    output["shot_type"] = shots["shot_type"].fillna("Unknown")
    output["under_pressure"] = shots["under_pressure"].fillna(False).astype(str)
    output["play_pattern"] = shots["play_pattern"].fillna("Unknown")
    output["last_action"] = "Unknown"
    output["assisted_by"] = "Unknown"
    output["home_away"] = np.where(
        shots.get("home_team", pd.Series(index=shots.index)).eq(shots["team"]),
        "Home",
        np.where(shots.get("away_team", pd.Series(index=shots.index)).eq(shots["team"]), "Away", "Unknown"),
    )
    output["is_goal"] = pd.to_numeric(shots["is_goal"], errors="coerce").fillna(0).astype(int)
    output["source_xg"] = np.nan

    for column in [
        "player",
        "team",
        "opponent",
        "competition",
        "league",
        "season",
        "body_part",
        "shot_type",
        "under_pressure",
        "play_pattern",
        "last_action",
        "assisted_by",
        "home_away",
    ]:
        output[column] = output[column].fillna("Unknown").astype(str).replace({"nan": "Unknown"})

    return output[STANDARD_COLUMNS]


def load_or_build_understat_features() -> pd.DataFrame:
    """Load Understat standardized features, building them from raw shots if needed."""
    if UNDERSTAT_FEATURES_FILE.exists():
        return pd.read_csv(UNDERSTAT_FEATURES_FILE)

    raw_understat = load_understat_shot_files()
    features = standardize_understat_shots(raw_understat)
    UNDERSTAT_FEATURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(UNDERSTAT_FEATURES_FILE, index=False)
    return features


def build_combined_features() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build StatsBomb-only, Understat-only, and combined standardized feature tables."""
    if not STATSBOMB_SHOTS_FILE.exists():
        raise FileNotFoundError(
            f"StatsBomb processed shots not found: {STATSBOMB_SHOTS_FILE}. "
            "Run python src/data/ingest_statsbomb.py first."
        )

    statsbomb_shots = pd.read_csv(STATSBOMB_SHOTS_FILE)
    statsbomb_features = standardize_statsbomb_shots(statsbomb_shots)
    understat_features = load_or_build_understat_features()
    combined_features = pd.concat([statsbomb_features, understat_features], ignore_index=True)

    return statsbomb_features, understat_features, combined_features[STANDARD_COLUMNS]


def build_report(
    statsbomb_features: pd.DataFrame,
    understat_features: pd.DataFrame,
    combined_features: pd.DataFrame,
) -> str:
    """Create a report describing source row counts and feature availability."""
    source_counts = combined_features["data_source"].value_counts()
    source_goal_rates = combined_features.groupby("data_source")["is_goal"].mean()
    understat_benchmark_rate = understat_features["source_xg"].notna().mean()

    lines = [
        "Combined Shot Feature Report",
        "============================",
        "",
        f"StatsBomb rows: {len(statsbomb_features):,}",
        f"Understat rows: {len(understat_features):,}",
        f"Combined rows: {len(combined_features):,}",
        "",
        "Rows by source:",
        source_counts.to_string(),
        "",
        "Goal rate by source:",
        source_goal_rates.apply(lambda value: f"{value:.2%}").to_string(),
        "",
        f"Understat rows with source_xg benchmark: {understat_benchmark_rate:.2%}",
        "",
        "Shared model inputs exclude source_xg to avoid leakage.",
    ]
    return "\n".join(lines)


def main() -> None:
    """Build standardized StatsBomb, Understat, and combined shot feature tables."""
    statsbomb_features, understat_features, combined_features = build_combined_features()

    STATSBOMB_FEATURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    statsbomb_features.to_csv(STATSBOMB_FEATURES_FILE, index=False)
    understat_features.to_csv(UNDERSTAT_FEATURES_FILE, index=False)
    combined_features.to_csv(COMBINED_FEATURES_FILE, index=False)

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        build_report(statsbomb_features, understat_features, combined_features),
        encoding="utf-8",
    )

    print(f"Saved StatsBomb standardized features to: {STATSBOMB_FEATURES_FILE}")
    print(f"Saved Understat standardized features to: {UNDERSTAT_FEATURES_FILE}")
    print(f"Saved combined features to: {COMBINED_FEATURES_FILE}")
    print(f"StatsBomb rows: {len(statsbomb_features):,}")
    print(f"Understat rows: {len(understat_features):,}")
    print(f"Combined rows: {len(combined_features):,}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
