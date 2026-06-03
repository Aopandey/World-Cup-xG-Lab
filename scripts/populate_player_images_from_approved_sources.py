from __future__ import annotations

from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAYER_PROFILES_PATH = PROJECT_ROOT / "data" / "dashboard_artifacts" / "player_profiles.json"


def main() -> None:
    """Placeholder for future approved/licensed player-image enrichment."""
    if not PLAYER_PROFILES_PATH.exists():
        raise FileNotFoundError(
            f"Player profiles not found: {PLAYER_PROFILES_PATH}. "
            "Run python scripts/build_dashboard_artifacts.py first."
        )

    with PLAYER_PROFILES_PATH.open("r", encoding="utf-8") as file:
        player_profiles = json.load(file)

    players_with_images = sum(1 for player in player_profiles if player.get("imageUrl"))
    print(f"Loaded {len(player_profiles):,} player profiles.")
    print(f"Profiles with approved imageUrl values: {players_with_images:,}")
    print(
        "No images were scraped. Add imageUrl values only from approved/licensed "
        "sources, or keep the avatarSeed placeholder system."
    )


if __name__ == "__main__":
    main()
