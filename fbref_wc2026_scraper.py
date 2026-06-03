"""Direct FBref scraper for confirmed World Cup 2026 players.

The scraper is intentionally conservative:
- reads roster and competition mapping files instead of hardcoding leagues
- caches every downloaded page by URL hash
- sleeps between uncached requests
- parses normal and comment-wrapped FBref tables
- keeps raw FBref columns plus normalized columns and provenance
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment
from rapidfuzz import fuzz, process

try:
    from unidecode import unidecode
except ImportError:  # pragma: no cover - dependency is declared, fallback helps bootstrapping.
    import unicodedata

    def unidecode(value: object) -> str:
        text = "" if value is None else str(value)
        normalized = unicodedata.normalize("NFKD", text)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_ROSTER_PATH = (
    PROJECT_ROOT
    / "data"
    / "squads"
    / "processed"
    / "world_cup_2026_players_fbref_scrape_handoff.xlsx"
)
DEFAULT_OUTDIR = PROJECT_ROOT / "fbref_wc2026_output"

DEFAULT_SEASONS = [
    "2023-2024",
    "2024-2025",
    "2025-2026",
    "2023",
    "2024",
    "2025",
    "2026",
]
EUROPEAN_COMPETITION_SEASONS = [
    "2021-2022",
    "2022-2023",
    "2023-2024",
    "2024-2025",
    "2025-2026",
]
DEFAULT_STAT_TYPES = [
    "standard",
    "shooting",
    "passing",
    "passing_types",
    "gca",
    "defense",
    "possession",
    "playing_time",
    "misc",
    "keeper",
    "keeper_adv",
]

STAT_URL_PATHS = {
    "standard": "stats",
    "shooting": "shooting",
    "passing": "passing",
    "passing_types": "passing_types",
    "gca": "gca",
    "defense": "defense",
    "possession": "possession",
    "playing_time": "playingtime",
    "misc": "misc",
    "keeper": "keepers",
    "keeper_adv": "keepersadv",
}

STOP_STATUS_CODES = {403, 429, 503}
EXCEL_MAX_ROWS = 1_048_576


@dataclass(frozen=True)
class Competition:
    competition_group: str
    competition_name: str
    fbref_comp_url: str
    season_type: str
    scrape_priority: int | None = None
    notes: str = ""


@dataclass
class FetchResult:
    url: str
    ok: bool
    html: str | None = None
    status_code: int | None = None
    from_cache: bool = False
    error_message: str = ""
    stop_requested: bool = False


class StopScraping(RuntimeError):
    """Raised when FBref returns a stop/backoff status."""


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unidecode(str(value)).casefold()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_compact(value: object) -> str:
    return re.sub(r"\s+", "", normalize_text(value))


def normalize_fbref_token(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unidecode(str(value)).strip().casefold()
    text = text.replace("per 90", "/90")
    text = re.sub(r"\s+", "", text)
    return text


def slugify_column(value: object) -> str:
    text = unidecode(str(value)).strip().casefold()
    text = text.replace("+/-", "plus_minus")
    text = text.replace("+", "_plus_")
    text = text.replace("-", "_")
    text = text.replace("%", "_pct")
    text = text.replace("#", "num_")
    text = text.replace("/", "_per_")
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or "column"


def make_unique_columns(columns: Iterable[object]) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    unique = []
    for column in columns:
        base = str(column) if str(column).strip() else "column"
        counts[base] += 1
        if counts[base] == 1:
            unique.append(base)
        else:
            unique.append(f"{base}__{counts[base]}")
    return unique


def find_alias_column(columns: Iterable[object], aliases: Iterable[str]) -> str | None:
    alias_lookup = {normalize_text(alias) for alias in aliases}
    compact_lookup = {normalize_compact(alias) for alias in aliases}
    for column in columns:
        normalized = normalize_text(column)
        compact = normalize_compact(column)
        if normalized in alias_lookup or compact in compact_lookup:
            return str(column)
    return None


ROSTER_COLUMN_ALIASES = {
    "team": ["team", "national team", "nation team", "country", "world cup team"],
    "player": ["player", "player name", "name"],
    "position": ["position", "pos"],
    "club": ["club", "club team", "squad", "current club"],
    "league": ["league", "league / competition", "competition", "league competition"],
    "birth_year": ["birth year", "born", "year born"],
}


MAP_COLUMN_ALIASES = {
    "competition_group": ["competition_group", "group", "type", "category"],
    "competition_name": [
        "competition_name",
        "competition",
        "league",
        "comp",
        "name",
    ],
    "fbref_comp_url": [
        "fbref_comp_url",
        "fbref_url",
        "url",
        "competition_url",
        "comp_url",
    ],
    "season_type": ["season_type", "season format", "calendar"],
    "scrape_priority": ["scrape_priority", "priority"],
    "notes": ["notes", "note"],
}


def read_tabular_file(path: Path, sheet_name: str | int | None = None) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        return pd.read_excel(path, sheet_name=0 if sheet_name is None else sheet_name)
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path)
    if suffix == ".tsv":
        return pd.read_csv(path, sep="\t")
    raise ValueError(f"Unsupported tabular file type: {path}")


def inspect_tabular_schema(path: Path) -> dict:
    info = {
        "path": str(path),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else None,
    }
    if not path.exists():
        return info

    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        workbook = pd.ExcelFile(path)
        info["sheets"] = {}
        for sheet in workbook.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet, nrows=5)
            info["sheets"][sheet] = {
                "columns": [str(column) for column in df.columns],
                "sample_rows": df.fillna("").astype(str).head(3).to_dict("records"),
            }
    else:
        df = read_tabular_file(path)
        info.update(
            {
                "rows": int(len(df)),
                "columns": [str(column) for column in df.columns],
                "sample_rows": df.fillna("").astype(str).head(5).to_dict("records"),
            }
        )
    return info


def select_roster_sheet(path: Path) -> tuple[str | int | None, pd.DataFrame]:
    if path.suffix.lower() not in {".xlsx", ".xls", ".xlsm"}:
        return None, read_tabular_file(path)

    workbook = pd.ExcelFile(path)
    best_sheet = workbook.sheet_names[0]
    best_score = -1
    best_df = pd.DataFrame()
    for sheet in workbook.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet)
        score = 0
        for aliases in ROSTER_COLUMN_ALIASES.values():
            if find_alias_column(df.columns, aliases):
                score += 1
        if score > best_score:
            best_sheet = sheet
            best_score = score
            best_df = df

    if best_score < 2:
        raise ValueError(
            f"Could not identify a roster sheet in {path}. "
            "Expected at least player/team-like columns."
        )
    return best_sheet, best_df


def normalize_roster_columns(df: pd.DataFrame) -> pd.DataFrame:
    roster = df.copy()
    rename_map = {}
    for target, aliases in ROSTER_COLUMN_ALIASES.items():
        column = find_alias_column(roster.columns, aliases)
        if column:
            rename_map[column] = target
    roster = roster.rename(columns=rename_map)

    required = ["player"]
    missing = [column for column in required if column not in roster.columns]
    if missing:
        raise ValueError(f"Roster is missing required columns after normalization: {missing}")

    for column in ["team", "position", "club", "league", "birth_year"]:
        if column not in roster.columns:
            roster[column] = pd.NA

    roster = roster[roster["player"].notna()].copy()
    roster["player"] = roster["player"].astype(str).str.strip()
    roster = roster[roster["player"] != ""].copy()
    roster["roster_player_normalized"] = roster["player"].apply(normalize_text)
    roster["roster_club_normalized"] = roster["club"].apply(normalize_text)
    roster["roster_league_normalized"] = roster["league"].apply(normalize_text)
    roster["roster_team_normalized"] = roster["team"].apply(normalize_text)
    roster["roster_position_normalized"] = roster["position"].apply(normalize_text)

    if "birth_year" in roster.columns:
        roster["birth_year"] = pd.to_numeric(roster["birth_year"], errors="coerce")

    return roster.reset_index(drop=True)


def load_roster(path: Path) -> pd.DataFrame:
    sheet, df = select_roster_sheet(path)
    roster = normalize_roster_columns(df)
    sheet_label = sheet if sheet is not None else path.name
    print(
        f"Detected roster schema: {path} / {sheet_label} "
        f"rows={len(roster):,} columns={list(df.columns)}",
        flush=True,
    )
    return roster


def classify_mapping_sheet(sheet_name: str, fallback: str = "domestic_leagues") -> str:
    normalized = normalize_text(sheet_name)
    if any(token in normalized for token in ["international", "tournament", "nation"]):
        return "international_tournaments"
    if any(token in normalized for token in ["europe", "uefa", "champions", "europa"]):
        return "european_competitions"
    if any(token in normalized for token in ["domestic", "league"]):
        return "domestic_leagues"
    return fallback


def infer_group_from_path(path: Path) -> str:
    return classify_mapping_sheet(path.stem, "domestic_leagues")


def infer_group_from_competition(
    competition_name: str,
    url: str,
    default_group: str,
) -> str:
    normalized = normalize_text(f"{competition_name} {url}")
    european_tokens = [
        "champions league",
        "europa league",
        "conference league",
        "uefa club",
    ]
    international_tokens = [
        "world cup",
        "uefa euro",
        "euros",
        "nations league",
        "afcon",
        "afocn",
        "africa cup",
        "copa america",
        "asian cup",
        "gold cup",
        "friendlies",
        "international",
    ]
    if any(token in normalized for token in european_tokens):
        return "european_competitions"
    if any(token in normalized for token in international_tokens):
        return "international_tournaments"
    return default_group


def infer_season_type(competition_name: str, group: str, url: str) -> str:
    normalized = normalize_text(f"{competition_name} {group} {url}")
    if group == "international_tournaments":
        return "tournament"
    if group == "european_competitions":
        return "european"
    calendar_keywords = [
        "mls",
        "major league soccer",
        "brazil",
        "argentina",
        "primera division",
        "j1 league",
        "j league",
        "k league",
        "liga mx",
        "mexico",
        "china",
        "japan",
        "korea",
        "sweden",
        "norway",
        "finland",
        "ireland",
        "copa libertadores",
    ]
    if any(keyword in normalized for keyword in calendar_keywords):
        return "calendar"
    return "european"


def normalize_mapping_frame(df: pd.DataFrame, default_group: str) -> list[Competition]:
    frame = df.copy()
    rename_map = {}
    for target, aliases in MAP_COLUMN_ALIASES.items():
        column = find_alias_column(frame.columns, aliases)
        if column:
            rename_map[column] = target
    frame = frame.rename(columns=rename_map)

    if "competition_name" not in frame.columns and "league" in frame.columns:
        frame = frame.rename(columns={"league": "competition_name"})
    if "competition_name" not in frame.columns:
        raise ValueError(
            "Competition map must include competition_name or league."
        )
    if "fbref_comp_url" not in frame.columns:
        raise ValueError("Competition map must include fbref_comp_url or url.")

    for column in ["competition_group", "season_type", "scrape_priority", "notes"]:
        if column not in frame.columns:
            frame[column] = pd.NA

    competitions = []
    for _, row in frame.iterrows():
        name = str(row.get("competition_name", "")).strip()
        url = str(row.get("fbref_comp_url", "")).strip()
        if (
            not name
            or not url
            or url.lower() == "nan"
            or not url.lower().startswith("http")
            or normalize_text(name) in {"competition", "league"}
        ):
            continue
        group_raw = row.get("competition_group")
        group = "" if pd.isna(group_raw) else str(group_raw).strip()
        if not group or group.lower() == "nan":
            group = infer_group_from_competition(name, url, default_group)
        season_type_raw = row.get("season_type")
        season_type = "" if pd.isna(season_type_raw) else str(season_type_raw).strip()
        if not season_type or season_type.lower() == "nan":
            season_type = infer_season_type(name, group, url)
        priority_raw = row.get("scrape_priority")
        priority = None
        if not pd.isna(priority_raw):
            try:
                priority = int(priority_raw)
            except (TypeError, ValueError):
                priority = None
        notes = "" if pd.isna(row.get("notes")) else str(row.get("notes"))
        competitions.append(
            Competition(
                competition_group=group,
                competition_name=name,
                fbref_comp_url=url,
                season_type=normalize_text(season_type).replace(" ", "_") or "european",
                scrape_priority=priority,
                notes=notes,
            )
        )
    return competitions


def load_mapping_workbook(path: Path) -> list[Competition]:
    competitions = []
    if path.suffix.lower() in {".xlsx", ".xls", ".xlsm"}:
        workbook = pd.ExcelFile(path)
        for sheet in workbook.sheet_names:
            default_group = classify_mapping_sheet(sheet)
            df = pd.read_excel(path, sheet_name=sheet)
            if df.dropna(how="all").empty:
                continue
            competitions.extend(normalize_mapping_frame(df, default_group))
    else:
        competitions.extend(
            normalize_mapping_frame(read_tabular_file(path), infer_group_from_path(path))
        )
    return competitions


def load_competition_maps(
    competition_map: Path | None,
    league_map: Path | None,
    international_map: Path | None,
    europe_map: Path | None,
) -> list[Competition]:
    competitions = []
    if competition_map:
        competitions.extend(load_mapping_workbook(competition_map))

    separate_maps = [
        (league_map, "domestic_leagues"),
        (international_map, "international_tournaments"),
        (europe_map, "european_competitions"),
    ]
    for path, group in separate_maps:
        if not path:
            continue
        df = read_tabular_file(path)
        competitions.extend(normalize_mapping_frame(df, group))

    deduped = {}
    for competition in competitions:
        key = (
            normalize_text(competition.competition_group),
            normalize_text(competition.competition_name),
            competition.fbref_comp_url.rstrip("/"),
        )
        deduped[key] = competition
    ordered = list(deduped.values())
    if any(item.scrape_priority is not None for item in ordered):
        ordered.sort(
            key=lambda item: (
                item.scrape_priority is None,
                item.scrape_priority if item.scrape_priority is not None else 999_999,
                item.competition_group,
                item.competition_name,
            )
        )
    print(
        "Detected competition map schema: "
        f"competitions={len(ordered):,} groups="
        f"{sorted({item.competition_group for item in ordered})}",
        flush=True,
    )
    return ordered


def parse_fbref_comp_url(url: str) -> dict:
    parsed = urlparse(url.rstrip("/"))
    path = parsed.path.rstrip("/")
    match = re.search(
        r"(?P<prefix>/en/comps/(?P<comp_id>[^/]+))"
        r"(?:/(?P<season>\d{4}(?:-\d{4})?))?"
        r"(?:/(?P<section>stats|shooting|passing|passing_types|gca|defense|possession|playingtime|misc|keepers|keepersadv|schedule|history))?"
        r"/(?P<slug>[^/]+)$",
        path,
    )
    if not match:
        raise ValueError(f"Could not parse FBref competition URL: {url}")
    slug = match.group("slug")
    existing_season = match.group("season")
    if existing_season and slug.startswith(f"{existing_season}-"):
        slug = slug[len(existing_season) + 1 :]
    return {
        "scheme": parsed.scheme or "https",
        "netloc": parsed.netloc or "fbref.com",
        "prefix": match.group("prefix"),
        "comp_id": match.group("comp_id"),
        "season": existing_season,
        "section": match.group("section"),
        "slug": slug,
    }


def compose_fbref_url(parts: dict, *segments: str) -> str:
    path = "/".join([parts["prefix"].strip("/"), *[segment.strip("/") for segment in segments]])
    return f"{parts['scheme']}://{parts['netloc']}/{path}"


def build_competition_season_url(base_url: str, season: str | None) -> str:
    parts = parse_fbref_comp_url(base_url)
    if parts["section"] == "history" and not season:
        return base_url.rstrip("/")
    slug = parts["slug"]
    if not season:
        if parts["season"]:
            return compose_fbref_url(parts, parts["season"], f"{parts['season']}-{slug}")
        return compose_fbref_url(parts, slug)
    return compose_fbref_url(parts, season, f"{season}-{slug}")


def build_stat_url(competition_season_url: str, stat_type: str) -> str:
    parts = parse_fbref_comp_url(competition_season_url)
    if parts["section"] == "history":
        return competition_season_url.rstrip("/")
    stat_path = STAT_URL_PATHS[stat_type]
    season = parts["season"]
    if season:
        slug = parts["slug"]
        if not slug.startswith(f"{season}-"):
            slug = f"{season}-{slug}"
        return compose_fbref_url(parts, season, stat_path, slug)
    return compose_fbref_url(parts, stat_path, parts["slug"])


def build_schedule_url(competition_season_url: str) -> str:
    parts = parse_fbref_comp_url(competition_season_url)
    season = parts["season"]
    slug = parts["slug"]
    fixture_slug = re.sub(r"-Stats$", "-Scores-and-Fixtures", slug)
    if fixture_slug == slug:
        fixture_slug = f"{slug}-Scores-and-Fixtures"
    if season:
        if not fixture_slug.startswith(f"{season}-"):
            fixture_slug = f"{season}-{fixture_slug}"
        return compose_fbref_url(parts, season, "schedule", fixture_slug)
    return compose_fbref_url(parts, "schedule", fixture_slug)


def build_candidate_season_urls(
    base_url: str,
    seasons: list[str],
    season_type: str,
) -> list[str]:
    """Build candidate FBref competition-season URLs for the requested season type."""
    season_type = normalize_text(season_type).replace(" ", "_")
    if season_type == "tournament":
        try:
            parsed = parse_fbref_comp_url(base_url)
            return [build_competition_season_url(base_url, parsed["season"])]
        except ValueError:
            return [base_url.rstrip("/")]

    if season_type == "calendar":
        selected_seasons: list[str | None] = [
            season for season in seasons if re.fullmatch(r"\d{4}", season)
        ]
    else:
        selected_seasons = [
            season for season in seasons if re.fullmatch(r"\d{4}-\d{4}", season)
        ]

    if not selected_seasons:
        selected_seasons = [None]
    return [build_competition_season_url(base_url, season) for season in selected_seasons]


def seasons_for_competition(competition: Competition, requested_seasons: list[str]) -> list[str | None]:
    if competition.season_type == "tournament":
        parsed = parse_fbref_comp_url(competition.fbref_comp_url)
        return [parsed["season"]]

    if competition.season_type == "calendar":
        seasons = [season for season in requested_seasons if re.fullmatch(r"\d{4}", season)]
    elif competition.competition_group == "european_competitions":
        requested = set(requested_seasons)
        seasons = [season for season in EUROPEAN_COMPETITION_SEASONS if season in requested]
        if not seasons:
            seasons = EUROPEAN_COMPETITION_SEASONS
    else:
        seasons = [season for season in requested_seasons if re.fullmatch(r"\d{4}-\d{4}", season)]

    return seasons or [None]


def discover_stat_links(html: str, page_url: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    links = {}
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        full_url = urljoin(page_url, href)
        for stat_type, path_part in STAT_URL_PATHS.items():
            if f"/{path_part}/" in full_url and stat_type not in links:
                links[stat_type] = full_url
    return links


def cache_path_for_url(cache_dir: Path, url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{digest}.html"


def fetch_html(
    url: str,
    cache_dir: Path,
    session: requests.Session,
    min_sleep: float,
    max_sleep: float,
    force_refresh: bool = False,
) -> FetchResult:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_path_for_url(cache_dir, url)
    if cache_path.exists() and not force_refresh:
        return FetchResult(
            url=url,
            ok=True,
            html=cache_path.read_text(encoding="utf-8", errors="replace"),
            from_cache=True,
            status_code=200,
        )

    sleep_seconds = random.uniform(min_sleep, max_sleep) if max_sleep > 0 else 0
    if sleep_seconds:
        time.sleep(sleep_seconds)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; personal academic football analytics project; "
            "contact: none)"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = session.get(url, headers=headers, timeout=30)
    except requests.RequestException as error:
        return FetchResult(url=url, ok=False, error_message=str(error))

    if response.status_code in STOP_STATUS_CODES:
        return FetchResult(
            url=url,
            ok=False,
            status_code=response.status_code,
            error_message=(
                f"FBref returned {response.status_code}; stopping live scraping "
                "to avoid repeated blocked requests"
            ),
            stop_requested=True,
        )
    if response.status_code == 404:
        return FetchResult(
            url=url,
            ok=False,
            status_code=response.status_code,
            error_message="404 not found",
        )
    if not response.ok:
        return FetchResult(
            url=url,
            ok=False,
            status_code=response.status_code,
            error_message=response.reason,
        )

    response.encoding = response.encoding or "utf-8"
    html = response.text
    cache_path.write_text(html, encoding="utf-8")
    return FetchResult(url=url, ok=True, html=html, status_code=response.status_code)


def extract_table_elements(html: str) -> list[BeautifulSoup]:
    soup = BeautifulSoup(html, "lxml")
    tables = list(soup.find_all("table"))
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        if "<table" not in comment:
            continue
        comment_soup = BeautifulSoup(str(comment), "lxml")
        tables.extend(comment_soup.find_all("table"))
    return tables


def flatten_fbref_columns(df: pd.DataFrame) -> pd.DataFrame:
    flattened = df.copy()
    if isinstance(flattened.columns, pd.MultiIndex):
        new_columns = []
        for column in flattened.columns:
            parts = [
                str(part).strip()
                for part in column
                if str(part).strip()
                and not str(part).startswith("Unnamed:")
                and str(part).strip().lower() != "nan"
            ]
            if len(parts) >= 2 and parts[-1] == parts[-2]:
                parts = parts[-1:]
            new_columns.append("__".join(parts) if parts else "column")
        flattened.columns = new_columns
    flattened.columns = make_unique_columns(flattened.columns)
    return flattened


def player_column_name(df: pd.DataFrame) -> str | None:
    return find_alias_column(
        df.columns,
        ["Player", "player", "player name", "Standard Player", "Unnamed: Player"],
    )


def extract_player_urls_from_table(table_html: str) -> dict[str, dict[str, str]]:
    soup = BeautifulSoup(table_html, "lxml")
    lookup = {}
    for row in soup.find_all("tr"):
        player_cell = row.find(attrs={"data-stat": "player"})
        anchor = player_cell.find("a", href=True) if player_cell else None
        if anchor is None:
            anchor = row.find("a", href=re.compile(r"/en/players/"))
        if anchor is None:
            continue
        player_name = anchor.get_text(" ", strip=True)
        href = anchor["href"]
        full_url = urljoin("https://fbref.com", href)
        match = re.search(r"/players/([^/]+)/", href)
        fbref_player_id = match.group(1) if match else ""
        lookup[normalize_text(player_name)] = {
            "fbref_player_url": full_url,
            "fbref_player_id": fbref_player_id,
            "matched_fbref_player": player_name,
        }
    return lookup


def parse_fbref_tables(html: str, url: str) -> list[dict]:
    tables = []
    for index, table in enumerate(extract_table_elements(html)):
        table_id = table.get("id") or f"table_{index + 1}"
        table_html = str(table)
        try:
            frames = pd.read_html(StringIO(table_html))
        except ValueError:
            continue
        for frame_index, frame in enumerate(frames):
            flattened = flatten_fbref_columns(frame)
            pcol = player_column_name(flattened)
            if not pcol:
                continue
            flattened = flattened[flattened[pcol].astype(str).str.strip() != pcol].copy()
            flattened = flattened[flattened[pcol].astype(str).str.strip().ne("")].copy()
            if flattened.empty:
                continue
            tables.append(
                {
                    "table_id": table_id if frame_index == 0 else f"{table_id}_{frame_index + 1}",
                    "df": flattened.reset_index(drop=True),
                    "player_links": extract_player_urls_from_table(table_html),
                    "source_url": url,
                }
            )
    return tables


def split_fbref_column(column: str) -> tuple[str, str]:
    parts = str(column).split("__")
    if len(parts) == 1:
        return "", parts[0]
    return "__".join(parts[:-1]), parts[-1]


def build_base_column_map() -> dict[str, str]:
    pairs = {
        "Player": "player",
        "Nation": "nation",
        "Squad": "squad",
        "Team": "team",
        "Comp": "competition",
        "Pos": "position",
        "Age": "age",
        "Born": "born",
        "MP": "matches_played",
        "Starts": "starts",
        "Min": "minutes",
        "90s": "nineties",
        "Gls": "goals",
        "Ast": "assists",
        "G+A": "goals_plus_assists",
        "G-PK": "non_penalty_goals",
        "PK": "penalties_made",
        "PKatt": "penalties_attempted",
        "xG": "xg",
        "npxG": "npxg",
        "xAG": "xag",
        "npxG+xAG": "npxg_plus_xag",
        "Sh": "shots",
        "SoT": "shots_on_target",
        "SoT%": "shots_on_target_pct",
        "Sh/90": "shots_per_90",
        "SoT/90": "shots_on_target_per_90",
        "G/Sh": "goals_per_shot",
        "G/SoT": "goals_per_shot_on_target",
        "Dist": "average_shot_distance",
        "FK": "free_kick_shots",
        "KP": "key_passes",
        "1/3": "passes_into_final_third",
        "PPA": "passes_into_penalty_area",
        "CrsPA": "crosses_into_penalty_area",
        "PrgP": "progressive_passes",
        "SCA": "shot_creating_actions",
        "SCA90": "shot_creating_actions_per_90",
        "GCA": "goal_creating_actions",
        "GCA90": "goal_creating_actions_per_90",
        "Tkl": "tackles",
        "TklW": "tackles_won",
        "Blocks": "blocks",
        "Int": "interceptions",
        "Clr": "clearances",
        "Err": "errors",
        "CrdY": "yellow_cards",
        "CrdR": "red_cards",
        "2Yel": "second_yellow_cards",
        "Fls": "fouls_committed",
        "Fld": "fouls_drawn",
        "Off": "offsides",
        "Crs": "crosses",
        "PKwon": "penalties_won",
        "PKcon": "penalties_conceded",
        "OG": "own_goals",
        "Recov": "ball_recoveries",
        "Won": "aerials_won",
        "Lost": "aerials_lost",
        "Won%": "aerial_win_pct",
        "GA": "goals_against",
        "SoTA": "shots_on_target_against",
        "Saves": "saves",
        "Save%": "save_pct",
        "CS": "clean_sheets",
        "PKA": "penalty_kicks_faced",
        "PKsv": "penalties_saved",
        "PSxG": "post_shot_xg",
        "PSxG/SoT": "psxg_per_shot_on_target",
        "PSxG+/-": "psxg_minus_goals_allowed",
        "Stp": "crosses_stopped",
        "#OPA": "defensive_actions_outside_box",
        "AvgDist": "average_distance_defensive_actions",
        "Cmp": "passes_completed",
        "Att": "passes_attempted",
        "Cmp%": "pass_completion_pct",
        "PrgDist": "progressive_passing_distance",
        "xA": "xa",
        "A-xAG": "assists_minus_xag",
        "Touches": "touches",
        "Carries": "carries",
        "PrgC": "progressive_carries",
        "Mis": "miscontrols",
        "Dis": "dispossessed",
        "Rec": "passes_received",
        "PrgR": "progressive_passes_received",
    }
    return {normalize_fbref_token(key): value for key, value in pairs.items()}


BASE_COLUMN_MAP = build_base_column_map()


def contextual_column_name(stat_type: str, parent: str, label: str) -> str | None:
    parent_key = normalize_text(parent)
    label_key = normalize_fbref_token(label)

    if parent_key == "per 90 minutes":
        per_90 = {
            "gls": "goals_per_90",
            "ast": "assists_per_90",
            "xg": "xg_per_90",
            "npxg": "npxg_per_90",
            "xag": "xag_per_90",
            "npxg+xag": "npxg_plus_xag_per_90",
        }
        if label_key in per_90:
            return per_90[label_key]

    if stat_type == "shooting" and parent_key == "expected":
        expected = {
            "xg": "shooting_xg",
            "npxg": "shooting_npxg",
            "npxg/sh": "npxg_per_shot",
            "g-xg": "goals_minus_xg",
            "np:g-xg": "non_penalty_goals_minus_npxg",
        }
        if label_key in expected:
            return expected[label_key]

    if stat_type == "passing":
        if parent_key == "total":
            total = {
                "cmp": "passes_completed",
                "att": "passes_attempted",
                "cmp%": "pass_completion_pct",
                "prgdist": "progressive_passing_distance",
            }
            if label_key in total:
                return total[label_key]
        if parent_key == "short" and label_key == "cmp%":
            return "short_pass_completion_pct"
        if parent_key == "medium" and label_key == "cmp%":
            return "medium_pass_completion_pct"
        if parent_key == "long" and label_key == "cmp%":
            return "long_pass_completion_pct"
        if parent_key == "expected":
            expected = {"xag": "passing_xag", "xa": "xa", "a-xag": "assists_minus_xag"}
            if label_key in expected:
                return expected[label_key]

    if stat_type == "possession":
        touches = {
            "defpen": "touches_defensive_penalty_area",
            "def3rd": "touches_defensive_third",
            "mid3rd": "touches_middle_third",
            "att3rd": "touches_attacking_third",
            "attpen": "touches_attacking_penalty_area",
        }
        take_ons = {
            "att": "take_ons_attempted",
            "succ": "successful_take_ons",
            "succ%": "take_on_success_pct",
        }
        carries = {
            "carries": "carries",
            "prgc": "progressive_carries",
            "1/3": "carries_into_final_third",
            "cpa": "carries_into_penalty_area",
            "mis": "miscontrols",
            "dis": "dispossessed",
        }
        receiving = {"rec": "passes_received", "prgr": "progressive_passes_received"}
        if parent_key == "touches" and label_key in touches:
            return touches[label_key]
        if parent_key in {"take ons", "takeons"} and label_key in take_ons:
            return take_ons[label_key]
        if parent_key == "carries" and label_key in carries:
            return carries[label_key]
        if parent_key == "receiving" and label_key in receiving:
            return receiving[label_key]

    if stat_type == "defense":
        if parent_key == "tackles":
            values = {
                "tkl": "tackles",
                "tklw": "tackles_won",
                "def3rd": "tackles_defensive_third",
                "mid3rd": "tackles_middle_third",
                "att3rd": "tackles_attacking_third",
            }
            if label_key in values:
                return values[label_key]
        if parent_key == "challenges":
            values = {
                "att": "dribblers_challenged",
                "tkl": "dribblers_tackled",
                "tkl%": "challenge_success_pct",
            }
            if label_key in values:
                return values[label_key]
        if parent_key == "blocks":
            values = {"blocks": "blocks", "sh": "shot_blocks", "pass": "pass_blocks"}
            if label_key in values:
                return values[label_key]

    if stat_type == "gca":
        sca = {
            "sca": "shot_creating_actions",
            "sca90": "shot_creating_actions_per_90",
            "passlive": "sca_live_passes",
            "passdead": "sca_dead_balls",
            "to": "sca_take_ons",
            "sh": "sca_shots",
            "fld": "sca_fouls_drawn",
            "def": "sca_defensive_actions",
        }
        gca = {
            "gca": "goal_creating_actions",
            "gca90": "goal_creating_actions_per_90",
            "passlive": "gca_live_passes",
            "passdead": "gca_dead_balls",
            "to": "gca_take_ons",
            "sh": "gca_shots",
            "fld": "gca_fouls_drawn",
            "def": "gca_defensive_actions",
        }
        if parent_key in {"sca", "shot creating actions"} and label_key in sca:
            return sca[label_key]
        if parent_key in {"gca", "goal creating actions"} and label_key in gca:
            return gca[label_key]

    if stat_type in {"keeper", "keeper_adv"}:
        if label_key == "pkatt":
            return "penalty_kicks_faced"
        if label_key == "pksv":
            return "penalties_saved"

    return None


def safe_assign_normalized_column(df: pd.DataFrame, target: str, source: str) -> None:
    if target not in df.columns:
        df[target] = df[source]
        return
    if df[target].isna().all() and not df[source].isna().all():
        df[target] = df[source]
        return
    if df[target].equals(df[source]):
        return
    suffix = slugify_column(source)
    alt = f"{target}_{suffix}"
    if alt not in df.columns:
        df[alt] = df[source]


def normalize_fbref_columns(df: pd.DataFrame, stat_type: str) -> pd.DataFrame:
    normalized = df.copy()
    for column in list(df.columns):
        parent, label = split_fbref_column(str(column))
        target = contextual_column_name(stat_type, parent, label)
        if target is None:
            target = BASE_COLUMN_MAP.get(normalize_fbref_token(label))
        if target:
            safe_assign_normalized_column(normalized, target, column)

    if "team" not in normalized.columns and "squad" in normalized.columns:
        normalized["team"] = normalized["squad"]
    if "competition" not in normalized.columns and "Comp" in normalized.columns:
        normalized["competition"] = normalized["Comp"]

    text_columns = {
        "player",
        "nation",
        "squad",
        "team",
        "competition",
        "position",
        "fbref_player_url",
        "fbref_player_id",
    }
    numeric_columns = set(BASE_COLUMN_MAP.values()) - {
        "player",
        "nation",
        "squad",
        "team",
        "competition",
        "position",
        "age",
        "fbref_player_url",
        "fbref_player_id",
    }
    for column in normalized.columns:
        if column in text_columns or column.startswith("raw_"):
            continue
        if column in {
            "source_url",
            "fbref_table_id",
            "stat_type",
            "competition_name",
            "competition_group",
            "season",
            "season_type",
            "scraped_at_utc",
        }:
            continue
        if column in numeric_columns or column.endswith("_per_90"):
            cleaned = (
                normalized[column]
                .astype(str)
                .str.replace(",", "", regex=False)
                .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
            )
            converted = pd.to_numeric(cleaned, errors="coerce")
            if converted.notna().sum() > 0:
                normalized[column] = converted
    return normalized


def attach_player_links(df: pd.DataFrame, player_links: dict[str, dict[str, str]]) -> pd.DataFrame:
    if "player" not in df.columns:
        return df
    linked = df.copy()
    link_records = linked["player"].apply(lambda value: player_links.get(normalize_text(value), {}))
    linked["fbref_player_url"] = link_records.apply(lambda item: item.get("fbref_player_url", pd.NA))
    linked["fbref_player_id"] = link_records.apply(lambda item: item.get("fbref_player_id", pd.NA))
    return linked


def scrape_competition_season_stat_type(
    stat_url: str,
    stat_type: str,
    competition: Competition,
    season: str | None,
    cache_dir: Path,
    session: requests.Session,
    min_sleep: float,
    max_sleep: float,
    force_refresh: bool,
) -> tuple[list[pd.DataFrame], FetchResult]:
    result = fetch_html(
        stat_url,
        cache_dir=cache_dir,
        session=session,
        min_sleep=min_sleep,
        max_sleep=max_sleep,
        force_refresh=force_refresh,
    )
    if not result.ok or not result.html:
        return [], result

    scraped_at = now_utc_iso()
    frames = []
    for table in parse_fbref_tables(result.html, stat_url):
        frame = normalize_fbref_columns(table["df"], stat_type)
        frame = attach_player_links(frame, table["player_links"])
        frame["source_url"] = stat_url
        frame["fbref_table_id"] = table["table_id"]
        frame["stat_type"] = stat_type
        frame["competition_name"] = competition.competition_name
        frame["competition_group"] = competition.competition_group
        frame["season"] = season or parse_fbref_comp_url(stat_url).get("season") or "mapped_url"
        frame["season_type"] = competition.season_type
        frame["scraped_at_utc"] = scraped_at
        frames.append(frame)
    return frames, result


def score_roster_match(stats_row: pd.Series, roster_row: pd.Series) -> tuple[float, list[str]]:
    notes = []
    stats_player = normalize_text(stats_row.get("player", ""))
    roster_player = roster_row.get("roster_player_normalized", "")
    if not stats_player or not roster_player:
        return 0.0, ["missing player name"]

    name_score = fuzz.token_sort_ratio(stats_player, roster_player)
    score = name_score * 0.70
    if stats_player == roster_player:
        score = 76.0
        notes.append("exact normalized player name")
    else:
        notes.append(f"name fuzzy score {name_score:.0f}")

    stats_squad = normalize_text(stats_row.get("squad", stats_row.get("team", "")))
    roster_club = roster_row.get("roster_club_normalized", "")
    if stats_squad and roster_club:
        club_score = fuzz.token_sort_ratio(stats_squad, roster_club)
        if stats_squad == roster_club or club_score >= 90:
            score += 12
            notes.append("club/squad match")
        elif club_score < 45:
            score -= 4
            notes.append("club/squad mismatch")

    stats_comp = normalize_text(stats_row.get("competition", stats_row.get("competition_name", "")))
    roster_league = roster_row.get("roster_league_normalized", "")
    if stats_comp and roster_league:
        league_score = fuzz.token_sort_ratio(stats_comp, roster_league)
        if stats_comp == roster_league or league_score >= 85:
            score += 6
            notes.append("league/competition match")

    stats_nation = normalize_text(stats_row.get("nation", ""))
    roster_team = roster_row.get("roster_team_normalized", "")
    if stats_nation and roster_team:
        nation_score = fuzz.partial_ratio(stats_nation, roster_team)
        if nation_score >= 80:
            score += 5
            notes.append("nation/team signal")

    stats_position = normalize_text(stats_row.get("position", ""))
    roster_position = roster_row.get("roster_position_normalized", "")
    if stats_position and roster_position:
        if (
            "goalkeeper" in roster_position
            and "gk" not in stats_position
            and "goalkeeper" not in stats_position
        ):
            score -= 4
            notes.append("position mismatch")
        elif "goalkeeper" not in roster_position and "gk" in stats_position:
            score -= 4
            notes.append("position mismatch")

    born = pd.to_numeric(stats_row.get("born", pd.NA), errors="coerce")
    birth_year = roster_row.get("birth_year", pd.NA)
    if not pd.isna(born) and not pd.isna(birth_year):
        if int(born) == int(birth_year):
            score += 12
            notes.append("birth year match")
        else:
            score -= 8
            notes.append("birth year mismatch")

    return max(0.0, min(100.0, score)), notes


def match_status_from_score(score: float, exact_name: bool) -> str:
    if exact_name and score >= 90:
        return "matched_exact"
    if score >= 88:
        return "matched_high_confidence"
    if score >= 75:
        return "matched_medium_confidence"
    return "unmatched"


def candidate_roster_rows(stats_row: pd.Series, roster: pd.DataFrame) -> pd.DataFrame:
    player = normalize_text(stats_row.get("player", ""))
    if not player:
        return roster.iloc[0:0]

    exact = roster[roster["roster_player_normalized"] == player]
    if not exact.empty:
        return exact

    choices = roster["roster_player_normalized"].dropna().unique().tolist()
    matches = process.extract(player, choices, scorer=fuzz.token_sort_ratio, limit=8)
    candidate_names = [name for name, score, _ in matches if score >= 78]
    return roster[roster["roster_player_normalized"].isin(candidate_names)]


FINAL_MIN_COLUMNS = [
    "player",
    "competition",
    "competition_name",
    "season",
    "stat_type",
    "source_url",
    "fbref_table_id",
    "competition_group",
    "season_type",
    "scraped_at_utc",
    "match_status",
    "match_confidence",
    "match_method",
    "matched_fbref_player",
    "matched_fbref_player_url",
    "matched_fbref_player_id",
    "match_notes",
]

RAW_MIN_COLUMNS = [
    "player",
    "competition",
    "competition_name",
    "season",
    "stat_type",
    "source_url",
    "fbref_table_id",
]

URL_USED_COLUMNS = [
    "competition_name",
    "competition_group",
    "season",
    "season_type",
    "url",
    "url_role",
    "from_cache",
]

URL_FAILED_COLUMNS = [
    "competition_name",
    "competition_group",
    "season",
    "stat_type",
    "url",
    "status_code",
    "error_message",
]


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    ensured = df.copy()
    for column in columns:
        if column not in ensured.columns:
            ensured[column] = pd.Series(dtype="object")
    return ensured


def match_stats_to_roster(
    stats_df: pd.DataFrame,
    roster_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if stats_df.empty:
        unmatched_roster = roster_df.copy()
        unmatched_roster["match_status"] = "unmatched"
        unmatched_roster["match_notes"] = "no stats rows scraped"
        return (
            ensure_columns(stats_df, FINAL_MIN_COLUMNS),
            pd.DataFrame(
                columns=[
                    "roster_player",
                    "roster_team",
                    "matched_fbref_player",
                    "matched_fbref_player_url",
                    "matched_fbref_player_id",
                    "match_status",
                    "match_confidence",
                    "stat_type",
                    "competition_name",
                    "season",
                    "source_url",
                    "match_notes",
                ]
            ),
            unmatched_roster,
            pd.DataFrame(columns=FINAL_MIN_COLUMNS + ["alternate_roster_candidates"]),
        )

    matched_rows = []
    ambiguous_rows = []
    match_log_rows = []

    for index, stats_row in stats_df.iterrows():
        candidates = candidate_roster_rows(stats_row, roster_df)
        if candidates.empty:
            continue

        scored = []
        for _, roster_row in candidates.iterrows():
            score, notes = score_roster_match(stats_row, roster_row)
            scored.append((score, notes, roster_row))
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_notes, best_roster = scored[0]
        exact_name = (
            normalize_text(stats_row.get("player", ""))
            == best_roster.get("roster_player_normalized", "")
        )
        status = match_status_from_score(best_score, exact_name)

        if len(scored) > 1 and best_score >= 75 and (best_score - scored[1][0]) <= 3:
            status = "ambiguous"

        record = stats_row.to_dict()
        record.update(
            {
                "roster_player": best_roster.get("player"),
                "roster_team": best_roster.get("team"),
                "roster_club": best_roster.get("club"),
                "roster_league": best_roster.get("league"),
                "roster_position": best_roster.get("position"),
                "match_status": status,
                "match_confidence": round(best_score, 2),
                "match_method": "direct_name_context_score",
                "matched_fbref_player": stats_row.get("player"),
                "matched_fbref_player_url": stats_row.get("fbref_player_url"),
                "matched_fbref_player_id": stats_row.get("fbref_player_id"),
                "match_notes": "; ".join(best_notes),
            }
        )

        if status == "ambiguous":
            record["alternate_roster_candidates"] = "; ".join(
                f"{item[2].get('player')} ({item[0]:.1f})" for item in scored[:4]
            )
            ambiguous_rows.append(record)
        elif status.startswith("matched"):
            matched_rows.append(record)
            match_log_rows.append(
                {
                    "roster_player": best_roster.get("player"),
                    "roster_team": best_roster.get("team"),
                    "matched_fbref_player": stats_row.get("player"),
                    "matched_fbref_player_url": stats_row.get("fbref_player_url"),
                    "matched_fbref_player_id": stats_row.get("fbref_player_id"),
                    "match_status": status,
                    "match_confidence": round(best_score, 2),
                    "stat_type": stats_row.get("stat_type"),
                    "competition_name": stats_row.get("competition_name"),
                    "season": stats_row.get("season"),
                    "source_url": stats_row.get("source_url"),
                    "match_notes": "; ".join(best_notes),
                }
            )

    matched_df = pd.DataFrame(matched_rows)
    match_log = pd.DataFrame(match_log_rows).drop_duplicates() if match_log_rows else pd.DataFrame()
    ambiguous_df = pd.DataFrame(ambiguous_rows)

    matched_players = (
        set(matched_df["roster_player"].dropna().astype(str))
        if not matched_df.empty and "roster_player" in matched_df.columns
        else set()
    )
    unmatched_roster = roster_df[~roster_df["player"].astype(str).isin(matched_players)].copy()
    unmatched_roster["match_status"] = "unmatched"
    unmatched_roster["match_notes"] = "no non-ambiguous FBref stat rows matched"
    return (
        ensure_columns(matched_df, FINAL_MIN_COLUMNS),
        match_log,
        unmatched_roster,
        ensure_columns(ambiguous_df, FINAL_MIN_COLUMNS + ["alternate_roster_candidates"]),
    )


SHOT_EVENT_COLUMNS = [
    "player",
    "team",
    "opponent",
    "competition",
    "season",
    "match_date",
    "minute",
    "period",
    "shot_outcome",
    "is_goal",
    "shot_distance",
    "body_part",
    "xg",
    "psxg",
    "shot_type",
    "assist_player",
    "assist_type",
    "shot_creating_action",
    "game_state",
    "home_away",
    "score_state",
    "source_match_url",
    "shot_x",
    "shot_y",
    "distance_to_goal",
    "angle_to_goal",
    "under_pressure",
    "play_pattern",
]


def normalize_shot_table(df: pd.DataFrame, match_url: str) -> pd.DataFrame:
    frame = flatten_fbref_columns(df)
    out = pd.DataFrame()
    aliases = {
        "player": ["Player"],
        "team": ["Squad", "Team"],
        "minute": ["Minute", "Min"],
        "shot_outcome": ["Outcome", "Result"],
        "shot_distance": ["Distance", "Dist"],
        "body_part": ["Body Part", "BodyPart"],
        "xg": ["xG"],
        "psxg": ["PSxG"],
        "assist_player": ["SCA 1 Player", "Assist", "Assisted By"],
        "shot_creating_action": ["SCA 1 Event", "SCA"],
    }
    for target, column_aliases in aliases.items():
        source = find_alias_column(frame.columns, column_aliases)
        out[target] = frame[source] if source else pd.NA
    out["is_goal"] = out["shot_outcome"].astype(str).str.contains("goal", case=False, na=False)
    out["source_match_url"] = match_url
    for column in SHOT_EVENT_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    return out[SHOT_EVENT_COLUMNS]


def scrape_match_report_shots(match_url: str, html: str) -> pd.DataFrame:
    frames = []
    for table in parse_fbref_tables(html, match_url):
        table_id = normalize_text(table["table_id"])
        columns = {normalize_text(column) for column in table["df"].columns}
        likely_shots = "shots" in table_id or {"player", "minute"}.issubset(columns)
        if not likely_shots:
            continue
        shot_frame = normalize_shot_table(table["df"], match_url)
        if "player" in shot_frame.columns and shot_frame["player"].notna().any():
            frames.append(shot_frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=SHOT_EVENT_COLUMNS)


def extract_match_report_urls(schedule_html: str, schedule_url: str) -> list[str]:
    soup = BeautifulSoup(schedule_html, "lxml")
    urls = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        text = normalize_text(anchor.get_text(" ", strip=True))
        if "/en/matches/" not in href:
            continue
        if "match report" not in text and not re.search(r"/matches/[a-f0-9]+/", href):
            continue
        full_url = urljoin(schedule_url, href)
        if full_url not in seen:
            seen.add(full_url)
            urls.append(full_url)
    return urls


def scrape_shot_events_for_competition_season(
    competition_season_url: str,
    competition: Competition,
    season: str | None,
    cache_dir: Path,
    session: requests.Session,
    min_sleep: float,
    max_sleep: float,
    force_refresh: bool,
    max_reports: int,
) -> tuple[pd.DataFrame, list[dict]]:
    failed = []
    schedule_url = build_schedule_url(competition_season_url)
    schedule_result = fetch_html(
        schedule_url,
        cache_dir,
        session,
        min_sleep,
        max_sleep,
        force_refresh=force_refresh,
    )
    if not schedule_result.ok or not schedule_result.html:
        failed.append(
            {
                "competition_name": competition.competition_name,
                "competition_group": competition.competition_group,
                "season": season,
                "stat_type": "shot_events_schedule",
                "url": schedule_url,
                "status_code": schedule_result.status_code,
                "error_message": schedule_result.error_message,
            }
        )
        return pd.DataFrame(columns=SHOT_EVENT_COLUMNS), failed

    match_urls = extract_match_report_urls(schedule_result.html, schedule_url)[:max_reports]
    frames = []
    for match_url in match_urls:
        match_result = fetch_html(
            match_url,
            cache_dir,
            session,
            min_sleep,
            max_sleep,
            force_refresh=force_refresh,
        )
        if not match_result.ok or not match_result.html:
            failed.append(
                {
                    "competition_name": competition.competition_name,
                    "competition_group": competition.competition_group,
                    "season": season,
                    "stat_type": "shot_events_match_report",
                    "url": match_url,
                    "status_code": match_result.status_code,
                    "error_message": match_result.error_message,
                }
            )
            continue
        events = scrape_match_report_shots(match_url, match_result.html)
        if events.empty:
            continue
        events["competition"] = competition.competition_name
        events["season"] = season
        frames.append(events)
    if not frames:
        return pd.DataFrame(columns=SHOT_EVENT_COLUMNS), failed
    return pd.concat(frames, ignore_index=True), failed


def build_data_dictionary() -> pd.DataFrame:
    descriptions = {
        "source_url": "FBref URL used for the scrape.",
        "fbref_table_id": "HTML table id parsed from FBref.",
        "stat_type": "Requested FBref stat table family.",
        "competition_name": "Competition label from the mapping file.",
        "competition_group": "Competition group from mapping file or inferred source.",
        "season": "Season or edition attempted.",
        "season_type": "calendar, european, or tournament season behavior.",
        "scraped_at_utc": "UTC timestamp when the table was parsed.",
        "match_status": "Roster matching status.",
        "match_confidence": "0-100 roster matching score.",
        "match_method": "Matching algorithm used.",
        "match_notes": "Human-readable match signals.",
    }
    normalized = sorted(set(BASE_COLUMN_MAP.values()))
    rows = [
        {
            "column_name": column,
            "description": descriptions.get(column, f"Normalized FBref field: {column}."),
            "source_stat_type": "varies",
            "fbref_raw_column": "",
            "notes": "",
        }
        for column in normalized
    ]
    rows.extend(
        {
            "column_name": column,
            "description": description,
            "source_stat_type": "provenance/matching",
            "fbref_raw_column": "",
            "notes": "",
        }
        for column, description in descriptions.items()
    )
    for column in ["under_pressure", "play_pattern", "shot_x", "shot_y"]:
        rows.append(
            {
                "column_name": column,
                "description": f"Shot-event field requested for audit: {column}.",
                "source_stat_type": "shot_events",
                "fbref_raw_column": "",
                "notes": "not_available_or_not_reliably_exposed_by_fbref",
            }
        )
    return pd.DataFrame(rows).drop_duplicates("column_name")


def safe_write_parquet(df: pd.DataFrame, path: Path, warnings: list[str]) -> None:
    try:
        df.to_parquet(path, index=False)
    except Exception as error:
        warnings.append(f"Could not write parquet {path}: {error}")


def write_excel_sheet(writer: pd.ExcelWriter, df: pd.DataFrame, sheet_name: str) -> None:
    if len(df) <= EXCEL_MAX_ROWS - 1:
        df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
        return
    chunk_size = EXCEL_MAX_ROWS - 1
    for index, start in enumerate(range(0, len(df), chunk_size), start=1):
        df.iloc[start : start + chunk_size].to_excel(
            writer,
            sheet_name=f"{sheet_name[:26]}_{index}",
            index=False,
        )


def validate_outputs(
    final_stats: pd.DataFrame,
    roster: pd.DataFrame,
    ambiguous: pd.DataFrame,
) -> dict:
    required_columns = ["player", "competition_name", "season", "stat_type", "source_url"]
    missing_required_rows = 0
    for column in required_columns:
        if column not in final_stats.columns:
            missing_required_rows += len(final_stats)
        else:
            missing_required_rows += int(final_stats[column].isna().sum())

    duplicate_subset = [
        column
        for column in ["player", "squad", "competition_name", "season", "stat_type"]
        if column in final_stats.columns
    ]
    duplicate_rows = (
        int(final_stats.duplicated(duplicate_subset).sum()) if duplicate_subset else 0
    )

    minutes_invalid = 0
    if "minutes" in final_stats.columns:
        minutes = pd.to_numeric(final_stats["minutes"], errors="coerce")
        minutes_invalid = int((minutes.dropna() < 0).sum())
    nineties_invalid = 0
    if "nineties" in final_stats.columns:
        nineties = pd.to_numeric(final_stats["nineties"], errors="coerce")
        nineties_invalid = int((nineties.dropna() < 0).sum())

    matched_players = (
        final_stats["roster_player"].dropna().astype(str).nunique()
        if "roster_player" in final_stats.columns
        else 0
    )
    return {
        "unique_roster_players": int(roster["player"].nunique()),
        "matched_players": int(matched_players),
        "unmatched_players": int(roster["player"].nunique() - matched_players),
        "ambiguous_matches": int(len(ambiguous)),
        "missing_required_output_values": int(missing_required_rows),
        "duplicate_player_squad_competition_season_stat_rows": duplicate_rows,
        "invalid_minutes_rows": minutes_invalid,
        "invalid_nineties_rows": nineties_invalid,
    }


def create_run_report(
    run_started: str,
    run_ended: str,
    roster: pd.DataFrame,
    competitions: list[Competition],
    urls_attempted: int,
    urls_successful: int,
    url_failures: list[dict],
    raw_rows: int,
    matched_players: int,
    unmatched_players: int,
    ambiguous_matches: int,
    shot_event_rows: int,
    unavailable_fields: list[str],
    validation: dict,
    warnings: list[str],
) -> dict:
    return {
        "run_started_utc": run_started,
        "run_ended_utc": run_ended,
        "number_of_roster_players": int(roster["player"].nunique()),
        "number_of_competitions_requested": len(competitions),
        "number_of_competition_season_urls_attempted": urls_attempted,
        "number_of_successful_competition_season_urls": urls_successful,
        "number_of_failed_urls": len(url_failures),
        "number_of_raw_stat_rows_scraped": raw_rows,
        "number_of_matched_players": matched_players,
        "number_of_unmatched_players": unmatched_players,
        "number_of_ambiguous_matches": ambiguous_matches,
        "shot_event_rows_scraped": shot_event_rows,
        "fields_unavailable_on_fbref": unavailable_fields,
        "validation": validation,
        "warnings": warnings,
    }


def write_markdown_report(report: dict, path: Path) -> None:
    lines = [
        "# FBref WC2026 Run Summary",
        "",
        f"- Run started UTC: {report['run_started_utc']}",
        f"- Run ended UTC: {report['run_ended_utc']}",
        f"- Roster players: {report['number_of_roster_players']:,}",
        f"- Competitions requested: {report['number_of_competitions_requested']:,}",
        f"- Competition-season URLs attempted: {report['number_of_competition_season_urls_attempted']:,}",
        f"- Successful competition-season URLs: {report['number_of_successful_competition_season_urls']:,}",
        f"- Failed URLs: {report['number_of_failed_urls']:,}",
        f"- Raw stat rows scraped: {report['number_of_raw_stat_rows_scraped']:,}",
        f"- Matched players: {report['number_of_matched_players']:,}",
        f"- Unmatched players: {report['number_of_unmatched_players']:,}",
        f"- Ambiguous matches: {report['number_of_ambiguous_matches']:,}",
        f"- Shot-event rows scraped: {report['shot_event_rows_scraped']:,}",
        "",
        "## Unavailable Fields",
        "",
    ]
    unavailable = report.get("fields_unavailable_on_fbref") or []
    lines.extend(f"- {field}" for field in unavailable)
    lines.extend(["", "## Validation", ""])
    for key, value in report.get("validation", {}).items():
        lines.append(f"- {key}: {value}")
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(
    outdir: Path,
    final_stats: pd.DataFrame,
    raw_tables: pd.DataFrame,
    matched_players: pd.DataFrame,
    unmatched_players: pd.DataFrame,
    ambiguous_matches: pd.DataFrame,
    urls_used: pd.DataFrame,
    urls_failed: pd.DataFrame,
    missing_seasons: pd.DataFrame,
    data_dictionary: pd.DataFrame,
    run_report: dict,
    shot_events: pd.DataFrame | None,
    shot_availability: pd.DataFrame | None,
    warnings: list[str],
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    raw_dir = outdir / "raw"
    logs_dir = outdir / "logs"
    shot_dir = outdir / "shot_events"
    raw_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    final_stats = ensure_columns(final_stats, FINAL_MIN_COLUMNS)
    raw_tables = ensure_columns(raw_tables, RAW_MIN_COLUMNS)
    matched_players = ensure_columns(
        matched_players,
        [
            "roster_player",
            "roster_team",
            "matched_fbref_player",
            "matched_fbref_player_url",
            "matched_fbref_player_id",
            "match_status",
            "match_confidence",
            "stat_type",
            "competition_name",
            "season",
            "source_url",
            "match_notes",
        ],
    )
    ambiguous_matches = ensure_columns(
        ambiguous_matches,
        FINAL_MIN_COLUMNS + ["alternate_roster_candidates"],
    )
    urls_used = ensure_columns(urls_used, URL_USED_COLUMNS)
    urls_failed = ensure_columns(urls_failed, URL_FAILED_COLUMNS)
    missing_seasons = ensure_columns(missing_seasons, URL_FAILED_COLUMNS)

    final_stats.to_csv(outdir / "wc2026_player_competition_season_stats.csv", index=False)
    safe_write_parquet(
        final_stats,
        outdir / "wc2026_player_competition_season_stats.parquet",
        warnings,
    )
    raw_tables.to_csv(raw_dir / "fbref_raw_all_tables.csv", index=False)
    safe_write_parquet(raw_tables, raw_dir / "fbref_raw_all_tables.parquet", warnings)

    matched_players.to_csv(logs_dir / "matched_players.csv", index=False)
    unmatched_players.to_csv(logs_dir / "unmatched_players.csv", index=False)
    ambiguous_matches.to_csv(logs_dir / "ambiguous_player_matches.csv", index=False)
    urls_used.to_csv(logs_dir / "competition_urls_used.csv", index=False)
    urls_failed.to_csv(logs_dir / "competition_urls_failed.csv", index=False)
    missing_seasons.to_csv(logs_dir / "missing_or_unavailable_seasons.csv", index=False)
    data_dictionary.to_csv(outdir / "data_dictionary.csv", index=False)

    if shot_events is not None:
        shot_dir.mkdir(parents=True, exist_ok=True)
        shot_events.to_csv(shot_dir / "wc2026_player_shot_events.csv", index=False)
        safe_write_parquet(
            shot_events,
            shot_dir / "wc2026_player_shot_events.parquet",
            warnings,
        )
        if shot_availability is not None:
            shot_availability.to_csv(
                shot_dir / "shot_event_data_availability_report.csv",
                index=False,
            )

    (outdir / "run_report.json").write_text(
        json.dumps(run_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_markdown_report(run_report, outdir / "README_RUN_SUMMARY.md")

    with pd.ExcelWriter(outdir / "wc2026_player_competition_season_stats.xlsx") as writer:
        write_excel_sheet(writer, final_stats, "final_player_stats")
        write_excel_sheet(writer, matched_players, "matched_players")
        write_excel_sheet(writer, unmatched_players, "unmatched_players")
        write_excel_sheet(writer, ambiguous_matches, "ambiguous_matches")
        write_excel_sheet(writer, urls_used, "competition_urls_used")
        write_excel_sheet(writer, urls_failed, "competition_urls_failed")
        write_excel_sheet(writer, missing_seasons, "missing_seasons")
        pd.DataFrame([run_report]).to_excel(writer, sheet_name="run_summary", index=False)
        data_dictionary.to_excel(writer, sheet_name="data_dictionary", index=False)


def build_shot_availability_report(shot_events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in SHOT_EVENT_COLUMNS:
        if shot_events.empty or column not in shot_events.columns:
            available = False
            populated = 0
        else:
            populated = int(shot_events[column].notna().sum())
            available = populated > 0
        note = ""
        if column in {"under_pressure", "play_pattern", "shot_x", "shot_y"} and not available:
            note = "not_available_or_not_reliably_exposed_by_fbref"
        rows.append(
            {
                "field": column,
                "populated_rows": populated,
                "available": available,
                "notes": note,
            }
        )
    return pd.DataFrame(rows)


def scrape_all_competitions(
    competitions: list[Competition],
    roster: pd.DataFrame,
    args: argparse.Namespace,
) -> dict:
    session = requests.Session()
    cache_dir = args.outdir / "cache"
    raw_frames = []
    urls_used = []
    urls_failed = []
    missing_seasons = []
    shot_frames = []
    shot_failures = []
    urls_attempted = 0
    urls_successful = 0
    stop_requested = False
    stop_reason = ""

    selected_competitions = competitions[: args.max_competitions] if args.max_competitions else competitions

    for comp_index, competition in enumerate(selected_competitions, start=1):
        if stop_requested:
            break
        seasons = seasons_for_competition(competition, args.seasons)
        if args.max_seasons_per_competition:
            seasons = seasons[: args.max_seasons_per_competition]

        print(
            f"[{comp_index}/{len(selected_competitions)}] {competition.competition_name} "
            f"({competition.competition_group}, {competition.season_type}) seasons={seasons}",
            flush=True,
        )

        for season in seasons:
            urls_attempted += 1
            try:
                competition_season_url = build_competition_season_url(
                    competition.fbref_comp_url,
                    season,
                )
            except ValueError as error:
                failure = {
                    "competition_name": competition.competition_name,
                    "competition_group": competition.competition_group,
                    "season": season,
                    "stat_type": "overview",
                    "url": competition.fbref_comp_url,
                    "status_code": None,
                    "error_message": str(error),
                }
                urls_failed.append(failure)
                missing_seasons.append(failure)
                print(f"  could not parse competition URL: {competition.fbref_comp_url}", flush=True)
                continue
            try:
                overview = fetch_html(
                    competition_season_url,
                    cache_dir,
                    session,
                    args.min_sleep,
                    args.max_sleep,
                    force_refresh=args.force_refresh_cache,
                )
            except StopScraping:
                raise
            except Exception as error:
                overview = FetchResult(
                    url=competition_season_url,
                    ok=False,
                    error_message=str(error),
                )

            if not overview.ok or not overview.html:
                failure = {
                    "competition_name": competition.competition_name,
                    "competition_group": competition.competition_group,
                    "season": season,
                    "stat_type": "overview",
                    "url": competition_season_url,
                    "status_code": overview.status_code,
                    "error_message": overview.error_message,
                }
                urls_failed.append(failure)
                missing_seasons.append(failure)
                print(
                    f"  unavailable season URL: {competition_season_url} "
                    f"({overview.error_message})",
                    flush=True,
                )
                if overview.stop_requested:
                    stop_requested = True
                    stop_reason = f"{overview.status_code} at {competition_season_url}"
                    print(
                        f"  FBref blocking signal detected ({stop_reason}); "
                        "stopping further live requests.",
                        flush=True,
                    )
                    break
                continue

            urls_successful += 1
            stat_links = discover_stat_links(overview.html, competition_season_url)
            urls_used.append(
                {
                    "competition_name": competition.competition_name,
                    "competition_group": competition.competition_group,
                    "season": season,
                    "season_type": competition.season_type,
                    "url": competition_season_url,
                    "url_role": "overview",
                    "from_cache": overview.from_cache,
                }
            )

            for stat_type in args.stat_types:
                stat_url = stat_links.get(stat_type) or build_stat_url(
                    competition_season_url,
                    stat_type,
                )
                frames, fetch_result = scrape_competition_season_stat_type(
                    stat_url,
                    stat_type,
                    competition,
                    season,
                    cache_dir,
                    session,
                    args.min_sleep,
                    args.max_sleep,
                    args.force_refresh_cache,
                )
                if not fetch_result.ok:
                    urls_failed.append(
                        {
                            "competition_name": competition.competition_name,
                            "competition_group": competition.competition_group,
                            "season": season,
                            "stat_type": stat_type,
                            "url": stat_url,
                            "status_code": fetch_result.status_code,
                            "error_message": fetch_result.error_message,
                        }
                    )
                    if fetch_result.stop_requested:
                        stop_requested = True
                        stop_reason = f"{fetch_result.status_code} at {stat_url}"
                        print(
                            f"  FBref blocking signal detected ({stop_reason}); "
                            "stopping further live requests.",
                            flush=True,
                        )
                        break
                    continue
                urls_used.append(
                    {
                        "competition_name": competition.competition_name,
                        "competition_group": competition.competition_group,
                        "season": season,
                        "season_type": competition.season_type,
                        "url": stat_url,
                        "url_role": stat_type,
                        "from_cache": fetch_result.from_cache,
                    }
                )
                if not frames:
                    urls_failed.append(
                        {
                            "competition_name": competition.competition_name,
                            "competition_group": competition.competition_group,
                            "season": season,
                            "stat_type": stat_type,
                            "url": stat_url,
                            "status_code": fetch_result.status_code,
                            "error_message": "no player tables parsed",
                        }
                    )
                    continue
                raw_frames.extend(frames)
                print(
                    f"  {season} {stat_type}: "
                    f"{sum(len(frame) for frame in frames):,} player rows",
                    flush=True,
                )

            if stop_requested:
                break

            if args.scrape_shot_events:
                events, failures = scrape_shot_events_for_competition_season(
                    competition_season_url,
                    competition,
                    season,
                    cache_dir,
                    session,
                    args.min_sleep,
                    args.max_sleep,
                    args.force_refresh_cache,
                    args.max_match_reports_per_competition_season,
                )
                if not events.empty:
                    shot_frames.append(events)
                shot_failures.extend(failures)

    raw_tables = pd.concat(raw_frames, ignore_index=True, sort=False) if raw_frames else pd.DataFrame()
    final_stats, matched_log, unmatched_roster, ambiguous = match_stats_to_roster(
        raw_tables,
        roster,
    )
    shot_events = (
        pd.concat(shot_frames, ignore_index=True, sort=False)
        if shot_frames
        else (pd.DataFrame(columns=SHOT_EVENT_COLUMNS) if args.scrape_shot_events else None)
    )

    return {
        "raw_tables": raw_tables,
        "final_stats": final_stats,
        "matched_log": matched_log,
        "unmatched_roster": unmatched_roster,
        "ambiguous": ambiguous,
        "urls_used": pd.DataFrame(urls_used),
        "urls_failed": pd.DataFrame(urls_failed + shot_failures),
        "missing_seasons": pd.DataFrame(missing_seasons),
        "shot_events": shot_events,
        "urls_attempted": urls_attempted,
        "urls_successful": urls_successful,
        "stop_requested": stop_requested,
        "stop_reason": stop_reason,
    }


def print_detected_schemas(args: argparse.Namespace) -> None:
    schema = {"roster": inspect_tabular_schema(args.roster)}
    if args.competition_map:
        schema["competition_map"] = inspect_tabular_schema(args.competition_map)
    for label, path in [
        ("league_map", args.league_map),
        ("international_map", args.international_map),
        ("europe_map", args.europe_map),
    ]:
        if path:
            schema[label] = inspect_tabular_schema(path)
    print(json.dumps(schema, indent=2, ensure_ascii=False), flush=True)


def print_input_summary(args: argparse.Namespace) -> None:
    roster_sheet, roster_raw = select_roster_sheet(args.roster)
    roster = normalize_roster_columns(roster_raw)
    competitions = load_competition_maps(
        args.competition_map,
        args.league_map,
        args.international_map,
        args.europe_map,
    )
    group_counts = (
        pd.Series([competition.competition_group for competition in competitions])
        .value_counts()
        .to_dict()
    )
    summary = {
        "roster_file_path": str(args.roster.resolve()),
        "roster_sheet_name": roster_sheet,
        "roster_row_count": int(len(roster)),
        "roster_columns": [str(column) for column in roster_raw.columns],
        "unique_player_count": int(roster["player"].nunique()),
        "competition_mapping_file_path": (
            str(args.competition_map.resolve()) if args.competition_map else None
        ),
        "detected_mapping_sections": sorted(group_counts),
        "number_of_domestic_competitions": int(group_counts.get("domestic_leagues", 0)),
        "number_of_international_competitions": int(
            group_counts.get("international_tournaments", 0)
        ),
        "number_of_european_club_competitions": int(
            group_counts.get("european_competitions", 0)
        ),
        "total_competition_urls": int(len(competitions)),
    }
    print("Detected input summary:", flush=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape FBref player stats for confirmed World Cup 2026 players."
    )
    parser.add_argument("--roster", type=Path, default=DEFAULT_ROSTER_PATH)
    parser.add_argument("--competition-map", type=Path)
    parser.add_argument("--league-map", type=Path)
    parser.add_argument("--international-map", type=Path)
    parser.add_argument("--europe-map", type=Path)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--seasons", nargs="+", default=DEFAULT_SEASONS)
    parser.add_argument("--stat-types", nargs="+", default=DEFAULT_STAT_TYPES)
    parser.add_argument("--min-sleep", type=float, default=6)
    parser.add_argument("--max-sleep", type=float, default=12)
    parser.add_argument("--scrape-shot-events", action="store_true")
    parser.add_argument("--max-match-reports-per-competition-season", type=int, default=10)
    parser.add_argument("--max-competitions", type=int)
    parser.add_argument("--limit-competitions", type=int, dest="max_competitions")
    parser.add_argument("--max-seasons-per-competition", type=int)
    parser.add_argument("--inspect-inputs-only", action="store_true")
    parser.add_argument("--inspect-inputs", action="store_true", dest="inspect_inputs_only")
    parser.add_argument("--force-refresh-cache", action="store_true")
    args = parser.parse_args(argv)

    if not args.competition_map and not any([args.league_map, args.international_map, args.europe_map]):
        raise SystemExit(
            "Provide --competition-map, or one or more of --league-map, "
            "--international-map, --europe-map."
        )
    unknown_stats = sorted(set(args.stat_types) - set(STAT_URL_PATHS))
    if unknown_stats:
        raise SystemExit(f"Unsupported stat types: {unknown_stats}")
    if args.max_sleep < args.min_sleep:
        raise SystemExit("--max-sleep must be greater than or equal to --min-sleep.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.outdir = args.outdir.resolve()
    run_started = now_utc_iso()

    print("Detected input schemas:", flush=True)
    print_detected_schemas(args)
    if args.inspect_inputs_only:
        print_input_summary(args)
        return 0

    roster = load_roster(args.roster)
    competitions = load_competition_maps(
        args.competition_map,
        args.league_map,
        args.international_map,
        args.europe_map,
    )
    if not competitions:
        raise SystemExit("No competitions found in the mapping input.")

    warnings = []
    try:
        result = scrape_all_competitions(competitions, roster, args)
    except StopScraping as error:
        print(str(error), file=sys.stderr, flush=True)
        return 2
    if result.get("stop_requested"):
        warnings.append(
            "Live FBref scraping stopped early after a blocking/status signal: "
            f"{result.get('stop_reason') or 'unknown'}"
        )

    raw_tables = result["raw_tables"]
    final_stats = result["final_stats"]
    matched_log = result["matched_log"]
    unmatched_roster = result["unmatched_roster"]
    ambiguous = result["ambiguous"]
    urls_failed = result["urls_failed"]
    urls_used = result["urls_used"]
    missing_seasons = result["missing_seasons"]
    shot_events = result["shot_events"]
    shot_availability = (
        build_shot_availability_report(shot_events)
        if shot_events is not None
        else None
    )
    data_dictionary = build_data_dictionary()
    validation = validate_outputs(final_stats, roster, ambiguous)
    run_ended = now_utc_iso()
    report = create_run_report(
        run_started=run_started,
        run_ended=run_ended,
        roster=roster,
        competitions=competitions,
        urls_attempted=result["urls_attempted"],
        urls_successful=result["urls_successful"],
        url_failures=urls_failed.to_dict("records") if not urls_failed.empty else [],
        raw_rows=len(raw_tables),
        matched_players=validation["matched_players"],
        unmatched_players=validation["unmatched_players"],
        ambiguous_matches=len(ambiguous),
        shot_event_rows=len(shot_events) if shot_events is not None else 0,
        unavailable_fields=["shot_x", "shot_y", "under_pressure", "play_pattern"],
        validation=validation,
        warnings=warnings,
    )
    write_outputs(
        args.outdir,
        final_stats,
        raw_tables,
        matched_log,
        unmatched_roster,
        ambiguous,
        urls_used,
        urls_failed,
        missing_seasons,
        data_dictionary,
        report,
        shot_events,
        shot_availability,
        warnings,
    )

    print("", flush=True)
    print("FBref WC2026 scrape summary", flush=True)
    print("===========================", flush=True)
    print(f"Output directory: {args.outdir}", flush=True)
    print(f"Roster players: {report['number_of_roster_players']:,}", flush=True)
    print(f"Competition-season URLs attempted: {report['number_of_competition_season_urls_attempted']:,}", flush=True)
    print(f"Successful competition-season URLs: {report['number_of_successful_competition_season_urls']:,}", flush=True)
    print(f"Raw stat rows scraped: {report['number_of_raw_stat_rows_scraped']:,}", flush=True)
    print(f"Matched players: {report['number_of_matched_players']:,}", flush=True)
    print(f"Unmatched players: {report['number_of_unmatched_players']:,}", flush=True)
    print(f"Ambiguous matches: {report['number_of_ambiguous_matches']:,}", flush=True)
    if warnings:
        print("Warnings:", flush=True)
        for warning in warnings:
            print(f"- {warning}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
