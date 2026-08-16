"""Statistical baseline demand forecasting models.

Implements three classical benchmarks for multi-horizon demand forecasting:
1. NaiveForecaster: Flat persistence of last observed demand value at cutoff t0.
2. SeasonalNaiveForecaster: Weekly 7-day cyclical persistence from most recent known cycle.
3. ExponentialSmoothingForecaster: Simple Exponential Smoothing (SES, alpha=0.3) level projection.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


class BaseForecaster(ABC):
    """Abstract base class for all forecasting models."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def fit(self, history_df: pd.DataFrame, target_col: str = "units_demanded") -> "BaseForecaster":
        """Fit or compute historical series states."""
        pass

    @abstractmethod
    def predict(
        self,
        test_df: pd.DataFrame,
        horizon_days: int = 30,
        target_col: str = "units_demanded",
    ) -> pd.DataFrame:
        """Generate forecasts for the test evaluation window."""
        pass


class NaiveForecaster(BaseForecaster):
    """Naive persistence baseline: forecasts last known value at cutoff t0 flat forward."""

    def __init__(self):
        super().__init__(name="Naive")
        self.last_observed: Dict[Tuple[str, str], float] = {}

    def fit(self, history_df: pd.DataFrame, target_col: str = "units_demanded") -> "NaiveForecaster":
        sorted_df = history_df.sort_values(["location_id", "product_id", "transaction_date"])
        for (loc_id, prod_id), group in sorted_df.groupby(["location_id", "product_id"]):
            self.last_observed[(loc_id, prod_id)] = float(group[target_col].iloc[-1])
        return self

    def predict(
        self,
        test_df: pd.DataFrame,
        horizon_days: int = 30,
        target_col: str = "units_demanded",
    ) -> pd.DataFrame:
        results = []
        for (loc_id, prod_id), group in test_df.groupby(["location_id", "product_id"]):
            last_val = self.last_observed.get((loc_id, prod_id), 0.0)
            group_sorted = group.sort_values("transaction_date").iloc[:horizon_days]
            for _, row in group_sorted.iterrows():
                results.append({
                    "transaction_date": row["transaction_date"],
                    "location_id": loc_id,
                    "product_id": prod_id,
                    "y_true": float(row[target_col]),
                    "y_pred": max(0.0, last_val),
                    "model_name": self.name,
                    "horizon_days": horizon_days,
                })
        return pd.DataFrame(results)


class SeasonalNaiveForecaster(BaseForecaster):
    """Seasonal Naive baseline: repeats the 7-day cyclical demand pattern from the last known week."""

    def __init__(self, season_length: int = 7):
        super().__init__(name="SeasonalNaive")
        self.season_length = season_length
        self.last_season_patterns: Dict[Tuple[str, str], List[float]] = {}

    def fit(self, history_df: pd.DataFrame, target_col: str = "units_demanded") -> "SeasonalNaiveForecaster":
        sorted_df = history_df.sort_values(["location_id", "product_id", "transaction_date"])
        for (loc_id, prod_id), group in sorted_df.groupby(["location_id", "product_id"]):
            recent_vals = group[target_col].tail(self.season_length).tolist()
            if len(recent_vals) < self.season_length:
                recent_vals = recent_vals + [recent_vals[-1]] * (self.season_length - len(recent_vals))
            self.last_season_patterns[(loc_id, prod_id)] = [float(v) for v in recent_vals]
        return self

    def predict(
        self,
        test_df: pd.DataFrame,
        horizon_days: int = 30,
        target_col: str = "units_demanded",
    ) -> pd.DataFrame:
        results = []
        for (loc_id, prod_id), group in test_df.groupby(["location_id", "product_id"]):
            pattern = self.last_season_patterns.get((loc_id, prod_id), [0.0] * self.season_length)
            group_sorted = group.sort_values("transaction_date").iloc[:horizon_days]
            for step_idx, (_, row) in enumerate(group_sorted.iterrows()):
                pred_val = pattern[step_idx % self.season_length]
                results.append({
                    "transaction_date": row["transaction_date"],
                    "location_id": loc_id,
                    "product_id": prod_id,
                    "y_true": float(row[target_col]),
                    "y_pred": max(0.0, pred_val),
                    "model_name": self.name,
                    "horizon_days": horizon_days,
                })
        return pd.DataFrame(results)


class ExponentialSmoothingForecaster(BaseForecaster):
    """Simple Exponential Smoothing (SES) level forecaster with alpha=0.3."""

    def __init__(self, alpha: float = 0.3):
        super().__init__(name="ExponentialSmoothing")
        self.alpha = alpha
        self.smoothed_levels: Dict[Tuple[str, str], float] = {}

    def fit(self, history_df: pd.DataFrame, target_col: str = "units_demanded") -> "ExponentialSmoothingForecaster":
        sorted_df = history_df.sort_values(["location_id", "product_id", "transaction_date"])
        for (loc_id, prod_id), group in sorted_df.groupby(["location_id", "product_id"]):
            series = group[target_col].values
            if len(series) == 0:
                level = 0.0
            else:
                level = float(series[0])
                for val in series[1:]:
                    level = self.alpha * float(val) + (1.0 - self.alpha) * level
            self.smoothed_levels[(loc_id, prod_id)] = round(level, 2)
        return self

    def predict(
        self,
        test_df: pd.DataFrame,
        horizon_days: int = 30,
        target_col: str = "units_demanded",
    ) -> pd.DataFrame:
        results = []
        for (loc_id, prod_id), group in test_df.groupby(["location_id", "product_id"]):
            level = self.smoothed_levels.get((loc_id, prod_id), 0.0)
            group_sorted = group.sort_values("transaction_date").iloc[:horizon_days]
            for _, row in group_sorted.iterrows():
                results.append({
                    "transaction_date": row["transaction_date"],
                    "location_id": loc_id,
                    "product_id": prod_id,
                    "y_true": float(row[target_col]),
                    "y_pred": max(0.0, level),
                    "model_name": self.name,
                    "horizon_days": horizon_days,
                })
        return pd.DataFrame(results)
