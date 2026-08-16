"""Forecasting package implementing multi-horizon demand forecasting and evaluation."""

from src.forecasting.baselines import (
    BaseForecaster,
    ExponentialSmoothingForecaster,
    NaiveForecaster,
    SeasonalNaiveForecaster,
)
from src.forecasting.evaluate import (
    compute_forecast_bias,
    compute_mae,
    compute_metrics_dict,
    compute_rmse,
    compute_wape,
    evaluate_predictions_dataframe,
    run_comprehensive_benchmark,
)
from src.forecasting.features import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_forecasting_dataset,
    engineer_forecasting_features,
    load_raw_timeseries_data,
)
from src.forecasting.model import LightGBMDemandForecaster
from src.forecasting.splits import (
    DEFAULT_BOUNDARIES,
    TemporalBoundaries,
    create_temporal_splits,
)

__all__ = [
    # Splits
    "TemporalBoundaries",
    "DEFAULT_BOUNDARIES",
    "create_temporal_splits",
    # Features
    "FEATURE_COLUMNS",
    "TARGET_COLUMN",
    "load_raw_timeseries_data",
    "engineer_forecasting_features",
    "build_forecasting_dataset",
    # Baselines
    "BaseForecaster",
    "NaiveForecaster",
    "SeasonalNaiveForecaster",
    "ExponentialSmoothingForecaster",
    # ML Model
    "LightGBMDemandForecaster",
    # Evaluation
    "compute_wape",
    "compute_mae",
    "compute_rmse",
    "compute_forecast_bias",
    "compute_metrics_dict",
    "evaluate_predictions_dataframe",
    "run_comprehensive_benchmark",
]
