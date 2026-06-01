from pathlib import Path
import re
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from src.data.player_matching import normalize_name
from src.data.world_cup_filter import build_team_alias_lookup, load_world_cup_teams


DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "squads" / "2026_world_cup_squads_espn_updated.xlsx"
PROCESSED_DIR = PROJECT_ROOT / "data" / "squads" / "processed"
OUTPUT_PATH = PROCESSED_DIR / "world_cup_2026_squads.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "world_cup_squad_coverage.txt"
DATA_SOURCE = "ESPN squad workbook"

POSITION_GROUP_MAP = {
    "goalkeeper": "Goalkeeper",
    "goalkeepers": "Goalkeeper",
    "gk": "Goalkeeper",
    "defender": "Defender",
    "defenders": "Defender",
    "df": "Defender",
    "midfielder": "Midfielder",
    "midfielders": "Midfielder",
    "mf": "Midfielder",
    "forward": "Forward",
    "forwards": "Forward",
    "striker": "Forward",
    "strikers": "Forward",
    "fw": "Forward",
}


def resolve_input_file() -> Path:
    """Find the squad workbook in the expected project locations."""
    if DEFAULT_INPUT_PATH.exists():
        return DEFAULT_INPUT_PATH

    candidate_dirs = [PROJECT_ROOT / "data" / "squads", PROJECT_ROOT]
    for candidate_dir in candidate_dirs:
        if not candidate_dir.exists():
            continue
        matches = sorted(candidate_dir.glob("*squad*.xlsx"))
        if matches:
            return matches[0]

    raise FileNotFoundError(
        "Could not find the squad Excel file. Expected "
        f"{DEFAULT_INPUT_PATH} or a similar .xlsx file in data/squads/ or the project root."
    )


def normalize_column(column: str) -> str:
    """Normalize workbook column names for flexible parsing."""
    normalized = normalize_name(column)
    normalized = normalized.replace(" ", "_")
    return normalized


def canonical_team_name(team_name: str, alias_lookup: dict[str, str]) -> str:
    """Normalize workbook team names to configured 2026 World Cup team names."""
    normalized = " ".join(str(team_name).strip().casefold().split())
    manual_aliases = {
        "bosnia-herzegovina": "Bosnia and Herzegovina",
        "bosnia herzegovina": "Bosnia and Herzegovina",
        "cape verde": "Cabo Verde",
        "curacao": "Curaçao",
        "congo dr": "DR Congo",
        "cote d ivoire": "Ivory Coast",
        "turkey": "Türkiye",
        "turkiye": "Türkiye",
    }

    return alias_lookup.get(normalized) or manual_aliases.get(normalized) or str(team_name).strip()


def map_position_group(value) -> str:
    """Map workbook positions into dashboard position groups."""
    normalized = normalize_name(value)
    return POSITION_GROUP_MAP.get(normalized, "Unknown")


def is_confirmed_status(status: str, team_count: int) -> bool:
    """Identify teams with usable official 26-player squad data."""
    status_normalized = normalize_name(status)
    if "preliminary" in status_normalized or "provisional" in status_normalized:
        return False
    if team_count != 26:
        return False
    return "announced" in status_normalized or "final" in status_normalized or "roster" in status_normalized


def read_workbook(path: Path) -> dict[str, pd.DataFrame]:
    """Read all workbook sheets for inspection and parsing."""
    excel = pd.ExcelFile(path)
    sheets = {}
    print(f"Reading squad workbook: {path}")
    print(f"Workbook sheets: {excel.sheet_names}")

    for sheet_name in excel.sheet_names:
        sheets[sheet_name] = pd.read_excel(path, sheet_name=sheet_name)
        print(f"Loaded sheet {sheet_name}: {sheets[sheet_name].shape}")

    return sheets


def parse_player_details(player_details: pd.DataFrame) -> pd.DataFrame:
    """Parse the normalized Player Details sheet."""
    df = player_details.copy()
    df.columns = [normalize_column(column) for column in df.columns]

    column_map = {
        "team": "world_cup_team_raw",
        "player": "player",
        "position_group": "position_group_raw",
        "club": "club",
        "league_competition": "league",
        "squad_status": "raw_squad_status",
    }
    available_map = {source: target for source, target in column_map.items() if source in df.columns}
    parsed = df.rename(columns=available_map)

    required = ["world_cup_team_raw", "player"]
    missing = [column for column in required if column not in parsed.columns]
    if missing:
        raise ValueError(f"Player Details sheet is missing required columns: {missing}")

    for optional_column in ["position_group_raw", "club", "league", "raw_squad_status"]:
        if optional_column not in parsed.columns:
            parsed[optional_column] = pd.NA

    parsed = parsed[parsed["player"].notna()].copy()
    parsed["position_group"] = parsed["position_group_raw"].apply(map_position_group)
    parsed["position"] = parsed["position_group"]
    return parsed


def split_grouped_players(value) -> list[tuple[str, str | None]]:
    """Split grouped team-summary cells like 'Player (Club), Player (Club)'."""
    if pd.isna(value):
        return []

    entries = []
    for raw_entry in re.split(r",\s*(?=[^()]*(?:\(|$))", str(value)):
        entry = raw_entry.strip()
        if not entry:
            continue

        match = re.match(r"^(.*?)\s*\((.*?)\)\s*$", entry)
        if match:
            entries.append((match.group(1).strip(), match.group(2).strip()))
        else:
            entries.append((entry, None))

    return entries


def parse_team_summary(team_summary: pd.DataFrame) -> pd.DataFrame:
    """Fallback parser for grouped squad columns."""
    df = team_summary.copy()
    df.columns = [normalize_column(column) for column in df.columns]
    records = []
    grouped_columns = {
        "goalkeepers": "Goalkeeper",
        "defenders": "Defender",
        "midfielders": "Midfielder",
        "forwards": "Forward",
        "strikers": "Forward",
    }

    for _, row in df.iterrows():
        team = row.get("team")
        raw_status = row.get("squad_status", pd.NA)
        leagues = row.get("unique_leagues_competitions", pd.NA)

        for column, position_group in grouped_columns.items():
            if column not in df.columns:
                continue

            for player, club in split_grouped_players(row[column]):
                records.append(
                    {
                        "world_cup_team_raw": team,
                        "player": player,
                        "position": position_group,
                        "position_group": position_group,
                        "club": club,
                        "league": leagues,
                        "raw_squad_status": raw_status,
                    }
                )

    return pd.DataFrame(records)


def build_clean_squad_table(sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Normalize workbook data to one row per player."""
    if "Player Details" in sheets:
        parsed = parse_player_details(sheets["Player Details"])
    elif "Team Summary" in sheets:
        parsed = parse_team_summary(sheets["Team Summary"])
    else:
        raise ValueError("Workbook must contain either Player Details or Team Summary.")

    alias_lookup = build_team_alias_lookup()
    parsed["world_cup_team"] = parsed["world_cup_team_raw"].apply(
        lambda team: canonical_team_name(team, alias_lookup)
    )
    parsed["player_normalized"] = parsed["player"].apply(normalize_name)
    parsed["team_normalized"] = parsed["world_cup_team"].apply(normalize_name)

    team_counts = parsed.groupby("world_cup_team")["player"].transform("count")
    parsed["squad_status"] = [
        "confirmed" if is_confirmed_status(status, int(count)) else "not_announced"
        for status, count in zip(parsed["raw_squad_status"], team_counts)
    ]
    parsed["data_source"] = DATA_SOURCE

    output_columns = [
        "world_cup_team",
        "player",
        "position",
        "position_group",
        "club",
        "league",
        "squad_status",
        "data_source",
        "player_normalized",
        "team_normalized",
        "raw_squad_status",
    ]

    return parsed[output_columns].sort_values(
        ["world_cup_team", "position_group", "player"],
    ).reset_index(drop=True)


def build_report(cleaned: pd.DataFrame) -> str:
    """Build a text coverage report for the squad file."""
    qualified_teams = set(load_world_cup_teams())
    teams_in_file = set(cleaned["world_cup_team"].dropna().unique())
    missing_teams = sorted(qualified_teams - teams_in_file)
    confirmed = cleaned[cleaned["squad_status"] == "confirmed"]
    players_per_team = cleaned.groupby("world_cup_team").size().sort_index()
    fewer_than_26 = players_per_team[players_per_team < 26]
    more_than_26 = players_per_team[players_per_team > 26]
    missing_final = sorted(
        cleaned.loc[cleaned["squad_status"] != "confirmed", "world_cup_team"].dropna().unique()
    )
    duplicates = cleaned[
        cleaned.duplicated(subset=["world_cup_team", "player_normalized"], keep=False)
    ].sort_values(["world_cup_team", "player"])

    lines = [
        "2026 World Cup Squad Coverage",
        "==============================",
        f"Number of teams in squad file: {len(teams_in_file)}",
        f"Number of confirmed players: {len(confirmed)}",
        "",
        "Players per team:",
        players_per_team.to_string(),
        "",
        "Teams with fewer than 26 players:",
        fewer_than_26.to_string() if not fewer_than_26.empty else "None",
        "",
        "Teams with more than 26 players:",
        more_than_26.to_string() if not more_than_26.empty else "None",
        "",
        "Teams missing final squads:",
        ", ".join(sorted(set(missing_teams) | set(missing_final))) or "None",
        "",
        "Duplicate player names within the same team:",
        (
            duplicates[["world_cup_team", "player", "position_group", "club"]].to_string(index=False)
            if not duplicates.empty
            else "None"
        ),
        "",
        "Top leagues represented:",
        cleaned["league"].dropna().value_counts().head(20).to_string(),
        "",
        "Top clubs represented:",
        cleaned["club"].dropna().value_counts().head(20).to_string(),
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    """Ingest the World Cup squad workbook."""
    input_path = resolve_input_file()
    sheets = read_workbook(input_path)
    cleaned = build_clean_squad_table(sheets)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(OUTPUT_PATH, index=False)

    report = build_report(cleaned)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("")
    print(f"Saved clean squad table to: {OUTPUT_PATH}")
    print(f"Rows: {len(cleaned):,}")
    print(f"Confirmed players: {(cleaned['squad_status'] == 'confirmed').sum():,}")
    print(f"Teams: {cleaned['world_cup_team'].nunique():,}")
    print(f"Saved report to: {REPORT_PATH}")
    print("")
    print(report)


if __name__ == "__main__":
    main()
