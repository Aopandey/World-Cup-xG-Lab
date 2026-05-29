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
