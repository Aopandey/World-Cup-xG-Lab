from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_UNDERSTAT_SHOTS_DIR = (
    PROJECT_ROOT / "data" / "understat" / "raw" / "archive_3_shot_data" / "understats"
)
OUTPUT_FILE = PROJECT_ROOT / "data" / "features" / "understat_model_features.csv"
REPORT_FILE = PROJECT_ROOT / "reports" / "understat_shot_feature_report.txt"

STANDARD_COLUMNS = [
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
    "under_pressure",
    "play_pattern",
    "last_action",
    "assisted_by",
    "home_away",
    "is_goal",
    "source_xg",
]


def read_understat_csv(path: Path) -> pd.DataFrame:
    """Read Understat CSV files, including semicolon-delimited archive files."""
    first_line = path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    sep = ";" if first_line.count(";") > first_line.count(",") else ","
    data = pd.read_csv(path, sep=sep, engine="python")
    unnamed_columns = [
        column
        for column in data.columns
        if str(column).startswith("Unnamed") or str(column).strip() == ""
    ]
    return data.drop(columns=unnamed_columns, errors="ignore")


def normalize_understat_coordinate(series: pd.Series) -> pd.Series:
    """Normalize Understat 0-1 coordinates, repairing values like 765 as 0.765."""
    values = pd.to_numeric(series, errors="coerce")
    return values.where(values <= 1, values / 1000)


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


def infer_period(minute: pd.Series) -> pd.Series:
    """Approximate match period from minute when explicit period is unavailable."""
    minute_numeric = pd.to_numeric(minute, errors="coerce")
    period = pd.Series(np.select([minute_numeric <= 45, minute_numeric <= 90], [1, 2], default=3))
    return period.astype(int)


def load_understat_shot_files(raw_dir: Path = RAW_UNDERSTAT_SHOTS_DIR) -> pd.DataFrame:
    """Load every Understat shot_data.csv file from the archive_3 folder."""
    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Understat shot archive folder not found: {raw_dir}. "
            "Place archive (3) shot data under data/understat/raw/archive_3_shot_data/understats/."
        )

    frames = []
    for shot_file in sorted(raw_dir.glob("*/shot_data.csv")):
        league = shot_file.parent.name.replace("_", " ")
        data = read_understat_csv(shot_file)
        if data.empty:
            continue
        data["league"] = league
        frames.append(data)

    if not frames:
        raise FileNotFoundError(f"No Understat shot_data.csv files found in: {raw_dir}")

    return pd.concat(frames, ignore_index=True)


def standardize_understat_shots(shots: pd.DataFrame) -> pd.DataFrame:
    """Convert raw Understat shot rows into the shared xG modeling schema."""
    required_columns = [
        "id",
        "minute",
        "result",
        "X",
        "Y",
        "xG",
        "player",
        "h_a",
        "situation",
        "season",
        "shotType",
        "match_id",
        "h_team",
        "a_team",
        "date",
    ]
    missing = [column for column in required_columns if column not in shots.columns]
    if missing:
        raise ValueError(f"Missing Understat shot columns: {', '.join(missing)}")

    output = pd.DataFrame(index=shots.index)
    output["data_source"] = "Understat"
    output["source_shot_id"] = shots["id"].astype(str)
    output["match_id"] = shots["match_id"].astype(str)
    output["player"] = shots["player"]
    output["team"] = np.where(shots["h_a"].eq("h"), shots["h_team"], shots["a_team"])
    output["opponent"] = np.where(shots["h_a"].eq("h"), shots["a_team"], shots["h_team"])
    output["competition"] = shots["league"]
    output["league"] = shots["league"]
    output["season"] = shots["season"]
    output["match_date"] = pd.to_datetime(shots["date"], errors="coerce").dt.date.astype(str)
    output["minute"] = pd.to_numeric(shots["minute"], errors="coerce")
    output["period"] = infer_period(output["minute"])

    normalized_x = normalize_understat_coordinate(shots["X"])
    normalized_y = normalize_understat_coordinate(shots["Y"])
    output["shot_x"] = normalized_x * 120
    output["shot_y"] = normalized_y * 80
    output["distance_to_goal"] = calculate_distance_to_goal_vectorized(output["shot_x"], output["shot_y"])
    output["angle_to_goal"] = calculate_angle_to_goal_vectorized(output["shot_x"], output["shot_y"])

    output["body_part"] = shots["shotType"].fillna("Unknown")
    output["shot_type"] = shots["shotType"].fillna("Unknown")
    output["under_pressure"] = "Unknown"
    output["play_pattern"] = shots["situation"].fillna("Unknown")
    output["last_action"] = shots.get("lastAction", pd.Series("Unknown", index=shots.index)).fillna("Unknown")
    output["assisted_by"] = shots.get("player_assisted", pd.Series("Unknown", index=shots.index)).fillna("Unknown")
    output["home_away"] = shots["h_a"].map({"h": "Home", "a": "Away"}).fillna("Unknown")
    output["is_goal"] = shots["result"].eq("Goal").astype(int)
    output["source_xg"] = pd.to_numeric(shots["xG"], errors="coerce")

    for column in ["body_part", "shot_type", "play_pattern", "last_action", "assisted_by", "home_away"]:
        output[column] = output[column].astype(str).replace({"nan": "Unknown"})

    return output[STANDARD_COLUMNS]


def build_report(features: pd.DataFrame) -> str:
    """Create a concise feature-build report for the Understat shot dataset."""
    seasons = sorted(features["season"].dropna().astype(str).unique())
    leagues = sorted(features["league"].dropna().astype(str).unique())
    situation_counts = features["play_pattern"].value_counts().head(12)
    body_part_counts = features["body_part"].value_counts().head(12)

    lines = [
        "Understat Shot Feature Report",
        "=============================",
        "",
        f"Rows: {len(features):,}",
        f"Goal rate: {features['is_goal'].mean():.2%}",
        f"Leagues: {', '.join(leagues)}",
        f"Seasons: {', '.join(seasons)}",
        f"Columns: {', '.join(features.columns)}",
        "",
        "Top play patterns/situations:",
        situation_counts.to_string(),
        "",
        "Top body part / shot type values:",
        body_part_counts.to_string(),
        "",
        "Note: source_xg is Understat's published xG and is kept for benchmarking only, not as a model input.",
    ]
    return "\n".join(lines)


def main() -> None:
    """Build and save Understat shot-level features."""
    raw_shots = load_understat_shot_files()
    features = standardize_understat_shots(raw_shots)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(OUTPUT_FILE, index=False)

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(build_report(features), encoding="utf-8")

    print(f"Saved Understat shot features to: {OUTPUT_FILE}")
    print(f"Rows: {len(features):,}")
    print(f"Leagues: {features['league'].nunique():,}")
    print(f"Seasons: {features['season'].nunique():,}")
    print(f"Goal rate: {features['is_goal'].mean():.2%}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
