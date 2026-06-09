from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.data_loader import ArtifactError, get_players, get_teams
from backend.routes import coverage, model, players, teams


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FLAGS_DIR = PROJECT_ROOT / "data" / "World Cup Flags"
DATAMB_RADARS_DIR = PROJECT_ROOT / "data" / "generated" / "datamb_radars"

app = FastAPI(
    title="World Cup xG Lab API",
    description="API for serving precomputed World Cup xG Lab dashboard artifacts.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(teams.router)
app.include_router(players.router)
app.include_router(model.router)
app.include_router(coverage.router)

if FLAGS_DIR.exists():
    app.mount(
        "/static/world-cup-flags",
        StaticFiles(directory=FLAGS_DIR),
        name="world-cup-flags",
    )

if DATAMB_RADARS_DIR.exists():
    app.mount(
        "/static/generated/datamb-radars",
        StaticFiles(directory=DATAMB_RADARS_DIR),
        name="datamb-radars",
    )


def _matches_query(value, query: str) -> bool:
    return query.casefold() in str(value).casefold()


@app.exception_handler(ArtifactError)
def artifact_error_handler(_, error: ArtifactError):
    """Return clean API errors for missing or invalid artifacts."""
    return JSONResponse(status_code=500, content={"detail": str(error)})


@app.get("/")
def read_root():
    """Return project metadata and available endpoints."""
    return {
        "project": "World Cup xG Lab",
        "description": (
            "FastAPI backend serving precomputed dashboard artifacts for historical "
            "StatsBomb xG analysis and recent FBref player context."
        ),
        "available_endpoints": [
            "/api/teams",
            "/api/teams/{team_name}",
            "/api/teams/{team_name}/squad",
            "/api/players",
            "/api/players/{player_name}",
            "/api/model/summary",
            "/api/coverage",
            "/api/search?q={query}",
        ],
    }


@app.get("/api/search")
def search(q: str = Query(..., min_length=1)):
    """Return teams and players matching a search query."""
    matching_teams = [
        team
        for team in get_teams()
        if _matches_query(team.get("world_cup_team", ""), q)
    ]
    matching_players = [
        player
        for player in get_players()
        if _matches_query(player.get("player", ""), q)
        or _matches_query(player.get("world_cup_team", ""), q)
        or _matches_query(player.get("club", ""), q)
    ]

    return {
        "query": q,
        "teams": matching_teams,
        "players": matching_players,
        "team_count": len(matching_teams),
        "player_count": len(matching_players),
    }
