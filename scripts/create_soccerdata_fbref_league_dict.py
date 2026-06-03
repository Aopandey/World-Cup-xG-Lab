from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "fbref"
    / "soccerdata_cache"
    / "config"
    / "league_dict.json"
)


CUSTOM_LEAGUES = {
    "ARG-Primera Division": {
        "FBref": "Primera División",
        "season_start": "Jan",
        "season_end": "Dec",
    },
    "AUT-Bundesliga": {
        "FBref": "Austrian Bundesliga",
        "season_start": "Jul",
        "season_end": "May",
    },
    "BEL-Pro League": {
        "FBref": "Belgian Pro League",
        "season_start": "Jul",
        "season_end": "May",
    },
    "BRA-Serie A": {
        "FBref": "Série A",
        "season_start": "Apr",
        "season_end": "Dec",
    },
    "CRO-HNL": {
        "FBref": "Hrvatska NL",
        "season_start": "Jul",
        "season_end": "May",
    },
    "CZE-First League": {
        "FBref": "Czech First League",
        "season_start": "Jul",
        "season_end": "May",
    },
    "DEN-Superliga": {
        "FBref": "Superliga",
        "season_start": "Jul",
        "season_end": "May",
    },
    "GRE-Super League": {
        "FBref": "Super League Greece",
        "season_start": "Aug",
        "season_end": "May",
    },
    "IRN-Persian Gulf Pro League": {
        "FBref": "Persian Gulf Pro League",
        "season_start": "Aug",
        "season_end": "May",
    },
    "JPN-J1 League": {
        "FBref": "J1 League",
        "season_start": "Feb",
        "season_end": "Dec",
    },
    "KOR-K League 1": {
        "FBref": "K League 1",
        "season_start": "Feb",
        "season_end": "Dec",
    },
    "MEX-Liga MX": {
        "FBref": "Liga MX",
        "season_start": "Jul",
        "season_end": "May",
    },
    "NED-Eredivisie": {
        "FBref": "Eredivisie",
        "season_start": "Aug",
        "season_end": "May",
    },
    "POR-Primeira Liga": {
        "FBref": "Primeira Liga",
        "season_start": "Aug",
        "season_end": "May",
    },
    "RUS-Premier League": {
        "FBref": "Russian Premier League",
        "season_start": "Jul",
        "season_end": "May",
    },
    "KSA-Saudi Pro League": {
        "FBref": "Saudi Pro League",
        "season_start": "Aug",
        "season_end": "May",
    },
    "SCO-Premiership": {
        "FBref": "Scottish Premiership",
        "season_start": "Aug",
        "season_end": "May",
    },
    "RSA-Premier Division": {
        "FBref": "South African Premiership",
        "season_start": "Aug",
        "season_end": "May",
    },
    "SUI-Super League": {
        "FBref": "Swiss Super League",
        "season_start": "Jul",
        "season_end": "May",
    },
    "TUR-Super Lig": {
        "FBref": "Süper Lig",
        "season_start": "Aug",
        "season_end": "May",
    },
    "USA-MLS": {
        "FBref": "Major League Soccer",
        "season_start": "Feb",
        "season_end": "Dec",
    },
    "INT-Champions League": {
        "FBref": "UEFA Champions League",
        "season_start": "Jul",
        "season_end": "May",
    },
    "INT-Europa League": {
        "FBref": "UEFA Europa League",
        "season_start": "Jul",
        "season_end": "May",
    },
    "INT-Conference League": {
        "FBref": "UEFA Conference League",
        "season_start": "Jul",
        "season_end": "May",
    },
    "INT-Nations League": {
        "FBref": "UEFA Nations League",
        "season_code": "single-year",
    },
    "INT-Africa Cup of Nations": {
        "FBref": "Africa Cup of Nations",
        "season_code": "single-year",
    },
    "INT-Copa America": {
        "FBref": "Copa América",
        "season_code": "single-year",
    },
    "INT-Friendlies": {
        "FBref": "Friendlies (M)",
        "season_code": "single-year",
    },
    "INT-Asian Cup": {
        "FBref": "AFC Asian Cup",
        "season_code": "single-year",
    },
}


def main() -> None:
    """Create soccerdata's local custom FBref league dictionary."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(CUSTOM_LEAGUES, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved soccerdata custom FBref league dictionary to: {OUTPUT_PATH}")
    print(f"Custom league entries: {len(CUSTOM_LEAGUES)}")


if __name__ == "__main__":
    main()
