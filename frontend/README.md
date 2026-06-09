# World Cup xG Lab Frontend

Next.js frontend for the World Cup xG Lab dashboard. It consumes the FastAPI backend, which serves precomputed JSON artifacts from `data/dashboard_artifacts/`.

## Production Dashboard Architecture

The current production-style dashboard is:

- Frontend: Next.js + TypeScript + Tailwind
- Backend: FastAPI
- Data source for the app: precomputed JSON artifacts in `data/dashboard_artifacts/`

Streamlit still exists in the repository as an earlier prototype/internal exploration surface. The production-style app is the Next.js frontend consuming FastAPI endpoints. Models are not retrained from the browser or API request path.

## Prerequisites

Generate dashboard artifacts from the project root:

```bash
python scripts/build_dashboard_artifacts.py
python scripts/validate_dashboard_artifacts.py
```

Start the FastAPI backend from the project root:

```bash
uvicorn backend.main:app --reload
```

The backend should be available at:

```text
http://localhost:8000
```

## Environment Variable

Create `frontend/.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

If this variable is not set, the frontend defaults to `http://localhost:8000`.

## Run Locally

From `frontend/`:

```bash
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

The frontend container serves the production Next.js app on `http://localhost:3000`.

In Docker Compose, the browser-facing API URL stays:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

The Next.js server inside the container uses:

```text
API_INTERNAL_BASE_URL=http://backend:8000
```

This lets server-rendered pages call the backend service over the Compose network while browser-visible links and static API URLs still point at localhost.

## Pages

```text
/                  Team grid and coverage summary
/teams/[teamName]  Team profile, squad grid, xG summaries, weak-sample warnings
/players           Player xG Explorer for historical StatsBomb player samples
/players/[name]    Player profile, StatsBomb metrics, FBref context, sample warnings
/model             Model explanation and metrics
/coverage          Dataset coverage and limitations
```

The dashboard uses truthful wording: StatsBomb powers historical xG and shot-location views, FBref adds recent aggregate player context where available, and the product is not a guaranteed 2026 World Cup prediction model.
