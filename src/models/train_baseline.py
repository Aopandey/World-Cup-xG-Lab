from pathlib import Path
import sys

import joblib
import mlflow
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.models.evaluate import (
    evaluate_binary_classifier,
    print_metrics,
    save_predictions,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_FILE = PROJECT_ROOT / "data" / "features" / "shot_features.csv"
MODEL_FILE = PROJECT_ROOT / "models" / "baseline_logistic_model.joblib"
PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "baseline_predictions.csv"

NUMERIC_COLUMNS = [
    "shot_x",
    "shot_y",
    "distance_to_goal",
    "angle_to_goal",
    "minute",
    "period",
]

CATEGORICAL_COLUMNS = [
    "body_part",
    "shot_type",
    "under_pressure",
    "play_pattern",
]

TARGET_COLUMN = "is_goal"
MODEL_NAME = "baseline_logistic_regression"
MLFLOW_EXPERIMENT_NAME = "world-cup-xg-lab"
RANDOM_STATE = 42


def build_pipeline() -> Pipeline:
    """Create a preprocessing and Logistic Regression modeling pipeline."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_COLUMNS),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_COLUMNS,
            ),
        ]
    )

    model = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )


def load_features(path: Path = FEATURES_FILE) -> pd.DataFrame:
    """Load the engineered shot feature dataset."""
    if not path.exists():
        raise FileNotFoundError(
            f"Feature file not found: {path}. "
            "Run python src/features/build_features.py first."
        )

    return pd.read_csv(path)


def split_features(df: pd.DataFrame):
    """Split features and target into train and test sets."""
    required_columns = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS + [TARGET_COLUMN]
    missing_columns = [column for column in required_columns if column not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    x = df[NUMERIC_COLUMNS + CATEGORICAL_COLUMNS]
    y = df[TARGET_COLUMN].astype(int)

    return train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )


def main() -> None:
    """Train, evaluate, and save the baseline Logistic Regression xG model."""
    features = load_features()
    x_train, x_test, y_train, y_test = split_features(features)
    feature_columns = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS

    pipeline = build_pipeline()
    pipeline.fit(x_train, y_train)

    predicted_xg = pipeline.predict_proba(x_test)[:, 1]
    metrics = evaluate_binary_classifier(y_test, predicted_xg)

    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_FILE)
    save_predictions(y_test, predicted_xg, PREDICTIONS_FILE, MODEL_NAME)

    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    with mlflow.start_run(run_name=MODEL_NAME):
        mlflow.log_param("model_name", MODEL_NAME)
        mlflow.log_param("train_rows", len(x_train))
        mlflow.log_param("test_rows", len(x_test))
        mlflow.log_param("feature_columns", ", ".join(feature_columns))
        mlflow.log_param("numeric_columns", ", ".join(NUMERIC_COLUMNS))
        mlflow.log_param("categorical_columns", ", ".join(CATEGORICAL_COLUMNS))
        mlflow.log_param("model_type", "LogisticRegression")
        mlflow.log_param("max_iter", 1000)
        mlflow.log_param("random_state", RANDOM_STATE)
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(MODEL_FILE))
        mlflow.log_artifact(str(PREDICTIONS_FILE))

    print("Baseline Logistic Regression Metrics")
    print("=" * 36)
    print_metrics(metrics)
    print(f"Saved model to: {MODEL_FILE}")
    print(f"Saved predictions to: {PREDICTIONS_FILE}")


if __name__ == "__main__":
    main()
