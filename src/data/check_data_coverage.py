from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHOTS_FILE = PROJECT_ROOT / "data" / "processed" / "shots.csv"
REPORT_FILE = PROJECT_ROOT / "reports" / "data_coverage_report.txt"

DATE_COLUMN = "match_date"
SEASON_COLUMN = "season_name"
COMPETITION_COLUMN = "competition_name"
PREVIEW_COLUMNS = [
    "match_id",
    "team",
    "player",
    "minute",
    "match_date",
    "season_name",
    "competition_name",
]


def _format_unique_values(df: pd.DataFrame, column: str) -> str:
    values = sorted(df[column].dropna().astype(str).unique())
    return ", ".join(values) if values else "None found"


def build_coverage_report(df: pd.DataFrame) -> str:
    """Build a text report describing shot dataset coverage."""
    report_lines = []
    has_match_date = DATE_COLUMN in df.columns
    has_season = SEASON_COLUMN in df.columns
    has_competition = COMPETITION_COLUMN in df.columns

    report_lines.append("World Cup xG Lab Data Coverage Report")
    report_lines.append("=" * 39)
    report_lines.append(f"Number of rows: {len(df):,}")

    if "match_id" in df.columns:
        report_lines.append(f"Number of matches: {df['match_id'].nunique():,}")
    else:
        report_lines.append("Number of matches: match_id column not found")

    if "team" in df.columns:
        report_lines.append(f"Unique teams: {df['team'].nunique():,}")
    else:
        report_lines.append("Unique teams: team column not found")

    if has_competition:
        report_lines.append(f"Unique competitions: {df[COMPETITION_COLUMN].nunique():,}")
    else:
        report_lines.append("Unique competitions: competition_name column not found")

    if has_season:
        report_lines.append(f"Unique seasons: {df[SEASON_COLUMN].nunique():,}")
    else:
        report_lines.append("Unique seasons: season_name column not found")

    if has_match_date:
        dates = pd.to_datetime(df[DATE_COLUMN], errors="coerce")
        if dates.notna().any():
            report_lines.append(f"Earliest match_date: {dates.min().date()}")
            report_lines.append(f"Latest match_date: {dates.max().date()}")
        else:
            report_lines.append("Earliest match_date: no valid dates found")
            report_lines.append("Latest match_date: no valid dates found")
    else:
        report_lines.append("Earliest match_date: match_date column not found")
        report_lines.append("Latest match_date: match_date column not found")

    if not has_match_date and not has_season:
        report_lines.append(
            "WARNING: Cannot verify season coverage because no date/season column exists. "
            "Add match metadata during ingestion."
        )

    if has_season:
        report_lines.append(f"Seasons: {_format_unique_values(df, SEASON_COLUMN)}")

    if has_competition:
        report_lines.append(f"Competitions: {_format_unique_values(df, COMPETITION_COLUMN)}")

    report_lines.append("")
    report_lines.append("Top 20 teams by shot count")
    report_lines.append("-" * 27)

    if "team" in df.columns:
        team_counts = df["team"].value_counts().head(20)
        report_lines.append(team_counts.to_string())
    else:
        report_lines.append("team column not found")

    report_lines.append("")
    report_lines.append("Top competitions by shot count")
    report_lines.append("-" * 30)

    if has_competition:
        competition_counts = df[COMPETITION_COLUMN].value_counts().head(20)
        report_lines.append(competition_counts.to_string())
    else:
        report_lines.append("competition_name column not found")

    report_lines.append("")
    report_lines.append("Top seasons by shot count")
    report_lines.append("-" * 25)

    if has_season:
        season_counts = df[SEASON_COLUMN].value_counts().head(20)
        report_lines.append(season_counts.to_string())
    else:
        report_lines.append("season_name column not found")

    preview_columns = [column for column in PREVIEW_COLUMNS if column in df.columns]

    report_lines.append("")
    report_lines.append("First 10 rows")
    report_lines.append("-" * 13)

    if preview_columns:
        report_lines.append(df[preview_columns].head(10).to_string(index=False))
    else:
        report_lines.append("No preview columns found")

    return "\n".join(report_lines)


def main() -> None:
    """Print and save a coverage report for the processed shots dataset."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not SHOTS_FILE.exists():
        raise SystemExit(
            f"Processed shots file not found: {SHOTS_FILE}\n"
            "Run python src/data/ingest_statsbomb.py first."
        )

    shots = pd.read_csv(SHOTS_FILE)
    report = build_coverage_report(shots)

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(report + "\n", encoding="utf-8")

    print(report)
    print(f"\nSaved coverage report to {REPORT_FILE}")


if __name__ == "__main__":
    main()
