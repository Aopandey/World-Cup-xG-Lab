from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_UNDERSTAT_DIR = PROJECT_ROOT / "data" / "understat" / "raw"
ARCHIVE_2_DIR = RAW_UNDERSTAT_DIR / "archive_2_player_game_stats"
ARCHIVE_3_DIR = RAW_UNDERSTAT_DIR / "archive_3_shot_data" / "understats"
PROCESSED_DIR = PROJECT_ROOT / "data" / "understat" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "understat_player_context.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "understat_player_context_report.txt"

sys.path.append(str(PROJECT_ROOT))

from src.data.player_matching import MATCH_NONE, match_player_to_fbref, normalize_name


PLAYER_COLUMNS = [
    "player",
    "team",
    "league",
    "season",
    "position",
    "games",
    "minutes",
    "goals",
    "shots",
    "xg",
    "assists",
    "xa",
    "key_passes",
    "yellow",
    "red",
    "npg",
    "npxg",
    "xg_chain",
    "xg_buildup",
    "shot_data_shots",
    "shot_data_goals",
    "shot_data_xg",
    "avg_shot_xg",
    "open_play_shots",
    "set_piece_shots",
    "penalty_shots",
    "data_source",
]


def read_understat_csv(path: Path) -> pd.DataFrame:
    """Read Understat CSV files, including semicolon-delimited archive files."""
    if not path.exists():
        return pd.DataFrame()

    preview = path.read_text(encoding="utf-8", errors="replace")[:500]
    first_line = preview.splitlines()[0] if preview.splitlines() else ""

    if first_line.startswith(";") or first_line.count(";") > first_line.count(","):
        data = pd.read_csv(path, sep=";", engine="python")
    else:
        data = pd.read_csv(path)

    unnamed_columns = [
        column
        for column in data.columns
        if str(column).startswith("Unnamed") or str(column).strip() == ""
    ]
    return data.drop(columns=unnamed_columns, errors="ignore")


def load_archive_2_player_stats() -> pd.DataFrame:
    """Load aggregate player-season stats from archive (2)."""
    path = ARCHIVE_2_DIR / "player_stats.csv"
    if not path.exists():
        return pd.DataFrame(columns=PLAYER_COLUMNS)

    data = pd.read_csv(path)
    data = data.rename(
        columns={
            "name": "player",
            "team": "team",
            "time": "minutes",
            "xG": "xg",
            "xA": "xa",
            "npxG": "npxg",
            "xGChain": "xg_chain",
            "xGBuildup": "xg_buildup",
        }
    )
    data["league"] = pd.NA
    data["data_source"] = "Understat archive 2 player_stats"
    return data


def load_archive_3_player_stats() -> pd.DataFrame:
    """Load aggregate player-season stats from per-league archive (3) folders."""
    if not ARCHIVE_3_DIR.exists():
        return pd.DataFrame(columns=PLAYER_COLUMNS)

    frames = []
    for league_dir in sorted(path for path in ARCHIVE_3_DIR.iterdir() if path.is_dir()):
        player_file = league_dir / "player.csv"
        data = read_understat_csv(player_file)
        if data.empty:
            continue

        data["league"] = league_dir.name.replace("_", " ")
        frames.append(data)

    if not frames:
        return pd.DataFrame(columns=PLAYER_COLUMNS)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.rename(
        columns={
            "player_name": "player",
            "team_title": "team",
            "year": "season",
            "time": "minutes",
            "xG": "xg",
            "xA": "xa",
            "yellow_cards": "yellow",
            "red_cards": "red",
            "npxG": "npxg",
            "xGChain": "xg_chain",
            "xGBuildup": "xg_buildup",
        }
    )
    combined["data_source"] = "Understat archive 3 player"
    return combined


def fix_understat_coordinate(value: object) -> float | None:
    """Normalize Understat coordinates to 0-1, repairing values like 895 -> 0.895."""
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return None
    if numeric > 1:
        numeric = numeric / 1000
    return float(numeric)


def build_shot_summary() -> pd.DataFrame:
    """Build player-team-season summaries from Understat shot-level data."""
    if not ARCHIVE_3_DIR.exists():
        return pd.DataFrame()

    frames = []
    for league_dir in sorted(path for path in ARCHIVE_3_DIR.iterdir() if path.is_dir()):
        shot_file = league_dir / "shot_data.csv"
        data = read_understat_csv(shot_file)
        if data.empty:
            continue

        data["league"] = league_dir.name.replace("_", " ")
        frames.append(data)

    if not frames:
        return pd.DataFrame()

    shots = pd.concat(frames, ignore_index=True)
    shots["x"] = shots["X"].apply(fix_understat_coordinate)
    shots["y"] = shots["Y"].apply(fix_understat_coordinate)
    shots["team"] = shots.apply(
        lambda row: row.get("h_team") if row.get("h_a") == "h" else row.get("a_team"),
        axis=1,
    )
    shots["is_goal"] = shots["result"].eq("Goal")
    shots["xg"] = pd.to_numeric(shots["xG"], errors="coerce")

    situation = pd.get_dummies(shots["situation"], prefix="situation")
    shots = pd.concat([shots, situation], axis=1)

    summary = (
        shots.groupby(["player", "team", "league", "season"], dropna=False)
        .agg(
            shot_data_shots=("xg", "size"),
            shot_data_goals=("is_goal", "sum"),
            shot_data_xg=("xg", "sum"),
            avg_shot_xg=("xg", "mean"),
            open_play_shots=("situation_OpenPlay", "sum")
            if "situation_OpenPlay" in shots.columns
            else ("xg", lambda _: 0),
            set_piece_shots=("situation_SetPiece", "sum")
            if "situation_SetPiece" in shots.columns
            else ("xg", lambda _: 0),
            penalty_shots=("situation_Penalty", "sum")
            if "situation_Penalty" in shots.columns
            else ("xg", lambda _: 0),
        )
        .reset_index()
    )

    return summary


def clean_player_context(player_stats: pd.DataFrame, shot_summary: pd.DataFrame) -> pd.DataFrame:
    """Combine aggregate and shot-level Understat context into one player-season table."""
    if player_stats.empty:
        return pd.DataFrame(columns=PLAYER_COLUMNS)

    keep_columns = [column for column in PLAYER_COLUMNS if column in player_stats.columns]
    context = player_stats[keep_columns].copy()

    for column in PLAYER_COLUMNS:
        if column not in context.columns:
            context[column] = pd.NA

    if not shot_summary.empty:
        context = context.merge(
            shot_summary,
            on=["player", "team", "league", "season"],
            how="left",
            suffixes=("", "_from_shots"),
        )
        for column in [
            "shot_data_shots",
            "shot_data_goals",
            "shot_data_xg",
            "avg_shot_xg",
            "open_play_shots",
            "set_piece_shots",
            "penalty_shots",
        ]:
            fallback_column = f"{column}_from_shots"
            if fallback_column in context.columns:
                context[column] = context[column].combine_first(context[fallback_column])
                context = context.drop(columns=[fallback_column])

    numeric_columns = [
        "games",
        "minutes",
        "goals",
        "shots",
        "xg",
        "assists",
        "xa",
        "key_passes",
        "yellow",
        "red",
        "npg",
        "npxg",
        "xg_chain",
        "xg_buildup",
        "shot_data_shots",
        "shot_data_goals",
        "shot_data_xg",
        "avg_shot_xg",
        "open_play_shots",
        "set_piece_shots",
        "penalty_shots",
    ]
    for column in numeric_columns:
        context[column] = pd.to_numeric(context[column], errors="coerce")

    context["player_normalized"] = context["player"].apply(normalize_name)
    context = context.drop_duplicates()

    return context[["player_normalized", *PLAYER_COLUMNS]].sort_values(
        ["player_normalized", "season", "league", "team"],
        ascending=[True, False, True, True],
    )


def count_world_cup_matches(context: pd.DataFrame) -> dict[str, int]:
    """Count safe Understat matches against the confirmed World Cup squad table."""
    squads_path = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
    if not squads_path.exists() or context.empty:
        return {
            "matched_players": 0,
            "total_players": 0,
            "matched_attackers_midfielders": 0,
            "total_attackers_midfielders": 0,
        }

    squads = pd.read_csv(squads_path)
    matched_players = 0
    matched_attackers_midfielders = 0
    total_attackers_midfielders = int(
        squads["position_group"].isin(["Forward", "Midfielder"]).sum()
    )

    for _, row in squads.iterrows():
        match = match_player_to_fbref(
            row["player"],
            context,
            selected_position=row.get("position_group"),
        )
        matched = match["confidence"] != MATCH_NONE and not match["rows"].empty
        if matched:
            matched_players += 1
            if row.get("position_group") in ["Forward", "Midfielder"]:
                matched_attackers_midfielders += 1

    return {
        "matched_players": matched_players,
        "total_players": int(len(squads)),
        "matched_attackers_midfielders": matched_attackers_midfielders,
        "total_attackers_midfielders": total_attackers_midfielders,
    }


def build_report(context: pd.DataFrame, counts: dict[str, int]) -> str:
    """Build a concise report for the Understat context output."""
    seasons = sorted(context["season"].dropna().astype(str).unique()) if not context.empty else []
    leagues = sorted(context["league"].dropna().astype(str).unique()) if not context.empty else []
    return "\n".join(
        [
            "Understat Player Context Report",
            "===============================",
            "",
            f"Rows: {len(context):,}",
            f"Unique players: {context['player'].nunique():,}" if not context.empty else "Unique players: 0",
            f"Leagues: {len(leagues):,}",
            f"Seasons: {', '.join(seasons)}",
            "",
            "World Cup squad coverage:",
            f"- Matched players: {counts['matched_players']:,}/{counts['total_players']:,}",
            (
                "- Matched midfielders/forwards: "
                f"{counts['matched_attackers_midfielders']:,}/"
                f"{counts['total_attackers_midfielders']:,}"
            ),
            "",
            "Leagues included:",
            ", ".join(leagues),
        ]
    )


def main() -> None:
    """Create the cleaned Understat player context table for the dashboard."""
    archive_2 = load_archive_2_player_stats()
    archive_3 = load_archive_3_player_stats()
    player_stats = pd.concat([archive_3, archive_2], ignore_index=True).drop_duplicates()
    shot_summary = build_shot_summary()
    context = clean_player_context(player_stats, shot_summary)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    context.to_csv(OUTPUT_PATH, index=False)

    counts = count_world_cup_matches(context)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(context, counts), encoding="utf-8")

    print(f"Saved Understat player context to: {OUTPUT_PATH}")
    print(f"Rows: {len(context):,}")
    print(f"Unique players: {context['player'].nunique():,}")
    print(
        "World Cup matched players: "
        f"{counts['matched_players']:,}/{counts['total_players']:,}"
    )
    print(
        "World Cup matched midfielders/forwards: "
        f"{counts['matched_attackers_midfielders']:,}/"
        f"{counts['total_attackers_midfielders']:,}"
    )


if __name__ == "__main__":
    main()
