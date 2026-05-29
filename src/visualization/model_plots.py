from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IMPORTANCE_PLOT = (
    PROJECT_ROOT / "reports" / "figures" / "xgboost_feature_importance.png"
)


def plot_feature_importance(model_pipeline, top_n: int = 20, save_path=None) -> pd.DataFrame:
    """Plot top feature importances from a preprocessing + XGBoost pipeline."""
    preprocessor = model_pipeline.named_steps["preprocessor"]
    model = model_pipeline.named_steps["model"]

    feature_names = preprocessor.get_feature_names_out()
    importances = model.feature_importances_

    if len(feature_names) != len(importances):
        raise ValueError(
            "Feature names and model importances have different lengths. "
            f"Got {len(feature_names)} names and {len(importances)} importances."
        )

    importance_df = (
        pd.DataFrame(
            {
                "feature": feature_names,
                "importance": importances,
            }
        )
        .sort_values("importance", ascending=False)
        .head(top_n)
    )

    plot_df = importance_df.sort_values("importance", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(plot_df["feature"], plot_df["importance"], color="#2f6fbb")
    ax.set_xlabel("Feature importance")
    ax.set_title(f"Top {len(plot_df)} XGBoost Feature Importances")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()

    output_path = Path(save_path) if save_path else DEFAULT_IMPORTANCE_PLOT
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return importance_df.reset_index(drop=True)
