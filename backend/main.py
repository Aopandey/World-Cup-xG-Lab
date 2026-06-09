from pathlib import Path
import logging
import os

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.data_loader import (
    ArtifactError,
    get_artifact_status,
    get_players,
    get_teams,
    validate_required_artifacts,
)
from backend.routes import coverage, model, players, teams


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FLAGS_DIR = PROJECT_ROOT / "data" / "World Cup Flags"
DATAMB_RADARS_DIR = PROJECT_ROOT / "data" / "generated" / "datamb_radars"
APP_VERSION = "0.1.0"
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

logger = logging.getLogger("world_cup_xg_lab_api")


def get_allowed_origins() -> list[str]:
    """Return CORS origins from env, with local development defaults."""
    raw_origins = os.getenv("BACKEND_ALLOWED_ORIGINS", "")
    if not raw_origins.strip():
        return DEFAULT_ALLOWED_ORIGINS

    return [
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip()
    ]

app = FastAPI(
    title="World Cup xG Lab API",
    description="API for serving precomputed World Cup xG Lab dashboard artifacts.",
    version=APP_VERSION,
)

allowed_origins = get_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials="*" not in allowed_origins,
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


@app.on_event("startup")
def check_dashboard_artifacts_on_startup():
    """Log artifact readiness with clear messages when files are missing."""
    missing_files = validate_required_artifacts()
    if missing_files:
        logger.warning(
            "Dashboard artifact startup check found missing files: %s. "
            "Run `python scripts/build_dashboard_artifacts.py` and "
            "`python scripts/validate_dashboard_artifacts.py` before using the dashboard.",
            ", ".join(missing_files),
        )
        return

    logger.info("Dashboard artifact startup check passed.")


@app.get("/")
def read_root():
    """Return project metadata and available endpoints."""
    return {
        "project": "World Cup xG Lab",
        "description": (
            "FastAPI backend serving precomputed dashboard artifacts for historical "
            "StatsBomb xG analysis and source-aware player/team context."
        ),
        "available_endpoints": [
            "/health",
            "/api/meta",
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


@app.get("/health")
def health_check():
    """Return API status and required artifact availability."""
    artifact_status = get_artifact_status()
    missing_files = artifact_status["missing_files"]
    return {
        "status": "ok" if not missing_files else "degraded",
        "api": "online",
        "project": "World Cup xG Lab",
        "version": APP_VERSION,
        "artifact_status": artifact_status,
    }


@app.get("/api/meta")
def read_meta():
    """Return lightweight project and artifact metadata for clients."""
    artifact_status = get_artifact_status()
    return {
        "project": "World Cup xG Lab",
        "description": "Next.js + FastAPI dashboard powered by precomputed JSON artifacts.",
        "version": APP_VERSION,
        "artifact_dir": artifact_status["artifact_dir"],
        "artifact_files_found": [
            filename
            for filename, metadata in artifact_status["artifacts"].items()
            if metadata["exists"]
        ],
        "missing_artifact_files": artifact_status["missing_files"],
        "artifacts": artifact_status["artifacts"],
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
