from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.data.data_confidence import calculate_team_data_confidence
from src.data.make_dataset import load_xg_predictions
from src.data.squad_filter import filter_to_squad_players, load_world_cup_squads
from src.data.squad_filter import teams_with_confirmed_squads
from src.data.world_cup_filter import filter_world_cup_teams
from src.visualization.pitch import draw_pitch


@st.cache_data
def load_dashboard_data():
    """Load shot-level xG predictions."""
    predictions = filter_world_cup_teams(load_xg_predictions())
    return filter_to_squad_players(predictions)


@st.cache_data
def load_squad_data():
    """Load official squad data when available."""
    return load_world_cup_squads()


def option_list(values):
    """Create a dropdown option list with an All option."""
    return ["All"] + sorted(values.dropna().astype(str).unique())


def position_options():
    """Return dashboard position group options."""
    return ["All", "Goalkeeper", "Defender", "Midfielder", "Forward", "Attacking players only"]


def apply_position_group_filter(df, selected_position_group):
    """Filter squad-enriched shot data by position group."""
    if selected_position_group == "All" or "squad_position_group" not in df.columns:
        return df

    if selected_position_group == "Attacking players only":
        return df[df["squad_position_group"].isin(["Midfielder", "Forward"])].copy()

    return df[df["squad_position_group"] == selected_position_group].copy()


def apply_filters(df, team, player, position_group, body_part, play_pattern):
    """Apply selected dashboard filters."""
    filtered = df.copy()

    if team != "All":
        filtered = filtered[filtered["world_cup_team"] == team]

    if player != "All":
        filtered = filtered[filtered["player"] == player]

    filtered = apply_position_group_filter(filtered, position_group)

    if body_part != "All":
        filtered = filtered[filtered["body_part"] == body_part]

    if play_pattern != "All":
        filtered = filtered[filtered["play_pattern"] == play_pattern]

    return filtered


def should_show_sample_warning(filtered_shots, selected_team, selected_player, selected_position_group):
    """Return whether selected filters create a weak scoring-zone sample."""
    shot_count = len(filtered_shots)

    if selected_player != "All":
        return shot_count < 20

    team_or_position_filtered = selected_team != "All" or selected_position_group != "All"
    return team_or_position_filtered and shot_count < 100


def plot_xg_heatmap(df):
    """Plot a pitch heatmap weighted by predicted xG."""
    fig, ax = plt.subplots(figsize=(12, 8))
    draw_pitch(ax)

    plot_data = df.dropna(subset=["shot_x", "shot_y", "predicted_xg"])

    if plot_data.empty:
        ax.set_title("No shots available for selected filters")
        return fig

    heatmap = ax.hist2d(
        plot_data["shot_x"],
        plot_data["shot_y"],
        bins=[24, 16],
        range=[[0, 120], [0, 80]],
        weights=plot_data["predicted_xg"],
        cmap="YlOrRd",
        alpha=0.75,
    )
    fig.colorbar(heatmap[3], ax=ax, fraction=0.035, pad=0.02, label="Total xG")
    ax.set_title("xG Heatmap")

    return fig


def plot_sized_shot_map(df):
    """Plot a shot map with point size based on predicted xG."""
    fig, ax = plt.subplots(figsize=(12, 8))
    draw_pitch(ax)

    plot_data = df.dropna(subset=["shot_x", "shot_y", "predicted_xg"])

    if plot_data.empty:
        ax.set_title("No shots available for selected filters")
        return fig

    sizes = 30 + (plot_data["predicted_xg"] * 420)
    colors = plot_data["actual_goal"].map({True: "#d62728", False: "#2f6fbb"})

    ax.scatter(
        plot_data["shot_x"],
        plot_data["shot_y"],
        s=sizes,
        c=colors,
        alpha=0.45,
        edgecolors="#ffffff",
        linewidths=0.5,
    )
    ax.set_title("Shot Map Sized by Predicted xG")

    return fig


def main() -> None:
    """Render the Scoring Zones dashboard page."""
    st.set_page_config(page_title="Scoring Zones", layout="wide")

    st.title("Scoring Zones")
    st.write(
        "Scoring zones show where the model believes shots had the highest "
        "probability of becoming goals."
    )
    st.info(
        "This dashboard combines historical StatsBomb shot-location data with recent "
        "FBref player context. It shows where players have generated high-quality chances "
        "in available data, not guaranteed future scoring locations."
    )

    try:
        predictions = load_dashboard_data()
    except FileNotFoundError as error:
        st.error(str(error))
        st.stop()

    squads = load_squad_data()
    confirmed_squad_teams = teams_with_confirmed_squads(squads)

    filter_columns = st.columns(5)
    selected_team = filter_columns[0].selectbox("Team", option_list(predictions["world_cup_team"]))
    selected_position_group = filter_columns[1].selectbox(
        "Position Group",
        position_options(),
        index=5,
    )

    player_pool = predictions.copy()
    if selected_team != "All":
        player_pool = player_pool[player_pool["world_cup_team"] == selected_team]
        if not squads.empty and selected_team in set(
            squads.loc[squads["squad_status"] == "not_announced", "world_cup_team"]
        ):
            st.warning("Official squad data is not available for this team yet.")

    player_pool = apply_position_group_filter(player_pool, selected_position_group)
    selected_player = filter_columns[2].selectbox("Player", option_list(player_pool["player"]))
    selected_body_part = filter_columns[3].selectbox(
        "Body Part",
        option_list(predictions["body_part"]),
    )
    selected_play_pattern = filter_columns[4].selectbox(
        "Play Pattern",
        option_list(predictions["play_pattern"]),
    )

    filtered_shots = apply_filters(
        predictions,
        selected_team,
        selected_player,
        selected_position_group,
        selected_body_part,
        selected_play_pattern,
    )

    st.caption(f"Showing {len(filtered_shots):,} shots for the selected filters.")

    if selected_team != "All":
        selected_team_shots = predictions[predictions["world_cup_team"] == selected_team]
        data_confidence = calculate_team_data_confidence(
            len(selected_team_shots),
            selected_team in confirmed_squad_teams,
            0.0,
        )
        st.metric("Team Data Confidence", data_confidence)

    if should_show_sample_warning(
        filtered_shots,
        selected_team,
        selected_player,
        selected_position_group,
    ):
        st.warning("Small sample size: scoring-zone patterns may not be reliable.")

    chart_columns = st.columns(2)
    chart_columns[0].pyplot(plot_xg_heatmap(filtered_shots), clear_figure=True)
    chart_columns[1].pyplot(plot_sized_shot_map(filtered_shots), clear_figure=True)

    st.divider()
    st.subheader("Top 10 Highest-xG Shots")

    table_columns = [
        "player",
        "team",
        "minute",
        "predicted_xg",
        "shot_outcome",
        "body_part",
        "play_pattern",
    ]
    table_data = filtered_shots.copy()
    table_data["team"] = table_data["world_cup_team"]
    top_shots = (
        table_data[table_columns]
        .sort_values("predicted_xg", ascending=False)
        .head(10)
        .round({"predicted_xg": 3})
    )

    st.dataframe(top_shots, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
