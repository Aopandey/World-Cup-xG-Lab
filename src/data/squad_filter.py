from pathlib import Path

import pandas as pd

from src.data.player_matching import normalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQUAD_PATH = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"


def _resolve_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    return resolved


def load_world_cup_squads(
    path: str | Path = DEFAULT_SQUAD_PATH,
) -> pd.DataFrame:
    """Load the cleaned World Cup squad table when available."""
    resolved = _resolve_path(path)
    if not resolved.exists():
        return pd.DataFrame()

    return pd.read_csv(resolved)


def build_squad_alias_lookup(squad_df: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """Build an exact normalized lookup for squad players by team and player."""
    if squad_df.empty:
        return {}

    lookup = {}
    prepared = squad_df.copy()
    prepared["team_normalized"] = prepared.get(
        "team_normalized",
        prepared["world_cup_team"].apply(normalize_name),
    )
    prepared["player_normalized"] = prepared.get(
        "player_normalized",
        prepared["player"].apply(normalize_name),
    )

    for _, row in prepared.iterrows():
        key = (row["team_normalized"], row["player_normalized"])
        lookup[key] = row.to_dict()

    return lookup


def _confirmed_squads(squad_df: pd.DataFrame) -> pd.DataFrame:
    if squad_df.empty or "squad_status" not in squad_df.columns:
        return pd.DataFrame()

    return squad_df[squad_df["squad_status"] == "confirmed"].copy()


def teams_with_confirmed_squads(squad_df: pd.DataFrame) -> set[str]:
    """Return teams with confirmed squad data."""
    confirmed = _confirmed_squads(squad_df)
    if confirmed.empty:
        return set()
    return set(confirmed["world_cup_team"].dropna().unique())


def teams_without_confirmed_squads(squad_df: pd.DataFrame) -> list[str]:
    """Return teams in the squad file that do not have confirmed squad data."""
    if squad_df.empty:
        return []

    all_teams = set(squad_df["world_cup_team"].dropna().unique())
    return sorted(all_teams - teams_with_confirmed_squads(squad_df))


def add_squad_player_columns(
    df: pd.DataFrame,
    squad_df: pd.DataFrame | None = None,
    player_col: str = "player",
    team_col: str = "world_cup_team",
) -> pd.DataFrame:
    """Add exact squad metadata columns without dropping unmatched rows."""
    if squad_df is None:
        squad_df = load_world_cup_squads()

    if df.empty or squad_df.empty:
        output = df.copy()
        output["squad_player"] = pd.NA
        output["squad_position_group"] = pd.NA
        return output

    if player_col not in df.columns:
        raise ValueError(f"Player column not found: {player_col}")
    if team_col not in df.columns:
        raise ValueError(f"Team column not found: {team_col}")

    confirmed = _confirmed_squads(squad_df)
    merge_cols = [
        "world_cup_team",
        "player",
        "position",
        "position_group",
        "club",
        "league",
        "player_normalized",
        "team_normalized",
    ]
    squad_lookup = confirmed[merge_cols].rename(
        columns={
            "player": "squad_player",
            "position": "squad_position",
            "position_group": "squad_position_group",
            "club": "squad_club",
            "league": "squad_league",
        }
    )

    output = df.copy()
    output["_team_normalized"] = output[team_col].apply(normalize_name)
    output["_player_normalized"] = output[player_col].apply(normalize_name)

    merged = output.merge(
        squad_lookup,
        left_on=["_team_normalized", "_player_normalized"],
        right_on=["team_normalized", "player_normalized"],
        how="left",
    )
    return merged.drop(
        columns=[
            "_team_normalized",
            "_player_normalized",
            "team_normalized",
            "player_normalized",
            "world_cup_team_y",
        ],
        errors="ignore",
    ).rename(columns={"world_cup_team_x": "world_cup_team"})


def filter_to_squad_players(
    df: pd.DataFrame,
    player_col: str = "player",
    team_col: str = "world_cup_team",
) -> pd.DataFrame:
    """Keep only official squad players for teams with confirmed squad data."""
    squad_df = load_world_cup_squads()
    enriched = add_squad_player_columns(df, squad_df, player_col=player_col, team_col=team_col)
    confirmed_teams = teams_with_confirmed_squads(squad_df)

    if not confirmed_teams:
        return enriched

    team_has_confirmed_squad = enriched[team_col].isin(confirmed_teams)
    matched_squad_player = enriched["squad_player"].notna()
    return enriched[(~team_has_confirmed_squad) | matched_squad_player].copy()


def get_available_squad_players(
    statsbomb_df: pd.DataFrame,
    squad_df: pd.DataFrame,
) -> pd.DataFrame:
    """Return confirmed squad players who exist in the StatsBomb shot dataset."""
    if statsbomb_df.empty or squad_df.empty:
        return pd.DataFrame()

    filtered = add_squad_player_columns(statsbomb_df, squad_df)
    return filtered[filtered["squad_player"].notna()][
        ["world_cup_team", "squad_player", "squad_position_group"]
    ].drop_duplicates().sort_values(["world_cup_team", "squad_player"])


def get_missing_squad_players_in_statsbomb(
    statsbomb_df: pd.DataFrame,
    squad_df: pd.DataFrame,
) -> pd.DataFrame:
    """Return confirmed squad players with no exact StatsBomb shot match."""
    confirmed = _confirmed_squads(squad_df)
    available = get_available_squad_players(statsbomb_df, squad_df)

    if confirmed.empty:
        return pd.DataFrame()

    available_keys = set(
        zip(
            available.get("world_cup_team", pd.Series(dtype=str)),
            available.get("squad_player", pd.Series(dtype=str)),
        )
    )
    missing = confirmed[
        ~confirmed.apply(
            lambda row: (row["world_cup_team"], row["player"]) in available_keys,
            axis=1,
        )
    ]
    return missing.copy()


def get_missing_squad_players_in_fbref(
    fbref_df: pd.DataFrame,
    squad_df: pd.DataFrame,
) -> pd.DataFrame:
    """Return confirmed squad players with no exact FBref player-name match."""
    confirmed = _confirmed_squads(squad_df)
    if confirmed.empty:
        return pd.DataFrame()
    if fbref_df.empty or "player" not in fbref_df.columns:
        return confirmed.copy()

    fbref_names = set(fbref_df["player"].apply(normalize_name))
    return confirmed[~confirmed["player_normalized"].isin(fbref_names)].copy()
