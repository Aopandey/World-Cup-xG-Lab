from pathlib import Path
import os
import sys

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.data.player_matching import get_aliases_for_player, normalize_name
from src.data.world_cup_filter import filter_world_cup_teams


SQUAD_PATH = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
PREDICTIONS_PATH = PROJECT_ROOT / "data" / "predictions" / "all_shots_xg.csv"
FBREF_CONTEXT_PATH = PROJECT_ROOT / "data" / "fbref" / "processed" / "fbref_player_context.csv"
LEAGUE_MAPPING_PATH = PROJECT_ROOT / "configs" / "fbref_league_mapping.yaml"
RAW_OUTPUT_PATH = PROJECT_ROOT / "data" / "fbref" / "shot_events" / "raw" / "fbref_shot_events_sample.csv"
COLUMN_REPORT_PATH = PROJECT_ROOT / "reports" / "fbref_shot_event_columns.txt"
PLAYER_COVERAGE_REPORT_PATH = PROJECT_ROOT / "reports" / "fbref_shot_event_player_coverage.txt"

TARGET_PLAYERS = [
    "Lamine Yamal",
    "Ferran Torres",
    "Kylian Mbappé",
    "Cristiano Ronaldo",
    "Riyad Mahrez",
    "Lionel Messi",
    "Neymar",
]
SEASONS = [2023, 2024, 2025]
ATTACKING_POSITION_GROUPS = {"Forward", "Midfielder"}


def import_soccerdata():
    """Import soccerdata and direct its cache into the project folder."""
    os.environ.setdefault(
        "SOCCERDATA_DIR",
        str(PROJECT_ROOT / "data" / "fbref" / "soccerdata_cache"),
    )

    try:
        import soccerdata as sd
    except ImportError as error:
        raise SystemExit(
            "soccerdata is not installed. Install it with `python -m pip install soccerdata` "
            "or run `pip install -r requirements.txt`."
        ) from error

    return sd


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load squads, StatsBomb predictions, and FBref player context."""
    missing_paths = [
        path for path in [SQUAD_PATH, PREDICTIONS_PATH, FBREF_CONTEXT_PATH] if not path.exists()
    ]
    if missing_paths:
        raise FileNotFoundError(
            "Required input files are missing: "
            + ", ".join(str(path) for path in missing_paths)
        )

    squads = pd.read_csv(SQUAD_PATH)
    predictions = filter_world_cup_teams(pd.read_csv(PREDICTIONS_PATH))
    fbref_context = pd.read_csv(FBREF_CONTEXT_PATH)
    return squads, predictions, fbref_context


def load_league_mapping() -> tuple[dict[str, str], dict[str, str]]:
    """Load active and maybe-supported league mappings."""
    if not LEAGUE_MAPPING_PATH.exists():
        return {}, {}

    with LEAGUE_MAPPING_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    active = config.get("league_mappings", {})
    maybe = config.get("maybe_supported_leagues", {})
    return active, maybe


def map_league(league: str, active_mapping: dict[str, str], maybe_mapping: dict[str, str]) -> dict:
    """Map a squad league to an active or maybe-supported FBref league id."""
    normalized_league = normalize_name(league)
    active_lookup = {normalize_name(source): target for source, target in active_mapping.items()}
    maybe_lookup = {normalize_name(source): target for source, target in maybe_mapping.items()}

    if normalized_league in active_lookup:
        return {"fbref_league": active_lookup[normalized_league], "mapping_status": "active"}
    if normalized_league in maybe_lookup:
        return {"fbref_league": maybe_lookup[normalized_league], "mapping_status": "maybe_supported"}
    return {"fbref_league": pd.NA, "mapping_status": "unmapped"}


def normalized_aliases(player_name: str) -> set[str]:
    """Return normalized aliases for a player."""
    aliases = set(get_aliases_for_player(player_name))
    aliases.add(player_name)
    return {normalize_name(alias) for alias in aliases}


def count_statsbomb_shots_for_player(
    predictions: pd.DataFrame,
    team: str,
    player_name: str,
) -> int:
    """Count StatsBomb shots by exact normalized aliases within the World Cup team."""
    team_shots = predictions[predictions["world_cup_team"] == team].copy()
    team_shots["_player_normalized"] = team_shots["player"].apply(normalize_name)
    return int(team_shots["_player_normalized"].isin(normalized_aliases(player_name)).sum())


def build_weak_sample_table(
    squads: pd.DataFrame,
    predictions: pd.DataFrame,
    active_mapping: dict[str, str],
    maybe_mapping: dict[str, str],
) -> pd.DataFrame:
    """Identify official squad players with fewer than 20 StatsBomb shots."""
    squad_attempts = build_squad_attempt_table(
        squads,
        predictions,
        active_mapping,
        maybe_mapping,
    )
    confirmed = squad_attempts[squad_attempts["squad_status"] == "confirmed"].copy()
    weak = confirmed[confirmed["statsbomb_shots"] < 20].copy()
    weak["priority_position"] = weak["position_group"].isin(ATTACKING_POSITION_GROUPS)

    return weak.sort_values(
        ["priority_position", "statsbomb_shots", "world_cup_team", "player"],
        ascending=[False, True, True, True],
    ).reset_index(drop=True)


def build_squad_attempt_table(
    squads: pd.DataFrame,
    predictions: pd.DataFrame,
    active_mapping: dict[str, str],
    maybe_mapping: dict[str, str],
) -> pd.DataFrame:
    """Add StatsBomb shot counts and FBref league mapping to all squad rows."""
    attempts = squads.copy()
    attempts["statsbomb_shots"] = attempts.apply(
        lambda row: count_statsbomb_shots_for_player(
            predictions,
            row["world_cup_team"],
            row["player"],
        ),
        axis=1,
    )

    mapping_info = attempts["league"].apply(
        lambda league: pd.Series(map_league(str(league), active_mapping, maybe_mapping))
    )
    return pd.concat([attempts, mapping_info], axis=1)


def sample_players_from_squads(squad_attempts: pd.DataFrame) -> pd.DataFrame:
    """Find requested sample players in the squad workbook."""
    records = []
    squad_attempts = squad_attempts.copy()
    squad_attempts["_player_normalized"] = squad_attempts["player"].apply(normalize_name)

    for target_player in TARGET_PLAYERS:
        target_aliases = normalized_aliases(target_player)
        matches = squad_attempts[squad_attempts["_player_normalized"].isin(target_aliases)]

        if matches.empty:
            records.append(
                {
                    "target_player": target_player,
                    "player": target_player,
                    "world_cup_team": pd.NA,
                    "position_group": pd.NA,
                    "club": pd.NA,
                    "league": pd.NA,
                    "squad_status": "not_found_in_squad",
                    "statsbomb_shots": 0,
                    "fbref_league": pd.NA,
                    "mapping_status": "not_found_in_squad",
                }
            )
            continue

        row = matches.iloc[0].to_dict()
        row["target_player"] = target_player
        records.append(row)

    return pd.DataFrame(records)


def has_read_shot_events(sd) -> bool:
    """Return whether installed soccerdata exposes FBref.read_shot_events."""
    return hasattr(sd.FBref, "read_shot_events")


def try_pull_shot_events(sd, sample_players: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Try soccerdata FBref shot-event pulls if the API is available."""
    errors = []
    frames = []

    if not has_read_shot_events(sd):
        errors.append(
            "Installed soccerdata FBref has no read_shot_events method; shot-event pulls skipped."
        )
        return pd.DataFrame(), errors

    attempted = sample_players[sample_players["mapping_status"] == "active"].copy()
    for _, row in attempted.iterrows():
        league = row.get("fbref_league")
        if pd.isna(league):
            continue

        for season in SEASONS:
            try:
                fbref = sd.FBref(leagues=[league], seasons=[season], no_cache=False)
                events = fbref.read_shot_events()
                events = events.copy()
                events["target_player"] = row["target_player"]
                events["squad_player"] = row["player"]
                events["requested_league"] = league
                events["requested_season"] = season
                frames.append(events)
            except Exception as error:
                errors.append(f"{row['target_player']} / {league} / {season}: {error}")

    if not frames:
        return pd.DataFrame(), errors

    return pd.concat(frames, ignore_index=True), errors


def column_presence(columns: list[str]) -> dict[str, bool]:
    """Inspect whether useful shot-event fields appear available."""
    normalized_columns = {normalize_name(column): column for column in columns}

    def has_any(*needles: str) -> bool:
        return any(
            any(needle in normalized for needle in needles)
            for normalized in normalized_columns
        )

    return {
        "xG": has_any("xg", "expected goals"),
        "PSxG": has_any("psxg", "post shot xg", "post shot expected"),
        "distance": has_any("distance", "dist"),
        "body_part": has_any("body part", "body_part", "bodypart"),
        "shot_outcome": has_any("outcome", "result"),
        "exact_x_y_coordinates": (
            ("x" in normalized_columns and "y" in normalized_columns)
            or has_any("location", "coordinate")
        ),
        "assist_type": has_any("assist", "sca", "pass"),
        "defender_pressure": has_any("pressure", "pressured", "defender"),
        "game_situation_play_pattern": has_any("play pattern", "situation", "phase"),
    }


def build_column_report(events: pd.DataFrame, errors: list[str]) -> str:
    """Build report describing available FBref shot-event columns."""
    columns = events.columns.tolist() if not events.empty else []
    presence = column_presence(columns)

    lines = [
        "FBref Shot Event Column Audit",
        "============================",
        f"Raw shot-event rows pulled: {len(events):,}",
        f"Raw shot-event columns: {columns if columns else 'None'}",
        "",
        "Column availability:",
        f"- Does FBref shot-event data include xG? {'Yes' if presence['xG'] else 'No'}",
        f"- Does it include PSxG? {'Yes' if presence['PSxG'] else 'No'}",
        f"- Does it include distance? {'Yes' if presence['distance'] else 'No'}",
        f"- Does it include body_part? {'Yes' if presence['body_part'] else 'No'}",
        f"- Does it include shot outcome? {'Yes' if presence['shot_outcome'] else 'No'}",
        (
            "- Does it include exact x/y shot coordinates? "
            f"{'Yes' if presence['exact_x_y_coordinates'] else 'No'}"
        ),
        f"- Does it include assist type? {'Yes' if presence['assist_type'] else 'No'}",
        f"- Does it include defender pressure? {'Yes' if presence['defender_pressure'] else 'No'}",
        (
            "- Does it include game situation/play pattern? "
            f"{'Yes' if presence['game_situation_play_pattern'] else 'No'}"
        ),
        "",
        "Errors / API limitations:",
        "\n".join(f"- {error}" for error in errors) if errors else "None",
        "",
    ]

    return "\n".join(lines)


def build_player_coverage_report(
    weak_samples: pd.DataFrame,
    sample_players: pd.DataFrame,
    events: pd.DataFrame,
    errors: list[str],
    sd,
) -> str:
    """Build player coverage and recommendation report."""
    players_found = []
    events_per_player = pd.Series(dtype=int)
    seasons_leagues_found = "None"

    if not events.empty and "squad_player" in events.columns:
        players_found = sorted(events["squad_player"].dropna().astype(str).unique())
        events_per_player = events["squad_player"].value_counts()
        seasons_leagues_found = (
            events[["requested_season", "requested_league"]]
            .drop_duplicates()
            .sort_values(["requested_season", "requested_league"])
            .to_string(index=False)
        )

    players_attempted = sample_players["target_player"].dropna().astype(str).tolist()
    missing_players = sorted(set(players_attempted) - set(players_found))
    weak_attackers = weak_samples[weak_samples["priority_position"]].copy()

    if has_read_shot_events(sd):
        retrain_answer = (
            "Not yet. Even if shot events are available, they need schema validation "
            "against StatsBomb coordinates/features before retraining."
        )
        simpler_model_answer = (
            "Possibly, if FBref shot events include xG/outcome and enough shot-level "
            "features for supported leagues."
        )
        context_answer = (
            "Yes. FBref shot events are safest as a recent-shot context layer until "
            "coverage and feature compatibility are proven."
        )
    else:
        retrain_answer = (
            "No. The installed soccerdata FBref API does not expose read_shot_events, "
            "so no comparable shot-event training table is available."
        )
        simpler_model_answer = (
            "No for this local setup. A separate model would require a reliable "
            "shot-event source with outcomes and shot-level features."
        )
        context_answer = (
            "Yes, but currently through aggregate FBref player-season context rather "
            "than FBref shot events."
        )

    lines = [
        "FBref Shot Event Player Coverage",
        "================================",
        f"Weak-sample confirmed squad players (<20 StatsBomb shots): {len(weak_samples):,}",
        f"Weak-sample midfielders/forwards: {len(weak_attackers):,}",
        "",
        "Players attempted:",
        "\n".join(f"- {player}" for player in players_attempted),
        "",
        "Players found:",
        "\n".join(f"- {player}" for player in players_found) if players_found else "None",
        "",
        "Number of FBref shot events per player:",
        events_per_player.to_string() if not events_per_player.empty else "None",
        "",
        "Seasons/leagues found:",
        seasons_leagues_found,
        "",
        "Players missing:",
        "\n".join(f"- {player}" for player in missing_players) if missing_players else "None",
        "",
        "Sample player squad/league mapping:",
        sample_players[
            [
                "target_player",
                "world_cup_team",
                "club",
                "league",
                "statsbomb_shots",
                "fbref_league",
                "mapping_status",
            ]
        ].to_string(index=False),
        "",
        "Errors encountered:",
        "\n".join(f"- {error}" for error in errors) if errors else "None",
        "",
        "Recommendation",
        "--------------",
        "Can FBref shot events be used to retrain the existing StatsBomb xG model?",
        retrain_answer,
        "",
        "Can FBref shot events support a separate simpler model?",
        simpler_model_answer,
        "",
        "Should FBref shot events be used only as a dashboard context layer?",
        context_answer,
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    """Audit whether FBref shot events can enrich weak-sample player profiles."""
    squads, predictions, _ = load_inputs()
    active_mapping, maybe_mapping = load_league_mapping()
    squad_attempts = build_squad_attempt_table(
        squads,
        predictions,
        active_mapping,
        maybe_mapping,
    )
    weak_samples = build_weak_sample_table(squads, predictions, active_mapping, maybe_mapping)
    sample_players = sample_players_from_squads(squad_attempts)
    sd = import_soccerdata()

    events, errors = try_pull_shot_events(sd, sample_players)

    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    COLUMN_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not events.empty:
        events.to_csv(RAW_OUTPUT_PATH, index=False)

    column_report = build_column_report(events, errors)
    player_report = build_player_coverage_report(
        weak_samples,
        sample_players,
        events,
        errors,
        sd,
    )
    COLUMN_REPORT_PATH.write_text(column_report, encoding="utf-8")
    PLAYER_COVERAGE_REPORT_PATH.write_text(player_report, encoding="utf-8")

    print(column_report)
    print(player_report)
    if not events.empty:
        print(f"Saved raw FBref shot-event sample to: {RAW_OUTPUT_PATH}")
    print(f"Saved column report to: {COLUMN_REPORT_PATH}")
    print(f"Saved player coverage report to: {PLAYER_COVERAGE_REPORT_PATH}")


if __name__ == "__main__":
    main()
