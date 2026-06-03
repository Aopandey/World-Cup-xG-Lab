from __future__ import annotations

from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = PROJECT_ROOT / "data" / "dashboard_artifacts"


class ArtifactError(RuntimeError):
    """Raised when a dashboard artifact cannot be loaded."""


def _normalize(value) -> str:
    return " ".join(str(value).casefold().split())


def load_json_artifact(filename):
    """Load one precomputed dashboard JSON artifact."""
    artifact_path = ARTIFACT_DIR / Path(filename).name

    if not artifact_path.exists():
        raise ArtifactError(
            f"Dashboard artifact not found: {artifact_path}. "
            "Run `python scripts/build_dashboard_artifacts.py` first."
        )

    try:
        with artifact_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as error:
        raise ArtifactError(f"Invalid JSON artifact: {artifact_path}") from error


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
