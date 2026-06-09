# Data Sources

World Cup xG Lab uses multiple football data sources, but each source has a clearly separated role.

## StatsBomb Open Data

StatsBomb Open Data powers the production historical xG model.

Used for:

- Shot-level event data.
- Shot coordinates.
- Geometry features such as distance and angle.
- Shot context such as body part, shot type, pressure, play pattern, minute, and period.
- Historical team/player xG and shot maps.

Not used for:

- Complete current-season coverage.
- Complete 2026 World Cup squad coverage.
- Guaranteed future scoring predictions.

## FBref

FBref is used as recent aggregate context for confirmed squad players.

Used for:

- Recent club/league minutes.
- Goals, assists, shots, shots on target.
- Shooting rates and player-season context.

Not used for:

- Replacing the StatsBomb xG model.
- Shot-location model training in the current production dashboard.

## Understat

Understat is used as club xG context and experimental model research.

Used for:

- Club-season xG, npxG, xA, shots, xGChain, xGBuildup.
- Shot-derived context where available.
- Research comparisons across StatsBomb-only, Understat-only, and combined-source models.

Not used for:

- Automatically replacing the production StatsBomb xG layer.

## DataMB

DataMB is used as a 25/26 percentile context layer.

Used for:

- Player percentile profiles from matched public/free DataMB data.
- Radar charts generated from scraped percentile values.

Not used for:

- Raw per-90 model training.
- Judging player quality without source context.

## Coverage Notes

Current artifact coverage:

- 48 World Cup teams.
- 1,248 squad players.
- 39 teams with historical StatsBomb data.
- FBref coverage: 1,002 of 1,248 players.
- Understat coverage: 593 of 1,248 players.
- DataMB coverage: 447 of 1,248 players.

Missing data is shown explicitly in the dashboard so users can interpret weak samples honestly.
