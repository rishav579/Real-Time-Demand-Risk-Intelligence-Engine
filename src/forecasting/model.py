"""LightGBM gradient-boosted demand forecasting model.

Implements multi-horizon regression forecasting with deterministic training (random_state=42):
- Incorporates autoregressive lags, rolling window statistics, calendar indicators, promotional schedules, and product economics.
- Supports evaluation over 7-day, 14-day, and 30-day horizons.
- Exposes feature importance rankings and non-negative prediction clipping.
"""

from typing import Dict, List, Optional
import lightgbm as lgb
import numpy as np
import pandas as pd

from src.forecasting.baselines import BaseForecaster
from src.forecasting.features import FEATURE_COLUMNS, TARGET_COLUMN


class LightGBMDemandForecaster(BaseForecaster):
    """Deterministic LightGBM gradient-boosted regressor for multi-horizon demand forecasting."""

    def __init__(
        self,
        random_state: int = 42,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        num_leaves: int = 31,
        min_child_samples: int = 5,
        feature_cols: Optional[List[str]] = None,
    ):
        super().__init__(name="LightGBM")
        self.random_state = random_state
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.feature_cols = feature_cols or FEATURE_COLUMNS

        self.model: Optional[lgb.LGBMRegressor] = None

    def fit(
        self,
        train_df: pd.DataFrame,
        val_df: Optional[pd.DataFrame] = None,
        target_col: str = TARGET_COLUMN,
    ) -> "LightGBMDemandForecaster":
        """Train LightGBM regressor on engineered feature matrix."""
        X_train = train_df[self.feature_cols]
        y_train = train_df[target_col]

        self.model = lgb.LGBMRegressor(
            random_state=self.random_state,
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            num_leaves=self.num_leaves,
            min_child_samples=self.min_child_samples,
            verbosity=-1,
            force_row_wise=True,
        )

        if val_df is not None and len(val_df) > 0:
            X_val = val_df[self.feature_cols]
            y_val = val_df[target_col]
            self.model.fit(
                X_train,
                y_train,
                eval_X=X_val,
                eval_y=y_val,
                callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)],
            )
        else:
            self.model.fit(X_train, y_train)

        return self

    def predict(
        self,
        test_df: pd.DataFrame,
        horizon_days: int = 30,
        target_col: str = TARGET_COLUMN,
    ) -> pd.DataFrame:
        """Generate demand forecasts for the evaluation test window."""
        if self.model is None:
            raise ValueError("Model must be fitted before calling predict.")

        results = []
        for (loc_id, prod_id), group in test_df.groupby(["location_id", "product_id"]):
            group_sorted = group.sort_values("transaction_date").iloc[:horizon_days]
            X_test = group_sorted[self.feature_cols]
            raw_preds = self.model.predict(X_test)
            clipped_preds = np.clip(raw_preds, a_min=0.0, a_max=None)

            for step_idx, (_, row) in enumerate(group_sorted.iterrows()):
                results.append({
                    "transaction_date": row["transaction_date"],
                    "location_id": loc_id,
                    "product_id": prod_id,
                    "y_true": float(row[target_col]),
                    "y_pred": round(float(clipped_preds[step_idx]), 2),
                    "model_name": self.name,
                    "horizon_days": horizon_days,
                })

        return pd.DataFrame(results)

    def get_feature_importances(self) -> pd.DataFrame:
        """Return feature importance rankings (gain and split counts)."""
        if self.model is None:
            raise ValueError("Model is not fitted.")

        importance_gain = self.model.booster_.feature_importance(importance_type="gain")
        importance_split = self.model.booster_.feature_importance(importance_type="split")

        df = pd.DataFrame({
            "feature": self.feature_cols,
            "importance_gain": importance_gain,
            "importance_split": importance_split,
        })
        return df.sort_values("importance_gain", ascending=False).reset_index(drop=True)
