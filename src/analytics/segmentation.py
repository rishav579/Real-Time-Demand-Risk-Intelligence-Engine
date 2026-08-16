"""ABC revenue and XYZ demand volatility segmentation engine.

Implements:
- ABC Segmentation: Annual network-wide gross revenue Pareto distribution at SKU level
  * Class A: Cumulative revenue <= 80%
  * Class B: Cumulative revenue > 80% and <= 95%
  * Class C: Cumulative revenue > 95%
- XYZ Segmentation: Demand volatility classification via Coefficient of Variation (CV)
  * Class X: CV <= 0.50 (Stable / predictable)
  * Class Y: 0.50 < CV <= 1.00 (Variable / promotional / seasonal)
  * Class Z: CV > 1.00 (Erratic / intermittent / slow-moving)
- Combined ABC-XYZ Matrix: 9 discrete operational segments (AX through CZ)
"""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Dict, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


class ABCClass(str, Enum):
    """ABC gross revenue importance classification."""
    A = "A"
    B = "B"
    C = "C"


class XYZClass(str, Enum):
    """XYZ demand predictability classification based on Coefficient of Variation."""
    X = "X"
    Y = "Y"
    Z = "Z"


@dataclass(frozen=True)
class SKUSegmentationResult:
    """Consolidated ABC/XYZ segmentation record for a single SKU."""
    product_id: str
    sku: str
    product_name: str
    category: str
    total_units_sold: int
    total_gross_revenue: float
    revenue_share_pct: float
    cumulative_revenue_pct: float
    abc_class: ABCClass
    mean_daily_demand: float
    std_daily_demand: float
    cv_demand: float
    xyz_class: XYZClass
    abc_xyz_segment: str


def compute_abc_xyz_segmentation(engine: Engine) -> pd.DataFrame:
    """Compute deterministic ABC/XYZ segmentation across all active catalog products.

    Uses SQL for aggregation over the complete 365-day analytical horizon.
    Calculates population standard deviation for daily demanded units.

    Returns:
        DataFrame with columns:
        [product_id, sku, product_name, category, total_units_sold, total_gross_revenue,
         revenue_share_pct, cumulative_revenue_pct, abc_class, mean_daily_demand,
         std_daily_demand, cv_demand, xyz_class, abc_xyz_segment]
    """
    # 1. Query Total Gross Revenue & Sales Volume per Product (All Stores, Full Year)
    revenue_query = text("""
        SELECT 
            p.product_id,
            p.sku,
            p.name AS product_name,
            p.category,
            COALESCE(SUM(s.units_sold), 0) AS total_units_sold,
            COALESCE(SUM(s.total_revenue), 0.0) AS total_gross_revenue
        FROM products p
        LEFT JOIN sales_transactions s ON p.product_id = s.product_id
        GROUP BY p.product_id, p.sku, p.name, p.category
        ORDER BY total_gross_revenue DESC, p.product_id ASC;
    """)

    with engine.connect() as conn:
        rev_df = pd.read_sql_query(revenue_query, conn)

    total_network_revenue = rev_df["total_gross_revenue"].sum()
    if total_network_revenue <= 0:
        total_network_revenue = 1.0

    # Calculate Revenue Share and Cumulative Percentage
    rev_df["revenue_share_pct"] = (rev_df["total_gross_revenue"] / total_network_revenue) * 100.0
    rev_df["cumulative_revenue_pct"] = rev_df["revenue_share_pct"].cumsum()

    # Assign ABC Classes
    def assign_abc(cum_pct: float, prev_cum_pct: float) -> str:
        # Standard Pareto: If previous item was under 80%, this item belongs to A (or if cum_pct <= 80)
        if cum_pct <= 80.0 or prev_cum_pct < 80.0:
            return ABCClass.A.value
        elif cum_pct <= 95.0 or prev_cum_pct < 95.0:
            return ABCClass.B.value
        else:
            return ABCClass.C.value

    # Compute previous cumulative percentage for boundary assignment
    prev_cum = [0.0] + list(rev_df["cumulative_revenue_pct"][:-1])
    abc_classes = [
        assign_abc(cum, prev) for cum, prev in zip(rev_df["cumulative_revenue_pct"], prev_cum)
    ]
    rev_df["abc_class"] = abc_classes

    # 2. Query Daily Demanded Units per Product across Network to compute Population CV
    # Query aggregated daily demand across all stores for each calendar day
    daily_demand_query = text("""
        SELECT 
            p.product_id,
            c.date_key,
            COALESCE(SUM(s.units_demanded), 0) AS daily_network_demand
        FROM products p
        CROSS JOIN calendar_dim c
        LEFT JOIN sales_transactions s 
            ON p.product_id = s.product_id 
            AND c.date_key = s.transaction_date
        GROUP BY p.product_id, c.date_key
        ORDER BY p.product_id, c.date_key;
    """)

    with engine.connect() as conn:
        daily_df = pd.read_sql_query(daily_demand_query, conn)

    # Group by product and calculate mean, population standard deviation (ddof=0), and CV
    volatility_stats = []
    for prod_id, group in daily_df.groupby("product_id"):
        demands = group["daily_network_demand"].values
        mean_d = float(demands.mean())
        # Population standard deviation ddof=0 since full 365-day population is present
        std_d = float(demands.std(ddof=0))
        cv = (std_d / mean_d) if mean_d > 0 else 0.0

        if cv <= 0.50:
            xyz = XYZClass.X.value
        elif cv <= 1.00:
            xyz = XYZClass.Y.value
        else:
            xyz = XYZClass.Z.value

        volatility_stats.append({
            "product_id": prod_id,
            "mean_daily_demand": round(mean_d, 2),
            "std_daily_demand": round(std_d, 2),
            "cv_demand": round(cv, 4),
            "xyz_class": xyz,
        })

    vol_df = pd.DataFrame(volatility_stats)

    # 3. Merge ABC and XYZ
    merged_df = pd.merge(rev_df, vol_df, on="product_id", how="left")
    merged_df["abc_xyz_segment"] = merged_df["abc_class"] + merged_df["xyz_class"]

    # Round floating values for presentation cleanliness
    merged_df["total_gross_revenue"] = merged_df["total_gross_revenue"].round(2)
    merged_df["revenue_share_pct"] = merged_df["revenue_share_pct"].round(2)
    merged_df["cumulative_revenue_pct"] = merged_df["cumulative_revenue_pct"].round(2)

    return merged_df
