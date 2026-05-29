from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "all_shots_xg.csv"


@st.cache_data
def load_predictions(path: Path = PREDICTIONS_FILE) -> pd.DataFrame:
    """Load shot-level xG predictions for the dashboard."""
    return pd.read_csv(path)


def show_sidebar() -> None:
    """Render project metadata in the sidebar."""
    st.sidebar.header("Project Info")
    st.sidebar.write("Model: XGBoost")
    st.sidebar.write("Experiment tracking: MLflow")
    st.sidebar.write("Dashboard: Streamlit")
    st.sidebar.write("Deployment target: Docker + AWS EC2")


def show_headline_metrics(df: pd.DataFrame) -> None:
    """Render headline dashboard metrics."""
    total_shots = len(df)
    total_goals = int(df["actual_goal"].sum())
    total_xg = df["predicted_xg"].sum()
    avg_xg_per_shot = df["predicted_xg"].mean()
    total_teams = df["team"].nunique()
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

    if not PREDICTIONS_FILE.exists():
        st.error(
            "Prediction file not found. Run `python src/models/predict.py` "
            "to create `data/predictions/all_shots_xg.csv`."
        )
        st.stop()

    predictions = load_predictions()
    show_headline_metrics(predictions)

    st.divider()
    st.subheader("How to Use This Dashboard")
    st.write(
        "Use the dashboard pages in the sidebar to explore team xG, player xG, "
        "goals minus xG, shot maps, and scoring zones."
    )


if __name__ == "__main__":
    main()
