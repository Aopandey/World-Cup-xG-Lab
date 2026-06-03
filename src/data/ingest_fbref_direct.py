from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from fbref_wc2026_scraper import (
    Competition,
    attach_player_links,
    build_competition_season_url,
    build_stat_url,
    load_mapping_workbook,
    normalize_fbref_columns,
    now_utc_iso,
    parse_fbref_comp_url,
    parse_fbref_tables,
)


DEFAULT_COMPETITION_MAP = PROJECT_ROOT / "configs" / "fbref_direct_competitions.csv"
RAW_DIRECT_DIR = PROJECT_ROOT / "data" / "fbref" / "raw_direct"
CACHE_DIR = RAW_DIRECT_DIR / "cache"
REPORT_PATH = PROJECT_ROOT / "reports" / "fbref_direct_ingest_report.txt"

DEFAULT_EUROPEAN_SEASONS = ["2025-2026", "2024-2025", "2023-2024"]
DEFAULT_CALENDAR_SEASONS = ["2025", "2024", "2023"]
DEFAULT_STAT_TYPES = ["standard", "shooting", "playing_time", "misc"]


class BrowserFetcher:
    """Fetch FBref pages with SeleniumBase and a simple disk cache."""

    def __init__(
        self,
        cache_dir: Path,
        min_sleep: float,
        max_sleep: float,
        force_refresh: bool,
        headless: bool,
    ) -> None:
        self.cache_dir = cache_dir
        self.min_sleep = min_sleep
        self.max_sleep = max_sleep
        self.force_refresh = force_refresh
        self.headless = headless
        self.driver = None
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "BrowserFetcher":
        from seleniumbase import Driver

        self.driver = Driver(uc=True, headless=self.headless)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass

    def cache_path(self, url: str) -> Path:
        import hashlib

        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.html"

    def fetch(self, url: str) -> tuple[bool, str, bool, str]:
        """Return ok, html, from_cache, error_message."""
        cache_path = self.cache_path(url)
        if cache_path.exists() and not self.force_refresh:
            return True, cache_path.read_text(encoding="utf-8", errors="replace"), True, ""

        if self.driver is None:
            raise RuntimeError("BrowserFetcher must be used as a context manager.")

        sleep_seconds = random.uniform(self.min_sleep, self.max_sleep)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

        try:
            self.driver.get(url)
            html = self.driver.page_source or ""
        except Exception as error:
            return False, "", False, f"{type(error).__name__}: {error}"

        if "Just a moment" in html and "Cloudflare" in html:
            return False, html, False, "Cloudflare wait page returned."
        if "<table" not in html:
            return False, html, False, "No HTML tables found on fetched page."

        cache_path.write_text(html, encoding="utf-8")
        return True, html, False, ""


def seasons_for_competition(competition: Competition, args: argparse.Namespace) -> list[str | None]:
    """Choose European or calendar seasons for one competition."""
    if competition.season_type == "tournament":
        return [None]

    if competition.season_type == "calendar":
        seasons = args.calendar_seasons
    else:
        seasons = args.european_seasons

    if args.max_seasons_per_competition:
        seasons = seasons[: args.max_seasons_per_competition]
    return seasons


def scrape_stat_page(
    html: str,
    url: str,
    competition: Competition,
    season: str,
    stat_type: str,
) -> list[pd.DataFrame]:
    """Parse one FBref stat page into normalized player-stat frames."""
    frames = []
    scraped_at = now_utc_iso()

    for table in parse_fbref_tables(html, url):
        frame = normalize_fbref_columns(table["df"], stat_type)
        frame = attach_player_links(frame, table["player_links"])
        if "team" not in frame.columns and "squad" in frame.columns:
            frame["team"] = frame["squad"]
        frame["league"] = competition.competition_name
        frame["source_url"] = url
        frame["fbref_table_id"] = table["table_id"]
        frame["stat_type"] = stat_type
        frame["competition_name"] = competition.competition_name
        frame["competition_group"] = competition.competition_group
        frame["season"] = season
        frame["season_type"] = competition.season_type
        frame["scraped_at_utc"] = scraped_at
        frames.append(frame)

    return frames


def output_path_for_stat_type(stat_type: str) -> Path:
    return RAW_DIRECT_DIR / f"player_season_{stat_type}.csv"


def write_stat_outputs(frames_by_stat_type: dict[str, list[pd.DataFrame]]) -> None:
    """Write direct FBref raw outputs, one CSV per stat type."""
    RAW_DIRECT_DIR.mkdir(parents=True, exist_ok=True)
    for stat_type, frames in frames_by_stat_type.items():
        if not frames:
            continue
        outputs = [pd.concat(frames, ignore_index=True)]
        output_path = output_path_for_stat_type(stat_type)
        if output_path.exists():
            outputs.append(pd.read_csv(output_path))
        data = pd.concat(outputs, ignore_index=True).drop_duplicates()
        data.to_csv(output_path_for_stat_type(stat_type), index=False)


def build_report(
    attempted_urls: list[dict],
    failed_urls: list[dict],
    frames_by_stat_type: dict[str, list[pd.DataFrame]],
) -> str:
    """Build a small direct-ingestion report."""
    lines = [
        "FBref Direct URL Ingestion Report",
        "=================================",
        "",
        f"Attempted URLs: {len(attempted_urls):,}",
        f"Failed URLs: {len(failed_urls):,}",
        "",
        "Rows saved by stat type:",
    ]
    for stat_type, frames in sorted(frames_by_stat_type.items()):
        rows = sum(len(frame) for frame in frames)
        lines.append(f"- {stat_type}: {rows:,}")

    lines.extend(["", "Failed URLs:"])
    if failed_urls:
        for failure in failed_urls:
            lines.append(
                f"- {failure['competition_name']} / {failure['season']} / "
                f"{failure['stat_type']}: {failure['error_message']} ({failure['url']})"
            )
    else:
        lines.append("None")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Direct FBref URL ingestion fallback using SeleniumBase."
    )
    parser.add_argument("--competition-map", type=Path, default=DEFAULT_COMPETITION_MAP)
    parser.add_argument("--stat-types", nargs="+", default=DEFAULT_STAT_TYPES)
    parser.add_argument("--european-seasons", nargs="+", default=DEFAULT_EUROPEAN_SEASONS)
    parser.add_argument("--calendar-seasons", nargs="+", default=DEFAULT_CALENDAR_SEASONS)
    parser.add_argument("--max-competitions", type=int)
    parser.add_argument("--max-seasons-per-competition", type=int)
    parser.add_argument("--min-sleep", type=float, default=6)
    parser.add_argument("--max-sleep", type=float, default=12)
    parser.add_argument("--force-refresh-cache", action="store_true")
    parser.add_argument("--headed", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    competitions = load_mapping_workbook(args.competition_map)
    if args.max_competitions:
        competitions = competitions[: args.max_competitions]

    RAW_DIRECT_DIR.mkdir(parents=True, exist_ok=True)
    frames_by_stat_type = {stat_type: [] for stat_type in args.stat_types}
    attempted_urls = []
    failed_urls = []

    with BrowserFetcher(
        cache_dir=CACHE_DIR,
        min_sleep=args.min_sleep,
        max_sleep=args.max_sleep,
        force_refresh=args.force_refresh_cache,
        headless=not args.headed,
    ) as fetcher:
        for competition in competitions:
            seasons = seasons_for_competition(competition, args)
            print(f"{competition.competition_name}: seasons={seasons}", flush=True)
            for season in seasons:
                season_label = season
                if season_label is None:
                    season_label = parse_fbref_comp_url(competition.fbref_comp_url)["season"]
                competition_url = build_competition_season_url(
                    competition.fbref_comp_url,
                    season,
                )
                for stat_type in args.stat_types:
                    stat_url = build_stat_url(competition_url, stat_type)
                    attempted_urls.append(
                        {
                            "competition_name": competition.competition_name,
                            "season": season_label,
                            "stat_type": stat_type,
                            "url": stat_url,
                        }
                    )
                    ok, html, from_cache, error_message = fetcher.fetch(stat_url)
                    if not ok:
                        failed_urls.append(
                            {
                                "competition_name": competition.competition_name,
                                "season": season_label,
                                "stat_type": stat_type,
                                "url": stat_url,
                                "error_message": error_message,
                            }
                        )
                        print(f"  FAILED {season} {stat_type}: {error_message}", flush=True)
                        continue

                    frames = scrape_stat_page(
                        html,
                        stat_url,
                        competition,
                        season_label,
                        stat_type,
                    )
                    frames_by_stat_type[stat_type].extend(frames)
                    row_count = sum(len(frame) for frame in frames)
                    cache_label = "cache" if from_cache else "live"
                    print(
                        f"  {season_label} {stat_type}: {row_count:,} rows ({cache_label})",
                        flush=True,
                    )

    write_stat_outputs(frames_by_stat_type)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        build_report(attempted_urls, failed_urls, frames_by_stat_type),
        encoding="utf-8",
    )
    print(f"Saved direct FBref report to: {REPORT_PATH}")
    print(f"Saved direct raw CSVs to: {RAW_DIRECT_DIR}")


if __name__ == "__main__":
    main()
