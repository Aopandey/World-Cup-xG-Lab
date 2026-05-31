from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = "configs/world_cup_2026_teams.yaml"


def _resolve_config_path(config_path: str | Path) -> Path:
    path = Path(config_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _canonical_key(team_name: str) -> str:
    return " ".join(str(team_name).strip().casefold().split())


def load_world_cup_teams(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> list[str]:
    """Load the configured 2026 World Cup team list."""
    path = _resolve_config_path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"World Cup team config not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config["qualified_teams"]


def build_team_alias_lookup(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> dict[str, str]:
    """Build a lookup from dataset team aliases to normalized World Cup names."""
    path = _resolve_config_path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"World Cup team config not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    qualified_teams = config["qualified_teams"]
    team_name_aliases = config.get("team_name_aliases", {})
    alias_lookup = {}

    for team in qualified_teams:
        alias_lookup[_canonical_key(team)] = team

    for normalized_team, aliases in team_name_aliases.items():
        alias_lookup[_canonical_key(normalized_team)] = normalized_team
        for alias in aliases:
            alias_lookup[_canonical_key(alias)] = normalized_team

    return alias_lookup


def normalize_team_name(team_name, alias_lookup: dict[str, str]) -> str | None:
    """Return the normalized World Cup team name for a raw team value."""
    if pd.isna(team_name):
        return None

    return alias_lookup.get(_canonical_key(team_name))


def filter_world_cup_teams(
    df: pd.DataFrame,
    team_col: str = "team",
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> pd.DataFrame:
    """Keep rows matching 2026 World Cup teams and add world_cup_team."""
    if team_col not in df.columns:
        raise ValueError(f"Team column not found: {team_col}")

    alias_lookup = build_team_alias_lookup(config_path)
    filtered = df.copy()
    filtered["world_cup_team"] = filtered[team_col].apply(
        lambda team: normalize_team_name(team, alias_lookup)
    )

    return filtered[filtered["world_cup_team"].notna()].copy()


def get_available_world_cup_teams(
    df: pd.DataFrame,
    team_col: str = "team",
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> list[str]:
    """Return normalized World Cup teams found in the current dataset."""
    filtered = filter_world_cup_teams(df, team_col=team_col, config_path=config_path)
    return sorted(filtered["world_cup_team"].dropna().unique())
