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


def summarize_team_xg(df: pd.DataFrame, team_col: str = "team") -> pd.DataFrame:
    """Summarize shots, goals, and xG by team."""
    if team_col not in df.columns:
        raise ValueError(f"Team column not found: {team_col}")

    summary = (
        df.groupby(team_col, dropna=False)
        .agg(
            shots=("predicted_xg", "size"),
            goals=("actual_goal", "sum"),
            total_xg=("predicted_xg", "sum"),
        )
        .reset_index()
    )

    summary["goals_minus_xg"] = summary["goals"] - summary["total_xg"]
    summary["avg_xg_per_shot"] = summary["total_xg"] / summary["shots"]

    return summary.rename(columns={team_col: "team"}).sort_values(
        "total_xg",
        ascending=False,
    ).reset_index(drop=True)


def summarize_player_xg(df: pd.DataFrame, team_col: str = "team") -> pd.DataFrame:
    """Summarize shots, goals, and xG by player and team."""
    if team_col not in df.columns:
        raise ValueError(f"Team column not found: {team_col}")

    summary = (
        df.groupby(["player", team_col], dropna=False)
        .agg(
            shots=("predicted_xg", "size"),
            goals=("actual_goal", "sum"),
            total_xg=("predicted_xg", "sum"),
        )
        .reset_index()
    )

    summary["goals_minus_xg"] = summary["goals"] - summary["total_xg"]
    summary["avg_xg_per_shot"] = summary["total_xg"] / summary["shots"]

    return summary.rename(columns={team_col: "team"}).sort_values(
        "total_xg",
        ascending=False,
    ).reset_index(drop=True)


def filter_by_team(df: pd.DataFrame, team: str, team_col: str = "team") -> pd.DataFrame:
    """Return shots for one team."""
    if team_col not in df.columns:
        raise ValueError(f"Team column not found: {team_col}")

    return df[df[team_col] == team].copy()


def filter_by_player(df: pd.DataFrame, player: str) -> pd.DataFrame:
    """Return shots for one player."""
    return df[df["player"] == player].copy()


def summarize_world_cup_team_coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize sample coverage for each normalized World Cup team."""
    if "world_cup_team" not in df.columns:
        raise ValueError("world_cup_team column not found.")

    coverage = (
        df.groupby("world_cup_team", dropna=False)
        .agg(
            shots=("predicted_xg", "size"),
            goals=("actual_goal", "sum"),
            matches=("match_id", "nunique") if "match_id" in df.columns else ("predicted_xg", "size"),
            earliest_match_date=("match_date", "min") if "match_date" in df.columns else ("predicted_xg", lambda _: pd.NA),
            latest_match_date=("match_date", "max") if "match_date" in df.columns else ("predicted_xg", lambda _: pd.NA),
            competitions_included=("competition_name", lambda values: ", ".join(sorted(values.dropna().astype(str).unique()))) if "competition_name" in df.columns else ("predicted_xg", lambda _: "Unknown"),
        )
        .reset_index()
    )

    coverage["goals"] = coverage["goals"].astype(int)

    return coverage.sort_values("world_cup_team").reset_index(drop=True)


def get_overall_date_range(df: pd.DataFrame) -> tuple[str, str]:
    """Return earliest and latest match dates when available."""
    if "match_date" not in df.columns:
        return "Unknown", "Unknown"

    dates = pd.to_datetime(df["match_date"], errors="coerce")
    if not dates.notna().any():
        return "Unknown", "Unknown"

    return str(dates.min().date()), str(dates.max().date())
