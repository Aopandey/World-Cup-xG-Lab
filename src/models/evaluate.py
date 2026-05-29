from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score


def evaluate_binary_classifier(y_true, y_pred_proba) -> dict[str, float]:
    """Evaluate binary classification probabilities."""
    y_pred = (y_pred_proba >= 0.5).astype(int)

    return {
        "log_loss": log_loss(y_true, y_pred_proba),
        "brier_score": brier_score_loss(y_true, y_pred_proba),
        "roc_auc": roc_auc_score(y_true, y_pred_proba),
        "accuracy_at_0_5": accuracy_score(y_true, y_pred),
    }


def print_metrics(metrics_dict: dict[str, float]) -> None:
    """Print model metrics in a consistent format."""
    print("Model Evaluation Metrics")
    print("=" * 24)

    for metric_name, metric_value in metrics_dict.items():
        print(f"{metric_name}: {metric_value:.4f}")


def save_predictions(y_true, y_pred_proba, output_path: str | Path, model_name: str) -> None:
    """Save actual labels and predicted probabilities."""
    predictions = pd.DataFrame(
        {
            "actual_goal": pd.Series(y_true).astype(int).to_numpy(),
            "predicted_xg": y_pred_proba,
            "model_name": model_name,
        }
    )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_file, index=False)
