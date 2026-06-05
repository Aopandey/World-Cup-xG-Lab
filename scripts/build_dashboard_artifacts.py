from __future__ import annotations

from pathlib import Path
import json
import math
import sys
from urllib.parse import quote

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.data.data_confidence import (
    calculate_player_data_confidence,
    calculate_team_data_confidence,
)
from src.data.player_matching import (
    MATCH_ALIAS,
    MATCH_EXACT,
    MATCH_FUZZY,
    MATCH_NONE,
    get_aliases_for_player,
    normalize_name,
)
from src.data.world_cup_filter import filter_world_cup_teams, load_world_cup_teams


PREDICTIONS_PATH = PROJECT_ROOT / "data" / "predictions" / "all_shots_xg.csv"
SQUADS_PATH = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
FBREF_CONTEXT_PATH = PROJECT_ROOT / "data" / "fbref" / "processed" / "fbref_player_context.csv"
UNDERSTAT_CONTEXT_PATH = PROJECT_ROOT / "data" / "understat" / "processed" / "understat_player_context.csv"
UNDERSTAT_MODEL_PREDICTIONS_PATH = PROJECT_ROOT / "data" / "predictions" / "all_understat_shots_xg.csv"
MODEL_COMPARISON_PATH = PROJECT_ROOT / "reports" / "model_comparison.csv"
SOURCE_MODEL_COMPARISON_PATH = PROJECT_ROOT / "reports" / "source_model_comparison.csv"
FEATURE_MISSINGNESS_PATH = PROJECT_ROOT / "reports" / "feature_missingness_experiment.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "dashboard_artifacts"
FLAGS_DIR = PROJECT_ROOT / "data" / "World Cup Flags"

FLAG_CODES = {
    "Algeria": "DZ",
    "Argentina": "AR",
    "Australia": "AU",
    "Austria": "AT",
    "Belgium": "BE",
    "Bosnia and Herzegovina": "BA",
    "Brazil": "BR",
    "Cabo Verde": "CV",
    "Canada": "CA",
    "Colombia": "CO",
    "Croatia": "HR",
    "Curaçao": "CW",
    "Czechia": "CZ",
    "DR Congo": "CD",
    "Ecuador": "EC",
    "Egypt": "EG",
    "England": "GB-ENG",
    "France": "FR",
    "Germany": "DE",
    "Ghana": "GH",
    "Haiti": "HT",
    "Iran": "IR",
    "Iraq": "IQ",
    "Ivory Coast": "CI",
    "Japan": "JP",
    "Jordan": "JO",
    "Mexico": "MX",
    "Morocco": "MA",
    "Netherlands": "NL",
    "New Zealand": "NZ",
    "Norway": "NO",
    "Panama": "PA",
    "Paraguay": "PY",
    "Portugal": "PT",
    "Qatar": "QA",
    "Saudi Arabia": "SA",
    "Scotland": "GB-SCT",
    "Senegal": "SN",
    "South Africa": "ZA",
    "South Korea": "KR",
    "Spain": "ES",
    "Sweden": "SE",
    "Switzerland": "CH",
    "Tunisia": "TN",
    "Türkiye": "TR",
    "United States": "US",
    "Uruguay": "UY",
    "Uzbekistan": "UZ",
}

FLAG_FILENAME_ALIASES = {
    "Curaçao": "Curacao.png",
    "DR Congo": "Congo.png",
    "Ivory Coast": "Côte d'Ivoire.png",
    "South Korea": "Korea Republic.png",
    "United States": "USA.png",
}

_PLAYER_MATCH_INDEX_CACHE = {}


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    """Read a CSV file if it exists, otherwise return an empty frame."""
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, low_memory=False)


def _position_is_goalkeeper(position) -> bool:
    normalized = normalize_name(position)
    return normalized in {"gk", "goalkeeper", "goalkeepers"} or "goalkeeper" in normalized


def _build_player_match_index(df: pd.DataFrame) -> dict:
    prepared = df.copy()
    if "player_normalized" not in prepared.columns and "player" in prepared.columns:
        prepared["player_normalized"] = prepared["player"].apply(normalize_name)

    grouped = {
        name: group.copy()
        for name, group in prepared.groupby("player_normalized", dropna=False)
    }
    return {
        "prepared": prepared,
        "grouped": grouped,
        "names": list(grouped.keys()),
    }


def _get_player_match_index(df: pd.DataFrame) -> dict:
    cache_key = id(df)
    if cache_key not in _PLAYER_MATCH_INDEX_CACHE:
        _PLAYER_MATCH_INDEX_CACHE[cache_key] = _build_player_match_index(df)
    return _PLAYER_MATCH_INDEX_CACHE[cache_key]


def _filter_goalkeeper_mismatch(
    candidates: pd.DataFrame,
    selected_position=None,
) -> pd.DataFrame:
    if selected_position is None or _position_is_goalkeeper(selected_position):
        return candidates

    position_col = "position_group" if "position_group" in candidates.columns else "pos"
    if position_col not in candidates.columns:
        return candidates

    return candidates[~candidates[position_col].apply(_position_is_goalkeeper)].copy()


def _sort_match_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    sorted_candidates = candidates.copy()
    if "minutes" in sorted_candidates.columns:
        sorted_candidates["_has_minutes"] = pd.to_numeric(
            sorted_candidates["minutes"],
            errors="coerce",
        ).fillna(0) > 0
    else:
        sorted_candidates["_has_minutes"] = False

    if "season" in sorted_candidates.columns:
        sorted_candidates["_season_sort"] = pd.to_numeric(
            sorted_candidates["season"],
            errors="coerce",
        ).fillna(-1)
    else:
        sorted_candidates["_season_sort"] = -1

    return sorted_candidates.sort_values(
        ["_has_minutes", "_season_sort"],
        ascending=[False, False],
    ).drop(columns=["_has_minutes", "_season_sort"])


def _safe_fuzzy_names(names: list[str], selected_normalized: str) -> list[str]:
    selected_tokens = selected_normalized.split()
    if len(selected_tokens) < 2:
        return []

    matches = []
    for candidate in names:
        candidate_tokens = str(candidate).split()
        if len(candidate_tokens) < 2:
            continue
        if selected_normalized in candidate or candidate in selected_normalized:
            matches.append(candidate)
    return matches


def match_player_to_context(
    selected_player,
    context_df: pd.DataFrame,
    selected_position=None,
) -> dict:
    """Match a player to a large context table using cached normalized-name lookups."""
    if context_df.empty or "player" not in context_df.columns:
        return {"rows": pd.DataFrame(), "confidence": MATCH_NONE, "matched_player": None}

    selected_normalized = normalize_name(selected_player)
    index = _get_player_match_index(context_df)
    grouped = index["grouped"]

    exact = grouped.get(selected_normalized)
    if exact is not None:
        exact = _filter_goalkeeper_mismatch(exact, selected_position)
        if not exact.empty:
            sorted_exact = _sort_match_candidates(exact)
            return {
                "rows": sorted_exact,
                "confidence": MATCH_EXACT,
                "matched_player": sorted_exact["player"].iloc[0],
            }

    alias_normalized = {normalize_name(alias) for alias in get_aliases_for_player(selected_player)}
    alias_frames = []
    for alias in alias_normalized:
        candidate = grouped.get(alias)
        if candidate is not None:
            alias_frames.append(candidate)
    if alias_frames:
        alias_rows = pd.concat(alias_frames, ignore_index=True)
        alias_rows = _filter_goalkeeper_mismatch(alias_rows, selected_position)
        if not alias_rows.empty:
            sorted_alias = _sort_match_candidates(alias_rows)
            return {
                "rows": sorted_alias,
                "confidence": MATCH_ALIAS,
                "matched_player": sorted_alias["player"].iloc[0],
            }

    fuzzy_names = _safe_fuzzy_names(index["names"], selected_normalized)
    if len(fuzzy_names) == 1:
        fuzzy_rows = grouped[fuzzy_names[0]]
        fuzzy_rows = _filter_goalkeeper_mismatch(fuzzy_rows, selected_position)
        if not fuzzy_rows.empty and fuzzy_rows["player"].nunique() == 1:
            sorted_fuzzy = _sort_match_candidates(fuzzy_rows)
            return {
                "rows": sorted_fuzzy,
                "confidence": MATCH_FUZZY,
                "matched_player": sorted_fuzzy["player"].iloc[0],
            }

    return {"rows": pd.DataFrame(), "confidence": MATCH_NONE, "matched_player": None}


def to_plain_value(value):
    """Convert pandas/numpy values into JSON-safe plain Python values."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def clean_json(value):
    """Recursively remove pandas/numpy values from a JSON structure."""
    if isinstance(value, dict):
        return {key: clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json(item) for item in value]
    return to_plain_value(value)


def write_json(filename: str, payload) -> None:
    """Write a dashboard artifact with stable formatting."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(clean_json(payload), file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(f"Saved {output_path}")


def flag_image_url(team: str) -> str | None:
    """Return the API-served flag image path for a team when available."""
    if not FLAGS_DIR.exists():
        return None

    filename = FLAG_FILENAME_ALIASES.get(team, f"{team}.png")
    flag_path = FLAGS_DIR / filename
    if not flag_path.exists():
        return None

    return f"/static/world-cup-flags/{quote(filename)}"


def prepare_predictions() -> pd.DataFrame:
    """Load shot-level predictions and keep 2026 World Cup teams."""
    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Prediction file not found: {PREDICTIONS_PATH}. "
            "Run python src/models/predict.py first."
        )

    predictions = pd.read_csv(PREDICTIONS_PATH)
    return filter_world_cup_teams(predictions)


def prepare_squads() -> pd.DataFrame:
    """Load squad data and ensure normalized helper columns exist."""
    squads = read_csv_if_exists(SQUADS_PATH)
    if squads.empty:
        return squads

    if "player_normalized" not in squads.columns:
        squads["player_normalized"] = squads["player"].apply(normalize_name)
    if "team_normalized" not in squads.columns:
        squads["team_normalized"] = squads["world_cup_team"].apply(normalize_name)
    return squads


def prepare_fbref_context() -> pd.DataFrame:
    """Load FBref player context and ensure normalized helper columns exist."""
    fbref = read_csv_if_exists(FBREF_CONTEXT_PATH)
    if fbref.empty:
        return fbref

    if "player_normalized" not in fbref.columns:
        fbref["player_normalized"] = fbref["player"].apply(normalize_name)
    return fbref


def prepare_understat_context() -> pd.DataFrame:
    """Load Understat player context and ensure normalized helper columns exist."""
    understat = read_csv_if_exists(UNDERSTAT_CONTEXT_PATH)
    if understat.empty:
        return understat

    if "player_normalized" not in understat.columns:
        understat["player_normalized"] = understat["player"].apply(normalize_name)
    if "pos" not in understat.columns and "position" in understat.columns:
        understat["pos"] = understat["position"]
    return understat


def prepare_understat_model_context() -> pd.DataFrame:
    """Load all-shot experimental Understat predictions and summarize by player-season."""
    predictions = read_csv_if_exists(UNDERSTAT_MODEL_PREDICTIONS_PATH)
    if predictions.empty:
        return predictions

    required_columns = ["player", "team", "league", "season", "actual_goal", "predicted_xg"]
    missing = [column for column in required_columns if column not in predictions.columns]
    if missing:
        print(
            "Warning: Understat model predictions are missing columns: "
            f"{', '.join(missing)}"
        )
        return pd.DataFrame()

    predictions["player_normalized"] = predictions["player"].apply(normalize_name)
    predictions["source_xg"] = pd.to_numeric(
        predictions.get("source_xg", pd.Series(0, index=predictions.index)),
        errors="coerce",
    )
    predictions["predicted_xg"] = pd.to_numeric(predictions["predicted_xg"], errors="coerce")
    predictions["actual_goal"] = pd.to_numeric(predictions["actual_goal"], errors="coerce").fillna(0)
    predictions["high_xg_shot"] = predictions["predicted_xg"] >= 0.20

    summary = (
        predictions.groupby(["player_normalized", "player", "team", "league", "season"], dropna=False)
        .agg(
            understat_model_shots=("predicted_xg", "size"),
            understat_model_goals=("actual_goal", "sum"),
            understat_model_xg=("predicted_xg", "sum"),
            understat_source_xg=("source_xg", "sum"),
            avg_understat_model_xg=("predicted_xg", "mean"),
            avg_understat_source_xg=("source_xg", "mean"),
            high_xg_shots=("high_xg_shot", "sum"),
            earliest_match_date=("match_date", "min") if "match_date" in predictions.columns else ("predicted_xg", lambda _: None),
            latest_match_date=("match_date", "max") if "match_date" in predictions.columns else ("predicted_xg", lambda _: None),
        )
        .reset_index()
    )
    summary["understat_model_minus_source_xg"] = (
        summary["understat_model_xg"] - summary["understat_source_xg"]
    )
    summary["data_source"] = "Experimental Understat shot model"
    return summary.sort_values(
        ["player_normalized", "season", "understat_model_xg"],
        ascending=[True, False, False],
    )


def team_shot_summary(team_shots: pd.DataFrame) -> dict:
    """Summarize shot-level xG metrics for a team or player."""
    shots = int(len(team_shots))
    goals = int(team_shots["actual_goal"].sum()) if shots and "actual_goal" in team_shots else 0
    total_xg = float(team_shots["predicted_xg"].sum()) if shots and "predicted_xg" in team_shots else 0.0
    avg_xg = float(total_xg / shots) if shots else 0.0

    return {
        "statsbomb_shots": shots,
        "statsbomb_goals": goals,
        "total_xg": round(total_xg, 4),
        "goals_minus_xg": round(goals - total_xg, 4),
        "avg_xg_per_shot": round(avg_xg, 4),
    }


def date_range(df: pd.DataFrame) -> dict:
    """Return a JSON-safe date range for a shot sample."""
    if df.empty or "match_date" not in df.columns:
        return {"earliest": None, "latest": None}

    dates = pd.to_datetime(df["match_date"], errors="coerce")
    if not dates.notna().any():
        return {"earliest": None, "latest": None}

    return {
        "earliest": str(dates.min().date()),
        "latest": str(dates.max().date()),
    }


def competitions_included(df: pd.DataFrame) -> list[str]:
    """Return sorted competition names for a shot sample."""
    if df.empty or "competition_name" not in df.columns:
        return []
    return sorted(df["competition_name"].dropna().astype(str).unique())


def shot_points(df: pd.DataFrame) -> list[dict]:
    """Return compact shot-location points for frontend pitch maps."""
    required_columns = {"shot_x", "shot_y"}
    if df.empty or not required_columns.issubset(df.columns):
        return []

    columns = [
        "shot_x",
        "shot_y",
        "predicted_xg",
        "actual_goal",
    ]
    available_columns = [column for column in columns if column in df.columns]
    points = df[available_columns].copy()
    points["shot_x"] = pd.to_numeric(points["shot_x"], errors="coerce")
    points["shot_y"] = pd.to_numeric(points["shot_y"], errors="coerce")
    if "predicted_xg" in points.columns:
        points["predicted_xg"] = pd.to_numeric(points["predicted_xg"], errors="coerce")
    if "actual_goal" in points.columns:
        points["actual_goal"] = points["actual_goal"].fillna(False).astype(bool)

    points = points.dropna(subset=["shot_x", "shot_y"])
    return points.to_dict(orient="records")


def squad_status_for_team(team_squad: pd.DataFrame) -> str:
    """Return the most useful squad status label for a team."""
    if team_squad.empty or "squad_status" not in team_squad.columns:
        return "not_available"
    if (team_squad["squad_status"] == "confirmed").any():
        return "confirmed"
    return str(team_squad["squad_status"].dropna().iloc[0])


def count_fbref_matches(team_squad: pd.DataFrame, fbref_context: pd.DataFrame) -> int:
    """Count safe FBref matches for squad players."""
    if team_squad.empty or fbref_context.empty:
        return 0

    matches = 0
    for _, row in team_squad.iterrows():
        matched, _ = fbref_rows_for_player(
            fbref_context,
            row["player"],
            row.get("position_group"),
        )
        if matched:
            matches += 1

    return matches


def count_understat_matches(team_squad: pd.DataFrame, understat_context: pd.DataFrame) -> int:
    """Count safe Understat matches for squad players."""
    if team_squad.empty or understat_context.empty:
        return 0

    matches = 0
    for _, row in team_squad.iterrows():
        matched, _ = understat_rows_for_player(
            understat_context,
            row["player"],
            row.get("position_group"),
        )
        if matched:
            matches += 1

    return matches


def find_player_shots(predictions: pd.DataFrame, team: str, player: str) -> pd.DataFrame:
    """Find a player's StatsBomb shots using configured aliases within one team."""
    team_shots = predictions[predictions["world_cup_team"] == team].copy()
    if team_shots.empty:
        return team_shots

    candidate_names = set(get_aliases_for_player(player))
    candidate_names.add(player)
    normalized_names = {normalize_name(name) for name in candidate_names if name}

    team_shots["_player_normalized"] = team_shots["player"].apply(normalize_name)
    matched = team_shots[team_shots["_player_normalized"].isin(normalized_names)].copy()
    return matched.drop(columns=["_player_normalized"])


def fbref_rows_for_player(
    fbref_context: pd.DataFrame,
    player: str,
    position_group: str | None,
) -> tuple[bool, list[dict]]:
    """Return safe FBref rows for one player."""
    match = match_player_to_context(
        player,
        fbref_context,
        selected_position=position_group,
    )
    if match["confidence"] == MATCH_NONE or match["rows"].empty:
        return False, []

    columns = [
        "season",
        "league",
        "team",
        "pos",
        "minutes",
        "goals",
        "assists",
        "shots",
        "shots_on_target",
        "shots_per_90",
        "xg",
        "npxg",
        "xg_per_90",
        "npxg_per_90",
    ]
    available_columns = [column for column in columns if column in match["rows"].columns]
    rows = match["rows"][available_columns].head(5).to_dict(orient="records")
    return True, rows


def understat_rows_for_player(
    understat_context: pd.DataFrame,
    player: str,
    position_group: str | None,
) -> tuple[bool, list[dict]]:
    """Return safe Understat aggregate rows for one player."""
    match = match_player_to_context(
        player,
        understat_context,
        selected_position=position_group,
    )
    if match["confidence"] == MATCH_NONE or match["rows"].empty:
        return False, []

    columns = [
        "season",
        "league",
        "team",
        "position",
        "games",
        "minutes",
        "goals",
        "assists",
        "shots",
        "xg",
        "npxg",
        "xa",
        "key_passes",
        "xg_chain",
        "xg_buildup",
        "yellow",
        "red",
        "shot_data_shots",
        "shot_data_xg",
        "avg_shot_xg",
    ]
    available_columns = [column for column in columns if column in match["rows"].columns]
    rows = match["rows"][available_columns].head(8).to_dict(orient="records")
    return True, rows


def understat_model_rows_for_player(
    understat_model_context: pd.DataFrame,
    player: str,
    position_group: str | None,
) -> tuple[bool, list[dict], dict | None]:
    """Return experimental Understat model summary rows for one player."""
    match = match_player_to_context(
        player,
        understat_model_context,
        selected_position=position_group,
    )
    if match["confidence"] == MATCH_NONE or match["rows"].empty:
        return False, [], None

    columns = [
        "season",
        "league",
        "team",
        "understat_model_shots",
        "understat_model_goals",
        "understat_model_xg",
        "understat_source_xg",
        "understat_model_minus_source_xg",
        "avg_understat_model_xg",
        "avg_understat_source_xg",
        "high_xg_shots",
        "earliest_match_date",
        "latest_match_date",
    ]
    available_columns = [column for column in columns if column in match["rows"].columns]
    rows = (
        match["rows"][available_columns]
        .round(
            {
                "understat_model_xg": 4,
                "understat_source_xg": 4,
                "understat_model_minus_source_xg": 4,
                "avg_understat_model_xg": 4,
                "avg_understat_source_xg": 4,
            }
        )
        .head(8)
        .to_dict(orient="records")
    )

    matched_rows = match["rows"].copy()
    total_shots = int(pd.to_numeric(matched_rows["understat_model_shots"], errors="coerce").fillna(0).sum())
    total_goals = int(pd.to_numeric(matched_rows["understat_model_goals"], errors="coerce").fillna(0).sum())
    total_model_xg = float(pd.to_numeric(matched_rows["understat_model_xg"], errors="coerce").fillna(0).sum())
    total_source_xg = float(pd.to_numeric(matched_rows["understat_source_xg"], errors="coerce").fillna(0).sum())
    high_xg_shots = int(pd.to_numeric(matched_rows["high_xg_shots"], errors="coerce").fillna(0).sum())
    summary = {
        "shots": total_shots,
        "goals": total_goals,
        "experimental_xg": round(total_model_xg, 4),
        "understat_source_xg": round(total_source_xg, 4),
        "experimental_minus_source_xg": round(total_model_xg - total_source_xg, 4),
        "avg_experimental_xg_per_shot": round(total_model_xg / total_shots, 4) if total_shots else 0.0,
        "avg_understat_source_xg_per_shot": round(total_source_xg / total_shots, 4) if total_shots else 0.0,
        "high_xg_shots": high_xg_shots,
        "match_confidence": match["confidence"],
        "matched_player": match["matched_player"],
    }
    return True, rows, summary


def build_teams_artifact(
    teams: list[str],
    predictions: pd.DataFrame,
    squads: pd.DataFrame,
    fbref_context: pd.DataFrame,
    understat_context: pd.DataFrame,
) -> list[dict]:
    """Build the high-level team list for the dashboard."""
    records = []

    for team in teams:
        team_shots = predictions[predictions["world_cup_team"] == team]
        team_squad = squads[squads["world_cup_team"] == team] if not squads.empty else pd.DataFrame()
        confirmed_squad = team_squad[team_squad["squad_status"] == "confirmed"] if not team_squad.empty else pd.DataFrame()

        players_confirmed = int(len(confirmed_squad))
        fbref_players_matched = count_fbref_matches(confirmed_squad, fbref_context)
        understat_players_matched = count_understat_matches(confirmed_squad, understat_context)
        fbref_coverage_rate = (
            round(fbref_players_matched / players_confirmed, 4)
            if players_confirmed
            else 0.0
        )
        understat_coverage_rate = (
            round(understat_players_matched / players_confirmed, 4)
            if players_confirmed
            else 0.0
        )
        shot_summary = team_shot_summary(team_shots)

        records.append(
            {
                "world_cup_team": team,
                "flag_code": FLAG_CODES.get(team),
                "flag_image_url": flag_image_url(team),
                "squad_status": squad_status_for_team(team_squad),
                "players_confirmed": players_confirmed,
                **shot_summary,
                "fbref_players_matched": fbref_players_matched,
                "fbref_coverage_rate": fbref_coverage_rate,
                "understat_players_matched": understat_players_matched,
                "understat_coverage_rate": understat_coverage_rate,
                "data_confidence": calculate_team_data_confidence(
                    shot_summary["statsbomb_shots"],
                    players_confirmed > 0,
                    max(fbref_coverage_rate, understat_coverage_rate),
                ),
            }
        )

    return records


def top_xg_players(team_shots: pd.DataFrame, top_n: int = 10) -> list[dict]:
    """Return top xG players from a team's StatsBomb shot sample."""
    if team_shots.empty:
        return []

    summary = (
        team_shots.groupby("player", dropna=False)
        .agg(
            shots=("predicted_xg", "size"),
            goals=("actual_goal", "sum"),
            total_xg=("predicted_xg", "sum"),
        )
        .reset_index()
    )
    summary["goals_minus_xg"] = summary["goals"] - summary["total_xg"]
    summary["avg_xg_per_shot"] = summary["total_xg"] / summary["shots"]
    return (
        summary.sort_values("total_xg", ascending=False)
        .head(top_n)
        .round(
            {
                "total_xg": 4,
                "goals_minus_xg": 4,
                "avg_xg_per_shot": 4,
            }
        )
        .to_dict(orient="records")
    )


def top_recent_fbref_players(team_squad: pd.DataFrame, fbref_context: pd.DataFrame) -> list[dict]:
    """Return recent FBref shooting rows for matched squad players."""
    if team_squad.empty or fbref_context.empty:
        return []

    fbref_prepared = fbref_context.copy()
    rows = []
    for _, player_row in team_squad.iterrows():
        player_rows = fbref_prepared[
            fbref_prepared["player_normalized"] == player_row["player_normalized"]
        ].copy()
        if player_rows.empty:
            continue

        player_rows["_season_sort"] = pd.to_numeric(
            player_rows.get("season"),
            errors="coerce",
        ).fillna(-1)
        latest = player_rows.sort_values("_season_sort", ascending=False).iloc[0]
        rows.append(
            {
                "player": player_row["player"],
                "position_group": player_row.get("position_group"),
                "club": player_row.get("club"),
                "league": latest.get("league"),
                "season": latest.get("season"),
                "minutes": latest.get("minutes"),
                "goals": latest.get("goals"),
                "shots": latest.get("shots"),
                "xg": latest.get("xg"),
                "xg_per_90": latest.get("xg_per_90"),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            0 if row.get("xg") is None or pd.isna(row.get("xg")) else float(row.get("xg")),
            0 if row.get("shots") is None or pd.isna(row.get("shots")) else float(row.get("shots")),
        ),
        reverse=True,
    )[:10]


def top_recent_understat_players(team_squad: pd.DataFrame, understat_context: pd.DataFrame) -> list[dict]:
    """Return recent Understat rows for matched squad players."""
    if team_squad.empty or understat_context.empty:
        return []

    understat_prepared = understat_context.copy()
    rows = []
    for _, player_row in team_squad.iterrows():
        player_rows = understat_prepared[
            understat_prepared["player_normalized"] == player_row["player_normalized"]
        ].copy()
        if player_rows.empty:
            continue

        player_rows["_season_sort"] = pd.to_numeric(
            player_rows.get("season"),
            errors="coerce",
        ).fillna(-1)
        latest = player_rows.sort_values("_season_sort", ascending=False).iloc[0]
        rows.append(
            {
                "player": player_row["player"],
                "position_group": player_row.get("position_group"),
                "club": player_row.get("club"),
                "league": latest.get("league"),
                "season": latest.get("season"),
                "team": latest.get("team"),
                "games": latest.get("games"),
                "minutes": latest.get("minutes"),
                "goals": latest.get("goals"),
                "assists": latest.get("assists"),
                "shots": latest.get("shots"),
                "xg": latest.get("xg"),
                "npxg": latest.get("npxg"),
                "xa": latest.get("xa"),
                "xg_chain": latest.get("xg_chain"),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            0 if row.get("xg") is None or pd.isna(row.get("xg")) else float(row.get("xg")),
            0 if row.get("shots") is None or pd.isna(row.get("shots")) else float(row.get("shots")),
        ),
        reverse=True,
    )[:10]


def position_group_summaries(team_squad: pd.DataFrame, predictions: pd.DataFrame, team: str) -> list[dict]:
    """Summarize squad count and StatsBomb shots by position group."""
    if team_squad.empty:
        return []

    records = []
    for position_group, group in team_squad.groupby("position_group", dropna=False):
        statsbomb_shots = 0
        for player in group["player"].dropna():
            statsbomb_shots += len(find_player_shots(predictions, team, player))
        records.append(
            {
                "position_group": position_group,
                "squad_players": int(len(group)),
                "statsbomb_shots": int(statsbomb_shots),
            }
        )
    return sorted(records, key=lambda row: str(row["position_group"]))


def build_team_profiles_artifact(
    teams: list[str],
    predictions: pd.DataFrame,
    squads: pd.DataFrame,
    fbref_context: pd.DataFrame,
    understat_context: pd.DataFrame,
) -> list[dict]:
    """Build detailed team profiles for the dashboard."""
    profiles = []
    for team in teams:
        team_shots = predictions[predictions["world_cup_team"] == team]
        team_squad = squads[
            (squads["world_cup_team"] == team) & (squads["squad_status"] == "confirmed")
        ] if not squads.empty else pd.DataFrame()
        shot_summary = team_shot_summary(team_shots)
        warnings = []
        if shot_summary["statsbomb_shots"] < 100:
            warnings.append("Small sample size: scoring-zone patterns may not be reliable.")
        if team_squad.empty:
            warnings.append("Confirmed squad data is not available for this team yet.")

        profiles.append(
            {
                "world_cup_team": team,
                "flag_code": FLAG_CODES.get(team),
                "flag_image_url": flag_image_url(team),
                **shot_summary,
                "statsbomb_date_range": date_range(team_shots),
                "competitions_included": competitions_included(team_shots),
                "shot_points": shot_points(team_shots),
                "top_xg_players": top_xg_players(team_shots),
                "top_recent_fbref_players": top_recent_fbref_players(team_squad, fbref_context),
                "top_recent_understat_players": top_recent_understat_players(
                    team_squad,
                    understat_context,
                ),
                "position_group_summaries": position_group_summaries(
                    team_squad,
                    predictions,
                    team,
                ),
                "warnings": warnings,
            }
        )
    return profiles


def build_player_profiles_artifact(
    squads: pd.DataFrame,
    predictions: pd.DataFrame,
    fbref_context: pd.DataFrame,
    understat_context: pd.DataFrame,
    understat_model_context: pd.DataFrame,
) -> list[dict]:
    """Build one player profile object per squad player."""
    if squads.empty:
        return []

    profiles = []
    for _, row in squads.sort_values(["world_cup_team", "player"]).iterrows():
        player = row["player"]
        team = row["world_cup_team"]
        player_shots = find_player_shots(predictions, team, player)
        shot_summary = team_shot_summary(player_shots)
        fbref_available, fbref_rows = fbref_rows_for_player(
            fbref_context,
            player,
            row.get("position_group"),
        )
        understat_available, understat_rows = understat_rows_for_player(
            understat_context,
            player,
            row.get("position_group"),
        )
        (
            understat_model_available,
            understat_model_rows,
            understat_model_summary,
        ) = understat_model_rows_for_player(
            understat_model_context,
            player,
            row.get("position_group"),
        )

        warnings = []
        if shot_summary["statsbomb_shots"] < 20:
            warnings.append(
                "This player is in the official World Cup squad, but the available "
                "historical StatsBomb data has too few shot events to create a reliable "
                "scoring-zone profile."
            )
        if not fbref_available:
            warnings.append(
                "FBref aggregate context is not available for this player with the "
                "currently supported/pulled leagues."
            )
        if not understat_available:
            warnings.append(
                "Understat club xG context is not available for this player in the "
                "current top-league/RFPL archive."
            )
        if not understat_model_available:
            warnings.append(
                "Experimental Understat shot-model context is not available for this player."
            )

        profiles.append(
            {
                "player": player,
                "player_normalized": row.get("player_normalized", normalize_name(player)),
                "world_cup_team": team,
                "position": row.get("position"),
                "position_group": row.get("position_group"),
                "club": row.get("club"),
                "league": row.get("league"),
                "squad_status": row.get("squad_status"),
                **shot_summary,
                "statsbomb_date_range": date_range(player_shots),
                "shot_points": shot_points(player_shots),
                "fbref_available": fbref_available,
                "fbref_recent_rows": fbref_rows,
                "understat_available": understat_available,
                "understat_recent_rows": understat_rows,
                "understat_model_available": understat_model_available,
                "understat_model_recent_rows": understat_model_rows,
                "understat_model_summary": understat_model_summary,
                "data_confidence": calculate_player_data_confidence(
                    shot_summary["statsbomb_shots"],
                    fbref_available or understat_available or understat_model_available,
                ),
                "imageUrl": None,
                "avatarSeed": row.get("player_normalized", normalize_name(player)),
                "warnings": warnings,
            }
        )
    return profiles


def build_squad_players_artifact(squads: pd.DataFrame) -> list[dict]:
    """Build a cleaned squad-player list."""
    if squads.empty:
        return []

    columns = [
        "world_cup_team",
        "player",
        "player_normalized",
        "position",
        "position_group",
        "club",
        "league",
        "squad_status",
        "data_source",
    ]
    available_columns = [column for column in columns if column in squads.columns]
    output = squads[available_columns].copy()
    output["imageUrl"] = None
    output["avatarSeed"] = output.get("player_normalized", output["player"].apply(normalize_name))
    return output.sort_values(["world_cup_team", "player"]).to_dict(orient="records")


def build_model_summary_artifact() -> dict:
    """Build a small model summary for dashboard display."""
    comparison = read_csv_if_exists(MODEL_COMPARISON_PATH)
    source_comparison = read_csv_if_exists(SOURCE_MODEL_COMPARISON_PATH)
    feature_missingness = read_csv_if_exists(FEATURE_MISSINGNESS_PATH)
    metrics = comparison.to_dict(orient="records") if not comparison.empty else []
    best_model = None
    if not comparison.empty and "log_loss" in comparison.columns:
        best_model = comparison.sort_values("log_loss").iloc[0]["model_name"]

    research_metrics = (
        source_comparison.to_dict(orient="records")
        if not source_comparison.empty
        else []
    )
    best_research_model = None
    if not source_comparison.empty and "log_loss" in source_comparison.columns:
        best_research_model = source_comparison.sort_values("log_loss").iloc[0]["model_label"]

    feature_experiments = (
        feature_missingness.to_dict(orient="records")
        if not feature_missingness.empty
        else []
    )

    return {
        "experiment_name": "world-cup-xg-lab",
        "best_model_by_log_loss": best_model,
        "models": metrics,
        "production_models": metrics,
        "research_source_models": research_metrics,
        "feature_missingness_experiments": feature_experiments,
        "best_research_model_by_log_loss": best_research_model,
        "research_explanation": (
            "Research experiments compare StatsBomb-only, Understat-only, "
            "combined-source, and reduced-feature xG models. These results are "
            "shown for transparency and are not automatically promoted into the "
            "dashboard's production player xG layer."
        ),
        "xg_explanation": (
            "Expected goals estimates the probability that a shot becomes a goal "
            "based on shot features available to the model."
        ),
        "limitations": [
            "StatsBomb powers the historical shot-location model and shot maps.",
            "FBref aggregate data is recent player context only and does not replace the xG model.",
            "Understat aggregate and shot-derived data is club context. The Understat shot model is experimental.",
            "Small samples are shown with warnings and should not be read as guaranteed future scoring locations.",
        ],
    }


def build_data_coverage_artifact(
    teams: list[str],
    predictions: pd.DataFrame,
    squads: pd.DataFrame,
    fbref_context: pd.DataFrame,
    understat_context: pd.DataFrame,
) -> dict:
    """Build high-level data coverage metadata."""
    found_statsbomb_teams = sorted(predictions["world_cup_team"].dropna().unique())
    missing_statsbomb_teams = sorted(set(teams) - set(found_statsbomb_teams))
    confirmed_squad_teams = sorted(
        squads.loc[squads["squad_status"] == "confirmed", "world_cup_team"].dropna().unique()
    ) if not squads.empty else []
    missing_squad_teams = sorted(set(teams) - set(confirmed_squad_teams))

    confirmed_squads = squads[squads["squad_status"] == "confirmed"].copy() if not squads.empty else pd.DataFrame()
    fbref_matched = count_fbref_matches(confirmed_squads, fbref_context)
    understat_matched = count_understat_matches(confirmed_squads, understat_context)
    total_squad_players = int(len(confirmed_squads))

    return {
        "total_world_cup_teams": len(teams),
        "teams_with_squad_data": len(confirmed_squad_teams),
        "teams_missing_squad_data": missing_squad_teams,
        "teams_with_statsbomb_data": len(found_statsbomb_teams),
        "missing_teams": missing_statsbomb_teams,
        "total_squad_players": total_squad_players,
        "fbref_matched_players": fbref_matched,
        "fbref_missing_players": total_squad_players - fbref_matched,
        "fbref_coverage_rate": round(fbref_matched / total_squad_players, 4)
        if total_squad_players
        else 0.0,
        "understat_matched_players": understat_matched,
        "understat_missing_players": total_squad_players - understat_matched,
        "understat_coverage_rate": round(understat_matched / total_squad_players, 4)
        if total_squad_players
        else 0.0,
        "date_range": date_range(predictions),
        "known_limitations": [
            "The xG model and shot maps use historical StatsBomb open/event data.",
            "The dashboard is not a complete 2026 prediction model.",
            "FBref aggregate data is used only as recent player context.",
            "Understat club xG data is used only as recent/historical club context.",
            "Player images are intentionally left as placeholders unless approved/licensed sources are provided.",
        ],
    }


def main() -> None:
    """Build dashboard-ready JSON artifacts for Streamlit and future frontend work."""
    teams = load_world_cup_teams()
    predictions = prepare_predictions()
    squads = prepare_squads()
    fbref_context = prepare_fbref_context()
    understat_context = prepare_understat_context()
    understat_model_context = prepare_understat_model_context()

    write_json(
        "teams.json",
        build_teams_artifact(teams, predictions, squads, fbref_context, understat_context),
    )
    write_json(
        "team_profiles.json",
        build_team_profiles_artifact(
            teams,
            predictions,
            squads,
            fbref_context,
            understat_context,
        ),
    )
    write_json(
        "player_profiles.json",
        build_player_profiles_artifact(
            squads,
            predictions,
            fbref_context,
            understat_context,
            understat_model_context,
        ),
    )
    write_json("squad_players.json", build_squad_players_artifact(squads))
    write_json("model_summary.json", build_model_summary_artifact())
    write_json(
        "data_coverage.json",
        build_data_coverage_artifact(
            teams,
            predictions,
            squads,
            fbref_context,
            understat_context,
        ),
    )

    print("Dashboard artifacts are ready for a future frontend.")


if __name__ == "__main__":
    main()
