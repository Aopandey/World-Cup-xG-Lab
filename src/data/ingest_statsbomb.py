import argparse
import json
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
LEGACY_STATS_BOMB_DIR = DEFAULT_RAW_DIR / "statsbomb"
DEFAULT_EVENTS_DIR = DEFAULT_RAW_DIR / "events"
DEFAULT_OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "shots.csv"
STATSBOMB_OPEN_DATA_URL = "https://github.com/statsbomb/open-data/archive/refs/heads/master.zip"

SHOT_COLUMNS = [
    "match_id",
    "team",
    "player",
    "position",
    "minute",
    "second",
    "shot_x",
    "shot_y",
    "body_part",
    "shot_type",
    "shot_technique",
    "shot_outcome",
    "is_goal",
    "under_pressure",
    "play_pattern",
    "period",
]

MATCH_METADATA_COLUMNS = [
    "match_id",
    "competition_id",
    "season_id",
    "competition_name",
    "season_name",
    "match_date",
    "home_team",
    "away_team",
]


def load_json(path: str | Path) -> list | dict:
    """Load a JSON file from disk."""
    json_path = Path(path)

    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with json_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_statsbomb_data_dir(raw_dir: str | Path = DEFAULT_RAW_DIR) -> Path:
    """Return the directory containing StatsBomb competitions, matches, and events."""
    raw_path = Path(raw_dir)

    if (raw_path / "competitions.json").exists():
        return raw_path

    if (raw_path / "statsbomb" / "competitions.json").exists():
        return raw_path / "statsbomb"

    raise FileNotFoundError(
        "StatsBomb metadata was not found. Expected data/raw/competitions.json "
        "and data/raw/matches/{competition_id}/{season_id}.json. "
        "Run python src/data/ingest_statsbomb.py --download or place StatsBomb Open Data "
        "files under data/raw/."
    )


def load_competitions(statsbomb_dir: str | Path = DEFAULT_RAW_DIR) -> pd.DataFrame:
    """Load StatsBomb competitions metadata."""
    competitions_file = find_statsbomb_data_dir(statsbomb_dir) / "competitions.json"
    return pd.DataFrame(load_json(competitions_file))


def load_matches(
    competition_id: int,
    season_id: int,
    statsbomb_dir: str | Path = DEFAULT_RAW_DIR,
) -> pd.DataFrame:
    """Load StatsBomb matches metadata for one competition and season."""
    matches_file = (
        find_statsbomb_data_dir(statsbomb_dir)
        / "matches"
        / str(competition_id)
        / f"{season_id}.json"
    )
    return pd.DataFrame(load_json(matches_file))


def download_statsbomb_open_data(
    statsbomb_dir: str | Path = DEFAULT_RAW_DIR,
    url: str = STATSBOMB_OPEN_DATA_URL,
) -> None:
    """Download StatsBomb Open Data into the local raw data directory."""
    output_dir = Path(statsbomb_dir)
    zip_path = output_dir.parent / "statsbomb-open-data.zip"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading StatsBomb Open Data from {url}")
    urllib.request.urlretrieve(url, zip_path)

    with zipfile.ZipFile(zip_path, "r") as archive:
        data_members = [
            member
            for member in archive.infolist()
            if "/data/" in member.filename and not member.is_dir()
        ]

        for member in data_members:
            relative_path = Path(member.filename.split("/data/", 1)[1])
            target_path = output_dir / relative_path

            try:
                target_path.resolve().relative_to(output_dir.resolve())
            except ValueError as error:
                raise RuntimeError(f"Unsafe path in archive: {member.filename}") from error

            target_path.parent.mkdir(parents=True, exist_ok=True)

            with archive.open(member) as source, target_path.open("wb") as target:
                target.write(source.read())

    zip_path.unlink()
    print(f"StatsBomb Open Data saved to {output_dir}")


def build_match_metadata(statsbomb_dir: str | Path = DEFAULT_RAW_DIR) -> pd.DataFrame:
    """Build match-level metadata from StatsBomb competitions and matches files."""
    data_dir = find_statsbomb_data_dir(statsbomb_dir)
    competitions = pd.DataFrame(load_json(data_dir / "competitions.json"))
    metadata_rows = []

    for competition in competitions.to_dict("records"):
        competition_id = competition.get("competition_id")
        season_id = competition.get("season_id")
        matches_file = data_dir / "matches" / str(competition_id) / f"{season_id}.json"

        if not matches_file.exists():
            print(f"WARNING: Match metadata file not found: {matches_file}")
            continue

        for match in load_json(matches_file):
            metadata_rows.append(
                {
                    "match_id": match.get("match_id"),
                    "competition_id": competition_id,
                    "season_id": season_id,
                    "competition_name": competition.get("competition_name"),
                    "season_name": competition.get("season_name"),
                    "match_date": match.get("match_date"),
                    "home_team": _get_nested_value(match, "home_team", "home_team_name"),
                    "away_team": _get_nested_value(match, "away_team", "away_team_name"),
                }
            )

    return pd.DataFrame(metadata_rows, columns=MATCH_METADATA_COLUMNS)


def _get_nested_value(data: dict, *keys: str) -> object:
    """Safely get a value from nested dictionaries."""
    value = data

    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)

    return value


def extract_shots_from_event_file(event_file: str | Path, match_id: int | None = None) -> pd.DataFrame:
    """Extract shot events from a StatsBomb event JSON file."""
    event_path = Path(event_file)
    events = load_json(event_path)
    resolved_match_id = match_id if match_id is not None else int(event_path.stem)
    shots = []

    for event in events:
        if _get_nested_value(event, "type", "name") != "Shot":
            continue

        location = event.get("location") or [None, None]
        shot = event.get("shot") or {}

        shots.append(
            {
                "match_id": resolved_match_id,
                "team": _get_nested_value(event, "team", "name"),
                "player": _get_nested_value(event, "player", "name"),
                "position": _get_nested_value(event, "position", "name"),
                "minute": event.get("minute"),
                "second": event.get("second"),
                "shot_x": location[0] if len(location) > 0 else None,
                "shot_y": location[1] if len(location) > 1 else None,
                "body_part": _get_nested_value(shot, "body_part", "name"),
                "shot_type": _get_nested_value(shot, "type", "name"),
                "shot_technique": _get_nested_value(shot, "technique", "name"),
                "shot_outcome": _get_nested_value(shot, "outcome", "name"),
                "is_goal": _get_nested_value(shot, "outcome", "name") == "Goal",
                "under_pressure": event.get("under_pressure", False),
                "play_pattern": _get_nested_value(event, "play_pattern", "name"),
                "period": event.get("period"),
            }
        )

    return pd.DataFrame(shots)


def build_shots_dataset(events_dir: str | Path = DEFAULT_EVENTS_DIR) -> pd.DataFrame:
    """Build one shots DataFrame from all StatsBomb event files in a directory."""
    events_path = Path(events_dir)

    if not events_path.exists():
        raise FileNotFoundError(
            "StatsBomb event files were not found. "
            f"Expected JSON files in: {events_path}. "
            "Place StatsBomb Open Data event files at data/raw/statsbomb/events/ "
            "or run: python src/data/ingest_statsbomb.py --download"
        )

    event_files = sorted(events_path.glob("*.json"))

    if not event_files:
        raise FileNotFoundError(
            "No StatsBomb event JSON files were found. "
            f"Expected files like data/raw/statsbomb/events/12345.json in: {events_path}. "
            "You can download the open data with: python src/data/ingest_statsbomb.py --download"
        )

    shot_frames = [extract_shots_from_event_file(event_file) for event_file in event_files]
    non_empty_frames = [frame for frame in shot_frames if not frame.empty]

    if not non_empty_frames:
        return pd.DataFrame(
            columns=[
                *SHOT_COLUMNS,
            ]
        )

    return pd.concat(non_empty_frames, ignore_index=True)


def merge_match_metadata(
    shots: pd.DataFrame,
    match_metadata: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """Merge shot rows with match metadata and count unmatched match IDs."""
    if match_metadata.empty:
        enriched_shots = shots.copy()
        for column in MATCH_METADATA_COLUMNS:
            if column != "match_id":
                enriched_shots[column] = pd.NA
        return enriched_shots, shots["match_id"].nunique()

    enriched_shots = shots.merge(match_metadata, on="match_id", how="left")
    unmatched_match_ids = enriched_shots.loc[
        enriched_shots["competition_id"].isna(),
        "match_id",
    ].nunique()

    return enriched_shots, unmatched_match_ids


def main() -> None:
    """Create the processed StatsBomb shots dataset."""
    parser = argparse.ArgumentParser(description="Ingest StatsBomb Open Data shot events.")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download StatsBomb Open Data before building the shots dataset.",
    )
    args = parser.parse_args()

    try:
        if args.download:
            download_statsbomb_open_data(DEFAULT_RAW_DIR)

        statsbomb_dir = find_statsbomb_data_dir(DEFAULT_RAW_DIR)
        match_metadata = build_match_metadata(statsbomb_dir)
        shots = build_shots_dataset(statsbomb_dir / "events")
        shots, unmatched_match_count = merge_match_metadata(shots, match_metadata)
    except FileNotFoundError as error:
        raise SystemExit(str(error)) from error
    except OSError as error:
        raise SystemExit(f"Could not download or read StatsBomb data: {error}") from error

    DEFAULT_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    shots.to_csv(DEFAULT_OUTPUT_FILE, index=False)

    if unmatched_match_count:
        print(
            "WARNING: Match metadata is missing for "
            f"{unmatched_match_count} match_id values."
        )

    print(f"Saved {len(shots)} shots to {DEFAULT_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
