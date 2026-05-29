from pathlib import Path
import sys

import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.data.make_dataset import (
    filter_by_player,
    load_xg_predictions,
    summarize_player_xg,
)
from src.visualization.shot_maps import plot_shot_map


@st.cache_data
def load_dashboard_data():
    """Load shot-level xG predictions."""
    return load_xg_predictions()


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

    try:
        predictions = load_dashboard_data()
    except FileNotFoundError as error:
        st.error(str(error))
        st.stop()

    players = sorted(predictions["player"].dropna().unique())
    selected_player = st.selectbox("Select a player", players)

    player_shots = filter_by_player(predictions, selected_player)
    player_summary = summarize_player_xg(player_shots).iloc[0]
    teams = ", ".join(sorted(player_shots["team"].dropna().unique()))

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
    st.dataframe(
        player_shots[shot_columns].sort_values("predicted_xg", ascending=False).round(
            {"predicted_xg": 3}
        ),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
