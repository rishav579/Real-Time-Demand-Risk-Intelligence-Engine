"""Unified analytical data marts layer.

Provides consolidated access and persistence for core analytical marts:
1. mart_daily_product_velocity: Daily sales demand & revenue aggregations
2. mart_abc_xyz_segmentation: ABC Pareto revenue and XYZ volatility matrix
3. mart_supplier_performance: Comprehensive OTIF and lead-time scorecards
4. mart_inventory_health: SKU x Location inventory positions, DoS, and risk categories
"""

from datetime import date
from typing import Dict, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.analytics.inventory_health import compute_inventory_health
from src.analytics.segmentation import compute_abc_xyz_segmentation
from src.analytics.supplier import compute_supplier_scorecards, compute_supplier_sku_lead_times


def compute_daily_product_velocity(engine: Engine) -> pd.DataFrame:
    """Compute daily product velocity aggregations across category, location, and promotion dimensions."""
    query = text("""
        SELECT 
            s.transaction_date,
            c.month,
            c.month_name,
            c.is_weekend,
            c.is_holiday,
            l.location_id,
            l.location_name,
            l.region,
            p.product_id,
            p.sku,
            p.name AS product_name,
            p.category,
            pr.promotion_id,
            pr.promo_code,
            s.units_demanded,
            s.units_sold,
            s.unfulfilled_units,
            s.unit_selling_price,
            s.discount_pct,
            s.total_revenue
        FROM sales_transactions s
        JOIN calendar_dim c ON s.transaction_date = c.date_key
        JOIN locations l ON s.location_id = l.location_id
        JOIN products p ON s.product_id = p.product_id
        LEFT JOIN promotions pr ON s.promotion_id = pr.promotion_id
        ORDER BY s.transaction_date, l.location_id, p.product_id;
    """)

    with engine.connect() as conn:
        return pd.read_sql_query(query, conn)


def build_all_marts(
    engine: Engine,
    as_of_date: Optional[date] = None,
    persist_to_db: bool = True,
) -> Dict[str, pd.DataFrame]:
    """Execute and return all analytical data marts.

    Args:
        engine: Target SQLAlchemy database engine.
        as_of_date: Optional reference date for inventory health (defaults to MAX date in DB).
        persist_to_db: If True, writes computed DataFrames into SQLite tables prefixed with 'mart_'.

    Returns:
        Dictionary of DataFrame marts keyed by table name.
    """
    marts: Dict[str, pd.DataFrame] = {
        "mart_daily_product_velocity": compute_daily_product_velocity(engine),
        "mart_abc_xyz_segmentation": compute_abc_xyz_segmentation(engine),
        "mart_supplier_performance": compute_supplier_scorecards(engine),
        "mart_supplier_sku_lead_times": compute_supplier_sku_lead_times(engine),
        "mart_inventory_health": compute_inventory_health(engine, as_of_date=as_of_date),
    }

    if persist_to_db:
        with engine.begin() as conn:
            for mart_name, df in marts.items():
                df.to_sql(mart_name, conn, if_exists="replace", index=False)

    return marts
