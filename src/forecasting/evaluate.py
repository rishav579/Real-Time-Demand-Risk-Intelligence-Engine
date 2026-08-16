"""Multi-horizon forecasting evaluation engine.

Implements standard supply chain forecasting accuracy metrics:
- WAPE (Weighted Absolute Percentage Error): sum(|y - y_hat|) / sum(y)
- MAE (Mean Absolute Error): mean(|y - y_hat|)
- RMSE (Root Mean Squared Error): sqrt(mean((y - y_hat)^2))
- Forecast Bias: sum(y_hat - y) / sum(y) (positive = over-forecasting, negative = under-forecasting)

Provides multi-dimensional slicing:
- Global overall benchmark
- Horizon-specific benchmarks (7-day, 14-day, 30-day)
- Segment-specific benchmarks (Class A vs Class B vs Class C; Class X vs Class Z)
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy.engine import Engine

from src.analytics.segmentation import compute_abc_xyz_segmentation
from src.forecasting.baselines import (
    ExponentialSmoothingForecaster,
    NaiveForecaster,
    SeasonalNaiveForecaster,
)
from src.forecasting.model import LightGBMDemandForecaster


def compute_wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Weighted Absolute Percentage Error (WAPE)."""
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    total_actual = float(np.sum(y_true_arr))
    if total_actual <= 0:
        return 0.0
    return round(float(np.sum(np.abs(y_true_arr - y_pred_arr)) / total_actual), 4)


def compute_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Mean Absolute Error (MAE)."""
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    if len(y_true_arr) == 0:
        return 0.0
    return round(float(np.mean(np.abs(y_true_arr - y_pred_arr))), 4)


def compute_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Root Mean Squared Error (RMSE)."""
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    if len(y_true_arr) == 0:
        return 0.0
    return round(float(np.sqrt(np.mean((y_true_arr - y_pred_arr) ** 2))), 4)


def compute_forecast_bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Normalized Forecast Bias (percentage over/under forecasting)."""
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    total_actual = float(np.sum(y_true_arr))
    if total_actual <= 0:
        return 0.0
    return round(float(np.sum(y_pred_arr - y_true_arr) / total_actual), 4)


def compute_metrics_dict(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate all 4 core metrics for a true vs predicted array."""
    return {
        "wape": compute_wape(y_true, y_pred),
        "mae": compute_mae(y_true, y_pred),
        "rmse": compute_rmse(y_true, y_pred),
        "forecast_bias": compute_forecast_bias(y_true, y_pred),
    }


def evaluate_predictions_dataframe(
    preds_df: pd.DataFrame,
    group_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Evaluate a predictions DataFrame containing [y_true, y_pred] across optional grouping columns."""
    if group_cols is None:
        metrics = compute_metrics_dict(preds_df["y_true"].values, preds_df["y_pred"].values)
        return pd.DataFrame([metrics])

    records = []
    for keys, group in preds_df.groupby(group_cols):
        if not isinstance(keys, tuple):
            keys = (keys,)
        metrics = compute_metrics_dict(group["y_true"].values, group["y_pred"].values)
        row = dict(zip(group_cols, keys))
        row.update(metrics)
        row["sample_count"] = len(group)
        records.append(row)

    return pd.DataFrame(records)


def run_comprehensive_benchmark(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    engine: Optional[Engine] = None,
    horizons: List[int] = [7, 14, 30],
) -> Dict[str, pd.DataFrame]:
    """Execute all baselines and LightGBM model across multiple horizons and evaluate performance.

    Returns:
        Dictionary containing:
        - "global_summary": Model comparison across all horizons combined
        - "horizon_summary": Model comparison broken down by 7d, 14d, and 30d
        - "segment_summary": Accuracy sliced by ABC and XYZ segments (if engine is provided)
        - "raw_predictions": Consolidated DataFrame with all prediction rows
    """
    models = [
        NaiveForecaster(),
        SeasonalNaiveForecaster(season_length=7),
        ExponentialSmoothingForecaster(alpha=0.3),
        LightGBMDemandForecaster(random_state=42),
    ]

    all_preds_list = []

    # Fit models on training data
    for model in models:
        if isinstance(model, LightGBMDemandForecaster):
            model.fit(train_df=train_df, val_df=val_df)
        else:
            model.fit(history_df=train_df)

        # Generate forecasts for each horizon
        for h in horizons:
            preds = model.predict(test_df=test_df, horizon_days=h)
            all_preds_list.append(preds)

    all_preds_df = pd.concat(all_preds_list, ignore_index=True)

    # 1. Global Model Summary
    global_summary = evaluate_predictions_dataframe(all_preds_df, group_cols=["model_name"]).sort_values("wape").reset_index(drop=True)

    # 2. Horizon Summary
    horizon_summary = evaluate_predictions_dataframe(all_preds_df, group_cols=["model_name", "horizon_days"]).sort_values(["horizon_days", "wape"]).reset_index(drop=True)

    # 3. Segment Summary (join with ABC/XYZ segmentation if engine provided)
    segment_summary = pd.DataFrame()
    if engine is not None:
        seg_df = compute_abc_xyz_segmentation(engine)[["product_id", "abc_class", "xyz_class", "abc_xyz_segment"]]
        enriched_preds = pd.merge(all_preds_df, seg_df, on="product_id", how="left")
        segment_summary = evaluate_predictions_dataframe(
            enriched_preds,
            group_cols=["model_name", "abc_class", "xyz_class"],
        ).sort_values(["abc_class", "xyz_class", "wape"]).reset_index(drop=True)

    return {
        "global_summary": global_summary,
        "horizon_summary": horizon_summary,
        "segment_summary": segment_summary,
        "raw_predictions": all_preds_df,
    }
