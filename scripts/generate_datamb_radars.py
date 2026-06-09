from __future__ import annotations

from pathlib import Path
import json
import math
import re
import sys
import textwrap
import unicodedata

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


CONTEXT_PATH = PROJECT_ROOT / "data" / "datamb" / "processed" / "datamb_player_context.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "generated" / "datamb_radars"
STATIC_URL_PREFIX = "/static/generated/datamb-radars"


def safe_slug(value: str) -> str:
    """Create a filesystem-safe ASCII slug."""
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = re.sub(r"[^A-Za-z0-9]+", "_", ascii_text)
    return ascii_text.strip("_") or "unknown"


def parse_percentiles(value) -> dict[str, float]:
    """Parse cleaned percentile JSON."""
    if value is None or pd.isna(value):
        return {}
    try:
        raw = json.loads(value) if isinstance(value, str) else dict(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}

    parsed = {}
    for metric, raw_value in raw.items():
        try:
            number = float(raw_value)
        except (TypeError, ValueError):
            continue
        if math.isnan(number):
            continue
        parsed[str(metric)] = max(0.0, min(100.0, number))
    return parsed


def radar_filename(row: pd.Series) -> str:
    """Build a stable filename for one player/template radar."""
    player = safe_slug(row.get("player", "player"))
    template = safe_slug(row.get("datamb_template", "datamb"))
    return f"{player}_{template}_datamb_25_26.png"


def wrap_label(label: str) -> str:
    """Wrap long radar labels without changing the metric text."""
    return "\n".join(textwrap.wrap(label, width=12, break_long_words=False))


def plot_radar(row: pd.Series, percentiles: dict[str, float], output_path: Path) -> None:
    """Generate a single-player DataMB-style percentile radar."""
    metrics = list(percentiles.keys())
    values = [percentiles[metric] for metric in metrics]
    count = len(metrics)
    angles = [2 * math.pi * index / count for index in range(count)]
    closed_angles = angles + angles[:1]
    closed_values = values + values[:1]

    fig = plt.figure(figsize=(7.2, 7.2), facecolor="#07181f")
    ax = fig.add_subplot(111, polar=True)
    fig.subplots_adjust(top=0.78, bottom=0.08, left=0.08, right=0.92)
    ax.set_facecolor("#0b222d")
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 100)

    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], color="#9cc7d8", fontsize=8)
    ax.yaxis.grid(True, color="#69b7ff", alpha=0.28, linewidth=1.0)
    ax.xaxis.grid(True, color="#d9fff0", alpha=0.18, linewidth=0.8)
    ax.spines["polar"].set_color("#69b7ff")
    ax.spines["polar"].set_linewidth(1.2)

    ax.set_xticks(angles)
    ax.set_xticklabels([wrap_label(metric) for metric in metrics], fontsize=9, color="#e5f3ff")
    ax.tick_params(axis="x", pad=16)

    blue = "#7c8cff"
    ax.plot(closed_angles, closed_values, color=blue, linewidth=2.4)
    ax.fill(closed_angles, closed_values, color=blue, alpha=0.24)
    ax.scatter(angles, values, s=44, color=blue, edgecolors="#e5f3ff", linewidths=1.1, zorder=3)

    template = str(row.get("datamb_template") or "DataMB")
    club = str(row.get("datamb_club") or row.get("club") or "Club unknown")
    player = str(row.get("player") or "Player")
    title = f"{player} - Percentile profile"
    fig.suptitle(title, y=0.97, fontsize=14, fontweight="bold", color="#ffffff")
    fig.text(
        0.5,
        0.925,
        f"DataMB 25/26 | {club} | {template.title()} | Percentiles, not raw stats",
        ha="center",
        fontsize=9.5,
        color="#9cc7d8",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor="#07181f")
    plt.close(fig)


def main() -> None:
    if not CONTEXT_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned DataMB context not found: {CONTEXT_PATH}. "
            "Run python src/data/build_datamb_player_context.py first."
        )

    context = pd.read_csv(CONTEXT_PATH, low_memory=False)
    if "generated_radar_path" not in context.columns:
        context["generated_radar_path"] = None
    context["generated_radar_path"] = context["generated_radar_path"].astype("object")

    generated = 0
    skipped = 0
    for index, row in context.iterrows():
        if str(row.get("datamb_available")).strip().casefold() not in {"true", "1", "yes"}:
            continue

        percentiles = parse_percentiles(row.get("percentiles_json"))
        if len(percentiles) < 3:
            skipped += 1
            continue

        filename = radar_filename(row)
        output_path = OUTPUT_DIR / filename
        plot_radar(row, percentiles, output_path)
        context.at[index, "generated_radar_path"] = f"{STATIC_URL_PREFIX}/{filename}"
        generated += 1

    context.to_csv(CONTEXT_PATH, index=False)
    print(f"Generated DataMB radar charts: {generated:,}")
    print(f"Skipped available rows with fewer than 3 metrics: {skipped:,}")
    print(f"Radar directory: {OUTPUT_DIR}")
    print(f"Updated context file: {CONTEXT_PATH}")


if __name__ == "__main__":
    main()
