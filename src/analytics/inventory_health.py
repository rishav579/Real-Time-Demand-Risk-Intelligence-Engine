"""Inventory health, Days-of-Supply (DoS), and operational risk classification engine.

Calculates SKU x Location level metrics:
- 30-day Average Daily Demand (ADD30)
- Current available inventory buffer
- Days of Supply (DoS)
- Stockout frequency over 30d and full-year windows
- Deterministic Risk Classification:
  * CRITICAL: DoS <= lead_time
  * LOW_BUFFER: lead_time < DoS <= 1.5 * lead_time
  * HEALTHY: 1.5 * lead_time < DoS <= 45
  * ELEVATED_BUFFER: 45 < DoS <= 90
  * EXCESS: DoS > 90
"""

from datetime import date, timedelta
from enum import Enum
from typing import Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


class InventoryRiskCategory(str, Enum):
    """Operational risk categories for SKU x Location inventory positions."""
    CRITICAL = "CRITICAL"
    LOW_BUFFER = "LOW_BUFFER"
    HEALTHY = "HEALTHY"
    ELEVATED_BUFFER = "ELEVATED_BUFFER"
    EXCESS = "EXCESS"


def classify_inventory_risk(dos: float, lead_time_days: int) -> InventoryRiskCategory:
    """Classify an inventory position into exactly one operational risk category."""
    if dos <= lead_time_days:
        return InventoryRiskCategory.CRITICAL
    elif dos <= 1.5 * lead_time_days:
        return InventoryRiskCategory.LOW_BUFFER
    elif dos <= 45.0:
        return InventoryRiskCategory.HEALTHY
    elif dos <= 90.0:
        return InventoryRiskCategory.ELEVATED_BUFFER
    else:
        return InventoryRiskCategory.EXCESS


def compute_inventory_health(
    engine: Engine,
    as_of_date: Optional[date] = None,
) -> pd.DataFrame:
    """Compute deterministic SKU x Location inventory health metrics and risk categories.

    Uses the latest available snapshot date in the database if as_of_date is omitted.

    Returns:
        DataFrame with columns:
        [as_of_date, location_id, location_name, location_type, product_id, sku,
         product_name, category, on_hand_qty, in_transit_qty, reserved_qty,
         available_stock, standard_lead_time_days, add_30d, days_of_supply,
         stockout_days_30d, stockout_days_365d, risk_category]
    """
    with engine.connect() as conn:
        # Determine analysis date (latest available snapshot in data)
        if as_of_date is None:
            max_date_str = conn.execute(text("SELECT MAX(snapshot_date) FROM inventory_snapshots;")).scalar()
            if max_date_str is None:
                return pd.DataFrame()
            if isinstance(max_date_str, str):
                analysis_date = date.fromisoformat(max_date_str)
            else:
                analysis_date = max_date_str
        else:
            analysis_date = as_of_date

        start_30d = analysis_date - timedelta(days=29)

        # 1. Query Current As-Of Snapshot & Master Details
        snapshot_query = text("""
            SELECT 
                s.snapshot_date AS as_of_date,
                l.location_id,
                l.location_name,
                l.location_type,
                p.product_id,
                p.sku,
                p.name AS product_name,
                p.category,
                p.standard_lead_time_days,
                s.on_hand_qty,
                s.in_transit_qty,
                s.reserved_qty,
                s.available_qty AS available_stock
            FROM inventory_snapshots s
            JOIN locations l ON s.location_id = l.location_id
            JOIN products p ON s.product_id = p.product_id
            WHERE s.snapshot_date = :as_of_date
            ORDER BY l.location_id, p.product_id;
        """)

        snap_df = pd.read_sql_query(snapshot_query, conn, params={"as_of_date": analysis_date})

        # 2. Query 30-Day Demanded Units (for Stores) or Outbound Draw (for DC)
        demand_30d_query = text("""
            SELECT 
                location_id,
                product_id,
                COALESCE(SUM(units_demanded), 0) AS total_demand_30d
            FROM sales_transactions
            WHERE transaction_date BETWEEN :start_30d AND :as_of_date
            GROUP BY location_id, product_id;
        """)
        demand_df = pd.read_sql_query(
            demand_30d_query,
            conn,
            params={"start_30d": start_30d, "as_of_date": analysis_date},
        )

        # 3. Query Historical Stockout Days (30d and Full Year)
        stockout_query = text("""
            SELECT 
                location_id,
                product_id,
                SUM(CASE WHEN snapshot_date BETWEEN :start_30d AND :as_of_date THEN stockout_flag ELSE 0 END) AS stockout_days_30d,
                SUM(stockout_flag) AS stockout_days_365d
            FROM inventory_snapshots
            GROUP BY location_id, product_id;
        """)
        so_df = pd.read_sql_query(
            stockout_query,
            conn,
            params={"start_30d": start_30d, "as_of_date": analysis_date},
        )

    # Merge Snapshots with Demand and Stockouts
    merged = pd.merge(snap_df, demand_df, on=["location_id", "product_id"], how="left")
    merged["total_demand_30d"] = merged["total_demand_30d"].fillna(0)

    # For Distribution Center, if no direct sales transactions exist, aggregate downstream store demand
    dc_mask = merged["location_type"] == "DC"
    if dc_mask.any():
        network_demand_30d = demand_df.groupby("product_id")["total_demand_30d"].sum().to_dict()
        for idx in merged[dc_mask].index:
            p_id = merged.at[idx, "product_id"]
            merged.at[idx, "total_demand_30d"] = network_demand_30d.get(p_id, 0)

    merged = pd.merge(merged, so_df, on=["location_id", "product_id"], how="left")
    merged["stockout_days_30d"] = merged["stockout_days_30d"].fillna(0).astype(int)
    merged["stockout_days_365d"] = merged["stockout_days_365d"].fillna(0).astype(int)

    # Calculate ADD30 and DoS
    merged["add_30d"] = (merged["total_demand_30d"] / 30.0).round(2)
    merged["days_of_supply"] = (
        merged["available_stock"] / merged["add_30d"].clip(lower=0.01)
    ).round(1)

    # Assign Risk Category
    merged["risk_category"] = [
        classify_inventory_risk(dos=dos, lead_time_days=int(lt)).value
        for dos, lt in zip(merged["days_of_supply"], merged["standard_lead_time_days"])
    ]

    # Clean up output columns
    output_cols = [
        "as_of_date",
        "location_id",
        "location_name",
        "location_type",
        "product_id",
        "sku",
        "product_name",
        "category",
        "on_hand_qty",
        "in_transit_qty",
        "reserved_qty",
        "available_stock",
        "standard_lead_time_days",
        "add_30d",
        "days_of_supply",
        "stockout_days_30d",
        "stockout_days_365d",
        "risk_category",
    ]

    return merged[output_cols].sort_values(["location_id", "product_id"]).reset_index(drop=True)
