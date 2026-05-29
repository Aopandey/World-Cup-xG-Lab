from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.visualization.pitch import draw_pitch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SHOTS_FILE = PROJECT_ROOT / "data" / "processed" / "shots.csv"
DEFAULT_FIGURE_FILE = PROJECT_ROOT / "reports" / "figures" / "basic_shot_map.png"


def _validate_shot_columns(df: pd.DataFrame) -> None:
    missing_columns = [column for column in ["shot_x", "shot_y"] if column not in df.columns]

    if missing_columns:
        raise ValueError(
            "Shot map requires shot location columns. "
            f"Missing columns: {', '.join(missing_columns)}"
        )


def plot_shot_map(df: pd.DataFrame, title: str | None = None, save_path: str | Path | None = None):
    """Plot shot locations on a StatsBomb-coordinate football pitch."""
    _validate_shot_columns(df)

    plot_data = df.dropna(subset=["shot_x", "shot_y"]).copy()

    fig, ax = plt.subplots(figsize=(12, 8))
    draw_pitch(ax)

    if "is_goal" in plot_data.columns:
        goals = plot_data[plot_data["is_goal"].astype(bool)]
        non_goals = plot_data[~plot_data["is_goal"].astype(bool)]

        ax.scatter(
            non_goals["shot_x"],
            non_goals["shot_y"],
            s=18,
            alpha=0.35,
            color="#2f6fbb",
            label="Non-goal shots",
        )
        ax.scatter(
            goals["shot_x"],
            goals["shot_y"],
            s=46,
            alpha=0.85,
            color="#d62728",
            edgecolors="#ffffff",
            linewidths=0.6,
            label="Goals",
        )
        ax.legend(loc="upper left", frameon=False)
    else:
        print("WARNING: is_goal column is missing. Plotting all shots with one marker style.")
        ax.scatter(
            plot_data["shot_x"],
            plot_data["shot_y"],
            s=18,
            alpha=0.35,
            color="#2f6fbb",
            label="Shots",
        )

    if title:
        ax.set_title(title, fontsize=16, pad=12)

    if save_path:
        output_path = Path(save_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight")

    return fig, ax


if __name__ == "__main__":
    shots = pd.read_csv(DEFAULT_SHOTS_FILE)
    plot_shot_map(
        shots,
        title="Basic Shot Map",
        save_path=DEFAULT_FIGURE_FILE,
    )
    print(f"Saved shot map to {DEFAULT_FIGURE_FILE}")
