from __future__ import annotations

from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = PROJECT_ROOT / "data" / "dashboard_artifacts"

EXPECTED_FILES = {
    "teams.json": [
        "world_cup_team",
        "squad_status",
        "players_confirmed",
        "statsbomb_shots",
        "total_xg",
        "fbref_coverage_rate",
        "data_confidence",
    ],
    "team_profiles.json": [
        "world_cup_team",
        "statsbomb_shots",
        "statsbomb_date_range",
        "competitions_included",
        "top_xg_players",
        "warnings",
    ],
    "player_profiles.json": [
        "player",
        "player_normalized",
        "world_cup_team",
        "position_group",
        "statsbomb_shots",
        "fbref_available",
        "data_confidence",
        "warnings",
    ],
    "squad_players.json": [
        "world_cup_team",
        "player",
        "position_group",
        "club",
        "league",
        "squad_status",
    ],
    "model_summary.json": [
        "experiment_name",
        "models",
        "xg_explanation",
        "limitations",
    ],
    "data_coverage.json": [
        "total_world_cup_teams",
        "teams_with_statsbomb_data",
        "missing_teams",
        "total_squad_players",
        "fbref_matched_players",
        "date_range",
        "known_limitations",
    ],
}


def load_json(path: Path):
    """Load one JSON artifact with a useful error if it is invalid."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def warn_missing_fields(filename: str, payload, required_fields: list[str]) -> None:
    """Print warnings for missing top-level or row-level fields."""
    if isinstance(payload, list):
        if not payload:
            print(f"WARNING: {filename} is an empty list.")
            return

        missing = sorted(set(required_fields) - set(payload[0].keys()))
        if missing:
            print(f"WARNING: {filename} first row is missing fields: {', '.join(missing)}")
        return

    if isinstance(payload, dict):
        missing = sorted(set(required_fields) - set(payload.keys()))
        if missing:
            print(f"WARNING: {filename} is missing fields: {', '.join(missing)}")
        return

    print(f"WARNING: {filename} has unexpected JSON type: {type(payload).__name__}")


def print_artifact_count(filename: str, payload) -> None:
    """Print a compact count for one artifact."""
    if isinstance(payload, list):
        print(f"{filename}: {len(payload):,} records")
    elif isinstance(payload, dict):
        print(f"{filename}: object with {len(payload):,} fields")
    else:
        print(f"{filename}: {type(payload).__name__}")


def main() -> None:
    """Validate dashboard artifact files for future frontend use."""
    all_valid = True

    for filename, required_fields in EXPECTED_FILES.items():
        path = ARTIFACT_DIR / filename
        if not path.exists():
            print(f"ERROR: Missing artifact: {path}")
            all_valid = False
            continue

        try:
            payload = load_json(path)
        except json.JSONDecodeError as error:
            print(f"ERROR: Invalid JSON in {filename}: {error}")
            all_valid = False
            continue

        print_artifact_count(filename, payload)
        warn_missing_fields(filename, payload, required_fields)

    if all_valid:
        print("Dashboard artifact validation completed.")
    else:
        raise SystemExit("Dashboard artifact validation failed.")


if __name__ == "__main__":
    main()
