from pathlib import Path
import subprocess
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQUAD_PATH = PROJECT_ROOT / "data" / "squads" / "processed" / "world_cup_2026_squads.csv"
MISSING_DETAIL_PATH = PROJECT_ROOT / "reports" / "missing_fbref_players_detailed.csv"

STEPS = [
    ("Audit missing FBref players before refresh", "scripts/audit_missing_fbref_players.py"),
    ("Ingest FBref player season stats", "src/data/ingest_fbref.py"),
    ("Build cleaned FBref player context", "src/data/build_fbref_player_context.py"),
    ("Audit missing FBref players after refresh", "scripts/audit_missing_fbref_players.py"),
]


def run_step(label: str, script_path: str) -> None:
    """Run one refresh step and stop if it fails."""
    print("")
    print(f"=== {label} ===")
    subprocess.run([sys.executable, script_path], cwd=PROJECT_ROOT, check=True)


def read_coverage_numbers() -> tuple[int, int, int] | None:
    """Read current squad/FBref coverage after an audit has written outputs."""
    if not SQUAD_PATH.exists() or not MISSING_DETAIL_PATH.exists():
        return None

    squads = pd.read_csv(SQUAD_PATH)
    missing = pd.read_csv(MISSING_DETAIL_PATH)
    confirmed_count = len(squads[squads["squad_status"] == "confirmed"])
    missing_count = len(missing)
    matched_count = confirmed_count - missing_count
    return confirmed_count, matched_count, missing_count


def print_coverage(label: str, coverage: tuple[int, int, int] | None) -> None:
    """Print coverage numbers when available."""
    if coverage is None:
        print(f"{label}: coverage numbers unavailable.")
        return

    confirmed_count, matched_count, missing_count = coverage
    print(
        f"{label}: {matched_count:,}/{confirmed_count:,} matched, "
        f"{missing_count:,} missing."
    )


def main() -> None:
    """Run a focused FBref refresh around the missing-player audit."""
    print("Refreshing FBref context after league audit.")

    run_step(*STEPS[0])
    before = read_coverage_numbers()
    print_coverage("Before refresh", before)

    for step in STEPS[1:3]:
        run_step(*step)

    run_step(*STEPS[3])
    after = read_coverage_numbers()
    print_coverage("After refresh", after)

    if before and after:
        improvement = after[1] - before[1]
        print(f"FBref matched-player improvement: {improvement:+,}")


if __name__ == "__main__":
    main()
