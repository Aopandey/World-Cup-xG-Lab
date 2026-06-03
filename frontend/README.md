# World Cup xG Lab Frontend

Next.js frontend for the World Cup xG Lab dashboard. It consumes the FastAPI backend, which serves precomputed JSON artifacts from `data/dashboard_artifacts/`.

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

## Pages

```text
/                  Team grid and coverage summary
/teams/[teamName]  Team profile, squad grid, xG summaries, weak-sample warnings
/players/[name]    Player profile, StatsBomb metrics, FBref context, sample warnings
/model             Model explanation and metrics
/coverage          Dataset coverage and limitations
```

The dashboard uses truthful wording: StatsBomb powers historical xG and shot-location views, FBref adds recent aggregate player context where available, and the product is not a guaranteed 2026 World Cup prediction model.
