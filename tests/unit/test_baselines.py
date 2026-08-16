"""Unit tests for statistical baseline models (Naive, Seasonal Naive, Exponential Smoothing)."""

from datetime import date
import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.data.generator import DataGenerator
from src.data.ingestion import ingest_dataset
from src.forecasting.baselines import (
    ExponentialSmoothingForecaster,
    NaiveForecaster,
    SeasonalNaiveForecaster,
)
from src.forecasting.features import load_raw_timeseries_data
from src.forecasting.splits import create_temporal_splits


@pytest.fixture(scope="module")
def train_and_test_data():
    """Extract train and test splits from populated Seed 42 dataset."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)

    raw_df = load_raw_timeseries_data(engine)
    train_df, val_df, test_df = create_temporal_splits(raw_df)
    return train_df, test_df


def test_naive_forecaster_projection(train_and_test_data):
    """Verify Naive forecaster outputs flat prediction matching last observed training value."""
    train_df, test_df = train_and_test_data
    model = NaiveForecaster()
    model.fit(train_df)

    preds = model.predict(test_df, horizon_days=14)

    # 4 stores x 15 SKUs = 60 series * 14 horizon days = 840 predictions
    assert len(preds) == 60 * 14
    assert set(preds.columns) == {
        "transaction_date", "location_id", "product_id", "y_true", "y_pred", "model_name", "horizon_days"
    }

    # Verify predictions are constant per series
    for _, group in preds.groupby(["location_id", "product_id"]):
        assert group["y_pred"].nunique() == 1
        assert (group["y_pred"] >= 0).all()


def test_seasonal_naive_forecaster_7day_cycle(train_and_test_data):
    """Verify Seasonal Naive forecaster repeats 7-day cyclical pattern."""
    train_df, test_df = train_and_test_data
    model = SeasonalNaiveForecaster(season_length=7)
    model.fit(train_df)

    preds = model.predict(test_df, horizon_days=14)

    assert len(preds) == 60 * 14
    for _, group in preds.groupby(["location_id", "product_id"]):
        group_sorted = group.sort_values("transaction_date")
        week1_preds = group_sorted.iloc[:7]["y_pred"].values
        week2_preds = group_sorted.iloc[7:14]["y_pred"].values
        assert (week1_preds == week2_preds).all()


def test_exponential_smoothing_forecaster_positive_predictions(train_and_test_data):
    """Verify Simple Exponential Smoothing computes valid level and non-negative forecasts."""
    train_df, test_df = train_and_test_data
    model = ExponentialSmoothingForecaster(alpha=0.3)
    model.fit(train_df)

    preds = model.predict(test_df, horizon_days=30)

    assert len(preds) == 60 * 30
    assert (preds["y_pred"] >= 0).all()
    for _, group in preds.groupby(["location_id", "product_id"]):
        assert group["y_pred"].nunique() == 1  # constant level forecast
