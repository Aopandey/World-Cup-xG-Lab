from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_XG_PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "all_shots_xg.csv"


def load_xg_predictions(path: str | Path = DEFAULT_XG_PREDICTIONS_FILE) -> pd.DataFrame:
    """Load shot-level xG predictions for dashboard use."""
    predictions_path = Path(path)

    if not predictions_path.is_absolute():
        predictions_path = PROJECT_ROOT / predictions_path

    if not predictions_path.exists():
        raise FileNotFoundError(
            f"xG predictions file not found: {predictions_path}. "
            "Run python src/models/predict.py first."
        )

    return pd.read_csv(predictions_path)


def summarize_team_xg(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize shots, goals, and xG by team."""
    summary = (
        df.groupby("team", dropna=False)
        .agg(
            shots=("predicted_xg", "size"),
            goals=("actual_goal", "sum"),
            total_xg=("predicted_xg", "sum"),
        )
        .reset_index()
    )

    summary["goals_minus_xg"] = summary["goals"] - summary["total_xg"]
    summary["avg_xg_per_shot"] = summary["total_xg"] / summary["shots"]

    return summary.sort_values("total_xg", ascending=False).reset_index(drop=True)


def summarize_player_xg(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize shots, goals, and xG by player and team."""
    summary = (
        df.groupby(["player", "team"], dropna=False)
        .agg(
            shots=("predicted_xg", "size"),
            goals=("actual_goal", "sum"),
            total_xg=("predicted_xg", "sum"),
        )
        .reset_index()
    )

    summary["goals_minus_xg"] = summary["goals"] - summary["total_xg"]
    summary["avg_xg_per_shot"] = summary["total_xg"] / summary["shots"]

    return summary.sort_values("total_xg", ascending=False).reset_index(drop=True)


def filter_by_team(df: pd.DataFrame, team: str) -> pd.DataFrame:
    """Return shots for one team."""
    return df[df["team"] == team].copy()


def filter_by_player(df: pd.DataFrame, player: str) -> pd.DataFrame:
    """Return shots for one player."""
    return df[df["player"] == player].copy()
