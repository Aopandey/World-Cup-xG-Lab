from pathlib import Path
import sys

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.data.ingest_world_cup_squads import build_report
from src.data.player_matching import normalize_name


SQUADS_PATH = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
CONFIG_PATH = PROJECT_ROOT / "configs" / "manual_confirmed_squads.yaml"
REPORT_PATH = PROJECT_ROOT / "reports" / "world_cup_squad_coverage.txt"
DATA_SOURCE = "User confirmed squad update"
RAW_STATUS = "Manual confirmed squad update"
UNKNOWN_VALUE = "Unknown / verify manually"


def load_manual_squads(path: Path = CONFIG_PATH) -> dict:
    """Load the manual confirmed squad override config."""
    if not path.exists():
        raise FileNotFoundError(f"Manual squad override config not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    return config.get("manual_confirmed_squads", {})


def build_previous_lookup(existing: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """Build a lookup of previous squad metadata by team/player."""
    lookup = {}

    for _, row in existing.iterrows():
        team_key = normalize_name(row["world_cup_team"])
        player_key = normalize_name(row["player"])
        lookup[(team_key, player_key)] = row.to_dict()

    return lookup


def resolve_team_name(config_team: str, payload: dict) -> str:
    """Return the canonical dashboard team name for a manual squad entry."""
    return payload.get("canonical_team") or config_team


def build_manual_rows(manual_squads: dict, previous_lookup: dict[tuple[str, str], dict]) -> pd.DataFrame:
    """Convert manual squad YAML rows into the processed squad schema."""
    records = []

    for config_team, payload in manual_squads.items():
        team = resolve_team_name(config_team, payload)
        team_key = normalize_name(team)

        for player in payload.get("players", []):
            player_name = player["player"]
            player_key = normalize_name(player_name)
            previous = previous_lookup.get((team_key, player_key), {})
            position_group = player.get("position_group") or previous.get("position_group") or "Unknown"

            records.append(
                {
                    "world_cup_team": team,
                    "player": player_name,
                    "position": player.get("position") or position_group,
                    "position_group": position_group,
                    "club": player.get("club") or previous.get("club") or UNKNOWN_VALUE,
                    "league": player.get("league") or previous.get("league") or UNKNOWN_VALUE,
                    "squad_status": "confirmed",
                    "data_source": DATA_SOURCE,
                    "player_normalized": player_key,
                    "team_normalized": team_key,
                    "raw_squad_status": RAW_STATUS,
                }
            )

    return pd.DataFrame(records)


def apply_manual_overrides(existing: pd.DataFrame, manual_squads: dict) -> pd.DataFrame:
    """Replace configured teams with manual confirmed squad rows."""
    previous_lookup = build_previous_lookup(existing)
    manual_rows = build_manual_rows(manual_squads, previous_lookup)
    override_teams = set(manual_rows["world_cup_team"].dropna().unique())

    retained = existing[~existing["world_cup_team"].isin(override_teams)].copy()
    updated = pd.concat([retained, manual_rows], ignore_index=True)
    updated = updated.sort_values(
        ["world_cup_team", "position_group", "player"],
    ).reset_index(drop=True)

    return updated


def print_override_summary(updated: pd.DataFrame, manual_squads: dict) -> None:
    """Print a compact summary of the manual squad update."""
    override_teams = [
        resolve_team_name(team, payload)
        for team, payload in manual_squads.items()
    ]
    counts = (
        updated[updated["world_cup_team"].isin(override_teams)]
        .groupby(["world_cup_team", "squad_status"])
        .size()
        .sort_index()
    )

    print("Manual squad overrides applied")
    print("==============================")
    print(counts.to_string())
    print("")
    print(f"Confirmed players total: {(updated['squad_status'] == 'confirmed').sum():,}")
    print(f"Teams still not announced: {updated.loc[updated['squad_status'] != 'confirmed', 'world_cup_team'].nunique():,}")


def main() -> None:
    """Apply manual confirmed squad overrides to the processed squad table."""
    if not SQUADS_PATH.exists():
        raise FileNotFoundError(
            f"Processed squad CSV not found: {SQUADS_PATH}. "
            "Run python src/data/ingest_world_cup_squads.py first."
        )

    existing = pd.read_csv(SQUADS_PATH)
    manual_squads = load_manual_squads()
    updated = apply_manual_overrides(existing, manual_squads)

    SQUADS_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    updated.to_csv(SQUADS_PATH, index=False)
    REPORT_PATH.write_text(build_report(updated), encoding="utf-8")

    print_override_summary(updated, manual_squads)
    print(f"Saved updated squads to: {SQUADS_PATH}")
    print(f"Saved updated report to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
