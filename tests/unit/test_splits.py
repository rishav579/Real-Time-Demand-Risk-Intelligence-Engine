"""Unit tests for chronological time-series splitting."""

from datetime import date
import pandas as pd
import pytest

from src.forecasting.splits import (
    DEFAULT_BOUNDARIES,
    TemporalBoundaries,
    create_temporal_splits,
)


@pytest.fixture
def sample_timeseries_df():
    """Generate sample daily time-series DataFrame across 2026."""
    dates = pd.date_range(start="2026-01-01", end="2026-12-31", freq="D").date
    return pd.DataFrame({
        "transaction_date": dates,
        "units_demanded": [10 + (i % 7) for i in range(len(dates))],
    })


def test_chronological_splits_boundaries(sample_timeseries_df):
    """Verify train, validation, and test sets strictly match specified date boundaries."""
    train_df, val_df, test_df = create_temporal_splits(sample_timeseries_df)

    # Train: Jan 1 to Sep 30 (273 days)
    assert train_df["transaction_date"].min() == date(2026, 1, 1)
    assert train_df["transaction_date"].max() == date(2026, 9, 30)
    assert len(train_df) == 273

    # Validation: Oct 1 to Nov 15 (46 days)
    assert val_df["transaction_date"].min() == date(2026, 10, 1)
    assert val_df["transaction_date"].max() == date(2026, 11, 15)
    assert len(val_df) == 46

    # Test: Nov 16 to Dec 31 (46 days)
    assert test_df["transaction_date"].min() == date(2026, 11, 16)
    assert test_df["transaction_date"].max() == date(2026, 12, 31)
    assert len(test_df) == 46


def test_no_temporal_overlap_between_splits(sample_timeseries_df):
    """Verify strict chronological disjointness between all splits (zero temporal leakage)."""
    train_df, val_df, test_df = create_temporal_splits(sample_timeseries_df)

    train_dates = set(train_df["transaction_date"])
    val_dates = set(val_df["transaction_date"])
    test_dates = set(test_df["transaction_date"])

    assert len(train_dates.intersection(val_dates)) == 0, "Train and Validation dates overlap"
    assert len(train_dates.intersection(test_dates)) == 0, "Train and Test dates overlap"
    assert len(val_dates.intersection(test_dates)) == 0, "Validation and Test dates overlap"

    # Total rows must equal full year (365)
    assert len(train_df) + len(val_df) + len(test_df) == 365


def test_empty_split_validation_error(sample_timeseries_df):
    """Verify ValueError is raised when an invalid boundary yields an empty split."""
    invalid_boundaries = TemporalBoundaries(
        train_start=date(2026, 1, 1),
        train_end=date(2026, 5, 31),
        val_start=date(2026, 6, 1),
        val_end=date(2026, 6, 1),  # single day
        test_start=date(2027, 1, 1),  # out of bounds
        test_end=date(2027, 1, 31),
    )

    with pytest.raises(ValueError, match="Test split is empty"):
        create_temporal_splits(sample_timeseries_df, boundaries=invalid_boundaries)
