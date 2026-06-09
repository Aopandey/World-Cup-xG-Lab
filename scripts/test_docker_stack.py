from __future__ import annotations

import os
import sys

import requests


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def check_url(label: str, url: str, expected_content: str | None = None) -> bool:
    """Request one URL and print a clear pass/fail result."""
    try:
        response = requests.get(url, timeout=15)
    except requests.RequestException as error:
        print(f"FAIL  {label}: could not connect to {url} ({error})")
        return False

    if response.status_code >= 400:
        print(f"FAIL  {label}: {url} returned HTTP {response.status_code}")
        return False

    if expected_content and expected_content not in response.text:
        print(f"FAIL  {label}: expected `{expected_content}` in response from {url}")
        return False

    print(f"PASS  {label}: {url}")
    return True


def check_backend_json(label: str, path: str, expected_key: str | None = None) -> bool:
    """Request one backend JSON endpoint and validate basic shape."""
    url = f"{BACKEND_URL.rstrip('/')}{path}"
    try:
        response = requests.get(url, timeout=15)
    except requests.RequestException as error:
        print(f"FAIL  {label}: could not connect to {url} ({error})")
        return False

    if response.status_code >= 400:
        print(f"FAIL  {label}: {url} returned HTTP {response.status_code}")
        return False

    try:
        payload = response.json()
    except ValueError:
        print(f"FAIL  {label}: {url} did not return JSON")
        return False

    if expected_key and isinstance(payload, dict) and expected_key not in payload:
        print(f"FAIL  {label}: `{expected_key}` missing from JSON response")
        return False

    print(f"PASS  {label}: {url}")
    return True


def main() -> None:
    """Smoke-test the local Docker Compose stack."""
    checks = [
        check_backend_json("backend health", "/health", "status"),
        check_backend_json("backend teams", "/api/teams"),
        check_url("frontend homepage", FRONTEND_URL, "World Cup xG Lab"),
    ]

    if not all(checks):
        raise SystemExit(1)

    print("PASS  Docker stack smoke test completed.")


if __name__ == "__main__":
    main()
