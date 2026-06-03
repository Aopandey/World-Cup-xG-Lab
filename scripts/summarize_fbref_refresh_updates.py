from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BEFORE_PATH = PROJECT_ROOT / "reports" / "player_profiles_before_fbref_refresh.json"
AFTER_PATH = PROJECT_ROOT / "data" / "dashboard_artifacts" / "player_profiles.json"
OUTPUT_PATH = PROJECT_ROOT / "reports" / "fbref_refresh_player_updates.txt"
CSV_OUTPUT_PATH = PROJECT_ROOT / "reports" / "fbref_refresh_player_updates.csv"


def load_json(path: Path) -> list[dict]:
    """Load a dashboard JSON artifact."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def profile_key(row: dict) -> tuple[str | None, str | None]:
    """Return the stable team/player key used for before-after comparison."""
    return (
        row.get("world_cup_team"),
        row.get("player_normalized") or row.get("player"),
    )


def build_report(before: list[dict], after: list[dict]) -> tuple[str, pd.DataFrame]:
    """Compare FBref availability and recent rows before and after refresh."""
    before_lookup = {profile_key(row): row for row in before}
    after_lookup = {profile_key(row): row for row in after}

    newly_matched = []
    no_longer_matched = []
    changed_rows = []
    csv_rows = []

    for key, after_row in after_lookup.items():
        before_row = before_lookup.get(key, {})
        before_available = bool(before_row.get("fbref_available"))
        after_available = bool(after_row.get("fbref_available"))

        if not before_available and after_available:
            newly_matched.append(after_row)
            csv_rows.append(
                {
                    "update_type": "newly_matched",
                    "world_cup_team": after_row.get("world_cup_team"),
                    "player": after_row.get("player"),
                    "club": after_row.get("club"),
                    "league": after_row.get("league"),
                    "what_changed": "FBref context became available",
                }
            )
        elif before_available and not after_available:
            no_longer_matched.append(after_row)
            csv_rows.append(
                {
                    "update_type": "no_longer_matched",
                    "world_cup_team": after_row.get("world_cup_team"),
                    "player": after_row.get("player"),
                    "club": after_row.get("club"),
                    "league": after_row.get("league"),
                    "what_changed": "FBref context is no longer available",
                }
            )
        elif (
            before_available
            and after_available
            and before_row.get("fbref_recent_rows") != after_row.get("fbref_recent_rows")
        ):
            changed_rows.append((before_row, after_row))
            csv_rows.append(
                {
                    "update_type": "changed_recent_rows",
                    "world_cup_team": after_row.get("world_cup_team"),
                    "player": after_row.get("player"),
                    "club": after_row.get("club"),
                    "league": after_row.get("league"),
                    "what_changed": (
                        "FBref recent rows changed, mostly explicit Bundesliga league "
                        "labels replacing blank Big 5 combined labels"
                    ),
                }
            )

    lines = [
        "FBref Refresh Player Update Report",
        "===================================",
        "",
        f"Players before: {len(before):,}",
        f"Players after: {len(after):,}",
        f"FBref available before: {sum(bool(row.get('fbref_available')) for row in before):,}",
        f"FBref available after: {sum(bool(row.get('fbref_available')) for row in after):,}",
        f"Newly matched players: {len(newly_matched):,}",
        f"Players no longer matched: {len(no_longer_matched):,}",
        f"Players with changed FBref recent rows: {len(changed_rows):,}",
        "",
        "Newly matched players:",
    ]

    if newly_matched:
        for row in newly_matched:
            lines.append(
                f"- {row.get('world_cup_team')} / {row.get('player')} / "
                f"{row.get('club')} / {row.get('league')}"
            )
    else:
        lines.append("None")

    lines.extend(["", "Players no longer matched:"])
    if no_longer_matched:
        for row in no_longer_matched:
            lines.append(
                f"- {row.get('world_cup_team')} / {row.get('player')} / "
                f"{row.get('club')} / {row.get('league')}"
            )
    else:
        lines.append("None")

    lines.extend(["", "Players with changed FBref rows:"])
    if changed_rows:
        for before_row, after_row in changed_rows:
            lines.append(
                f"- {after_row.get('world_cup_team')} / {after_row.get('player')}"
            )
            lines.append(f"  before: {before_row.get('fbref_recent_rows')}")
            lines.append(f"  after: {after_row.get('fbref_recent_rows')}")
    else:
        lines.append("None")

    return "\n".join(lines), pd.DataFrame(csv_rows)


def main() -> None:
    """Write the FBref refresh before-after report."""
    if not BEFORE_PATH.exists():
        raise FileNotFoundError(f"Before snapshot not found: {BEFORE_PATH}")
    if not AFTER_PATH.exists():
        raise FileNotFoundError(f"After player profiles not found: {AFTER_PATH}")

    before = load_json(BEFORE_PATH)
    after = load_json(AFTER_PATH)
    report, csv_rows = build_report(before, after)
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    csv_rows.to_csv(CSV_OUTPUT_PATH, index=False)
    print(f"Saved FBref refresh update report to: {OUTPUT_PATH}")
    print(f"Saved compact FBref refresh CSV to: {CSV_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
