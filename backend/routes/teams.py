from fastapi import APIRouter, HTTPException

from backend.data_loader import get_squad_players, get_team_profile, get_teams


router = APIRouter(prefix="/api/teams", tags=["teams"])


def _normalize(value) -> str:
    return " ".join(str(value).casefold().split())


@router.get("")
def list_teams():
    """Return all World Cup team summaries."""
    return get_teams()


@router.get("/{team_name}")
def read_team_profile(team_name: str):
    """Return one detailed team profile."""
    profile = get_team_profile(team_name)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Team not found: {team_name}")
    return profile


@router.get("/{team_name}/squad")
def read_team_squad(team_name: str):
    """Return squad players for one team."""
    requested_team = _normalize(team_name)
    squad_players = [
        player
        for player in get_squad_players()
        if _normalize(player.get("world_cup_team", "")) == requested_team
    ]

    if not squad_players:
        raise HTTPException(status_code=404, detail=f"Squad not found for team: {team_name}")

    return {
        "world_cup_team": squad_players[0]["world_cup_team"],
        "players": squad_players,
        "count": len(squad_players),
    }
