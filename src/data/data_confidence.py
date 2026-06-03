import pandas as pd


def _safe_int(value) -> int:
    """Convert missing or numeric-like values to a safe integer."""
    if pd.isna(value):
        return 0
    return int(value)


def calculate_player_data_confidence(statsbomb_shots, fbref_available) -> str:
    """Return a player-level data confidence label."""
    statsbomb_shots = _safe_int(statsbomb_shots)
    fbref_available = bool(fbref_available)

    if statsbomb_shots >= 40 and fbref_available:
        return "Strong"
    if statsbomb_shots >= 20:
        return "Moderate"
    if statsbomb_shots > 0 or fbref_available:
        return "Limited"
    return "Unavailable"


def calculate_team_data_confidence(
    team_shots,
    squad_confirmed,
    fbref_coverage_rate,
) -> str:
    """Return a team-level data confidence label."""
    team_shots = _safe_int(team_shots)

    if team_shots >= 500 and bool(squad_confirmed):
        return "Strong"
    if team_shots >= 150:
        return "Moderate"
    if team_shots > 0:
        return "Limited"
    return "Unavailable"
