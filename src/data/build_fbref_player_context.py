from pathlib import Path
import re

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "fbref" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "fbref" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "fbref_player_context.csv"

RAW_FILES = {
    "standard": "player_season_standard.csv",
    "shooting": "player_season_shooting.csv",
    "playing_time": "player_season_playing_time.csv",
    "misc": "player_season_misc.csv",
}

KEY_COLUMNS = ["player", "team", "league", "season"]
DISPLAY_COLUMNS = [
    "player",
    "team",
    "league",
    "season",
    "nation",
    "pos",
    "age",
    "minutes",
    "matches_played",
    "starts",
    "goals",
    "assists",
    "shots",
    "shots_on_target",
    "shots_per_90",
    "shots_on_target_per_90",
    "goals_per_shot",
    "goals_per_shot_on_target",
    "xg",
    "npxg",
    "xg_per_90",
    "npxg_per_90",
    "data_source",
]

USEFUL_COLUMN_CANDIDATES = {
    "nation": ["nation"],
    "pos": ["pos", "position"],
    "age": ["age"],
    "minutes": ["playing_time_min", "minutes", "min"],
    "matches_played": ["playing_time_mp", "mp", "matches_played", "matches"],
    "starts": ["playing_time_starts", "starts_starts", "starts"],
    "goals": ["standard_gls", "performance_gls", "gls", "goals"],
    "assists": ["performance_ast", "standard_ast", "ast", "assists"],
    "shots": ["standard_sh", "sh", "shots"],
    "shots_on_target": ["standard_sot", "sot", "shots_on_target"],
    "shots_per_90": ["standard_sh_per_90", "sh_per_90", "shots_per_90"],
    "shots_on_target_per_90": [
        "standard_sot_per_90",
        "sot_per_90",
        "shots_on_target_per_90",
    ],
    "goals_per_shot": ["standard_g_per_sh", "g_per_sh", "goals_per_shot"],
    "goals_per_shot_on_target": [
        "standard_g_per_sot",
        "g_per_sot",
        "goals_per_shot_on_target",
    ],
    "xg": ["expected_xg", "standard_xg", "xg"],
    "npxg": ["expected_npxg", "standard_npxg", "npxg"],
    "xg_per_90": ["expected_xg_per_90", "per_90_minutes_xg", "xg_per_90"],
    "npxg_per_90": [
        "expected_npxg_per_90",
        "per_90_minutes_npxg",
        "npxg_per_90",
    ],
}

NUMERIC_COLUMNS = [
    "age",
    "minutes",
    "matches_played",
    "starts",
    "goals",
    "assists",
    "shots",
    "shots_on_target",
    "shots_per_90",
    "shots_on_target_per_90",
    "goals_per_shot",
    "goals_per_shot_on_target",
    "xg",
    "npxg",
    "xg_per_90",
    "npxg_per_90",
]


def normalize_column_name(column: str) -> str:
    """Normalize a column name for flexible matching."""
    column = str(column).strip().lower()
    column = column.replace("%", "pct")
    column = re.sub(r"[^a-z0-9]+", "_", column)
    column = re.sub(r"_+", "_", column)
    return column.strip("_")


def load_raw_tables(raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Load whichever FBref raw files are available."""
    tables = {}

    if not raw_dir.exists():
        raise FileNotFoundError(
            f"FBref raw folder was not found: {raw_dir}. "
            "Run python src/data/ingest_fbref.py first."
        )

    for stat_type, filename in RAW_FILES.items():
        path = raw_dir / filename
        if not path.exists():
            print(f"WARNING: Missing optional FBref raw file: {path}")
            continue

        df = pd.read_csv(path)
        df.columns = [normalize_column_name(column) for column in df.columns]
        tables[stat_type] = df
        print(f"Loaded {stat_type}: {len(df):,} rows, {len(df.columns):,} columns")

    if not tables:
        raise FileNotFoundError(
            f"No FBref raw CSV files were found in {raw_dir}. "
            "Run python src/data/ingest_fbref.py first."
        )

    return tables


def prepare_table_for_merge(stat_type: str, df: pd.DataFrame) -> pd.DataFrame | None:
    """Keep merge keys and prefix non-key columns with the stat table name."""
    missing_keys = [column for column in KEY_COLUMNS if column not in df.columns]

    if missing_keys:
        print(
            f"WARNING: Skipping {stat_type} table because merge keys are missing: "
            f"{missing_keys}"
        )
        return None

    prepared = df.copy()
    prepared = prepared.drop_duplicates(subset=KEY_COLUMNS)
    rename_map = {
        column: f"{stat_type}__{column}"
        for column in prepared.columns
        if column not in KEY_COLUMNS
    }

    return prepared.rename(columns=rename_map)


def merge_raw_tables(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Outer-merge available FBref tables at player/team/league/season level."""
    merged = None

    for stat_type, df in tables.items():
        prepared = prepare_table_for_merge(stat_type, df)
        if prepared is None:
            continue

        if merged is None:
            merged = prepared
        else:
            merged = merged.merge(prepared, on=KEY_COLUMNS, how="outer")

    if merged is None:
        raise ValueError("No FBref tables had the required player/team/league/season keys.")

    return merged


def column_base_name(column: str) -> str:
    """Remove the stat-table prefix from a merged FBref column name."""
    return str(column).split("__", 1)[-1]


def find_matching_columns(columns: list[str], candidates: list[str]) -> list[str]:
    """Find columns by exact normalized names first, then by token containment."""
    normalized_candidates = [normalize_column_name(candidate) for candidate in candidates]
    matches = []

    for candidate in normalized_candidates:
        for column in columns:
            normalized_full = normalize_column_name(column)
            normalized_base = normalize_column_name(column_base_name(column))

            if normalized_full == candidate or normalized_base == candidate:
                matches.append(column)

    if matches:
        return list(dict.fromkeys(matches))

    for candidate in normalized_candidates:
        candidate_tokens = [token for token in candidate.split("_") if token]

        for column in columns:
            normalized_base = normalize_column_name(column_base_name(column))

            if candidate_tokens and all(token in normalized_base for token in candidate_tokens):
                matches.append(column)

    return list(dict.fromkeys(matches))


def coalesce_columns(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Return the first non-null value from a list of matching columns."""
    if not columns:
        return pd.Series([pd.NA] * len(df), index=df.index)

    result = df[columns[0]].copy()

    for column in columns[1:]:
        result = result.combine_first(df[column])

    return result


def build_clean_context(merged: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Create the dashboard-friendly FBref player context table."""
    output = merged[KEY_COLUMNS].copy()
    missing_useful_columns = []

    for output_column, candidates in USEFUL_COLUMN_CANDIDATES.items():
        matching_columns = find_matching_columns(list(merged.columns), candidates)

        if not matching_columns:
            print(f"WARNING: Missing useful FBref column for {output_column}")
            missing_useful_columns.append(output_column)
            output[output_column] = pd.NA
            continue

        output[output_column] = coalesce_columns(merged, matching_columns)

    for column in NUMERIC_COLUMNS:
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce")

    output["data_source"] = "FBref"
    return output[DISPLAY_COLUMNS], missing_useful_columns


def print_summary(df: pd.DataFrame, missing_useful_columns: list[str]) -> None:
    """Print a compact summary of the cleaned FBref context table."""
    print("")
    print(f"Saved cleaned FBref player context to: {OUTPUT_PATH}")
    print(f"rows: {len(df):,}")
    print(f"unique players: {df['player'].nunique():,}")
    print(f"seasons included: {sorted(df['season'].dropna().astype(str).unique())}")
    print(f"leagues included: {sorted(df['league'].dropna().astype(str).unique())}")
    print(f"first 30 columns: {df.columns[:30].tolist()}")
    print(f"missing useful columns: {missing_useful_columns}")


def main() -> None:
    """Build a cleaned FBref player shooting context table."""
    tables = load_raw_tables()
    merged = merge_raw_tables(tables)
    cleaned, missing_useful_columns = build_clean_context(merged)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(OUTPUT_PATH, index=False)
    print_summary(cleaned, missing_useful_columns)


if __name__ == "__main__":
    main()
