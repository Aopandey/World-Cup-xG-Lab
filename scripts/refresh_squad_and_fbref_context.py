from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("Ingest World Cup squads", "src/data/ingest_world_cup_squads.py"),
    ("Ingest FBref player season context", "src/data/ingest_fbref.py"),
    ("Build cleaned FBref player context", "src/data/build_fbref_player_context.py"),
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
