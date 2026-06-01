from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.data.player_matching import MATCH_NONE, match_player_to_fbref


SQUAD_PATH = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
FBREF_CONTEXT_PATH = PROJECT_ROOT / "data" / "fbref" / "processed" / "fbref_player_context.csv"
DETAILED_OUTPUT_PATH = PROJECT_ROOT / "reports" / "missing_fbref_players_detailed.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "missing_fbref_players_audit.txt"

ATTACKING_POSITION_GROUPS = {"Midfielder", "Forward"}


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load confirmed squad players and cleaned FBref context."""
    if not SQUAD_PATH.exists():
        raise FileNotFoundError(
            f"Squad file not found: {SQUAD_PATH}. "
            "Run python src/data/ingest_world_cup_squads.py first."
        )

    if not FBREF_CONTEXT_PATH.exists():
        raise FileNotFoundError(
            f"FBref context file not found: {FBREF_CONTEXT_PATH}. "
            "Run python src/data/build_fbref_player_context.py first."
        )

    squads = pd.read_csv(SQUAD_PATH)
    fbref = pd.read_csv(FBREF_CONTEXT_PATH)
    confirmed_squads = squads[squads["squad_status"] == "confirmed"].copy()
    return confirmed_squads, fbref


def audit_missing_players(
    squad_df: pd.DataFrame,
    fbref_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Identify squad players without a reliable FBref match."""
    missing_records = []
    matched_records = []

    for _, row in squad_df.iterrows():
        selected_position = row.get("position_group")
        match = match_player_to_fbref(
            row["player"],
            fbref_df,
            selected_team=row.get("world_cup_team"),
            selected_position=selected_position,
        )

        record = {
            "world_cup_team": row.get("world_cup_team"),
            "player": row.get("player"),
            "position": row.get("position"),
            "position_group": row.get("position_group"),
            "club": row.get("club"),
            "league": row.get("league"),
        }

        if match["confidence"] == MATCH_NONE or match["rows"].empty:
            record["reason_missing"] = (
                "No reliable FBref match in currently supported/pulled leagues"
            )
            missing_records.append(record)
        else:
            record["match_confidence"] = match["confidence"]
            record["matched_fbref_player"] = match["matched_player"]
            matched_records.append(record)

    return pd.DataFrame(missing_records), pd.DataFrame(matched_records)


def top_counts(df: pd.DataFrame, column: str, n: int = 20) -> pd.Series:
    """Return top value counts for a column."""
    if df.empty or column not in df.columns:
        return pd.Series(dtype=int)

    return df[column].fillna("Unknown").value_counts().head(n)


def recommend_leagues(missing_attackers: pd.DataFrame, n: int = 10) -> list[str]:
    """Recommend the highest-impact leagues based on missing midfielders/forwards."""
    if missing_attackers.empty:
        return []

    excluded = {"Unknown / verify manually", "Unknown"}
    counts = top_counts(missing_attackers, "league", n=50)
    return [league for league in counts.index if league not in excluded][:n]


def build_report(
    squad_df: pd.DataFrame,
    missing: pd.DataFrame,
    matched: pd.DataFrame,
) -> str:
    """Create a text report from audit outputs."""
    missing_attackers = missing[
        missing["position_group"].isin(ATTACKING_POSITION_GROUPS)
    ].copy()
    recommended = recommend_leagues(missing_attackers)

    sections = [
        "Missing FBref Squad-Player Audit",
        "=================================",
        f"Total confirmed squad players: {len(squad_df):,}",
        f"Total matched in FBref: {len(matched):,}",
        f"Total missing from FBref: {len(missing):,}",
        f"Missing attackers/midfielders count: {len(missing_attackers):,}",
        "",
        "Missing players by world_cup_team:",
        top_counts(missing, "world_cup_team", n=60).to_string() if not missing.empty else "None",
        "",
        "Missing players by position_group:",
        top_counts(missing, "position_group").to_string() if not missing.empty else "None",
        "",
        "Top 20 missing leagues by player count:",
        top_counts(missing, "league").to_string() if not missing.empty else "None",
        "",
        "Top 20 missing leagues by forward/midfielder count:",
        top_counts(missing_attackers, "league").to_string()
        if not missing_attackers.empty
        else "None",
        "",
        "Top 20 missing clubs by player count:",
        top_counts(missing, "club").to_string() if not missing.empty else "None",
        "",
        "Top 20 missing clubs by forward/midfielder count:",
        top_counts(missing_attackers, "club").to_string()
        if not missing_attackers.empty
        else "None",
        "",
        "Recommended leagues to try next based on missing forward/midfielder counts:",
        "\n".join(f"- {league}" for league in recommended) if recommended else "None",
        "",
    ]

    return "\n".join(sections)


def main() -> None:
    """Run the missing FBref player audit."""
    squad_df, fbref_df = load_inputs()
    missing, matched = audit_missing_players(squad_df, fbref_df)

    DETAILED_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    missing.to_csv(DETAILED_OUTPUT_PATH, index=False)

    report = build_report(squad_df, missing, matched)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(report)
    print(f"Saved detailed missing-player CSV to: {DETAILED_OUTPUT_PATH}")
    print(f"Saved audit report to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
