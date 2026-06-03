from __future__ import annotations

import sys

import requests


BASE_URL = "http://127.0.0.1:8000"
ENDPOINTS = [
    "/",
    "/api/teams",
    "/api/coverage",
    "/api/model/summary",
]


def test_endpoint(path: str) -> bool:
    """Call one backend endpoint and print a pass/fail result."""
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException as error:
        print(f"FAIL {path}: {error}")
        return False

    if response.ok:
        print(f"PASS {path}: {response.status_code}")
        return True

    print(f"FAIL {path}: {response.status_code} {response.text}")
    return False


def main() -> None:
    """Smoke test key FastAPI endpoints."""
    print(f"Testing backend API at {BASE_URL}")
    results = [test_endpoint(path) for path in ENDPOINTS]

    if not all(results):
        raise SystemExit(1)

    print("Backend API smoke test passed.")


if __name__ == "__main__":
    main()
