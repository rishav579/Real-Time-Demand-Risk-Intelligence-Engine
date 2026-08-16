"""Feature engineering pipeline for demand forecasting.

Constructs strictly non-leaking tabular features per SKU x Location time series:
- Autoregressive Lags: lag_1, lag_7, lag_14, lag_28
- Rolling Statistics: rolling_mean_7, rolling_mean_14, rolling_std_7 (anchored strictly on historical lags)
- Calendar Indicators: day_of_week, month, is_weekend, is_holiday
- Promotional & Pricing Telemetry: promotion_active, discount_pct, unit_price, unit_cost
- Operational Supply Attributes: standard_lead_time_days
- Target Variable: units_demanded (true unconstrained customer demand)
"""

from datetime import date
from typing import List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


FEATURE_COLUMNS: List[str] = [
    "lag_1",
    "lag_7",
    "lag_14",
    "lag_28",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_std_7",
    "day_of_week",
    "month",
    "is_weekend",
    "is_holiday",
    "promotion_active",
    "discount_pct",
    "unit_price",
    "unit_cost",
    "standard_lead_time_days",
]

TARGET_COLUMN: str = "units_demanded"


def load_raw_timeseries_data(engine: Engine) -> pd.DataFrame:
    """Extract raw daily sales transactions joined with calendar, product, and promotion dimensions."""
    query = text("""
        SELECT 
            s.transaction_date,
            s.location_id,
            l.location_name,
            l.region,
            l.location_type,
            s.product_id,
            p.sku,
            p.name AS product_name,
            p.category,
            p.unit_cost,
            p.unit_price,
            p.standard_lead_time_days,
            c.day_of_week,
            c.month,
            c.is_weekend,
            c.is_holiday,
            CASE WHEN s.promotion_id IS NOT NULL THEN 1 ELSE 0 END AS promotion_active,
            s.discount_pct,
            s.units_demanded,
            s.units_sold,
            s.unfulfilled_units,
            s.total_revenue
        FROM sales_transactions s
        JOIN calendar_dim c ON s.transaction_date = c.date_key
        JOIN locations l ON s.location_id = l.location_id
        JOIN products p ON s.product_id = p.product_id
        ORDER BY s.location_id, s.product_id, s.transaction_date;
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)

    df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.date
    return df


def engineer_forecasting_features(
    df: pd.DataFrame,
    target_col: str = TARGET_COLUMN,
    fill_na: bool = True,
) -> pd.DataFrame:
    """Engineer autoregressive lag, rolling statistics, calendar, and operational features.

    Features are calculated independently per (location_id, product_id) series.
    All rolling statistics use shift(1) so that target demand at step t is never seen.

    Args:
        df: Input DataFrame with raw time series transactions.
        target_col: Target demand column to engineer lags and rolling statistics from.
        fill_na: If True, backfills or zero-fills initial missing lag windows cleanly.

    Returns:
        DataFrame enriched with engineered features.
    """
    df_sorted = df.sort_values(["location_id", "product_id", "transaction_date"]).copy()

    # Group by time series series
    grouped = df_sorted.groupby(["location_id", "product_id"])

    # 1. Autoregressive Lags
    df_sorted["lag_1"] = grouped[target_col].shift(1)
    df_sorted["lag_7"] = grouped[target_col].shift(7)
    df_sorted["lag_14"] = grouped[target_col].shift(14)
    df_sorted["lag_28"] = grouped[target_col].shift(28)

    # 2. Rolling Statistics (computed strictly on shifted historical data)
    # rolling on shift(1) ensures no current-day target leakage
    shifted_target = grouped[target_col].shift(1)
    
    # We apply rolling within groups on the shifted series
    df_sorted["rolling_mean_7"] = (
        df_sorted.groupby(["location_id", "product_id"])[target_col]
        .transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
    )
    df_sorted["rolling_mean_14"] = (
        df_sorted.groupby(["location_id", "product_id"])[target_col]
        .transform(lambda s: s.shift(1).rolling(14, min_periods=1).mean())
    )
    df_sorted["rolling_std_7"] = (
        df_sorted.groupby(["location_id", "product_id"])[target_col]
        .transform(lambda s: s.shift(1).rolling(7, min_periods=1).std().fillna(0.0))
    )

    if fill_na:
        # For initial rows where lag_28 or lag_14 is NaN, backfill from available lags / rolling mean
        df_sorted["lag_1"] = df_sorted["lag_1"].bfill().fillna(0.0)
        df_sorted["lag_7"] = df_sorted["lag_7"].fillna(df_sorted["lag_1"])
        df_sorted["lag_14"] = df_sorted["lag_14"].fillna(df_sorted["lag_7"])
        df_sorted["lag_28"] = df_sorted["lag_28"].fillna(df_sorted["lag_14"])
        df_sorted["rolling_mean_7"] = df_sorted["rolling_mean_7"].fillna(df_sorted["lag_1"])
        df_sorted["rolling_mean_14"] = df_sorted["rolling_mean_14"].fillna(df_sorted["rolling_mean_7"])
        df_sorted["rolling_std_7"] = df_sorted["rolling_std_7"].fillna(0.0)

    return df_sorted.reset_index(drop=True)


def build_forecasting_dataset(engine: Engine) -> pd.DataFrame:
    """Extract raw data from database and build the complete forecasting feature matrix."""
    raw_df = load_raw_timeseries_data(engine)
    return engineer_forecasting_features(raw_df)
