from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("Ingest World Cup squads", "src/data/ingest_world_cup_squads.py"),
    ("Apply manual confirmed squad overrides", "scripts/apply_manual_squad_overrides.py"),
    ("Apply final squad text update", "scripts/apply_final_squad_text.py"),
    ("Apply final 26-player squad corrections", "scripts/apply_final_26_corrections.py"),
    ("Export FBref scrape handoff workbook", "scripts/export_fbref_scrape_handoff.py"),
    ("Ingest FBref player season context", "src/data/ingest_fbref.py"),
    ("Build cleaned FBref player context", "src/data/build_fbref_player_context.py"),
    ("Build dashboard artifacts", "scripts/build_dashboard_artifacts.py"),
    ("Validate dashboard artifacts", "scripts/validate_dashboard_artifacts.py"),
]


def run_step(label: str, script_path: str) -> None:
    """Run one refresh step and stop if it fails."""
    print("")
    print(f"=== {label} ===")
    command = [sys.executable, script_path]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def main() -> None:
    """Refresh squad data and FBref dashboard context."""
    print("Refreshing squad and FBref dashboard context.")

    for label, script_path in STEPS:
        run_step(label, script_path)

    print("")
    print("Refresh complete.")


if __name__ == "__main__":
    main()
