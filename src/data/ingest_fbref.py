from pathlib import Path
import os
import sys

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.data.player_matching import normalize_name


OUTPUT_DIR = PROJECT_ROOT / "data" / "fbref" / "raw"
SOCCERDATA_DIR = PROJECT_ROOT / "data" / "fbref" / "soccerdata_cache"
SQUAD_PATH = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
LEAGUE_MAPPING_PATH = PROJECT_ROOT / "configs" / "fbref_league_mapping.yaml"
FAILED_LEAGUES_REPORT_PATH = PROJECT_ROOT / "reports" / "fbref_failed_leagues.txt"

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


def load_league_mapping(
    mapping_path: Path = LEAGUE_MAPPING_PATH,
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Load default FBref leagues and squad-league mappings."""
    if not mapping_path.exists():
        return ["Big 5 European Leagues Combined"], {}, {}

    with mapping_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    return (
        config.get("default_leagues", []),
        config.get("league_mappings", {}),
        config.get("maybe_supported_leagues", {}),
    )


def load_squad_leagues(squad_path: Path = SQUAD_PATH) -> list[str]:
    """Load unique club leagues from the cleaned squad table."""
    if not squad_path.exists():
        print(
            f"Squad file not found at {squad_path}; using default FBref leagues only.",
            flush=True,
        )
        return []

    squads = pd.read_csv(squad_path)
    if "league" not in squads.columns:
        print("Squad file has no league column; using default FBref leagues only.", flush=True)
        return []

    leagues = sorted(
        league
        for league in squads["league"].dropna().astype(str).unique()
        if league and league != "Unknown / verify manually"
    )
    return leagues


def map_squad_leagues_to_fbref(
    squad_leagues: list[str],
    league_mapping: dict[str, str],
) -> tuple[list[str], list[str]]:
    """Map squad workbook league labels to soccerdata FBref league names."""
    normalized_mapping = {
        normalize_name(source): target for source, target in league_mapping.items()
    }
    mapped_leagues = []
    unmapped_leagues = []

    for league in squad_leagues:
        mapped = normalized_mapping.get(normalize_name(league))
        if mapped:
            mapped_leagues.append(mapped)
        else:
            unmapped_leagues.append(league)

    return sorted(set(mapped_leagues)), unmapped_leagues


def get_leagues_to_pull() -> tuple[list[str], list[str], dict[str, str]]:
    """Return default plus squad-derived FBref leagues."""
    default_leagues, league_mapping, maybe_supported = load_league_mapping()
    squad_leagues = load_squad_leagues()
    mapped_leagues, unmapped_leagues = map_squad_leagues_to_fbref(
        squad_leagues,
        league_mapping,
    )
    maybe_source_lookup = {normalize_name(source) for source in maybe_supported}
    unmapped_leagues = [
        league for league in unmapped_leagues if normalize_name(league) not in maybe_source_lookup
    ]
    leagues = list(dict.fromkeys(default_leagues + mapped_leagues))

    print(f"Active leagues attempted: {leagues}", flush=True)
    if maybe_supported:
        maybe_targets = sorted(set(maybe_supported.values()))
        print(
            "Maybe-supported leagues not attempted: " + ", ".join(maybe_targets),
            flush=True,
        )
    if unmapped_leagues:
        print(
            "WARNING: No FBref mapping configured for these squad leagues: "
            + ", ".join(unmapped_leagues),
            flush=True,
        )

    return leagues, unmapped_leagues, maybe_supported


def clean_fbref_frame(
    df: pd.DataFrame,
    requested_league: str,
    season: int,
    stat_type: str,
) -> pd.DataFrame:
    """Reset index, flatten columns, and add ingestion metadata."""
    cleaned = df.reset_index()
    cleaned = flatten_columns(cleaned)
    cleaned["requested_league"] = requested_league
    cleaned["requested_season"] = season
    cleaned["stat_type"] = stat_type
    return cleaned


def create_fbref_reader(sd, league: str, season: int):
    """Create one FBref reader for one league-season."""
    try:
        return sd.FBref(leagues=[league], seasons=[season], no_cache=NO_CACHE)
    except TypeError:
        return sd.FBref(leagues=[league], seasons=[season])


def close_fbref_reader(fbref) -> None:
    """Close soccerdata's browser driver when it exists."""
    driver = getattr(fbref, "_driver", None)

    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass


def read_player_stats_for_league_season(
    fbref,
    league: str,
    season: int,
) -> dict[str, pd.DataFrame]:
    """Read all requested FBref player stat types for one league-season."""
    season_frames = {}

    for stat_type in STAT_TYPES:
        print(
            f"Reading FBref league={league}, stat_type={stat_type}, season={season}",
            flush=True,
        )

        try:
            stats = fbref.read_player_season_stats(stat_type=stat_type)
        except Exception as error:
            print(
                f"WARNING: Could not read FBref {stat_type} stats for "
                f"{league} {season}: {error}",
                flush=True,
            )
            continue

        if stats.empty:
            print(
                f"WARNING: FBref returned no {stat_type} rows for {league} {season}.",
                flush=True,
            )
            continue

        season_frames[stat_type] = clean_fbref_frame(stats, league, season, stat_type)

    return season_frames


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
) -> pd.DataFrame:
    """Save all collected seasons/leagues for one FBref stat type."""
    stats = pd.concat(frames, ignore_index=True).drop_duplicates()
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

    return stats


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

    useful_columns = [
        column
        for column in df.columns
        if any(
            token in column
            for token in ["gls", "sh", "sot", "xg", "min", "90s", "ast"]
        )
    ]
    print(f"useful columns found: {useful_columns[:30]}")


def print_ingestion_summary(
    successful_leagues: set[str],
    failed_leagues: set[str],
    rows_by_league_stat: dict[tuple[str, str], int],
) -> None:
    """Print league-level ingestion status."""
    print("")
    print("FBref ingestion summary")
    print("=======================")
    print(f"leagues successfully pulled: {sorted(successful_leagues)}")
    print(f"leagues failed: {sorted(failed_leagues)}")
    print("rows per league/stat_type:")
    for (league, stat_type), rows in sorted(rows_by_league_stat.items()):
        print(f"- {league} / {stat_type}: {rows:,}")


def write_failed_leagues_report(
    active_leagues: list[str],
    maybe_supported: dict[str, str],
    unsupported_leagues: list[str],
    failed_leagues: set[str],
    unmapped_leagues: list[str],
) -> None:
    """Write failed/skipped FBref league information to a report."""
    FAILED_LEAGUES_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    maybe_lines = [
        f"{source} -> {target}" for source, target in sorted(maybe_supported.items())
    ]

    lines = [
        "FBref Failed/Skipped League Attempts",
        "====================================",
        "",
        "Active leagues attempted:",
        "\n".join(f"- {league}" for league in active_leagues) or "None",
        "",
        "Mapped active leagues unsupported by current soccerdata FBref:",
        "\n".join(f"- {league}" for league in sorted(unsupported_leagues)) or "None",
        "",
        "Failed active leagues:",
        "\n".join(f"- {league}" for league in sorted(failed_leagues)) or "None",
        "",
        "Maybe-supported leagues not attempted:",
        "\n".join(f"- {line}" for line in maybe_lines) or "None",
        "",
        "Squad leagues with no configured active mapping:",
        "\n".join(f"- {league}" for league in sorted(unmapped_leagues)) or "None",
        "",
    ]

    FAILED_LEAGUES_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved failed/skipped league report to: {FAILED_LEAGUES_REPORT_PATH}")


def filter_supported_leagues(sd, leagues: list[str]) -> tuple[list[str], list[str]]:
    """Keep leagues supported by soccerdata and report unsupported mappings."""
    try:
        supported_leagues = set(sd.FBref.available_leagues())
    except Exception as error:
        print(
            f"WARNING: Could not inspect soccerdata FBref supported leagues: {error}. "
            "Attempting all mapped leagues.",
            flush=True,
        )
        return leagues, []

    supported = [league for league in leagues if league in supported_leagues]
    unsupported = [league for league in leagues if league not in supported_leagues]

    if unsupported:
        print(
            "WARNING: These mapped leagues are not currently supported by soccerdata FBref "
            "and will be skipped: "
            + ", ".join(unsupported),
            flush=True,
        )

    return supported, unsupported


def main() -> None:
    """Pull FBref player season stats through soccerdata."""
    sd = import_soccerdata()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    clear_previous_outputs()
    requested_leagues, unmapped_leagues, maybe_supported = get_leagues_to_pull()
    leagues = requested_leagues
    leagues, unsupported_leagues = filter_supported_leagues(sd, leagues)
    frames_by_stat_type = {stat_type: [] for stat_type in STAT_TYPES}
    successful_leagues = set()
    failed_leagues = set(unsupported_leagues)
    rows_by_league_stat = {}
    write_failed_leagues_report(
        active_leagues=requested_leagues,
        maybe_supported=maybe_supported,
        unsupported_leagues=unsupported_leagues,
        failed_leagues=failed_leagues,
        unmapped_leagues=unmapped_leagues,
    )

    for league in leagues:
        league_succeeded = False

        for season in SEASONS:
            print(f"Initializing FBref reader for league={league}, season={season}", flush=True)

            try:
                fbref = create_fbref_reader(sd, league, season)
            except Exception as error:
                print(
                    f"WARNING: Could not initialize FBref reader for {league} {season}: {error}",
                    flush=True,
                )
                failed_leagues.add(league)
                continue

            try:
                season_frames = read_player_stats_for_league_season(fbref, league, season)
            finally:
                close_fbref_reader(fbref)

            if season_frames:
                league_succeeded = True

            for stat_type, frame in season_frames.items():
                frames_by_stat_type[stat_type].append(frame)
                rows_by_league_stat[(league, stat_type)] = (
                    rows_by_league_stat.get((league, stat_type), 0) + len(frame)
                )
                save_combined_stat_type(stat_type, frames_by_stat_type[stat_type])

        if league_succeeded:
            successful_leagues.add(league)
        else:
            failed_leagues.add(league)

        write_failed_leagues_report(
            active_leagues=requested_leagues,
            maybe_supported=maybe_supported,
            unsupported_leagues=unsupported_leagues,
            failed_leagues=failed_leagues,
            unmapped_leagues=unmapped_leagues,
        )

    for stat_type in STAT_TYPES:
        if not frames_by_stat_type[stat_type]:
            print(f"WARNING: No FBref data collected for stat_type={stat_type}.", flush=True)
            continue

        save_combined_stat_type(
            stat_type,
            frames_by_stat_type[stat_type],
            print_summary=True,
        )

    print_ingestion_summary(successful_leagues, failed_leagues, rows_by_league_stat)
    write_failed_leagues_report(
        active_leagues=requested_leagues,
        maybe_supported=maybe_supported,
        unsupported_leagues=unsupported_leagues,
        failed_leagues=failed_leagues,
        unmapped_leagues=unmapped_leagues,
    )


if __name__ == "__main__":
    main()
