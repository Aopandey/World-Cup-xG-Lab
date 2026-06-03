from __future__ import annotations

from pathlib import Path
import re
import sys
import unicodedata

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.data.ingest_world_cup_squads import build_report
from src.data.player_matching import normalize_name
from src.data.world_cup_filter import load_world_cup_teams


INPUT_TEXT_PATH = PROJECT_ROOT / "data" / "squads" / "manual" / "final_squads_2026_text.txt"
SQUADS_PATH = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
ARTIFACT_SQUAD_PATH = PROJECT_ROOT / "data" / "dashboard_artifacts" / "squad_players.json"
CHANGE_REPORT_PATH = PROJECT_ROOT / "reports" / "final_squad_update_report.txt"
SQUAD_COVERAGE_REPORT_PATH = PROJECT_ROOT / "reports" / "world_cup_squad_coverage.txt"

DATA_SOURCE = "User final squad text"
RAW_STATUS = "Final squad text update"
UNKNOWN = "Unknown / verify manually"

TEAM_ALIASES = {
    "Bosnia": "Bosnia and Herzegovina",
    "Cape Verde": "Cabo Verde",
    "Curacao": "Curaçao",
    "Czech Republic": "Czechia",
    "Turkey": "Türkiye",
    "USA": "United States",
}

POSITION_LABELS = {
    "Goalkeepers": "Goalkeeper",
    "Defenders": "Defender",
    "Midfielders": "Midfielder",
    "Forwards": "Forward",
}

CLUB_LEAGUE_OVERRIDES = {
    "AC Milan": "Serie A",
    "Ajax": "Eredivisie / Dutch football league system",
    "Al Ahli": "Saudi Pro League",
    "Al-Ahli": "Saudi Pro League",
    "Al-Hilal": "Saudi Pro League",
    "Al Hilal": "Saudi Pro League",
    "Al Nassr": "Saudi Pro League",
    "Al-Nassr": "Saudi Pro League",
    "Arsenal": "Premier League",
    "Aston Villa": "Premier League",
    "Atalanta": "Serie A",
    "Atletico Madrid": "LaLiga",
    "Barcelona": "LaLiga",
    "Bayer Leverkusen": "Bundesliga",
    "Bayern Munich": "Bundesliga",
    "Benfica": "Primeira Liga",
    "Borussia Dortmund": "Bundesliga",
    "Brighton": "Premier League",
    "Brighton and Hove Albion": "Premier League",
    "Burnley": "Premier League",
    "Chelsea": "Premier League",
    "Crystal Palace": "Premier League",
    "Eintracht Frankfurt": "Bundesliga",
    "Everton": "Premier League",
    "Fenerbahce": "Turkish Süper Lig",
    "Fulham": "Premier League",
    "Galatasaray": "Turkish Süper Lig",
    "Inter Milan": "Serie A",
    "Juventus": "Serie A",
    "Leeds United": "English football league system",
    "Liverpool": "Premier League",
    "Lyon": "Ligue 1 / French football league system",
    "Manchester City": "Premier League",
    "Manchester United": "Premier League",
    "Marseille": "Ligue 1 / French football league system",
    "Monaco": "Ligue 1 / French football league system",
    "Napoli": "Serie A",
    "Newcastle": "Premier League",
    "Newcastle United": "Premier League",
    "Nice": "Ligue 1 / French football league system",
    "Nottingham Forest": "Premier League",
    "Paris St-Germain": "Ligue 1 / French football league system",
    "Paris Saint-Germain": "Ligue 1 / French football league system",
    "Porto": "Primeira Liga",
    "PSV Eindhoven": "Eredivisie / Dutch football league system",
    "RB Leipzig": "Bundesliga",
    "Real Betis": "LaLiga",
    "Real Madrid": "LaLiga",
    "Real Sociedad": "LaLiga",
    "Roma": "Serie A",
    "Sassuolo": "Serie A",
    "Sevilla": "LaLiga",
    "Sporting": "Primeira Liga",
    "Sporting CP": "Primeira Liga",
    "Tottenham": "Premier League",
    "Tottenham Hotspur": "Premier League",
    "Villarreal": "LaLiga",
    "West Ham": "Premier League",
    "West Ham United": "Premier League",
    "Wolves": "Premier League",
    "Wolverhampton": "Premier League",
    "Wolverhampton Wanderers": "Premier League",
}


def clean_text(value: str) -> str:
    """Normalize pasted text without removing meaningful accents."""
    cleaned = unicodedata.normalize("NFKC", str(value))
    cleaned = "".join(
        character
        for character in cleaned
        if unicodedata.category(character) != "Cf"
    )
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" .;")


def canonical_team(raw_team: str) -> str:
    """Map pasted team headers to dashboard canonical team names."""
    team = clean_text(raw_team)
    team = re.sub(r"['’]s\b", "", team)
    team = team.replace(" final", "")
    team = team.replace("World Cup squad", "")
    team = team.replace("squad for 2026 World Cup", "")
    team = team.replace("squad for World Cup", "")
    team = team.replace("squad in full:", "")
    team = team.replace("in full:", "")
    team = clean_text(team)
    return TEAM_ALIASES.get(team, team)


def is_team_header(line: str) -> bool:
    """Return whether a line starts a team squad section."""
    markers = [
        "World Cup squad",
        "squad in full:",
        "final World Cup squad",
        "squad for World Cup",
        "squad for 2026 World Cup",
        "in full:",
    ]
    return any(marker in line for marker in markers)


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split the pasted final-squad text into team sections."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    sections: list[tuple[str, list[str]]] = []
    current_team = None
    current_lines: list[str] = []

    for raw_line in lines:
        line = clean_text(raw_line)
        if not line:
            continue

        if is_team_header(line):
            if current_team and current_lines:
                sections.append((current_team, current_lines))
            current_team = canonical_team(line)
            current_lines = []
            continue

        if current_team:
            current_lines.append(line)

    if current_team and current_lines:
        sections.append((current_team, current_lines))

    return [(team, "\n".join(body_lines)) for team, body_lines in sections]


def split_entries(value: str) -> list[str]:
    """Split comma-separated player entries while preserving commas inside parentheses."""
    entries = []
    current = []
    depth = 0

    for char in value:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)

        if char == "," and depth == 0:
            entry = clean_text("".join(current))
            if entry:
                entries.append(entry)
            current = []
        else:
            current.append(char)

    final_entry = clean_text("".join(current))
    if final_entry:
        entries.append(final_entry)

    return entries


def clean_club(value: str | None) -> str | None:
    """Clean club text from parenthesized squad entries."""
    if not value:
        return None

    club = clean_text(value)
    club = re.sub(r"^(both|all)\s+", "", club, flags=re.IGNORECASE)
    club = re.split(r",\s*on loan from\s+", club, flags=re.IGNORECASE)[0]
    return clean_text(club)


def parse_player_entry(entry: str) -> tuple[str, str | None, bool]:
    """Parse one player entry into player, club, and backfill flag."""
    match = re.match(r"^(.*?)\s*\((.*?)\)\s*$", entry)
    if not match:
        return clean_text(entry), None, False

    raw_player = clean_text(match.group(1))
    raw_club = clean_text(match.group(2))
    should_backfill = bool(re.match(r"^(both|all)\s+", raw_club, flags=re.IGNORECASE))
    return raw_player, clean_club(raw_club), should_backfill


def extract_position_blocks(section_body: str) -> list[tuple[str, str]]:
    """Extract Goalkeeper/Defender/Midfielder/Forward blocks from one team section."""
    pattern = re.compile(r"(Goalkeepers|Defenders|Midfielders|Forwards):", flags=re.IGNORECASE)
    matches = list(pattern.finditer(section_body))
    blocks = []

    for index, match in enumerate(matches):
        label = match.group(1).title()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section_body)
        blocks.append((POSITION_LABELS[label], section_body[start:end]))

    return blocks


def parse_section(team: str, section_body: str) -> list[dict]:
    """Parse one team section into player records."""
    records = []
    default_iran_club = "Iran-based club not specified" if team == "Iran" else None

    for position_group, block in extract_position_blocks(section_body):
        pending_no_club_indices: list[int] = []

        for entry in split_entries(block):
            player, club, should_backfill = parse_player_entry(entry)
            if not player:
                continue

            if club and should_backfill:
                for record_index in pending_no_club_indices:
                    records[record_index]["club"] = club
                pending_no_club_indices = []

            if not club and default_iran_club:
                club = default_iran_club

            records.append(
                {
                    "world_cup_team": team,
                    "player": player,
                    "position": position_group,
                    "position_group": position_group,
                    "club": club or UNKNOWN,
                    "squad_status": "confirmed",
                    "data_source": DATA_SOURCE,
                    "raw_squad_status": RAW_STATUS,
                }
            )

            if not club:
                pending_no_club_indices.append(len(records) - 1)

    return records


def surname_backfill(parsed: pd.DataFrame, existing: pd.DataFrame) -> pd.DataFrame:
    """Expand one-token pasted names when the old team row has one unique matching surname."""
    output = parsed.copy()

    for index, row in output.iterrows():
        if len(str(row["player"]).split()) != 1:
            continue

        team_rows = existing[existing["world_cup_team"] == row["world_cup_team"]]
        surname = normalize_name(row["player"])
        candidates = [
            player
            for player in team_rows["player"].dropna().unique()
            if normalize_name(player).split() and normalize_name(player).split()[-1] == surname
        ]

        if len(candidates) == 1:
            output.at[index, "player"] = candidates[0]

    return output


def build_club_league_lookup(existing: pd.DataFrame) -> dict[str, str]:
    """Build a club-to-league lookup from current data and manual overrides."""
    lookup = {
        normalize_name(club): league
        for club, league in CLUB_LEAGUE_OVERRIDES.items()
    }

    known = existing[
        existing["club"].notna()
        & existing["league"].notna()
        & ~existing["club"].astype(str).str.contains("Unknown", case=False, na=False)
        & ~existing["league"].astype(str).str.contains("Unknown", case=False, na=False)
    ]
    counts = (
        known.groupby(["club", "league"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    for _, row in counts.iterrows():
        lookup.setdefault(normalize_name(row["club"]), row["league"])

    return lookup


def infer_leagues(parsed: pd.DataFrame, existing: pd.DataFrame) -> pd.DataFrame:
    """Infer league labels from previous player/club metadata."""
    output = parsed.copy()
    club_lookup = build_club_league_lookup(existing)
    player_lookup = {
        (normalize_name(row["world_cup_team"]), normalize_name(row["player"])): row
        for _, row in existing.iterrows()
    }

    leagues = []
    for _, row in output.iterrows():
        key = (normalize_name(row["world_cup_team"]), normalize_name(row["player"]))
        old_row = player_lookup.get(key)
        club_key = normalize_name(row["club"])

        if old_row is not None and normalize_name(old_row.get("club")) == club_key:
            league = old_row.get("league")
        elif row["world_cup_team"] == "Iran" and row["club"] == "Iran-based club not specified":
            league = "Iran Persian Gulf Pro League"
        else:
            league = club_lookup.get(club_key)

        leagues.append(league if league and not pd.isna(league) else UNKNOWN)

    output["league"] = leagues
    return output


def add_normalized_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add normalized helper columns used by dashboard matching."""
    output = df.copy()
    output["player_normalized"] = output["player"].apply(normalize_name)
    output["team_normalized"] = output["world_cup_team"].apply(normalize_name)
    return output


def parse_final_squad_text(text: str, existing: pd.DataFrame) -> pd.DataFrame:
    """Parse final-squad pasted text into the processed squad schema."""
    records = []
    for team, body in split_sections(text):
        records.extend(parse_section(team, body))

    parsed = pd.DataFrame(records)
    parsed = surname_backfill(parsed, existing)
    parsed = infer_leagues(parsed, existing)
    parsed = add_normalized_columns(parsed)
    return parsed[
        [
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
    ]


def build_change_report(old: pd.DataFrame, new: pd.DataFrame, parsed_teams: set[str]) -> str:
    """Build a before/after report for the final squad update."""
    old_unknown_clubs = old["club"].fillna("").str.contains("Unknown", case=False, regex=False).sum()
    new_unknown_clubs = new["club"].fillna("").str.contains("Unknown", case=False, regex=False).sum()
    old_unknown_leagues = old["league"].fillna("").str.contains("Unknown", case=False, regex=False).sum()
    new_unknown_leagues = new["league"].fillna("").str.contains("Unknown", case=False, regex=False).sum()

    old_keys = set(zip(old["world_cup_team"], old["player_normalized"]))
    new_keys = set(zip(new["world_cup_team"], new["player_normalized"]))
    added = new_keys - old_keys
    removed = old_keys - new_keys

    merged = old.merge(
        new,
        on=["world_cup_team", "player_normalized"],
        suffixes=("_old", "_new"),
        how="inner",
    )
    club_changes = merged[
        merged["club_old"].fillna("") != merged["club_new"].fillna("")
    ]
    league_changes = merged[
        merged["league_old"].fillna("") != merged["league_new"].fillna("")
    ]
    position_changes = merged[
        merged["position_group_old"].fillna("") != merged["position_group_new"].fillna("")
    ]

    missing_qualified = sorted(set(load_world_cup_teams()) - set(new["world_cup_team"].unique()))
    counts = new.groupby("world_cup_team").size().sort_index()

    lines = [
        "Final Squad Text Update Report",
        "==============================",
        f"Teams parsed from text: {len(parsed_teams)}",
        f"Teams in updated squad table: {new['world_cup_team'].nunique()}",
        f"Rows before: {len(old):,}",
        f"Rows after: {len(new):,}",
        f"Players added by team/name: {len(added):,}",
        f"Players removed by team/name: {len(removed):,}",
        f"Club changes for matched players: {len(club_changes):,}",
        f"League changes for matched players: {len(league_changes):,}",
        f"Position-group changes for matched players: {len(position_changes):,}",
        f"Unknown clubs before: {old_unknown_clubs:,}",
        f"Unknown clubs after: {new_unknown_clubs:,}",
        f"Unknown leagues before: {old_unknown_leagues:,}",
        f"Unknown leagues after: {new_unknown_leagues:,}",
        "",
        "Teams missing from updated squad table:",
        ", ".join(missing_qualified) if missing_qualified else "None",
        "",
        "Updated player counts by team:",
        counts.to_string(),
        "",
        "Top 30 club changes:",
        (
            club_changes[
                ["world_cup_team", "player_old", "club_old", "club_new"]
            ]
            .head(30)
            .to_string(index=False)
            if not club_changes.empty
            else "None"
        ),
        "",
        "Top 30 added players:",
        (
            new[
                new.apply(
                    lambda row: (row["world_cup_team"], row["player_normalized"]) in added,
                    axis=1,
                )
            ][["world_cup_team", "player", "position_group", "club"]]
            .head(30)
            .to_string(index=False)
            if added
            else "None"
        ),
        "",
        "Top 30 removed players:",
        (
            old[
                old.apply(
                    lambda row: (row["world_cup_team"], row["player_normalized"]) in removed,
                    axis=1,
                )
            ][["world_cup_team", "player", "position_group", "club"]]
            .head(30)
            .to_string(index=False)
            if removed
            else "None"
        ),
    ]
    return "\n".join(lines)


def main() -> None:
    """Apply the final pasted squad text to the processed squad table."""
    if not INPUT_TEXT_PATH.exists():
        raise FileNotFoundError(f"Final squad text file not found: {INPUT_TEXT_PATH}")
    if not SQUADS_PATH.exists():
        raise FileNotFoundError(f"Processed squad file not found: {SQUADS_PATH}")

    text = INPUT_TEXT_PATH.read_text(encoding="utf-8")
    current = pd.read_csv(SQUADS_PATH)
    comparison_old = pd.read_json(ARTIFACT_SQUAD_PATH) if ARTIFACT_SQUAD_PATH.exists() else current
    old = current[current["world_cup_team"].isin(load_world_cup_teams())].copy()
    parsed = parse_final_squad_text(text, old)
    parsed_teams = set(parsed["world_cup_team"].dropna().unique())

    retained = old[
        (~old["world_cup_team"].isin(parsed_teams))
        & (old["world_cup_team"].isin(load_world_cup_teams()))
    ].copy()
    updated = pd.concat([retained, parsed], ignore_index=True)
    updated = updated.sort_values(
        ["world_cup_team", "position_group", "player"],
    ).reset_index(drop=True)

    SQUADS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHANGE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    updated.to_csv(SQUADS_PATH, index=False)

    CHANGE_REPORT_PATH.write_text(
        build_change_report(comparison_old, updated, parsed_teams),
        encoding="utf-8",
    )
    SQUAD_COVERAGE_REPORT_PATH.write_text(build_report(updated), encoding="utf-8")

    print(f"Saved updated squads to: {SQUADS_PATH}")
    print(f"Saved final update report to: {CHANGE_REPORT_PATH}")
    print(f"Rows before: {len(comparison_old):,}")
    print(f"Rows after: {len(updated):,}")
    print(f"Teams parsed from text: {len(parsed_teams):,}")
    print(f"Teams in updated table: {updated['world_cup_team'].nunique():,}")
    print(
        "Unknown clubs: "
        f"{comparison_old['club'].fillna('').str.contains('Unknown', case=False, regex=False).sum():,} -> "
        f"{updated['club'].fillna('').str.contains('Unknown', case=False, regex=False).sum():,}"
    )
    print(
        "Unknown leagues: "
        f"{comparison_old['league'].fillna('').str.contains('Unknown', case=False, regex=False).sum():,} -> "
        f"{updated['league'].fillna('').str.contains('Unknown', case=False, regex=False).sum():,}"
    )


if __name__ == "__main__":
    main()
