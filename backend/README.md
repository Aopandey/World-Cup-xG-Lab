# World Cup xG Lab API

This FastAPI backend serves precomputed dashboard artifacts from `data/dashboard_artifacts/`.
It does not retrain models or rebuild data pipelines at request time.

## Generate Artifacts First

From the project root, run:

```bash
python scripts/build_dashboard_artifacts.py
python scripts/validate_dashboard_artifacts.py
```

## Run the API

```bash
uvicorn backend.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

## Example Endpoints

```text
GET /
GET /api/teams
GET /api/teams/Argentina
GET /api/teams/Argentina/squad
GET /api/players
GET /api/players?team=Argentina&position_group=Forward
GET /api/players/Lionel Messi
GET /api/model/summary
GET /api/coverage
GET /api/search?q=Messi
```

The backend enables CORS for `http://localhost:3000` so a local Next.js frontend can call these endpoints during development.
