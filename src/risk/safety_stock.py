"""Multi-tier safety stock and dynamic reorder point (ROP) calculation engine.

Calculates:
- Statistical Safety Stock (SS) incorporating demand variance and supplier lead-time variance:
  SS = Z_SL * sqrt(LT * sigma_D^2 + D_avg^2 * sigma_LT^2)
- Tiered Service Levels by ABC Revenue Classification:
  * Class A: 98% Service Level (Z = 2.05)
  * Class B: 95% Service Level (Z = 1.65)
  * Class C: 90% Service Level (Z = 1.28)
- Dynamic Reorder Point (ROP):
  ROP = Lead_Time_Demand + SS = sum_{t=1}^{LT}(D_hat_t) + SS
- Target Replenishment Inventory Level (Order-up-to S):
  S = ROP + (Cycle_Stock_Days * D_avg)
"""

import math
from typing import Dict, Optional
import numpy as np
import pandas as pd
from sqlalchemy.engine import Engine

from src.analytics.segmentation import compute_abc_xyz_segmentation
from src.analytics.supplier import compute_supplier_scorecards


Z_SERVICE_LEVELS: Dict[str, float] = {
    "A": 2.05,  # 98% Service Level
    "B": 1.65,  # 95% Service Level
    "C": 1.28,  # 90% Service Level
}


def calculate_safety_stock(
    lead_time_days: int,
    lead_time_stddev: float,
    avg_daily_demand: float,
    demand_stddev: float,
    abc_class: str = "A",
) -> float:
    """Calculate statistical safety stock combining demand and lead-time variance."""
    z_score = Z_SERVICE_LEVELS.get(abc_class.upper(), 1.65)
    lt = max(1, lead_time_days)
    sigma_d = max(0.1, demand_stddev)
    sigma_lt = max(0.0, lead_time_stddev)
    d_avg = max(0.01, avg_daily_demand)

    # SS = Z * sqrt(LT * sigma_D^2 + D_avg^2 * sigma_LT^2)
    combined_variance = (lt * (sigma_d ** 2)) + ((d_avg ** 2) * (sigma_lt ** 2))
    ss = z_score * math.sqrt(combined_variance)
    return round(float(ss), 2)


def compute_node_reorder_points(
    simulation_df: pd.DataFrame,
    engine: Engine,
    cycle_stock_days: int = 14,
) -> pd.DataFrame:
    """Enrich simulation DataFrame with ABC/XYZ tiers, supplier lead-time stats, SS, and ROP.

    Args:
        simulation_df: DataFrame from simulate_network_runout.
        engine: Database engine to query ABC/XYZ and supplier scorecards.
        cycle_stock_days: Number of days demand to target as cycle replenishment stock.

    Returns:
        DataFrame enriched with safety_stock, reorder_point, inventory_position, and target_stock.
    """
    # 1. Fetch ABC/XYZ segments and supplier metrics
    seg_df = compute_abc_xyz_segmentation(engine)[["product_id", "abc_class", "xyz_class", "abc_xyz_segment", "std_daily_demand"]]
    sup_df = compute_supplier_scorecards(engine)[["supplier_id", "lead_time_stddev"]]

    # Map supplier to product via relational query
    with engine.connect() as conn:
        prod_sup_df = pd.read_sql_query(
            "SELECT DISTINCT product_id, supplier_id FROM supplier_deliveries;", conn
        )

    prod_metrics = pd.merge(seg_df, prod_sup_df, on="product_id", how="left")
    prod_metrics = pd.merge(prod_metrics, sup_df, on="supplier_id", how="left")
    prod_metrics["lead_time_stddev"] = prod_metrics["lead_time_stddev"].fillna(1.0)
    prod_metrics["std_daily_demand"] = prod_metrics["std_daily_demand"].fillna(1.0)

    # 2. Merge with simulation DataFrame
    merged = pd.merge(simulation_df, prod_metrics, on="product_id", how="left")

    records = []
    for _, row in merged.iterrows():
        lt = int(row["standard_lead_time_days"])
        d_avg = float(row["avg_daily_forecast"])
        abc = str(row["abc_class"]) if pd.notna(row["abc_class"]) else "A"
        sigma_d = float(row["std_daily_demand"]) if pd.notna(row["std_daily_demand"]) else 1.0
        sigma_lt = float(row["lead_time_stddev"]) if pd.notna(row["lead_time_stddev"]) else 1.0

        # Safety Stock
        ss = calculate_safety_stock(
            lead_time_days=lt,
            lead_time_stddev=sigma_lt,
            avg_daily_demand=d_avg,
            demand_stddev=sigma_d,
            abc_class=abc,
        )

        # Lead time forecast demand
        lead_time_demand = round(lt * d_avg, 2)

        # Reorder Point (ROP)
        rop = round(lead_time_demand + ss, 2)

        # Net Inventory Position = available + in_transit
        inv_pos = round(float(row["starting_available_stock"]) + float(row["in_transit_units"]), 2)

        # Target Order-Up-To Level S
        target_s = round(rop + (cycle_stock_days * d_avg), 2)

        # Reorder Trigger Flag
        reorder_triggered = inv_pos <= rop

        row_dict = row.to_dict()
        row_dict.update({
            "lead_time_demand": lead_time_demand,
            "safety_stock": ss,
            "reorder_point": rop,
            "inventory_position": inv_pos,
            "target_inventory_level": target_s,
            "reorder_triggered": reorder_triggered,
        })
        records.append(row_dict)

    return pd.DataFrame(records)
