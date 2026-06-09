from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_BACKEND_FILES = [
    "backend/main.py",
    "backend/data_loader.py",
    "backend/routes/teams.py",
    "backend/routes/players.py",
    "backend/routes/model.py",
    "backend/routes/coverage.py",
]

REQUIRED_FRONTEND_FILES = [
    "frontend/app/layout.tsx",
    "frontend/app/page.tsx",
    "frontend/app/players/page.tsx",
    "frontend/app/model/page.tsx",
    "frontend/app/coverage/page.tsx",
    "frontend/lib/api.ts",
    "frontend/package.json",
    "frontend/tailwind.config.ts",
]

REQUIRED_ARTIFACT_FILES = [
    "data/dashboard_artifacts/teams.json",
    "data/dashboard_artifacts/team_profiles.json",
    "data/dashboard_artifacts/player_profiles.json",
    "data/dashboard_artifacts/squad_players.json",
    "data/dashboard_artifacts/model_summary.json",
    "data/dashboard_artifacts/data_coverage.json",
]

REQUIRED_DOCKER_STACK_FILES = [
    "backend/Dockerfile",
    "frontend/Dockerfile",
    ".dockerignore",
    "backend/.dockerignore",
    "frontend/.dockerignore",
    "docker-compose.yml",
    "docker-compose.prod.yml",
    "scripts/test_docker_stack.py",
]

REQUIRED_DEPLOYMENT_FILES = [
    "deploy/README.md",
    "deploy/docker-compose.prod.yml",
    "deploy/nginx.conf",
    "deploy/.env.production.example",
    "scripts/check_deployment_urls.py",
]


def check_path(path: str, label: str, failures: list[str]) -> None:
    """Print a pass/fail line for one required file."""
    full_path = PROJECT_ROOT / path
    if full_path.exists():
        print(f"PASS  {label}: {path}")
        return

    print(f"FAIL  {label}: missing {path}")
    failures.append(path)


def check_text(path: str, required_text: str, label: str, warnings: list[str]) -> None:
    """Print a pass/warning line for expected documentation text."""
    full_path = PROJECT_ROOT / path
    if not full_path.exists():
        print(f"WARN  {label}: {path} does not exist")
        warnings.append(path)
        return

    text = full_path.read_text(encoding="utf-8", errors="ignore")
    if required_text in text:
        print(f"PASS  {label}: found `{required_text}` in {path}")
        return

    print(f"WARN  {label}: `{required_text}` not found in {path}")
    warnings.append(path)


def main() -> None:
    """Run lightweight production-readiness checks before Dockerizing."""
    failures: list[str] = []
    warnings: list[str] = []

    print("World Cup xG Lab production-readiness check")
    print("=" * 52)

    for path in REQUIRED_BACKEND_FILES:
        check_path(path, "backend file", failures)

    for path in REQUIRED_FRONTEND_FILES:
        check_path(path, "frontend file", failures)

    for path in REQUIRED_ARTIFACT_FILES:
        check_path(path, "dashboard artifact", failures)

    for path in REQUIRED_DOCKER_STACK_FILES:
        check_path(path, "docker file", failures)

    for path in REQUIRED_DEPLOYMENT_FILES:
        check_path(path, "deployment file", failures)

    check_path("frontend/.env.example", "frontend env example", failures)
    check_text("backend/README.md", "/health", "backend health docs", warnings)
    check_text("backend/README.md", "BACKEND_ALLOWED_ORIGINS", "backend CORS docs", warnings)
    check_text("README.md", "Production Dashboard Architecture", "architecture docs", warnings)

    print("=" * 52)
    if failures:
        print(f"FAIL  {len(failures)} required checks failed.")
        raise SystemExit(1)

    if warnings:
        print(f"WARN  {len(warnings)} advisory checks need review.")
    else:
        print("PASS  No advisory warnings.")

    print("PASS  Production-readiness check completed.")


if __name__ == "__main__":
    main()
