from fastapi import APIRouter, HTTPException, Query

from backend.data_loader import get_player_profile, get_players


router = APIRouter(prefix="/api/players", tags=["players"])


def _matches_filter(value, selected_filter) -> bool:
    if selected_filter is None:
        return True
    return str(value).casefold() == selected_filter.casefold()


@router.get("")
def list_players(
    team: str | None = Query(default=None),
    position_group: str | None = Query(default=None),
    data_confidence: str | None = Query(default=None),
):
    """Return player profiles with optional filters."""
    players = get_players()
    filtered_players = [
        player
        for player in players
        if _matches_filter(player.get("world_cup_team"), team)
        and _matches_filter(player.get("position_group"), position_group)
        and _matches_filter(player.get("data_confidence"), data_confidence)
    ]

    return {
        "count": len(filtered_players),
        "players": filtered_players,
    }


@router.get("/{player_name}")
def read_player_profile(player_name: str):
    """Return one player profile."""
    profile = get_player_profile(player_name)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Player not found: {player_name}")
    return profile
