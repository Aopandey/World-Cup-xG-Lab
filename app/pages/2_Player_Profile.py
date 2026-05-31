from pathlib import Path
import sys

import plotly.express as px
import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FBREF_CONTEXT_PATH = PROJECT_ROOT / "data" / "fbref" / "processed" / "fbref_player_context.csv"
sys.path.append(str(PROJECT_ROOT))

from src.data.make_dataset import (
    filter_by_player,
    get_overall_date_range,
    load_xg_predictions,
    summarize_player_xg,
)
from src.data.world_cup_filter import filter_world_cup_teams
from src.visualization.shot_maps import plot_shot_map


@st.cache_data
def load_dashboard_data():
    """Load shot-level xG predictions."""
    return filter_world_cup_teams(load_xg_predictions())


@st.cache_data
def load_fbref_player_context():
    """Load cleaned FBref player context when it has been generated."""
    if not FBREF_CONTEXT_PATH.exists():
        return pd.DataFrame()

    return pd.read_csv(FBREF_CONTEXT_PATH)


def normalize_player_name(player_name):
    """Normalize player names for simple case-insensitive matching."""
    if pd.isna(player_name):
        return ""

    return " ".join(str(player_name).casefold().split())


def find_fbref_player_rows(fbref_context, selected_player):
    """Find FBref rows by exact player name first, then simple contains matching."""
    if fbref_context.empty or "player" not in fbref_context.columns:
        return pd.DataFrame()

    selected_normalized = normalize_player_name(selected_player)
    fbref_data = fbref_context.copy()
    fbref_data["_player_normalized"] = fbref_data["player"].apply(normalize_player_name)

    exact_matches = fbref_data[fbref_data["_player_normalized"] == selected_normalized]
    if not exact_matches.empty:
        return exact_matches.drop(columns=["_player_normalized"])

    fuzzy_matches = fbref_data[
        fbref_data["_player_normalized"].apply(
            lambda name: bool(name)
            and (selected_normalized in name or name in selected_normalized)
        )
    ]

    return fuzzy_matches.drop(columns=["_player_normalized"])


def sort_fbref_context(fbref_rows):
    """Show the most recent FBref seasons first."""
    sorted_rows = fbref_rows.copy()
    sorted_rows["_season_sort"] = pd.to_numeric(sorted_rows["season"], errors="coerce")
    sorted_rows = sorted_rows.sort_values(
        ["_season_sort", "league", "team"],
        ascending=[False, True, True],
        na_position="last",
    )

    return sorted_rows.drop(columns=["_season_sort"])


def render_fbref_context(fbref_context, selected_player):
    """Render recent/current FBref shooting context for the selected player."""
    st.subheader("Recent Club/League Shooting Context from FBref")
    st.write(
        "StatsBomb data powers the historical shot-map and xG model views. "
        "FBref adds recent player shooting context where available, especially when "
        "the historical shot sample is small."
    )

    fbref_rows = find_fbref_player_rows(fbref_context, selected_player)

    if fbref_rows.empty:
        st.info("No FBref current/recent shooting context found for this player yet.")
        return

    display_columns = [
        "season",
        "league",
        "team",
        "pos",
        "minutes",
        "goals",
        "assists",
        "shots",
        "shots_on_target",
        "shots_per_90",
        "xg",
        "npxg",
        "xg_per_90",
    ]
    available_columns = [
        column
        for column in display_columns
        if column in fbref_rows.columns and not fbref_rows[column].isna().all()
    ]
    column_labels = {
        "pos": "position",
        "shots_on_target": "shots on target",
        "shots_per_90": "shots per 90",
        "xg": "xG",
        "npxg": "npxG",
        "xg_per_90": "xG per 90",
    }
    fbref_display = sort_fbref_context(fbref_rows)[available_columns].rename(
        columns=column_labels
    )

    st.dataframe(
        fbref_display.round(
            {
                "minutes": 0,
                "goals": 0,
                "assists": 0,
                "shots": 0,
                "shots on target": 0,
                "shots per 90": 2,
                "xG": 2,
                "npxG": 2,
                "xG per 90": 2,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def summarize_category_xg(player_shots, category_column):
    """Summarize total xG by a categorical shot field."""
    return (
        player_shots.groupby(category_column, dropna=False)
        .agg(shots=("predicted_xg", "size"), total_xg=("predicted_xg", "sum"))
        .reset_index()
        .sort_values("total_xg", ascending=False)
    )


def main() -> None:
    """Render the Player Profile dashboard page."""
    st.set_page_config(page_title="Player Profile", layout="wide")

    st.title("Player Profile")
    st.write("Explore a player's shot quality, finishing performance, and xG sources.")
    st.info(
        "Showing players from 2026 World Cup teams found in the available historical data. "
        "Final 26-player squad filtering will be added after official squads are announced."
    )

    try:
        predictions = load_dashboard_data()
    except FileNotFoundError as error:
        st.error(str(error))
        st.stop()

    fbref_context = load_fbref_player_context()

    players = sorted(predictions["player"].dropna().unique())
    selected_player = st.selectbox("Select a player", players)

    player_shots = filter_by_player(predictions, selected_player)
    player_summary = summarize_player_xg(player_shots, team_col="world_cup_team").iloc[0]
    teams = ", ".join(sorted(player_shots["world_cup_team"].dropna().unique()))
    earliest_date, latest_date = get_overall_date_range(player_shots)

    st.subheader("Sample Coverage")
    coverage_columns = st.columns(3)
    coverage_columns[0].metric("Shots in Sample", f"{len(player_shots):,}")
    coverage_columns[1].metric("Team", teams)
    coverage_columns[2].metric("Date Range", f"{earliest_date} to {latest_date}")

    metric_columns = st.columns(6)
    metric_columns[0].metric("Team", teams)
    metric_columns[1].metric("Shots", f"{int(player_summary['shots']):,}")
    metric_columns[2].metric("Goals", f"{int(player_summary['goals']):,}")
    metric_columns[3].metric("Total xG", f"{player_summary['total_xg']:,.2f}")
    metric_columns[4].metric("Goals minus xG", f"{player_summary['goals_minus_xg']:,.2f}")
    metric_columns[5].metric("Avg xG per Shot", f"{player_summary['avg_xg_per_shot']:.3f}")

    st.info(
        "Positive goals minus xG means the player finished above expected based on shot quality. "
        "Negative means they scored fewer than expected."
    )

    if len(player_shots) < 20:
        st.warning(
            "Small StatsBomb shot sample: use the FBref context below to better understand "
            "recent player form."
        )

    render_fbref_context(fbref_context, selected_player)

    st.divider()

    st.subheader(f"Shot Map: {selected_player}")
    shot_map_data = player_shots.rename(columns={"actual_goal": "is_goal"})
    fig, _ = plot_shot_map(shot_map_data, title=f"{selected_player} Shot Map")
    st.pyplot(fig, clear_figure=True)

    st.divider()

    chart_columns = st.columns(3)

    body_part_xg = summarize_category_xg(player_shots, "body_part")
    body_part_chart = px.bar(
        body_part_xg,
        x="body_part",
        y="total_xg",
        title="xG by Body Part",
        labels={"body_part": "Body Part", "total_xg": "Total xG"},
    )
    chart_columns[0].plotly_chart(body_part_chart, use_container_width=True)

    play_pattern_xg = summarize_category_xg(player_shots, "play_pattern").head(10)
    play_pattern_chart = px.bar(
        play_pattern_xg,
        x="total_xg",
        y="play_pattern",
        orientation="h",
        title="xG by Play Pattern",
        labels={"play_pattern": "Play Pattern", "total_xg": "Total xG"},
    )
    play_pattern_chart.update_layout(yaxis={"categoryorder": "total ascending"})
    chart_columns[1].plotly_chart(play_pattern_chart, use_container_width=True)

    outcome_data = player_shots.assign(
        result=player_shots["actual_goal"].map({True: "Goal", False: "Non-goal"})
    )
    outcome_chart = px.histogram(
        outcome_data,
        x="result",
        title="Goal vs Non-goal Shots",
        labels={"result": "Result", "count": "Shots"},
    )
    chart_columns[2].plotly_chart(outcome_chart, use_container_width=True)

    st.divider()

    st.subheader("Shot Table")
    shot_columns = [
        "minute",
        "team",
        "shot_outcome",
        "predicted_xg",
        "body_part",
        "play_pattern",
    ]
    shot_table = player_shots.copy()
    shot_table["team"] = shot_table["world_cup_team"]
    st.dataframe(
        shot_table[shot_columns].sort_values("predicted_xg", ascending=False).round(
            {"predicted_xg": 3}
        ),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
