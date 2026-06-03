from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from scripts.apply_final_squad_text import add_normalized_columns, clean_text
from src.data.ingest_world_cup_squads import build_report


CONFIG_PATH = PROJECT_ROOT / "configs" / "final_26_squad_corrections.yaml"
SQUADS_PATH = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
CORRECTION_REPORT_PATH = PROJECT_ROOT / "reports" / "final_26_squad_corrections_report.txt"
SQUAD_COVERAGE_REPORT_PATH = PROJECT_ROOT / "reports" / "world_cup_squad_coverage.txt"

DATA_SOURCE = "User final 26-player squad correction"
RAW_STATUS = "Final 26-player squad correction"
EXPECTED_PLAYERS_PER_TEAM = 26

OUTPUT_COLUMNS = [
    "world_cup_team",
    "player",
    "position",
    "position_group",
    "club",
    "league",
    "squad_status",
    "data_source",
    "player_normalized",
    "team_normalized",
    "raw_squad_status",
]


def load_corrections(config_path: Path = CONFIG_PATH) -> dict:
    """Load final 26-player roster corrections from YAML."""
    if not config_path.exists():
        raise FileNotFoundError(f"Correction config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    corrections = config.get("final_26_squad_corrections", {})
    if not corrections:
        raise ValueError(
            "No final_26_squad_corrections section found in "
            f"{config_path}"
        )

    return corrections


def build_corrected_team_rows(team: str, players: list[dict]) -> pd.DataFrame:
    """Convert one corrected team roster into the processed squad schema."""
    if len(players) != EXPECTED_PLAYERS_PER_TEAM:
        raise ValueError(
            f"{team} correction has {len(players)} players; "
            f"expected {EXPECTED_PLAYERS_PER_TEAM}."
        )

    records = []
    for player in players:
        position_group = clean_text(player["position_group"])
        records.append(
            {
                "world_cup_team": clean_text(team),
                "player": clean_text(player["player"]),
                "position": position_group,
                "position_group": position_group,
                "club": clean_text(player.get("club", "Unknown / verify manually")),
                "league": clean_text(player.get("league", "Unknown / verify manually")),
                "squad_status": "confirmed",
                "data_source": DATA_SOURCE,
                "raw_squad_status": RAW_STATUS,
            }
        )

    return add_normalized_columns(pd.DataFrame(records))[OUTPUT_COLUMNS]


def build_change_report(
    before: pd.DataFrame,
    after: pd.DataFrame,
    corrected_teams: list[str],
) -> str:
    """Summarize what changed after applying the final 26-player corrections."""
    before_counts = before.groupby("world_cup_team").size()
    after_counts = after.groupby("world_cup_team").size()

    lines = [
        "Final 26-Player Squad Corrections Report",
        "=========================================",
        f"Corrected teams: {', '.join(corrected_teams)}",
        f"Rows before: {len(before):,}",
        f"Rows after: {len(after):,}",
        "",
        "Corrected team counts:",
    ]

    for team in corrected_teams:
        lines.append(
            f"- {team}: {int(before_counts.get(team, 0))} -> "
            f"{int(after_counts.get(team, 0))}"
        )

    lines.extend(["", "Corrected roster details:"])
    corrected_rows = after[after["world_cup_team"].isin(corrected_teams)].copy()
    for team in corrected_teams:
        team_rows = corrected_rows[corrected_rows["world_cup_team"] == team]
        lines.append("")
        lines.append(f"{team} ({len(team_rows)} players)")
        lines.append(
            team_rows[
                ["player", "position_group", "club", "league"]
            ].to_string(index=False)
        )

    non_26_counts = after_counts[after_counts != EXPECTED_PLAYERS_PER_TEAM]
    lines.extend(["", "Teams not at 26 players after correction:"])
    if non_26_counts.empty:
        lines.append("None")
    else:
        lines.append(non_26_counts.sort_index().to_string())

    return "\n".join(lines)


def apply_corrections(squads: pd.DataFrame, corrections: dict) -> pd.DataFrame:
    """Replace corrected teams in the squad table with exact 26-player rosters."""
    corrected_teams = sorted(corrections.keys())
    corrected_frames = [
        build_corrected_team_rows(team, payload.get("players", []))
        for team, payload in corrections.items()
    ]

    retained = squads[~squads["world_cup_team"].isin(corrected_teams)].copy()
    updated = pd.concat([retained, *corrected_frames], ignore_index=True)
    updated = updated[OUTPUT_COLUMNS].sort_values(
        ["world_cup_team", "position_group", "player"]
    )
    return updated.reset_index(drop=True)


def main() -> None:
    """Apply final 26-player corrections to the processed squad table."""
    if not SQUADS_PATH.exists():
        raise FileNotFoundError(f"Processed squad file not found: {SQUADS_PATH}")

    before = pd.read_csv(SQUADS_PATH)
    corrections = load_corrections()
    corrected_teams = sorted(corrections.keys())
    after = apply_corrections(before, corrections)

    SQUADS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CORRECTION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    after.to_csv(SQUADS_PATH, index=False)
    CORRECTION_REPORT_PATH.write_text(
        build_change_report(before, after, corrected_teams),
        encoding="utf-8",
    )
    SQUAD_COVERAGE_REPORT_PATH.write_text(build_report(after), encoding="utf-8")

    print(f"Saved corrected squads to: {SQUADS_PATH}")
    print(f"Saved correction report to: {CORRECTION_REPORT_PATH}")
    print(f"Rows before: {len(before):,}")
    print(f"Rows after: {len(after):,}")
    for team in corrected_teams:
        before_count = int((before["world_cup_team"] == team).sum())
        after_count = int((after["world_cup_team"] == team).sum())
        print(f"{team}: {before_count} -> {after_count}")


if __name__ == "__main__":
    main()
