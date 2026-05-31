from pathlib import Path
import os

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "fbref" / "raw"
SOCCERDATA_DIR = PROJECT_ROOT / "data" / "fbref" / "soccerdata_cache"

LEAGUES = ["Big 5 European Leagues Combined"]
SEASONS = [2023, 2024, 2025]
STAT_TYPES = ["standard", "shooting", "playing_time", "misc"]
NO_CACHE = os.environ.get("FBREF_NO_CACHE", "true").lower() in {"1", "true", "yes"}


def import_soccerdata():
    """Import soccerdata with a clear message if it is missing."""
    os.environ.setdefault("SOCCERDATA_DIR", str(SOCCERDATA_DIR))

    try:
        import soccerdata as sd
    except ImportError as error:
        raise SystemExit(
            "soccerdata is not installed. Install it with:\n\n"
            "python -m pip install soccerdata\n\n"
            "or run:\n\n"
            "pip install -r requirements.txt"
        ) from error

    return sd


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex columns into readable snake_case column names."""
    flattened = df.copy()

    if isinstance(flattened.columns, pd.MultiIndex):
        flattened.columns = [
            "_".join(
                str(part).strip()
                for part in column
                if str(part).strip()
                and not str(part).startswith("Unnamed:")
                and str(part) != "nan"
            )
            for column in flattened.columns
        ]

    flattened.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_per_")
        .replace("-", "_")
        .replace("%", "pct")
        for column in flattened.columns
    ]

    return flattened


def clean_fbref_frame(df: pd.DataFrame, season: int, stat_type: str) -> pd.DataFrame:
    """Reset index, flatten columns, and add ingestion metadata."""
    cleaned = df.reset_index()
    cleaned = flatten_columns(cleaned)
    cleaned["requested_season"] = season
    cleaned["stat_type"] = stat_type

    return cleaned


def create_fbref_reader(sd, season: int):
    """Create one FBref reader for a season."""
    try:
        return sd.FBref(leagues=LEAGUES, seasons=[season], no_cache=NO_CACHE)
    except TypeError:
        return sd.FBref(leagues=LEAGUES, seasons=[season])


def close_fbref_reader(fbref) -> None:
    """Close soccerdata's browser driver when it exists."""
    driver = getattr(fbref, "_driver", None)

    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass


def read_player_stats_for_season(fbref, season: int) -> dict[str, pd.DataFrame]:
    """Read all requested FBref player stat types for one season."""
    season_frames = {}

    for stat_type in STAT_TYPES:
        print(f"Reading FBref stat_type={stat_type}, season={season}", flush=True)

        try:
            stats = fbref.read_player_season_stats(stat_type=stat_type)
        except Exception as error:
            print(
                f"WARNING: Could not read FBref {stat_type} stats for season {season}: {error}",
                flush=True,
            )
            continue

        if stats.empty:
            print(
                f"WARNING: FBref returned no {stat_type} rows for season {season}.",
                flush=True,
            )
            continue

        season_frames[stat_type] = clean_fbref_frame(stats, season, stat_type)

    return season_frames


def print_saved_summary(stat_type: str, df: pd.DataFrame, output_path: Path) -> None:
    """Print a compact summary for a saved FBref CSV."""
    print("")
    print(f"Saved FBref player season stats: {output_path}")
    print(f"stat_type: {stat_type}")
    print(f"rows: {len(df):,}")
    print(f"columns: {len(df.columns):,}")
    print(f"first 20 columns: {df.columns[:20].tolist()}")

    if "season" in df.columns:
        seasons = sorted(df["season"].dropna().astype(str).unique())
        print(f"seasons found: {seasons}")
    elif "requested_season" in df.columns:
        seasons = sorted(df["requested_season"].dropna().astype(str).unique())
        print(f"requested seasons found: {seasons}")

    if "league" in df.columns:
        leagues = sorted(df["league"].dropna().astype(str).unique())
        print(f"leagues found: {leagues}")


def output_path_for_stat_type(stat_type: str) -> Path:
    """Return the raw FBref CSV path for one stat type."""
    return OUTPUT_DIR / f"player_season_{stat_type}.csv"


def clear_previous_outputs() -> None:
    """Remove previously generated FBref raw CSVs before a new run."""
    for stat_type in STAT_TYPES:
        output_path = output_path_for_stat_type(stat_type)
        if output_path.exists():
            output_path.unlink()


def save_combined_stat_type(
    stat_type: str,
    frames: list[pd.DataFrame],
    print_summary: bool = False,
) -> None:
    """Save all collected seasons for one FBref stat type."""
    stats = pd.concat(frames, ignore_index=True)
    output_path = output_path_for_stat_type(stat_type)
    stats.to_csv(output_path, index=False)

    if print_summary:
        print_saved_summary(stat_type, stats, output_path)
    else:
        print(
            f"Saved interim FBref {stat_type} data to {output_path} "
            f"({len(stats):,} rows).",
            flush=True,
        )


def main() -> None:
    """Pull FBref player season stats through soccerdata."""
    sd = import_soccerdata()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clear_previous_outputs()
    frames_by_stat_type = {stat_type: [] for stat_type in STAT_TYPES}

    for season in SEASONS:
        print(f"Initializing FBref reader for season={season}", flush=True)

        try:
            fbref = create_fbref_reader(sd, season)
        except Exception as error:
            print(
                f"WARNING: Could not initialize FBref reader for season {season}: {error}",
                flush=True,
            )
            continue

        try:
            season_frames = read_player_stats_for_season(fbref, season)
        finally:
            close_fbref_reader(fbref)

        for stat_type, frame in season_frames.items():
            frames_by_stat_type[stat_type].append(frame)
            save_combined_stat_type(stat_type, frames_by_stat_type[stat_type])

    for stat_type in STAT_TYPES:
        if not frames_by_stat_type[stat_type]:
            print(f"WARNING: No FBref data collected for stat_type={stat_type}.", flush=True)
            continue

        save_combined_stat_type(
            stat_type,
            frames_by_stat_type[stat_type],
            print_summary=True,
        )


if __name__ == "__main__":
    main()
