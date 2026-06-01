from pathlib import Path
import re
import unicodedata

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALIASES_PATH = PROJECT_ROOT / "configs" / "player_aliases.yaml"

MATCH_EXACT = "Exact match"
MATCH_ALIAS = "Alias match"
MATCH_FUZZY = "Safe fuzzy match"
MATCH_NONE = "No reliable match"


def normalize_name(name) -> str:
    """Normalize names for safer cross-source matching."""
    if pd.isna(name):
        return ""

    normalized = unicodedata.normalize("NFKD", str(name))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.casefold()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _resolve_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    return resolved


def load_player_aliases(
    config_path: str | Path = DEFAULT_ALIASES_PATH,
) -> dict[str, list[str]]:
    """Load configured player aliases."""
    path = _resolve_path(config_path)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    return config.get("player_aliases", {})


def get_aliases_for_player(player_name) -> list[str]:
    """Return aliases for a player if the configured canonical/alias names match."""
    player_normalized = normalize_name(player_name)

    for canonical_name, aliases in load_player_aliases().items():
        all_names = [canonical_name] + list(aliases or [])
        normalized_names = {normalize_name(name) for name in all_names}
        if player_normalized in normalized_names:
            return list(dict.fromkeys(all_names))

    return [str(player_name)] if not pd.isna(player_name) else []


def _position_is_goalkeeper(position) -> bool:
    normalized = normalize_name(position)
    return normalized in {"gk", "goalkeeper", "goalkeepers"} or "goalkeeper" in normalized


def _prepare_player_frame(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    if "player_normalized" not in prepared.columns and "player" in prepared.columns:
        prepared["player_normalized"] = prepared["player"].apply(normalize_name)
    return prepared


def _safe_fuzzy_mask(names: pd.Series, selected_normalized: str) -> pd.Series:
    selected_tokens = selected_normalized.split()

    if len(selected_tokens) < 2:
        return pd.Series(False, index=names.index)

    def is_safe(candidate: str) -> bool:
        candidate_tokens = str(candidate).split()
        if len(candidate_tokens) < 2:
            return False
        return selected_normalized in candidate or candidate in selected_normalized

    return names.fillna("").apply(is_safe)


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


def match_player_to_fbref(
    selected_player,
    fbref_df: pd.DataFrame,
    selected_team=None,
    selected_position=None,
) -> dict:
    """Match a selected player to FBref rows using safe ordered matching rules."""
    if fbref_df.empty or "player" not in fbref_df.columns:
        return {"rows": pd.DataFrame(), "confidence": MATCH_NONE, "matched_player": None}

    selected_normalized = normalize_name(selected_player)
    candidates = _prepare_player_frame(fbref_df)
    candidates = _filter_goalkeeper_mismatch(candidates, selected_position)

    exact = candidates[candidates["player_normalized"] == selected_normalized]
    if not exact.empty:
        sorted_exact = _sort_match_candidates(exact)
        return {
            "rows": sorted_exact,
            "confidence": MATCH_EXACT,
            "matched_player": sorted_exact["player"].iloc[0],
        }

    alias_names = get_aliases_for_player(selected_player)
    alias_normalized = {normalize_name(alias) for alias in alias_names}
    alias = candidates[candidates["player_normalized"].isin(alias_normalized)]
    if not alias.empty:
        sorted_alias = _sort_match_candidates(alias)
        return {
            "rows": sorted_alias,
            "confidence": MATCH_ALIAS,
            "matched_player": sorted_alias["player"].iloc[0],
        }

    fuzzy = candidates[_safe_fuzzy_mask(candidates["player_normalized"], selected_normalized)]
    if fuzzy["player"].nunique() == 1:
        sorted_fuzzy = _sort_match_candidates(fuzzy)
        return {
            "rows": sorted_fuzzy,
            "confidence": MATCH_FUZZY,
            "matched_player": sorted_fuzzy["player"].iloc[0],
        }

    return {"rows": pd.DataFrame(), "confidence": MATCH_NONE, "matched_player": None}


def match_player_to_squad(
    selected_player,
    squad_df: pd.DataFrame,
    selected_team=None,
) -> dict:
    """Match a selected player to the official squad table."""
    if squad_df.empty or "player" not in squad_df.columns:
        return {"row": None, "confidence": MATCH_NONE, "matched_player": None}

    selected_normalized = normalize_name(selected_player)
    candidates = _prepare_player_frame(squad_df)

    if selected_team and "world_cup_team" in candidates.columns:
        candidates = candidates[candidates["world_cup_team"] == selected_team]

    exact = candidates[candidates["player_normalized"] == selected_normalized]
    if not exact.empty:
        return {
            "row": exact.iloc[0],
            "confidence": MATCH_EXACT,
            "matched_player": exact["player"].iloc[0],
        }

    alias_names = get_aliases_for_player(selected_player)
    alias_normalized = {normalize_name(alias) for alias in alias_names}
    alias = candidates[candidates["player_normalized"].isin(alias_normalized)]
    if not alias.empty:
        return {
            "row": alias.iloc[0],
            "confidence": MATCH_ALIAS,
            "matched_player": alias["player"].iloc[0],
        }

    fuzzy = candidates[_safe_fuzzy_mask(candidates["player_normalized"], selected_normalized)]
    if fuzzy["player"].nunique() == 1:
        return {
            "row": fuzzy.iloc[0],
            "confidence": MATCH_FUZZY,
            "matched_player": fuzzy["player"].iloc[0],
        }

    return {"row": None, "confidence": MATCH_NONE, "matched_player": None}
