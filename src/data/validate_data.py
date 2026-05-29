from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHOTS_FILE = PROJECT_ROOT / "data" / "processed" / "shots.csv"
REPORT_FILE = PROJECT_ROOT / "reports" / "data_validation_report.txt"

REQUIRED_COLUMNS = [
    "match_id",
    "team",
    "player",
    "minute",
    "shot_x",
    "shot_y",
    "shot_outcome",
    "is_goal",
]

METADATA_COLUMNS = [
    "competition_name",
    "season_name",
    "match_date",
    "home_team",
    "away_team",
]

IMPORTANT_COLUMNS = REQUIRED_COLUMNS + METADATA_COLUMNS
DUPLICATE_COLUMNS = ["match_id", "player", "minute", "second", "shot_x", "shot_y"]


def _format_unique_values(df: pd.DataFrame, column: str) -> str:
    values = sorted(df[column].dropna().astype(str).unique())
    return ", ".join(values) if values else "None found"


def _is_binary(series: pd.Series) -> bool:
    values = set(series.dropna().unique())
    valid_values = {True, False, 0, 1, "True", "False", "true", "false", "0", "1"}
    return values.issubset(valid_values)


def build_validation_report(df: pd.DataFrame) -> str:
    """Build a validation report for the enriched shots dataset."""
    report_lines = []
    warnings = []

    missing_required = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    missing_metadata = [column for column in METADATA_COLUMNS if column not in df.columns]

    report_lines.append("World Cup xG Lab Data Validation Report")
    report_lines.append("=" * 41)
    report_lines.append(f"Number of rows: {len(df):,}")

    if "match_id" in df.columns:
        report_lines.append(f"Number of unique matches: {df['match_id'].nunique():,}")
    else:
        report_lines.append("Number of unique matches: match_id column not found")

    if "team" in df.columns:
        report_lines.append(f"Number of unique teams: {df['team'].nunique():,}")
    else:
        report_lines.append("Number of unique teams: team column not found")

    if "player" in df.columns:
        report_lines.append(f"Number of unique players: {df['player'].nunique():,}")
    else:
        report_lines.append("Number of unique players: player column not found")

    if "is_goal" in df.columns:
        goal_rate = pd.to_numeric(df["is_goal"], errors="coerce").mean()
        report_lines.append(f"Goal rate: {goal_rate:.2%}")
    else:
        report_lines.append("Goal rate: is_goal column not found")

    if "competition_name" in df.columns:
        report_lines.append(
            f"Unique competitions: {df['competition_name'].nunique():,}"
        )
        report_lines.append(
            f"Competitions: {_format_unique_values(df, 'competition_name')}"
        )

    if "season_name" in df.columns:
        report_lines.append(f"Unique seasons: {df['season_name'].nunique():,}")
        report_lines.append(f"Seasons: {_format_unique_values(df, 'season_name')}")

    if "match_date" in df.columns:
        parsed_dates = pd.to_datetime(df["match_date"], errors="coerce")
        invalid_dates = df["match_date"].notna() & parsed_dates.isna()

        if invalid_dates.any():
            warnings.append(
                f"match_date exists but {invalid_dates.sum():,} values could not be parsed as dates."
            )

        if parsed_dates.notna().any():
            report_lines.append(f"Earliest match_date: {parsed_dates.min().date()}")
            report_lines.append(f"Latest match_date: {parsed_dates.max().date()}")
        else:
            report_lines.append("Earliest match_date: no valid dates found")
            report_lines.append("Latest match_date: no valid dates found")

    if missing_required:
        warnings.append(f"Missing required columns: {', '.join(missing_required)}")

    if missing_metadata:
        warnings.append(
            f"Match metadata columns are missing: {', '.join(missing_metadata)}"
        )

    available_metadata = [column for column in METADATA_COLUMNS if column in df.columns]
    metadata_missing_counts = df[available_metadata].isna().sum() if available_metadata else pd.Series(dtype=int)
    metadata_columns_with_missing_values = metadata_missing_counts[
        metadata_missing_counts > 0
    ]

    if not metadata_columns_with_missing_values.empty:
        missing_summary = ", ".join(
            f"{column}={count:,}"
            for column, count in metadata_columns_with_missing_values.items()
        )
        warnings.append(f"Match metadata has missing values: {missing_summary}")

    if len(df) < 100:
        warnings.append("Dataset has fewer than 100 shots.")

    if "match_id" in df.columns and df["match_id"].isna().any():
        warnings.append(f"match_id has {df['match_id'].isna().sum():,} missing values.")

    if "shot_x" in df.columns and df["shot_x"].isna().any():
        warnings.append(f"shot_x has {df['shot_x'].isna().sum():,} missing values.")

    if "shot_y" in df.columns and df["shot_y"].isna().any():
        warnings.append(f"shot_y has {df['shot_y'].isna().sum():,} missing values.")

    if "is_goal" in df.columns and not _is_binary(df["is_goal"]):
        warnings.append("is_goal is not binary.")

    duplicate_columns = [column for column in DUPLICATE_COLUMNS if column in df.columns]
    if "second" not in df.columns:
        duplicate_columns = [column for column in duplicate_columns if column != "second"]

    if duplicate_columns:
        duplicate_count = df.duplicated(subset=duplicate_columns).sum()
        if duplicate_count:
            warnings.append(
                "Duplicate rows found for "
                f"{', '.join(duplicate_columns)}: {duplicate_count:,}"
            )

    report_lines.append("")
    report_lines.append("Missing Value Counts")
    report_lines.append("-" * 20)

    available_important_columns = [
        column for column in IMPORTANT_COLUMNS if column in df.columns
    ]

    if available_important_columns:
        report_lines.append(df[available_important_columns].isna().sum().to_string())
    else:
        report_lines.append("No important columns found")

    report_lines.append("")
    report_lines.append("Warnings")
    report_lines.append("-" * 8)

    if warnings:
        report_lines.extend(f"WARNING: {warning}" for warning in warnings)
    else:
        report_lines.append("No validation warnings found.")

    return "\n".join(report_lines)


def main() -> None:
    """Print and save a validation report for the processed shots dataset."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not SHOTS_FILE.exists():
        raise SystemExit(
            f"Processed shots file not found: {SHOTS_FILE}\n"
            "Run python src/data/ingest_statsbomb.py first."
        )

    shots = pd.read_csv(SHOTS_FILE)
    report = build_validation_report(shots)

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(report + "\n", encoding="utf-8")

    print(report)
    print(f"\nSaved validation report to {REPORT_FILE}")


if __name__ == "__main__":
    main()
