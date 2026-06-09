from __future__ import annotations

import argparse
import sys
from urllib.parse import urljoin

import requests


JSON_ENDPOINTS = [
    "/api/teams",
    "/api/coverage",
    "/api/model/summary",
]


def check_url(label: str, url: str, expect_json: bool = False) -> bool:
    """Request one deployment URL and print a pass/fail line."""
    try:
        response = requests.get(url, timeout=20)
    except requests.RequestException as error:
        print(f"FAIL  {label}: could not reach {url} ({error})")
        return False

    if response.status_code >= 400:
        print(f"FAIL  {label}: {url} returned HTTP {response.status_code}")
        return False

    if expect_json:
        try:
            response.json()
        except ValueError:
            print(f"FAIL  {label}: {url} did not return JSON")
            return False

    print(f"PASS  {label}: {url}")
    return True


def first_working_health_url(base_url: str) -> bool:
    """Accept either /health or /api/health from the reverse proxy."""
    for path in ["/health", "/api/health"]:
        url = urljoin(base_url, path)
        if check_url(f"health {path}", url, expect_json=True):
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test a deployed World Cup xG Lab URL.")
    parser.add_argument("base_url", help="Deployment base URL, for example http://YOUR_EC2_PUBLIC_IP")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    checks = [check_url("frontend homepage", base_url)]
    checks.extend(
        check_url(path, urljoin(base_url, path.lstrip("/")), expect_json=True)
        for path in JSON_ENDPOINTS
    )
    checks.append(first_working_health_url(base_url))

    if not all(checks):
        raise SystemExit(1)

    print("PASS  Deployment URL smoke test completed.")


if __name__ == "__main__":
    main()
