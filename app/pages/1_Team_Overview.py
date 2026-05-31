from pathlib import Path
import sys

import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.data.make_dataset import (
    filter_by_team,
    load_xg_predictions,
    summarize_world_cup_team_coverage,
    summarize_player_xg,
    summarize_team_xg,
)
from src.data.world_cup_filter import filter_world_cup_teams
from src.visualization.shot_maps import plot_shot_map


@st.cache_data
def load_dashboard_data():
    """Load shot-level xG predictions."""
    return filter_world_cup_teams(load_xg_predictions())


def format_player_table(player_summary):
    """Return a display-friendly player summary table."""
    display_columns = [
        "player",
        "shots",
        "goals",
        "total_xg",
        "goals_minus_xg",
        "avg_xg_per_shot",
    ]

    return player_summary[display_columns].round(
        {
            "total_xg": 2,
            "goals_minus_xg": 2,
            "avg_xg_per_shot": 3,
        }
    )


def main() -> None:
    """Render the Team Overview dashboard page."""
    st.set_page_config(page_title="Team Overview", layout="wide")

    st.title("Team Overview")
    st.write("Explore a team's shot volume, expected goals, finishing performance, and shot locations.")
    st.info(
        "Showing only 2026 World Cup teams found in the available historical data. "
        "Final 26-player squad filtering will be added after official squads are announced."
    )

    try:
        predictions = load_dashboard_data()
    except FileNotFoundError as error:
        st.error(str(error))
        st.stop()

    teams = sorted(predictions["world_cup_team"].dropna().unique())
    selected_team = st.selectbox("Select a team", teams)

    team_shots = filter_by_team(predictions, selected_team, team_col="world_cup_team")
    team_summary = summarize_team_xg(team_shots, team_col="world_cup_team").iloc[0]
    team_coverage = summarize_world_cup_team_coverage(team_shots).iloc[0]

    st.subheader("Sample Coverage")
    coverage_columns = st.columns(4)
    coverage_columns[0].metric("Matches in Sample", f"{int(team_coverage['matches']):,}")
    coverage_columns[1].metric("Shots in Sample", f"{int(team_coverage['shots']):,}")
    coverage_columns[2].metric(
        "Date Range",
        f"{team_coverage['earliest_match_date']} to {team_coverage['latest_match_date']}",
    )
    coverage_columns[3].metric("Goals in Sample", f"{int(team_coverage['goals']):,}")

    st.caption(f"Competitions included: {team_coverage['competitions_included']}")

    if int(team_coverage["shots"]) < 50:
        st.warning("Small sample size: interpret this team's xG profile carefully.")

    metric_columns = st.columns(5)
    metric_columns[0].metric("Shots", f"{int(team_summary['shots']):,}")
    metric_columns[1].metric("Goals", f"{int(team_summary['goals']):,}")
    metric_columns[2].metric("Total xG", f"{team_summary['total_xg']:,.2f}")
    metric_columns[3].metric("Goals minus xG", f"{team_summary['goals_minus_xg']:,.2f}")
    metric_columns[4].metric("Avg xG per Shot", f"{team_summary['avg_xg_per_shot']:.3f}")

    st.divider()

    st.subheader(f"Top Players: {selected_team}")
    player_summary = summarize_player_xg(team_shots, team_col="world_cup_team")
    player_table = format_player_table(player_summary)
    st.dataframe(player_table.head(25), use_container_width=True, hide_index=True)

    top_players = player_summary.head(10).sort_values("total_xg", ascending=True)
    bar_chart = px.bar(
        top_players,
        x="total_xg",
        y="player",
        orientation="h",
        title="Top 10 Players by Total xG",
        labels={"total_xg": "Total xG", "player": "Player"},
        text=top_players["total_xg"].round(1),
    )
    bar_chart.update_layout(height=420, margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(bar_chart, use_container_width=True)

    st.divider()

    st.subheader(f"Shot Map: {selected_team}")
    shot_map_data = team_shots.rename(columns={"actual_goal": "is_goal"})
    fig, _ = plot_shot_map(shot_map_data, title=f"{selected_team} Shot Map")
    st.pyplot(fig, clear_figure=True)


if __name__ == "__main__":
    main()
