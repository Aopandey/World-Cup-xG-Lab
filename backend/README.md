# World Cup xG Lab API

This FastAPI backend serves precomputed dashboard artifacts from `data/dashboard_artifacts/`.
It does not retrain models or rebuild data pipelines at request time.

## Production Dashboard Architecture

World Cup xG Lab's production-style dashboard uses:

- Frontend: Next.js + TypeScript + Tailwind
- Backend: FastAPI
- Data: precomputed JSON artifacts in `data/dashboard_artifacts/`

Streamlit remains in the repository as an earlier prototype and internal exploration tool. It is not the production dashboard surface. FastAPI loads existing artifacts and serves JSON to the Next.js frontend; models are not retrained at request time.

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

## Environment Variables

```text
BACKEND_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

If `BACKEND_ALLOWED_ORIGINS` is not set, the API defaults to the two local Next.js origins above.

## Example Endpoints

```text
GET /
GET /health
GET /api/meta
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

`GET /health` reports API status and required artifact availability. `GET /api/meta` reports project metadata, artifact files found, and artifact modified timestamps.

## Local Full-App Run

Terminal 1, from the project root:

```bash
uvicorn backend.main:app --reload
```

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:3000
```

## Docker

From the project root:

```bash
docker compose up --build
```

The backend container serves `http://localhost:8000` and exposes `GET /health` for Compose health checks. The image includes the FastAPI code, precomputed dashboard JSON artifacts, World Cup flags, and generated DataMB radar images. It excludes raw/cached data and does not retrain models at startup.
