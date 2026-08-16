"""Strict chronological time-series splitting for demand forecasting.

Prevents temporal data leakage by enforcing non-overlapping sequential windows:
- Train: 2026-01-01 through 2026-09-30 (273 days, ~9 months)
- Validation: 2026-10-01 through 2026-11-15 (46 days)
- Test Holdout: 2026-11-16 through 2026-12-31 (46 days)

Random train/test splits are strictly prohibited.
"""

from dataclasses import dataclass
from datetime import date
from typing import Tuple
import pandas as pd


@dataclass(frozen=True)
class TemporalBoundaries:
    """Explicit date boundaries for chronological splitting."""
    train_start: date = date(2026, 1, 1)
    train_end: date = date(2026, 9, 30)
    val_start: date = date(2026, 10, 1)
    val_end: date = date(2026, 11, 15)
    test_start: date = date(2026, 11, 16)
    test_end: date = date(2026, 12, 31)


DEFAULT_BOUNDARIES = TemporalBoundaries()


def create_temporal_splits(
    df: pd.DataFrame,
    date_col: str = "transaction_date",
    boundaries: TemporalBoundaries = DEFAULT_BOUNDARIES,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split time-series DataFrame into strict chronological Train, Validation, and Test sets.

    Args:
        df: Input DataFrame containing time-series telemetry.
        date_col: Name of the date column.
        boundaries: TemporalBoundaries instance defining cutoffs.

    Returns:
        Tuple of (train_df, val_df, test_df)
    """
    df_copy = df.copy()
    
    # Ensure date column is Python date object or comparable string
    if not isinstance(df_copy[date_col].iloc[0], (date, str)):
        df_copy[date_col] = pd.to_datetime(df_copy[date_col]).dt.date
    elif isinstance(df_copy[date_col].iloc[0], str):
        df_copy[date_col] = pd.to_datetime(df_copy[date_col]).dt.date

    train_mask = (df_copy[date_col] >= boundaries.train_start) & (df_copy[date_col] <= boundaries.train_end)
    val_mask = (df_copy[date_col] >= boundaries.val_start) & (df_copy[date_col] <= boundaries.val_end)
    test_mask = (df_copy[date_col] >= boundaries.test_start) & (df_copy[date_col] <= boundaries.test_end)

    train_df = df_copy[train_mask].copy().reset_index(drop=True)
    val_df = df_copy[val_mask].copy().reset_index(drop=True)
    test_df = df_copy[test_mask].copy().reset_index(drop=True)

    if len(train_df) == 0:
        raise ValueError(f"Train split is empty for date range {boundaries.train_start} to {boundaries.train_end}")
    if len(val_df) == 0:
        raise ValueError(f"Validation split is empty for date range {boundaries.val_start} to {boundaries.val_end}")
    if len(test_df) == 0:
        raise ValueError(f"Test split is empty for date range {boundaries.test_start} to {boundaries.test_end}")

    return train_df, val_df, test_df
