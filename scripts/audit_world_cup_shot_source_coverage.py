from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.data.player_matching import MATCH_NONE, match_player_to_fbref, normalize_name


SQUADS_FILE = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
STATSBOMB_FEATURES_FILE = PROJECT_ROOT / "data" / "features" / "statsbomb_model_features.csv"
UNDERSTAT_FEATURES_FILE = PROJECT_ROOT / "data" / "features" / "understat_model_features.csv"
DETAILED_OUTPUT_FILE = PROJECT_ROOT / "reports" / "world_cup_shot_source_coverage.csv"
SUMMARY_OUTPUT_FILE = PROJECT_ROOT / "reports" / "world_cup_shot_source_coverage.txt"


def load_source_features(path: Path, source_name: str) -> pd.DataFrame:
    """Load source shot features and summarize them at player level for fast matching."""
    if not path.exists():
        print(f"Warning: {source_name} feature file not found at {path}")
        return pd.DataFrame(columns=["player", "player_normalized"])

    data = pd.read_csv(path, low_memory=False)
    if "player" not in data.columns:
        print(f"Warning: {source_name} feature file has no player column.")
        return pd.DataFrame(columns=["player", "player_normalized"])

    data["player_normalized"] = data["player"].apply(normalize_name)
    summary = (
        data.groupby("player_normalized", dropna=False)
        .agg(
            player=("player", "first"),
            shot_count=("player", "size"),
        )
        .reset_index()
    )
    return summary


def source_match_summary(
    squad_row: pd.Series,
    source_df: pd.DataFrame,
) -> tuple[bool, int, str, str | None]:
    """Match one squad player to a source shot table and return coverage details."""
    match = match_player_to_fbref(
        squad_row["player"],
        source_df,
        selected_team=squad_row.get("world_cup_team"),
        selected_position=squad_row.get("position_group"),
    )
    matched = match["confidence"] != MATCH_NONE and not match["rows"].empty
    if not matched:
        return False, 0, MATCH_NONE, None

    rows = match["rows"]
    shot_count = int(pd.to_numeric(rows.get("shot_count", pd.Series([len(rows)])), errors="coerce").fillna(0).sum())
    return True, shot_count, match["confidence"], match["matched_player"]


def classify_coverage(has_statsbomb: bool, has_understat: bool) -> str:
    """Classify a player's shot-level source coverage."""
    if has_statsbomb and has_understat:
        return "both"
    if has_statsbomb:
        return "statsbomb_only"
    if has_understat:
        return "understat_only"
    return "neither"


def build_coverage_table(
    squads: pd.DataFrame,
    statsbomb_features: pd.DataFrame,
    understat_features: pd.DataFrame,
) -> pd.DataFrame:
    """Build player-level World Cup shot-source coverage details."""
    rows = []
    for _, squad_row in squads.iterrows():
        has_statsbomb, statsbomb_shots, statsbomb_confidence, statsbomb_match = source_match_summary(
            squad_row,
            statsbomb_features,
        )
        has_understat, understat_shots, understat_confidence, understat_match = source_match_summary(
            squad_row,
            understat_features,
        )
        rows.append(
            {
                "world_cup_team": squad_row.get("world_cup_team"),
                "player": squad_row.get("player"),
                "position_group": squad_row.get("position_group"),
                "club": squad_row.get("club"),
                "league": squad_row.get("league"),
                "coverage_bucket": classify_coverage(has_statsbomb, has_understat),
                "has_statsbomb_shots": has_statsbomb,
                "statsbomb_shots": statsbomb_shots,
                "statsbomb_match_confidence": statsbomb_confidence,
                "statsbomb_matched_player": statsbomb_match,
                "has_understat_shots": has_understat,
                "understat_shots": understat_shots,
                "understat_match_confidence": understat_confidence,
                "understat_matched_player": understat_match,
            }
        )

    return pd.DataFrame(rows)


def build_summary_report(coverage: pd.DataFrame) -> str:
    """Build a readable text summary of shot-source coverage."""
    bucket_counts = coverage["coverage_bucket"].value_counts()
    attackers_midfielders = coverage[coverage["position_group"].isin(["Forward", "Midfielder"])]
    am_bucket_counts = attackers_midfielders["coverage_bucket"].value_counts()
    top_understat_only = coverage[coverage["coverage_bucket"].eq("understat_only")].sort_values(
        "understat_shots",
        ascending=False,
    )
    top_both = coverage[coverage["coverage_bucket"].eq("both")].sort_values(
        ["understat_shots", "statsbomb_shots"],
        ascending=False,
    )

    lines = [
        "World Cup Shot-Source Coverage",
        "==============================",
        "",
        f"Total squad players: {len(coverage):,}",
        f"Players with StatsBomb shots: {coverage['has_statsbomb_shots'].sum():,}",
        f"Players with Understat shots: {coverage['has_understat_shots'].sum():,}",
        "",
        "Coverage buckets:",
        bucket_counts.to_string(),
        "",
        f"Midfielders/forwards: {len(attackers_midfielders):,}",
        "Midfielder/forward coverage buckets:",
        am_bucket_counts.to_string(),
        "",
        "Top Understat-only shot coverage players:",
        top_understat_only[
            ["world_cup_team", "player", "position_group", "club", "understat_shots"]
        ]
        .head(20)
        .to_string(index=False),
        "",
        "Top players covered by both sources:",
        top_both[
            [
                "world_cup_team",
                "player",
                "position_group",
                "statsbomb_shots",
                "understat_shots",
            ]
        ]
        .head(20)
        .to_string(index=False),
    ]
    return "\n".join(lines)


def main() -> None:
    """Audit World Cup squad player coverage across StatsBomb and Understat shot-level data."""
    if not SQUADS_FILE.exists():
        raise FileNotFoundError(f"Squad file not found: {SQUADS_FILE}")

    squads = pd.read_csv(SQUADS_FILE)
    statsbomb_features = load_source_features(STATSBOMB_FEATURES_FILE, "StatsBomb")
    understat_features = load_source_features(UNDERSTAT_FEATURES_FILE, "Understat")
    coverage = build_coverage_table(squads, statsbomb_features, understat_features)

    DETAILED_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(DETAILED_OUTPUT_FILE, index=False)
    SUMMARY_OUTPUT_FILE.write_text(build_summary_report(coverage), encoding="utf-8")

    print(f"Saved detailed coverage to: {DETAILED_OUTPUT_FILE}")
    print(f"Saved summary report to: {SUMMARY_OUTPUT_FILE}")
    print("")
    print(build_summary_report(coverage))


if __name__ == "__main__":
    main()
