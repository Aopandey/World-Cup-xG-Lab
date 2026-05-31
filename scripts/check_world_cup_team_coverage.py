from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.data.world_cup_filter import filter_world_cup_teams, load_world_cup_teams

import pandas as pd


PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "all_shots_xg.csv"
SHOTS_FILE = PROJECT_ROOT / "data" / "processed" / "shots.csv"
REPORT_FILE = PROJECT_ROOT / "reports" / "world_cup_team_coverage.txt"


def load_available_shot_data() -> pd.DataFrame:
    """Load predictions if available, otherwise processed shots."""
    if PREDICTIONS_FILE.exists():
        print(f"Reading {PREDICTIONS_FILE}")
        return pd.read_csv(PREDICTIONS_FILE)

    if SHOTS_FILE.exists():
        print(f"Reading {SHOTS_FILE}")
        return pd.read_csv(SHOTS_FILE)

    raise FileNotFoundError(
        "No shot data found. Expected data/predictions/all_shots_xg.csv "
        "or data/processed/shots.csv."
    )


def build_coverage_report(df: pd.DataFrame) -> str:
    """Build a text report for 2026 World Cup team coverage."""
    qualified_teams = load_world_cup_teams()
    filtered = filter_world_cup_teams(df)
    found_teams = sorted(filtered["world_cup_team"].dropna().unique())
    missing_teams = sorted(set(qualified_teams) - set(found_teams))
    shot_counts = filtered["world_cup_team"].value_counts().sort_index()

    lines = [
        "2026 World Cup Team Coverage",
        "=" * 28,
        f"Total 2026 World Cup teams in config: {len(qualified_teams)}",
        f"Number of World Cup teams found in dataset: {len(found_teams)}",
        "",
        "Found teams:",
        ", ".join(found_teams) if found_teams else "None",
        "",
        "Missing teams:",
        ", ".join(missing_teams) if missing_teams else "None",
        "",
        "Shot count by found team:",
        shot_counts.to_string() if not shot_counts.empty else "None",
    ]

    return "\n".join(lines)


def main() -> None:
    """Print and save the World Cup team coverage report."""
    df = load_available_shot_data()
    report = build_coverage_report(df)

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(report + "\n", encoding="utf-8")

    print(report)
    print(f"\nSaved report to {REPORT_FILE}")


if __name__ == "__main__":
    main()
