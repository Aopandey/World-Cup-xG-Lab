from __future__ import annotations

import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOCCERDATA_DIR = PROJECT_ROOT / "data" / "fbref" / "soccerdata_cache"
REPORT_PATH = PROJECT_ROOT / "reports" / "custom_fbref_league_smoke_test.txt"

TEST_LEAGUES = ["POR-Primeira Liga", "NED-Eredivisie"]
TEST_SEASONS = [2025]
TEST_STAT_TYPES = ["standard", "shooting"]


def import_soccerdata():
    """Import soccerdata using the repo-local soccerdata cache."""
    os.environ.setdefault("SOCCERDATA_DIR", str(SOCCERDATA_DIR))
    import soccerdata as sd

    return sd


def close_reader(fbref) -> None:
    """Close soccerdata's browser driver when present."""
    driver = getattr(fbref, "_driver", None)
    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass


def main() -> None:
    """Smoke test custom FBref leagues configured through soccerdata."""
    sd = import_soccerdata()
    available = set(sd.FBref.available_leagues())
    lines = [
        "Custom FBref League Smoke Test",
        "==============================",
        "",
        f"Soccerdata custom cache: {SOCCERDATA_DIR}",
        f"Test leagues: {', '.join(TEST_LEAGUES)}",
        f"Test seasons: {', '.join(str(season) for season in TEST_SEASONS)}",
        "",
    ]

    for league in TEST_LEAGUES:
        lines.append(f"{league} available in soccerdata: {league in available}")

    for league in TEST_LEAGUES:
        for season in TEST_SEASONS:
            lines.append("")
            lines.append(f"=== {league} {season} ===")

            if league not in available:
                lines.append("SKIPPED: league not available in soccerdata.")
                continue

            fbref = None
            try:
                fbref = sd.FBref(leagues=[league], seasons=[season], no_cache=False)
            except Exception as error:
                lines.append(f"INIT_FAILED: {type(error).__name__}: {error}")
                continue

            try:
                for stat_type in TEST_STAT_TYPES:
                    try:
                        stats = fbref.read_player_season_stats(stat_type=stat_type)
                    except Exception as error:
                        lines.append(
                            f"{stat_type}: FAILED {type(error).__name__}: {error}"
                        )
                        continue

                    columns = list(stats.reset_index().columns[:15])
                    lines.append(
                        f"{stat_type}: rows={len(stats):,}, "
                        f"columns={len(stats.columns):,}, first_columns={columns}"
                    )
            finally:
                close_reader(fbref)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("")
    print(f"Saved smoke test report to: {REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Interrupted.")
