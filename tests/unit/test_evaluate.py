"""Unit tests for forecasting evaluation metrics (WAPE, MAE, RMSE, Bias)."""

import numpy as np
import pytest

from src.forecasting.evaluate import (
    compute_forecast_bias,
    compute_mae,
    compute_metrics_dict,
    compute_rmse,
    compute_wape,
)


def test_perfect_forecast_metrics():
    """Verify metrics for identical true and predicted vectors."""
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    y_pred = np.array([10.0, 20.0, 30.0, 40.0])

    assert compute_wape(y_true, y_pred) == 0.0
    assert compute_mae(y_true, y_pred) == 0.0
    assert compute_rmse(y_true, y_pred) == 0.0
    assert compute_forecast_bias(y_true, y_pred) == 0.0


def test_analytical_metric_calculations():
    """Verify exact formula values on small known test array."""
    # Actual: [10, 20], Pred: [12, 16] -> Errors: [+2, -4], Abs: [2, 4], Sq: [4, 16]
    y_true = np.array([10.0, 20.0])
    y_pred = np.array([12.0, 16.0])

    # sum(|e|) = 6, sum(y) = 30 -> WAPE = 6/30 = 0.20
    assert compute_wape(y_true, y_pred) == 0.20

    # MAE = (2 + 4) / 2 = 3.0
    assert compute_mae(y_true, y_pred) == 3.0

    # RMSE = sqrt((4 + 16)/2) = sqrt(10) = 3.1623
    assert pytest.approx(compute_rmse(y_true, y_pred), 0.001) == 3.1623

    # Bias = sum(pred - true) / sum(true) = (28 - 30) / 30 = -2/30 = -0.0667
    assert pytest.approx(compute_forecast_bias(y_true, y_pred), 0.001) == -0.0667


def test_zero_actuals_division_safety():
    """Verify metric calculators gracefully handle zero or empty inputs without exceptions."""
    y_true_zero = np.array([0.0, 0.0])
    y_pred_zero = np.array([0.0, 0.0])

    assert compute_wape(y_true_zero, y_pred_zero) == 0.0
    assert compute_forecast_bias(y_true_zero, y_pred_zero) == 0.0
    assert compute_mae(np.array([]), np.array([])) == 0.0
    assert compute_rmse(np.array([]), np.array([])) == 0.0


def test_compute_metrics_dict_keys():
    """Verify dictionary structure and return types."""
    y_true = np.array([15.0, 25.0])
    y_pred = np.array([14.0, 26.0])

    m = compute_metrics_dict(y_true, y_pred)
    assert set(m.keys()) == {"wape", "mae", "rmse", "forecast_bias"}
    for v in m.values():
        assert isinstance(v, float)
