from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = PROJECT_ROOT / "data" / "dashboard_artifacts"
REQUIRED_ARTIFACT_FILES = [
    "teams.json",
    "team_profiles.json",
    "player_profiles.json",
    "squad_players.json",
    "model_summary.json",
    "data_coverage.json",
]


class ArtifactError(RuntimeError):
    """Raised when a dashboard artifact cannot be loaded."""


def _normalize(value) -> str:
    return " ".join(str(value).casefold().split())


def load_json_artifact(filename):
    """Load one precomputed dashboard JSON artifact."""
    artifact_path = ARTIFACT_DIR / Path(filename).name

    if not artifact_path.exists():
        raise ArtifactError(
            f"Required dashboard artifact is missing: {artifact_path}. "
            "Generate artifacts with `python scripts/build_dashboard_artifacts.py`, "
            "then validate them with `python scripts/validate_dashboard_artifacts.py`."
        )

    try:
        with artifact_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as error:
        raise ArtifactError(
            f"Dashboard artifact is not valid JSON: {artifact_path}. "
            "Regenerate the dashboard artifacts before starting the API."
        ) from error


def _artifact_metadata(filename: str) -> dict:
    """Return file availability metadata for one expected artifact."""
    artifact_path = ARTIFACT_DIR / filename
    exists = artifact_path.exists()
    metadata = {
        "filename": filename,
        "exists": exists,
        "path": str(artifact_path),
        "size_bytes": None,
        "modified_at": None,
    }

    if exists:
        stat = artifact_path.stat()
        metadata["size_bytes"] = stat.st_size
        metadata["modified_at"] = datetime.fromtimestamp(
            stat.st_mtime,
            tz=timezone.utc,
        ).isoformat()

    return metadata


def get_artifact_status() -> dict:
    """Return availability metadata for all required dashboard artifacts."""
    artifacts = {
        filename: _artifact_metadata(filename)
        for filename in REQUIRED_ARTIFACT_FILES
    }
    missing = [
        filename
        for filename, metadata in artifacts.items()
        if not metadata["exists"]
    ]

    return {
        "artifact_dir": str(ARTIFACT_DIR),
        "required_files": REQUIRED_ARTIFACT_FILES,
        "missing_files": missing,
        "artifacts": artifacts,
    }


def validate_required_artifacts() -> list[str]:
    """Return required artifact filenames that are missing."""
    return get_artifact_status()["missing_files"]


def get_teams():
    """Return all team summary records."""
    return load_json_artifact("teams.json")


def get_team_profile(team_name):
    """Return one team profile using case-insensitive matching."""
    requested_team = _normalize(team_name)
    for profile in load_json_artifact("team_profiles.json"):
        if _normalize(profile.get("world_cup_team", "")) == requested_team:
            return profile
    return None


def get_players():
    """Return all player profile records."""
    return load_json_artifact("player_profiles.json")


def get_player_profile(player_name):
    """Return one player profile using case-insensitive matching."""
    requested_player = _normalize(player_name)
    for profile in load_json_artifact("player_profiles.json"):
        if _normalize(profile.get("player", "")) == requested_player:
            return profile
    return None


def get_squad_players():
    """Return all squad-player records."""
    return load_json_artifact("squad_players.json")


def get_model_summary():
    """Return model comparison and explanation metadata."""
    return load_json_artifact("model_summary.json")


def get_data_coverage():
    """Return dashboard data coverage metadata."""
    return load_json_artifact("data_coverage.json")
