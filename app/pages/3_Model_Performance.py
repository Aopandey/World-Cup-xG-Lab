from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_COMPARISON_FILE = PROJECT_ROOT / "reports" / "model_comparison.csv"
BASELINE_PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "baseline_predictions.csv"
XGBOOST_PREDICTIONS_FILE = PROJECT_ROOT / "data" / "predictions" / "xgboost_predictions.csv"
FEATURE_IMPORTANCE_FILE = PROJECT_ROOT / "reports" / "figures" / "xgboost_feature_importance.png"


@st.cache_data
def load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV file for dashboard display."""
    return pd.read_csv(path)


def load_prediction_files() -> pd.DataFrame:
    """Load available model prediction files into one DataFrame."""
    prediction_frames = []

    for path in [BASELINE_PREDICTIONS_FILE, XGBOOST_PREDICTIONS_FILE]:
        if path.exists():
            prediction_frames.append(load_csv(path))

    if not prediction_frames:
        return pd.DataFrame()

    return pd.concat(prediction_frames, ignore_index=True)


def build_calibration_data(predictions: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    """Create calibration data by grouping predictions into probability bins."""
    calibration_frames = []

    for model_name, model_predictions in predictions.groupby("model_name"):
        data = model_predictions.copy()
        data["xg_bin"] = pd.cut(
            data["predicted_xg"],
            bins=bins,
            labels=False,
            include_lowest=True,
        )
        calibration = (
            data.groupby("xg_bin", observed=True)
            .agg(
                mean_predicted_xg=("predicted_xg", "mean"),
                actual_goal_rate=("actual_goal", "mean"),
                shots=("actual_goal", "size"),
            )
            .reset_index(drop=True)
        )
        calibration["model_name"] = model_name
        calibration_frames.append(calibration)

    return pd.concat(calibration_frames, ignore_index=True)


def plot_calibration_curve(predictions: pd.DataFrame):
    """Plot calibration curves for available models."""
    calibration = build_calibration_data(predictions)
    fig = px.line(
        calibration,
        x="mean_predicted_xg",
        y="actual_goal_rate",
        color="model_name",
        markers=True,
        hover_data=["shots"],
        labels={
            "mean_predicted_xg": "Average predicted xG",
            "actual_goal_rate": "Actual goal rate",
            "model_name": "Model",
        },
        title="Calibration Curve",
    )
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            name="Perfect calibration",
            line=dict(color="gray", dash="dash"),
        )
    )
    fig.update_layout(height=520)
    return fig


def plot_prediction_histogram(predictions: pd.DataFrame):
    """Plot predicted xG distributions by model."""
    fig = px.histogram(
        predictions,
        x="predicted_xg",
        color="model_name",
        nbins=40,
        barmode="overlay",
        opacity=0.65,
        labels={"predicted_xg": "Predicted xG", "model_name": "Model"},
        title="Predicted xG Distribution",
    )
    fig.update_layout(height=420)
    return fig


def main() -> None:
    """Render the Model Performance dashboard page."""
    st.set_page_config(page_title="Model Performance", layout="wide")

    st.title("Model Performance")
    st.write("Compare model quality, calibration, and predicted xG distributions.")
    st.info("For expected goals models, probability calibration matters more than raw accuracy.")

    st.subheader("Model Comparison")
    if MODEL_COMPARISON_FILE.exists():
        comparison = load_csv(MODEL_COMPARISON_FILE)
        st.dataframe(comparison.round(4), use_container_width=True, hide_index=True)
    else:
        st.warning(
            "Model comparison file not found. Run `python src/models/compare_models.py`."
        )

    predictions = load_prediction_files()

    if predictions.empty:
        st.warning(
            "Prediction files not found. Run the baseline and XGBoost training scripts first."
        )
    else:
        st.divider()
        chart_columns = st.columns(2)
        chart_columns[0].plotly_chart(
            plot_calibration_curve(predictions),
            use_container_width=True,
        )
        chart_columns[1].plotly_chart(
            plot_prediction_histogram(predictions),
            use_container_width=True,
        )

    st.divider()
    st.subheader("Metric Guide")
    st.write(
        "**Log loss** measures probability quality and strongly penalizes confident wrong predictions. "
        "Lower is better."
    )
    st.write(
        "**Brier score** is the average squared error between predicted xG and the actual goal outcome. "
        "Lower is better."
    )
    st.write(
        "**ROC-AUC** measures how well the model ranks goals above non-goals across thresholds. "
        "Higher is better."
    )
    st.write(
        "**Accuracy** measures correct goal/non-goal classifications at a 0.5 threshold. "
        "It is secondary for xG because most shots are not goals."
    )

    if FEATURE_IMPORTANCE_FILE.exists():
        st.divider()
        st.subheader("XGBoost Feature Importance")
        st.image(str(FEATURE_IMPORTANCE_FILE), use_container_width=True)


if __name__ == "__main__":
    main()
