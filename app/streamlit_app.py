from pathlib import Path
import sys

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.data.make_dataset import get_overall_date_range, summarize_world_cup_team_coverage
from src.data.squad_filter import load_world_cup_squads, teams_without_confirmed_squads
from src.data.world_cup_filter import filter_world_cup_teams, load_world_cup_teams


PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "all_shots_xg.csv"


@st.cache_data
def load_predictions(path: Path = PREDICTIONS_FILE) -> pd.DataFrame:
    """Load shot-level xG predictions for the dashboard."""
    predictions = pd.read_csv(path)
    return filter_world_cup_teams(predictions)


def show_sidebar() -> None:
    """Render project metadata in the sidebar."""
    st.sidebar.header("Project Info")
    st.sidebar.write("Model: XGBoost")
    st.sidebar.write("Experiment tracking: MLflow")
    st.sidebar.write("Dashboard: Streamlit")
    st.sidebar.write("Deployment target: Docker + AWS EC2")
    st.sidebar.caption(
        "Official squad filtering is enabled where final 26-player squad data is available."
    )


def show_headline_metrics(df: pd.DataFrame) -> None:
    """Render headline dashboard metrics."""
    total_shots = len(df)
    total_goals = int(df["actual_goal"].sum())
    total_xg = df["predicted_xg"].sum()
    avg_xg_per_shot = df["predicted_xg"].mean()
    total_teams = df["world_cup_team"].nunique()
    total_players = df["player"].nunique()

    row_one = st.columns(3)
    row_one[0].metric("Total Shots", f"{total_shots:,}")
    row_one[1].metric("Total Goals", f"{total_goals:,}")
    row_one[2].metric("Total xG", f"{total_xg:,.1f}")

    row_two = st.columns(3)
    row_two[0].metric("Average xG per Shot", f"{avg_xg_per_shot:.3f}")
    row_two[1].metric("Teams", f"{total_teams:,}")
    row_two[2].metric("Players", f"{total_players:,}")


def main() -> None:
    """Render the World Cup xG Lab home page."""
    st.set_page_config(
        page_title="World Cup xG Lab",
        page_icon="WC",
        layout="wide",
    )

    show_sidebar()

    st.title("World Cup xG Lab")
    st.write(
        "This dashboard uses a machine learning expected goals model to analyze "
        "shot quality, scoring zones, and player/team finishing performance."
    )
    st.info(
        "The dashboard is currently filtered to 2026 World Cup teams found in the "
        "available historical StatsBomb data and official squad players where final "
        "squad data is available."
    )
    st.caption(
        "This dashboard combines historical StatsBomb shot-location data with recent "
        "FBref player context. It shows where players have generated high-quality "
        "chances in available data, not guaranteed future scoring locations."
    )

    if not PREDICTIONS_FILE.exists():
        st.error(
            "Prediction file not found. Run `python src/models/predict.py` "
            "to create `data/predictions/all_shots_xg.csv`."
        )
        st.stop()

    predictions = load_predictions()
    show_headline_metrics(predictions)

    qualified_teams = load_world_cup_teams()
    squads = load_world_cup_squads()
    coverage = summarize_world_cup_team_coverage(predictions)
    found_teams = sorted(coverage["world_cup_team"].unique())
    missing_teams = sorted(set(qualified_teams) - set(found_teams))
    teams_missing_squads = teams_without_confirmed_squads(squads)
    earliest_date, latest_date = get_overall_date_range(predictions)

    st.divider()
    st.subheader("2026 World Cup Data Coverage")
    coverage_columns = st.columns(5)
    coverage_columns[0].metric("2026 Teams in Config", f"{len(qualified_teams):,}")
    coverage_columns[1].metric("Teams Found", f"{len(found_teams):,}")
    coverage_columns[2].metric("Teams Missing", f"{len(missing_teams):,}")
    coverage_columns[3].metric(
        "Teams Missing Final Squads",
        f"{len(teams_missing_squads):,}",
    )
    coverage_columns[4].metric("Date Range", f"{earliest_date} to {latest_date}")

    with st.expander("Missing teams from current dataset"):
        st.write(", ".join(missing_teams) if missing_teams else "No missing teams.")

    with st.expander("Teams without confirmed final squad data"):
        st.write(
            ", ".join(teams_missing_squads)
            if teams_missing_squads
            else "All teams have confirmed final squad data."
        )

    st.divider()
    st.subheader("How to Use This Dashboard")
    st.write(
        "Use the dashboard pages in the sidebar to explore team xG, player xG, "
        "goals minus xG, shot maps, scoring zones, and recent FBref shooting context."
    )
    st.caption(
        "Some players may not have FBref context if their league is unsupported or has not "
        "been pulled yet. Weak player-name matches are intentionally rejected."
    )


if __name__ == "__main__":
    main()
