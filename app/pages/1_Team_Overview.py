from pathlib import Path
import sys

import plotly.express as px
import pandas as pd
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
from src.data.squad_filter import (
    filter_to_squad_players,
    load_world_cup_squads,
    teams_with_confirmed_squads,
)
from src.data.world_cup_filter import filter_world_cup_teams
from src.visualization.shot_maps import plot_shot_map


@st.cache_data
def load_dashboard_data():
    """Load shot-level xG predictions."""
    return filter_world_cup_teams(load_xg_predictions())


@st.cache_data
def load_squad_data():
    """Load official squad data when available."""
    return load_world_cup_squads()


def position_options():
    """Return dashboard position group options."""
    return ["All", "Goalkeeper", "Defender", "Midfielder", "Forward", "Attacking players only"]


def apply_position_group_filter(df, selected_position_group):
    """Filter enriched shot data by squad position group."""
    if selected_position_group == "All" or "squad_position_group" not in df.columns:
        return df

    if selected_position_group == "Attacking players only":
        return df[df["squad_position_group"].isin(["Midfielder", "Forward"])].copy()

    return df[df["squad_position_group"] == selected_position_group].copy()


def format_player_table(player_summary):
    """Return a display-friendly player summary table."""
    display_columns = [
        "player",
        "position_group",
        "shots",
        "goals",
        "total_xg",
        "goals_minus_xg",
        "avg_xg_per_shot",
    ]

    available_columns = [column for column in display_columns if column in player_summary.columns]

    return player_summary[available_columns].round(
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

    squads = load_squad_data()
    confirmed_squad_teams = teams_with_confirmed_squads(squads)

    teams = sorted(predictions["world_cup_team"].dropna().unique())
    filter_columns = st.columns(2)
    selected_team = filter_columns[0].selectbox("Select a team", teams)
    selected_position_group = filter_columns[1].selectbox(
        "Position group",
        position_options(),
    )

    team_shots_all = filter_by_team(predictions, selected_team, team_col="world_cup_team")
    if selected_team in confirmed_squad_teams:
        team_shots = filter_to_squad_players(team_shots_all)
        st.caption("Showing official squad players with matching historical StatsBomb shots.")
    else:
        team_shots = team_shots_all.copy()
        st.warning("Official squad data is not available for this team yet.")

    team_shots = apply_position_group_filter(team_shots, selected_position_group)

    if team_shots.empty:
        st.warning("No historical StatsBomb shots found for the selected squad/position filter.")
        st.stop()

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
    if "squad_position_group" in team_shots.columns:
        position_lookup = (
            team_shots[["player", "squad_position_group"]]
            .dropna()
            .drop_duplicates(subset=["player"])
            .rename(columns={"squad_position_group": "position_group"})
        )
        player_summary = player_summary.merge(position_lookup, on="player", how="left")
    else:
        player_summary["position_group"] = pd.NA

    player_table = format_player_table(player_summary)
    st.dataframe(player_table.head(25), use_container_width=True, hide_index=True)

    if selected_team in confirmed_squad_teams and not squads.empty:
        with st.expander("Official squad list for selected position filter"):
            squad_table = squads[
                (squads["world_cup_team"] == selected_team)
                & (squads["squad_status"] == "confirmed")
            ].copy()
            if selected_position_group == "Attacking players only":
                squad_table = squad_table[
                    squad_table["position_group"].isin(["Midfielder", "Forward"])
                ]
            elif selected_position_group != "All":
                squad_table = squad_table[
                    squad_table["position_group"] == selected_position_group
                ]

            st.dataframe(
                squad_table[["player", "position_group", "club", "league"]],
                use_container_width=True,
                hide_index=True,
            )

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
