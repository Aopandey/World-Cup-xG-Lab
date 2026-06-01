from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FBREF_CONTEXT_PATH = PROJECT_ROOT / "data" / "fbref" / "processed" / "fbref_player_context.csv"
sys.path.append(str(PROJECT_ROOT))

from src.data.make_dataset import get_overall_date_range, load_xg_predictions
from src.data.player_matching import (
    MATCH_NONE,
    get_aliases_for_player,
    match_player_to_fbref,
    normalize_name,
)
from src.data.squad_filter import load_world_cup_squads, teams_with_confirmed_squads
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


@st.cache_data
def load_squad_data():
    """Load official squad data when available."""
    return load_world_cup_squads()


def position_options():
    """Return dashboard position group options."""
    return ["All", "Goalkeeper", "Defender", "Midfielder", "Forward", "Attacking players only"]


def filter_squad_by_position_group(squad_df, selected_position_group):
    """Filter squad metadata by dashboard position group."""
    if squad_df.empty or selected_position_group == "All":
        return squad_df

    if selected_position_group == "Attacking players only":
        return squad_df[squad_df["position_group"].isin(["Midfielder", "Forward"])].copy()

    return squad_df[squad_df["position_group"] == selected_position_group].copy()


def player_options_for_team(predictions, squads, selected_team, selected_position_group):
    """Use official squad players when confirmed squad data exists for a team."""
    confirmed_teams = teams_with_confirmed_squads(squads)

    if selected_team in confirmed_teams:
        team_squad = squads[
            (squads["world_cup_team"] == selected_team)
            & (squads["squad_status"] == "confirmed")
        ].copy()
        team_squad = filter_squad_by_position_group(team_squad, selected_position_group)
        return sorted(team_squad["player"].dropna().unique()), True

    team_shots = predictions[predictions["world_cup_team"] == selected_team]
    return sorted(team_shots["player"].dropna().unique()), False


def get_squad_row(squads, selected_team, selected_player):
    """Return exact normalized squad row for selected player/team."""
    if squads.empty:
        return None

    selected_normalized = normalize_name(selected_player)
    matches = squads[
        (squads["world_cup_team"] == selected_team)
        & (squads["player_normalized"] == selected_normalized)
    ]

    if matches.empty:
        return None

    return matches.iloc[0]


def find_statsbomb_shots(predictions, selected_team, selected_player, squad_row=None):
    """Find historical StatsBomb rows using exact/alias normalized names only."""
    team_shots = predictions[predictions["world_cup_team"] == selected_team].copy()
    player_names = set(get_aliases_for_player(selected_player))
    player_names.add(selected_player)

    if squad_row is not None:
        player_names.add(squad_row["player"])

    normalized_names = {normalize_name(name) for name in player_names if name}
    team_shots["_player_normalized"] = team_shots["player"].apply(normalize_name)
    matched = team_shots[team_shots["_player_normalized"].isin(normalized_names)].copy()
    return matched.drop(columns=["_player_normalized"])


def summarize_player_shots(player_shots):
    """Summarize a selected player's historical StatsBomb xG profile."""
    shots = len(player_shots)
    goals = int(player_shots["actual_goal"].sum()) if shots else 0
    total_xg = float(player_shots["predicted_xg"].sum()) if shots else 0.0
    avg_xg = float(player_shots["predicted_xg"].mean()) if shots else 0.0

    return {
        "shots": shots,
        "goals": goals,
        "total_xg": total_xg,
        "goals_minus_xg": goals - total_xg,
        "avg_xg_per_shot": avg_xg,
    }


def summarize_category_xg(player_shots, category_column):
    """Summarize total xG by a categorical shot field."""
    return (
        player_shots.groupby(category_column, dropna=False)
        .agg(shots=("predicted_xg", "size"), total_xg=("predicted_xg", "sum"))
        .reset_index()
        .sort_values("total_xg", ascending=False)
    )


def render_squad_metadata(squad_row, selected_team):
    """Render squad metadata for the selected player."""
    st.subheader("Squad Metadata")

    if squad_row is None:
        st.warning("Official squad data is not available for this team yet.")
        st.write(f"Team: {selected_team}")
        return

    metadata_columns = st.columns(5)
    metadata_columns[0].metric("World Cup Team", squad_row["world_cup_team"])
    metadata_columns[1].metric("Position", squad_row["position"])
    metadata_columns[2].metric("Position Group", squad_row["position_group"])
    metadata_columns[3].metric("Club", squad_row["club"])
    metadata_columns[4].metric("League", squad_row["league"])


def render_fbref_context(fbref_context, selected_player, selected_position, squad_row=None):
    """Render recent/current FBref shooting context for the selected player."""
    st.subheader("Recent Club/League Shooting Context from FBref")
    st.write(
        "StatsBomb data powers the historical shot-map and xG model views. "
        "FBref adds recent player shooting context where available, especially when "
        "the historical shot sample is small."
    )

    match = match_player_to_fbref(
        selected_player,
        fbref_context,
        selected_position=selected_position,
    )
    fbref_rows = match["rows"]

    if match["confidence"] == MATCH_NONE or fbref_rows.empty:
        st.info("No reliable FBref match found for this player yet.")
        if squad_row is not None:
            st.write(
                f"Squad club/league: {squad_row['club']} / {squad_row['league']}"
            )
        st.caption(
            "FBref context is unavailable for this player with the currently "
            "supported/pulled leagues."
        )
        return

    st.caption(f"FBref match confidence: {match['confidence']}")

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
    fbref_display = fbref_rows[available_columns].rename(columns=column_labels)

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


def render_statsbomb_sections(selected_player, player_shots):
    """Render historical StatsBomb charts/tables when shots are available."""
    if player_shots.empty:
        st.info("No historical StatsBomb shot sample found for this player in the current data.")
        return

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


def main() -> None:
    """Render the Player Profile dashboard page."""
    st.set_page_config(page_title="Player Profile", layout="wide")

    st.title("Player Profile")
    st.write("Explore a player's shot quality, finishing performance, and recent shooting context.")
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
    fbref_context = load_fbref_player_context()
    teams = sorted(predictions["world_cup_team"].dropna().unique())

    filter_columns = st.columns(3)
    selected_team = filter_columns[0].selectbox("Select a team", teams)
    selected_position_group = filter_columns[1].selectbox(
        "Position group",
        position_options(),
        index=5,
    )
    players, using_squad_players = player_options_for_team(
        predictions,
        squads,
        selected_team,
        selected_position_group,
    )

    if not players:
        st.warning("No players found for the selected team and position filter.")
        st.stop()

    selected_player = filter_columns[2].selectbox("Select a player", players)
    squad_row = get_squad_row(squads, selected_team, selected_player) if using_squad_players else None

    if not using_squad_players:
        st.warning("Official squad data is not available for this team yet.")

    render_squad_metadata(squad_row, selected_team)

    player_shots = find_statsbomb_shots(predictions, selected_team, selected_player, squad_row)
    player_summary = summarize_player_shots(player_shots)
    earliest_date, latest_date = get_overall_date_range(player_shots)

    st.subheader("Historical StatsBomb xG Sample")
    coverage_columns = st.columns(3)
    coverage_columns[0].metric("Shots in Sample", f"{player_summary['shots']:,}")
    coverage_columns[1].metric("Team", selected_team)
    coverage_columns[2].metric("Date Range", f"{earliest_date} to {latest_date}")

    metric_columns = st.columns(5)
    metric_columns[0].metric("Goals", f"{player_summary['goals']:,}")
    metric_columns[1].metric("Total xG", f"{player_summary['total_xg']:,.2f}")
    metric_columns[2].metric("Goals minus xG", f"{player_summary['goals_minus_xg']:,.2f}")
    metric_columns[3].metric("Avg xG per Shot", f"{player_summary['avg_xg_per_shot']:.3f}")
    metric_columns[4].metric("Shots", f"{player_summary['shots']:,}")

    st.info(
        "Positive goals minus xG means the player finished above expected based on shot quality. "
        "Negative means they scored fewer than expected."
    )

    if player_summary["shots"] < 20:
        st.warning(
            "Small historical shot sample. Use FBref recent context to supplement this profile."
        )

    selected_position = squad_row["position_group"] if squad_row is not None else None
    render_fbref_context(fbref_context, selected_player, selected_position, squad_row)
    render_statsbomb_sections(selected_player, player_shots)


if __name__ == "__main__":
    main()
