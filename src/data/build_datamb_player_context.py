from __future__ import annotations

from pathlib import Path
import argparse
import json
import math
import sys

import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.data.player_matching import get_aliases_for_player, normalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQUADS_PATH = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "datamb" / "processed" / "datamb_player_context.csv"
MANUAL_OVERRIDES_PATH = PROJECT_ROOT / "data" / "datamb" / "manual" / "datamb_manual_overrides.csv"
REPORT_CSV_PATH = PROJECT_ROOT / "reports" / "datamb_coverage_report.csv"
SUMMARY_JSON_PATH = PROJECT_ROOT / "reports" / "datamb_coverage_summary.json"
DEFAULT_SEASON = "25/26"

LOCAL_INPUT_CANDIDATES = [
    PROJECT_ROOT / "data" / "datamb" / "raw" / "datamb_wc_2026_results.csv",
    PROJECT_ROOT / "data" / "datamb" / "raw" / "datamb_wc_2026_results.xlsx",
    Path.home()
    / "Downloads"
    / "datamb_scraper_starter"
    / "datamb_scraper_starter"
    / "outputs"
    / "datamb_25_26_full"
    / "datamb_wc_2026_results.csv",
    Path.home()
    / "Downloads"
    / "datamb_scraper_starter"
    / "datamb_scraper_starter"
    / "outputs"
    / "datamb_25_26_full"
    / "datamb_wc_2026_results.xlsx",
]

NON_PERCENTILE_COLUMNS = {
    "player",
    "team",
    "club",
    "club_team",
    "country",
    "nation",
    "national_team",
    "position",
    "template",
    "datamb_template",
    "season",
    "status",
    "source_url",
    "page_url",
    "screenshot_path",
    "raw_text_path",
    "network_json_path",
    "error",
    "generated_radar_path",
    "minutes",
}

SUCCESS_STATUSES = {"found", "success", "matched", "ok"}


def resolve_input_path(input_path: str | None = None) -> Path:
    """Find the DataMB scraper output file."""
    if input_path:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"DataMB input file not found: {path}")
        return path

    for candidate in LOCAL_INPUT_CANDIDATES:
        if candidate.exists():
            return candidate

    searched = "\n".join(str(path) for path in LOCAL_INPUT_CANDIDATES)
    raise FileNotFoundError(
        "DataMB scraper output was not found. Expected one of:\n"
        f"{searched}"
    )


def read_datamb_file(path: Path) -> pd.DataFrame:
    """Read a DataMB CSV/XLSX output file."""
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path, low_memory=False)


def read_manual_overrides() -> pd.DataFrame:
    """Read manually transcribed DataMB rows from screenshot evidence."""
    if not MANUAL_OVERRIDES_PATH.exists():
        return pd.DataFrame()
    manual = read_datamb_file(MANUAL_OVERRIDES_PATH)
    manual["manual_override"] = True
    if "status" not in manual.columns:
        manual["status"] = "found"
    manual["status"] = manual["status"].fillna("found")
    return manual


def read_squads() -> pd.DataFrame:
    """Read the confirmed World Cup squad table."""
    if not SQUADS_PATH.exists():
        raise FileNotFoundError(
            f"Squad file not found: {SQUADS_PATH}. "
            "Run the squad processing step first."
        )
    squads = pd.read_csv(SQUADS_PATH)
    if "player_normalized" not in squads.columns:
        squads["player_normalized"] = squads["player"].apply(normalize_name)
    if "team_normalized" not in squads.columns:
        squads["team_normalized"] = squads["world_cup_team"].apply(normalize_name)
    return squads


def is_success_status(value) -> bool:
    """Return whether a DataMB row should be considered usable."""
    return normalize_name(value) in SUCCESS_STATUSES


def numeric_or_none(value):
    """Convert values to float, keeping missing/unparseable values as None."""
    if value is None or pd.isna(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def parse_metrics(value) -> tuple[dict[str, float], float | None, list[str]]:
    """Parse DataMB metric JSON and separate minutes from percentile metrics."""
    warnings = []
    if value is None or pd.isna(value):
        return {}, None, ["missing metrics_json"]

    try:
        raw_metrics = json.loads(value) if isinstance(value, str) else dict(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}, None, ["invalid metrics_json"]

    percentiles = {}
    minutes = None
    for metric, raw_value in raw_metrics.items():
        metric_name = str(metric).strip()
        if normalize_name(metric_name) in NON_PERCENTILE_COLUMNS:
            if normalize_name(metric_name) == "minutes":
                minutes = numeric_or_none(raw_value)
            continue

        number = numeric_or_none(raw_value)
        if number is None:
            warnings.append(f"{metric_name}: non-numeric percentile")
            continue
        if number < 0 or number > 100:
            warnings.append(f"{metric_name}: clipped percentile from {number}")
            number = max(0.0, min(100.0, number))
        percentiles[metric_name] = round(float(number), 2)

    return percentiles, minutes, warnings


def template_position_score(template, position_group) -> int:
    """Score whether a DataMB template fits the squad position group."""
    template_norm = normalize_name(template)
    position_norm = normalize_name(position_group)

    if not template_norm or not position_norm:
        return 0
    if "goalkeeper" in position_norm or position_norm == "gk":
        return 2 if "keeper" in template_norm else 0
    if "defender" in position_norm:
        if "centreback" in template_norm or "centerback" in template_norm or "fullback" in template_norm:
            return 2
        return 1 if "back" in template_norm else 0
    if "midfielder" in position_norm:
        return 2 if "midfielder" in template_norm else 0
    if "forward" in position_norm:
        if "striker" in template_norm or "winger" in template_norm or "forward" in template_norm:
            return 2
        return 1 if "midfielder" in template_norm else 0
    return 0


def text_match_score(left, right) -> int:
    """Return a small score for exact or containment text matches."""
    left_norm = normalize_name(left)
    right_norm = normalize_name(right)
    if not left_norm or not right_norm:
        return 0
    if left_norm == right_norm:
        return 3
    if left_norm in right_norm or right_norm in left_norm:
        return 2
    return 0


def prepare_datamb_rows(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize DataMB rows and parse percentile JSON."""
    prepared = raw.copy()
    rename_map = {
        "team": "club_team",
        "club": "club_team",
        "country": "national_team",
        "nation": "national_team",
        "template": "datamb_template",
        "source_url": "page_url",
    }
    prepared = prepared.rename(
        columns={source: target for source, target in rename_map.items() if source in prepared.columns}
    )

    required_columns = ["player", "status", "metrics_json"]
    missing = [column for column in required_columns if column not in prepared.columns]
    if missing:
        raise ValueError(f"DataMB input is missing required columns: {', '.join(missing)}")

    for column in ["national_team", "club_team", "position", "league", "datamb_template", "page_url"]:
        if column not in prepared.columns:
            prepared[column] = None

    parsed = prepared["metrics_json"].apply(parse_metrics)
    prepared["percentiles_json"] = parsed.apply(lambda item: json.dumps(item[0], ensure_ascii=False))
    prepared["minutes"] = parsed.apply(lambda item: item[1])
    prepared["validation_warnings"] = parsed.apply(lambda item: "; ".join(item[2]))
    prepared["metric_count"] = parsed.apply(lambda item: len(item[0]))
    prepared["player_normalized"] = prepared["player"].apply(normalize_name)
    prepared["national_team_normalized"] = prepared["national_team"].apply(normalize_name)
    prepared["club_normalized"] = prepared["club_team"].apply(normalize_name)
    prepared["is_success"] = prepared["status"].apply(is_success_status)
    return prepared


def candidate_rows_for_player(squad_row: pd.Series, datamb: pd.DataFrame) -> pd.DataFrame:
    """Find DataMB candidates using player aliases, then prefer same national team."""
    aliases = {normalize_name(alias) for alias in get_aliases_for_player(squad_row["player"])}
    aliases.add(normalize_name(squad_row["player"]))
    candidates = datamb[
        datamb["is_success"] & datamb["player_normalized"].isin(aliases)
    ].copy()
    if candidates.empty:
        return candidates

    team_norm = normalize_name(squad_row["world_cup_team"])
    with_team = candidates[
        candidates["national_team_normalized"].isna()
        | (candidates["national_team_normalized"] == "")
        | (candidates["national_team_normalized"] == team_norm)
    ].copy()
    return with_team if not with_team.empty else candidates.iloc[0:0].copy()


def select_best_candidate(squad_row: pd.Series, candidates: pd.DataFrame) -> tuple[pd.Series | None, str, str]:
    """Select the safest DataMB candidate or flag an ambiguity."""
    if candidates.empty:
        return None, "unavailable", "No DataMB 25/26 public/free data found for this player."

    ranked = candidates.copy()
    ranked["_club_score"] = ranked["club_team"].apply(lambda value: text_match_score(squad_row.get("club"), value))
    ranked["_template_score"] = ranked["datamb_template"].apply(
        lambda value: template_position_score(value, squad_row.get("position_group"))
    )
    ranked["_minutes_sort"] = pd.to_numeric(ranked["minutes"], errors="coerce").fillna(-1)
    ranked["_score"] = ranked["_club_score"] * 10 + ranked["_template_score"] * 5
    ranked = ranked.sort_values(["_score", "_minutes_sort"], ascending=[False, False])

    best = ranked.iloc[0]
    ties = ranked[
        (ranked["_score"] == best["_score"])
        & (ranked["_minutes_sort"] == best["_minutes_sort"])
    ]
    if len(ties) > 1:
        return None, "ambiguous", "Multiple DataMB rows tied for this player; no row was guessed."

    confidence = "name+nation"
    if best["_club_score"] > 0:
        confidence += "+club"
    if best["_template_score"] > 0:
        confidence += "+template"
    return best, confidence, ""


def build_context_rows(squads: pd.DataFrame, datamb: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Build one DataMB context row per confirmed squad player."""
    rows = []
    ambiguous = []
    confirmed = squads[squads["squad_status"] == "confirmed"].copy()

    for _, squad_row in confirmed.sort_values(["world_cup_team", "player"]).iterrows():
        candidates = candidate_rows_for_player(squad_row, datamb)
        best, match_confidence, reason = select_best_candidate(squad_row, candidates)

        base = {
            "world_cup_team": squad_row.get("world_cup_team"),
            "player": squad_row.get("player"),
            "player_normalized": squad_row.get("player_normalized", normalize_name(squad_row.get("player"))),
            "position": squad_row.get("position"),
            "position_group": squad_row.get("position_group"),
            "club": squad_row.get("club"),
            "league": squad_row.get("league"),
            "season": DEFAULT_SEASON,
            "source": "DataMB",
        }

        if best is None:
            if match_confidence == "ambiguous":
                ambiguous.append(
                    {
                        "world_cup_team": squad_row.get("world_cup_team"),
                        "player": squad_row.get("player"),
                        "candidate_count": int(len(candidates)),
                    }
                )
            rows.append(
                {
                    **base,
                    "datamb_available": False,
                    "match_status": match_confidence,
                    "match_confidence": match_confidence,
                    "reason": reason,
                    "datamb_player": None,
                    "datamb_national_team": None,
                    "datamb_club": None,
                    "datamb_position": None,
                    "datamb_template": None,
                    "minutes": None,
                    "percentiles_json": "{}",
                    "metric_count": 0,
                    "source_url": None,
                    "screenshot_path": None,
                    "raw_text_path": None,
                    "generated_radar_path": None,
                    "validation_warnings": None,
                }
            )
            continue

        if int(best.get("metric_count") or 0) < 3:
            rows.append(
                {
                    **base,
                    "datamb_available": False,
                    "match_status": "unavailable",
                    "match_confidence": match_confidence,
                    "reason": "DataMB row found, but no usable percentile metrics were available.",
                    "datamb_player": best.get("player"),
                    "datamb_national_team": best.get("national_team"),
                    "datamb_club": best.get("club_team"),
                    "datamb_position": best.get("position"),
                    "datamb_template": best.get("datamb_template"),
                    "minutes": best.get("minutes"),
                    "percentiles_json": "{}",
                    "metric_count": int(best.get("metric_count") or 0),
                    "source_url": best.get("page_url"),
                    "screenshot_path": best.get("screenshot_path"),
                    "raw_text_path": best.get("raw_text_path"),
                    "generated_radar_path": None,
                    "validation_warnings": "insufficient usable percentile metrics",
                }
            )
            continue

        rows.append(
            {
                **base,
                "datamb_available": True,
                "match_status": "matched",
                "match_confidence": match_confidence,
                "reason": None,
                "datamb_player": best.get("player"),
                "datamb_national_team": best.get("national_team"),
                "datamb_club": best.get("club_team"),
                "datamb_position": best.get("position"),
                "datamb_template": best.get("datamb_template"),
                "minutes": best.get("minutes"),
                "percentiles_json": best.get("percentiles_json"),
                "metric_count": best.get("metric_count"),
                "source_url": best.get("page_url"),
                "screenshot_path": best.get("screenshot_path"),
                "raw_text_path": best.get("raw_text_path"),
                "generated_radar_path": None,
                "validation_warnings": best.get("validation_warnings"),
            }
        )

    return pd.DataFrame(rows), ambiguous


def coverage_by(df: pd.DataFrame, column: str) -> list[dict]:
    """Summarize DataMB coverage by one dimension."""
    if column not in df.columns:
        return []
    summary = (
        df.groupby(column, dropna=False)
        .agg(
            players=("player", "size"),
            datamb_available=("datamb_available", "sum"),
        )
        .reset_index()
    )
    summary["coverage_rate"] = summary["datamb_available"] / summary["players"]
    return summary.sort_values(["datamb_available", "players"], ascending=False).to_dict(orient="records")


def write_reports(context: pd.DataFrame, ambiguous: list[dict], raw: pd.DataFrame, input_path: Path) -> None:
    """Write CSV and JSON DataMB coverage reports."""
    REPORT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    context.to_csv(REPORT_CSV_PATH, index=False)

    total = int(len(context))
    available = int(context["datamb_available"].sum())
    raw_found = int(raw["is_success"].sum()) if "is_success" in raw.columns else None
    manual_series = raw["manual_override"] if "manual_override" in raw.columns else pd.Series(False, index=raw.index)
    manual_rows = int(manual_series.astype("boolean").fillna(False).sum())
    summary = {
        "source": "DataMB",
        "season": DEFAULT_SEASON,
        "input_path": str(input_path),
        "manual_overrides_path": str(MANUAL_OVERRIDES_PATH) if MANUAL_OVERRIDES_PATH.exists() else None,
        "total_confirmed_world_cup_players": total,
        "datamb_available_players": available,
        "datamb_missing_players": total - available,
        "coverage_rate": round(available / total, 4) if total else 0.0,
        "raw_rows": int(len(raw)),
        "raw_success_rows": raw_found,
        "manual_override_rows": manual_rows,
        "ambiguous_players": ambiguous,
        "coverage_by_national_team": coverage_by(context, "world_cup_team"),
        "coverage_by_position": coverage_by(context, "position_group"),
        "coverage_by_club": coverage_by(context, "club"),
        "coverage_by_league": coverage_by(context, "league"),
    }
    with SUMMARY_JSON_PATH.open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cleaned DataMB 25/26 player context.")
    parser.add_argument("--input", help="Optional path to datamb_wc_2026_results.csv/xlsx")
    args = parser.parse_args()

    input_path = resolve_input_path(args.input)
    scraper_raw = read_datamb_file(input_path)
    manual_overrides = read_manual_overrides()
    raw_input = pd.concat([scraper_raw, manual_overrides], ignore_index=True, sort=False)
    raw = prepare_datamb_rows(raw_input)
    squads = read_squads()
    context, ambiguous = build_context_rows(squads, raw)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    context.to_csv(OUTPUT_PATH, index=False)
    write_reports(context, ambiguous, raw, input_path)

    total = len(context)
    available = int(context["datamb_available"].sum())
    print(f"Read DataMB input: {input_path}")
    print(f"Manual override rows: {len(manual_overrides):,}")
    print(f"Saved cleaned DataMB context: {OUTPUT_PATH}")
    print(f"Confirmed squad players: {total:,}")
    print(f"DataMB 25/26 available: {available:,}")
    print(f"DataMB 25/26 missing: {total - available:,}")
    print(f"Ambiguous matches logged: {len(ambiguous):,}")
    print(f"Saved coverage CSV: {REPORT_CSV_PATH}")
    print(f"Saved coverage summary: {SUMMARY_JSON_PATH}")


if __name__ == "__main__":
    main()
