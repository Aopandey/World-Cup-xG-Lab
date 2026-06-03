from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "fbref_browser_fetch_smoke_test.txt"
TEST_URL = "https://fbref.com/en/comps/32/Primeira-Liga-Stats"


def main() -> None:
    """Test whether SeleniumBase can fetch an FBref page behind Cloudflare."""
    lines = [
        "FBref Browser Fetch Smoke Test",
        "==============================",
        f"URL: {TEST_URL}",
        "",
    ]

    driver = None
    try:
        from seleniumbase import Driver

        driver = Driver(uc=True, headless=True)
        driver.get(TEST_URL)
        html = driver.page_source or ""
        title = driver.title or ""
        lines.extend(
            [
                f"title: {title}",
                f"html_length: {len(html):,}",
                f"contains_cloudflare_wait: {'Just a moment' in html}",
                f"contains_fbref_table: {'<table' in html and 'stats_standard' in html}",
                f"contains_primeira_liga: {'Primeira Liga' in html}",
            ]
        )
    except Exception as error:
        lines.append(f"FAILED: {type(error).__name__}: {error}")
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("")
    print(f"Saved browser fetch smoke report to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
