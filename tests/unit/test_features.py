"""Unit tests for feature engineering and data leakage prevention."""

from datetime import date
import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.data.generator import DataGenerator
from src.data.ingestion import ingest_dataset
from src.forecasting.features import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_forecasting_dataset,
    engineer_forecasting_features,
    load_raw_timeseries_data,
)


@pytest.fixture(scope="module")
def populated_engine():
    """Create in-memory SQLite database populated with 365-day Seed 42 dataset."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)
    return engine


def test_feature_columns_completeness(populated_engine):
    """Verify all engineered features are computed without NaN values."""
    feat_df = build_forecasting_dataset(populated_engine)

    assert len(feat_df) == 21900  # 365 days x 4 retail stores x 15 SKUs
    assert TARGET_COLUMN in feat_df.columns
    for col in FEATURE_COLUMNS:
        assert col in feat_df.columns, f"Missing feature column: {col}"
        assert feat_df[col].isna().sum() == 0, f"Feature column {col} contains NaN values"


def test_zero_temporal_data_leakage_in_lags_and_rolling(populated_engine):
    """Verify that features at date t are computed strictly from demand observed prior to date t."""
    raw_df = load_raw_timeseries_data(populated_engine)
    feat_df = engineer_forecasting_features(raw_df)

    # Filter for a single series (e.g. LOC-ST-01, PRD-BEV-001)
    series_df = feat_df[(feat_df["location_id"] == "LOC-ST-01") & (feat_df["product_id"] == "PRD-BEV-001")].sort_values("transaction_date").reset_index(drop=True)

    # For day index i >= 7: lag_1 must equal demand at index i-1, lag_7 must equal demand at index i-7
    for i in range(14, 25):
        actual_t_minus_1 = series_df.loc[i - 1, "units_demanded"]
        actual_t_minus_7 = series_df.loc[i - 7, "units_demanded"]
        actual_t_minus_14 = series_df.loc[i - 14, "units_demanded"]

        assert series_df.loc[i, "lag_1"] == actual_t_minus_1
        assert series_df.loc[i, "lag_7"] == actual_t_minus_7
        assert series_df.loc[i, "lag_14"] == actual_t_minus_14

        # rolling_mean_7 at step i must equal mean of demand from i-7 to i-1 (7 historical days, excluding day i)
        expected_rolling_7 = series_df.loc[i - 7 : i - 1, "units_demanded"].mean()
        assert pytest.approx(series_df.loc[i, "rolling_mean_7"], 0.01) == expected_rolling_7


def test_target_variable_is_unconstrained_demand(populated_engine):
    """Verify target column represents unconstrained customer demand (sold + unfulfilled)."""
    raw_df = load_raw_timeseries_data(populated_engine)
    assert (raw_df["units_demanded"] == raw_df["units_sold"] + raw_df["unfulfilled_units"]).all()
