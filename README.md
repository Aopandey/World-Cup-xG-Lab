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

Player squad filtering will be added once official final 26-player squads are announced.
