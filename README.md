# World Cup xG Lab

World Cup xG Lab is a football analytics project for predicting expected goals from shot data.

The project uses pandas, scikit-learn, XGBoost, MLflow, Streamlit, Docker, AWS S3, and EC2 to build, track, deploy, and present expected goals models.

The dashboard will show team and player xG, goals minus xG, shot maps, and scoring zones.

## Project Structure

```text
app/                 Streamlit app files
configs/            Project configuration files
data/               Raw, processed, feature, and prediction datasets
notebooks/          Exploratory analysis notebooks
src/                Reusable project source code
tests/              Automated tests
models/             Trained model artifacts
reports/figures/    Exported charts and figures
```

## Setup

```bash
pip install -r requirements.txt
```

## Quick Check

```bash
python -c "from src.utils.paths import get_project_root; print(get_project_root())"
```

## MLflow Tracking

Model training scripts log metrics, parameters, models, predictions, and figures to a local MLflow experiment named `world-cup-xg-lab`.

Start the MLflow UI from the project root:

```bash
mlflow ui
```

Then visit the local MLflow dashboard shown in the terminal, usually:

```text
http://127.0.0.1:5000
```

## 2026 World Cup Filtering

The Streamlit dashboard currently filters views to 2026 World Cup teams found in the available dataset. Team names are normalized with aliases from `configs/world_cup_2026_teams.yaml`, and the original raw `team` column is preserved alongside a normalized `world_cup_team` column.

Currently, 39 of the 48 configured 2026 World Cup teams are present in the available historical event data. The remaining 9 teams are missing from the current dataset.

The underlying data is historical StatsBomb open event data, not guaranteed 2025/26 current-season data.

This is a historical xG analysis dashboard, not a complete 2026 prediction model.

## Official Squad + FBref Context Layer

StatsBomb powers the xG model, historical shot maps, and scoring-zone views. FBref adds recent club/league shooting context for players where available, including minutes, goals, assists, shots, shots on target, and per-90 shooting rates.

Official squad filtering limits player views to 2026 World Cup squad players where confirmed final squad data is available. Some teams are still marked as missing final squad data because the workbook contains preliminary, provisional, or non-26-player lists for those teams.

Some players may not have FBref context if their league is unsupported by soccerdata/FBref, has not been mapped in `configs/fbref_league_mapping.yaml`, or has not been pulled yet. Weak player-name matches are intentionally rejected to avoid showing false player stats.

Refresh the squad and FBref context layer with:

```bash
python scripts/refresh_squad_and_fbref_context.py
```

You can also run the steps individually:

```bash
python src/data/ingest_world_cup_squads.py
python src/data/ingest_fbref.py
python src/data/build_fbref_player_context.py
```

## Known Limitations

This is not a guaranteed 2026 World Cup prediction model. It shows historical scoring zones and recent player context from available data.

Player matching across StatsBomb, squad lists, and FBref is difficult because sources use different name formats. The dashboard uses exact matches, configured aliases, and conservative safe fuzzy matching only when confidence is high.

FBref league availability may vary, and some squad leagues may remain unmapped or unsupported.
