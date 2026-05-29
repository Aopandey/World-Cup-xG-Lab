from pathlib import Path
import sys

import joblib
import mlflow
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier


if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.append(str(PROJECT_ROOT))

from src.models.evaluate import (
    evaluate_binary_classifier,
    print_metrics,
    save_predictions,
)
from src.models.train_baseline import (
    CATEGORICAL_COLUMNS,
    NUMERIC_COLUMNS,
    RANDOM_STATE,
    load_features,
    split_features,
)
from src.visualization.model_plots import plot_feature_importance


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_FILE = PROJECT_ROOT / "models" / "xgboost_xg_model.joblib"
PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "xgboost_predictions.csv"
BASELINE_PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "baseline_predictions.csv"
FEATURE_IMPORTANCE_FILE = PROJECT_ROOT / "reports" / "figures" / "xgboost_feature_importance.png"
MODEL_NAME = "xgboost_xg_model"
MLFLOW_EXPERIMENT_NAME = "world-cup-xg-lab"
XGBOOST_PARAMS = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 4,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "eval_metric": "logloss",
    "random_state": RANDOM_STATE,
}


def build_pipeline() -> Pipeline:
    """Create a preprocessing and XGBoost modeling pipeline."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", "passthrough", NUMERIC_COLUMNS),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_COLUMNS,
            ),
        ]
    )

    model = XGBClassifier(**XGBOOST_PARAMS)

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )


def load_prediction_metrics(path: Path) -> dict[str, float] | None:
    """Load saved prediction probabilities and calculate metrics."""
    if not path.exists():
        return None

    predictions = pd.read_csv(path)
    return evaluate_binary_classifier(
        predictions["actual_goal"],
        predictions["predicted_xg"],
    )


def print_baseline_comparison(xgboost_metrics: dict[str, float]) -> None:
    """Print XGBoost metrics beside baseline metrics if predictions exist."""
    baseline_metrics = load_prediction_metrics(BASELINE_PREDICTIONS_FILE)

    if baseline_metrics is None:
        print(f"Baseline predictions not found at: {BASELINE_PREDICTIONS_FILE}")
        return

    print("")
    print("Comparison vs Baseline Logistic Regression")
    print("=" * 42)
    print("metric, baseline, xgboost, change")

    for metric_name, xgboost_value in xgboost_metrics.items():
        baseline_value = baseline_metrics[metric_name]
        change = xgboost_value - baseline_value
        print(
            f"{metric_name}: "
            f"{baseline_value:.4f} -> {xgboost_value:.4f} "
            f"({change:+.4f})"
        )


def main() -> None:
    """Train, evaluate, and save the XGBoost xG model."""
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
    feature_importances = plot_feature_importance(
        pipeline,
        top_n=20,
        save_path=FEATURE_IMPORTANCE_FILE,
    )

    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    with mlflow.start_run(run_name=MODEL_NAME):
        mlflow.log_param("model_name", MODEL_NAME)
        mlflow.log_param("train_rows", len(x_train))
        mlflow.log_param("test_rows", len(x_test))
        mlflow.log_param("feature_columns", ", ".join(feature_columns))
        mlflow.log_param("numeric_columns", ", ".join(NUMERIC_COLUMNS))
        mlflow.log_param("categorical_columns", ", ".join(CATEGORICAL_COLUMNS))
        mlflow.log_param("model_type", "XGBClassifier")
        mlflow.log_params(XGBOOST_PARAMS)
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(MODEL_FILE))
        mlflow.log_artifact(str(PREDICTIONS_FILE))

        if FEATURE_IMPORTANCE_FILE.exists():
            mlflow.log_artifact(str(FEATURE_IMPORTANCE_FILE))

    print("XGBoost xG Model Metrics")
    print("=" * 24)
    print_metrics(metrics)
    print_baseline_comparison(metrics)
    print("")
    print("Top XGBoost Features")
    print("=" * 20)
    print(feature_importances.head(10).to_string(index=False))
    print(f"Saved model to: {MODEL_FILE}")
    print(f"Saved predictions to: {PREDICTIONS_FILE}")
    print(f"Saved feature importance plot to: {FEATURE_IMPORTANCE_FILE}")


if __name__ == "__main__":
    main()
