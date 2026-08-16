"""Stockout risk scoring, excess inventory quantification, and capital-at-risk engine.

Calculates:
- Normalized Stockout Risk Score (0-100):
  SRS = min(100.0, max(0.0, (1.0 - DTR / LT) * 100.0))
- 4-Tier Stockout Severity Taxonomy:
  * CRITICAL: DTR <= LT (runout will occur before standard replenishment arrives)
  * HIGH: LT < DTR <= 1.5 * LT
  * MEDIUM: 1.5 * LT < DTR <= 2.0 * LT
  * LOW: DTR > 2.0 * LT
- Excess Inventory & Capital-at-Risk:
  * Excess Buffer: Days of Supply (DoS) > 90 days
  * Excess Units: max(0, Available Stock - 45 * D_avg)
  * Capital at Risk: Excess Units * unit_cost
  * Annual Holding Cost Exposure: Capital at Risk * 20%
"""

from enum import Enum
from typing import Optional
import numpy as np
import pandas as pd


class StockoutRiskTier(str, Enum):
    """Stockout severity classification tiers."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def calculate_stockout_risk_score(days_to_runout: float, lead_time_days: int) -> float:
    """Calculate normalized 0-100 Stockout Risk Score based on lead-time coverage."""
    if np.isinf(days_to_runout) or days_to_runout > 1000:
        return 0.0
    lt = max(1, lead_time_days)
    score = (1.0 - (days_to_runout / lt)) * 100.0
    return round(float(min(100.0, max(0.0, score))), 2)


def classify_stockout_tier(days_to_runout: float, lead_time_days: int) -> StockoutRiskTier:
    """Classify days-to-runout into exact 4-tier stockout severity taxonomy."""
    lt = max(1, lead_time_days)
    if days_to_runout <= lt:
        return StockoutRiskTier.CRITICAL
    elif days_to_runout <= 1.5 * lt:
        return StockoutRiskTier.HIGH
    elif days_to_runout <= 2.0 * lt:
        return StockoutRiskTier.MEDIUM
    else:
        return StockoutRiskTier.LOW


def compute_risk_scoring(enriched_node_df: pd.DataFrame) -> pd.DataFrame:
    """Compute stockout risk scores, tiers, excess inventory, and capital-at-risk across all nodes.

    Args:
        enriched_node_df: DataFrame from compute_node_reorder_points.

    Returns:
        DataFrame enriched with stockout_risk_score, stockout_risk_tier, is_excess,
        excess_units, capital_at_risk, and annual_holding_cost.
    """
    df = enriched_node_df.copy()

    risk_scores = []
    risk_tiers = []
    dos_list = []
    is_excess_list = []
    excess_units_list = []
    capital_at_risk_list = []
    holding_cost_list = []

    for _, row in df.iterrows():
        dtr = float(row["days_to_runout"])
        lt = int(row["standard_lead_time_days"])
        avail_stock = float(row["starting_available_stock"])
        d_avg = max(0.01, float(row["avg_daily_forecast"]))
        cost = float(row["unit_cost"])

        # Stockout Risk Score & Tier
        srs = calculate_stockout_risk_score(days_to_runout=dtr, lead_time_days=lt)
        tier = classify_stockout_tier(days_to_runout=dtr, lead_time_days=lt).value

        # Days of Supply (forecast-based)
        dos = round(avail_stock / d_avg, 1)

        # Excess Inventory (DoS > 90 days, target buffer 45 days)
        is_excess = dos > 90.0
        excess_u = max(0.0, avail_stock - (45.0 * d_avg)) if is_excess else 0.0
        cap_risk = round(excess_u * cost, 2)
        hold_cost = round(cap_risk * 0.20, 2)

        risk_scores.append(srs)
        risk_tiers.append(tier)
        dos_list.append(dos)
        is_excess_list.append(is_excess)
        excess_units_list.append(round(excess_u, 2))
        capital_at_risk_list.append(cap_risk)
        holding_cost_list.append(hold_cost)

    df["days_of_supply_forecast"] = dos_list
    df["stockout_risk_score"] = risk_scores
    df["stockout_risk_tier"] = risk_tiers
    df["is_excess"] = is_excess_list
    df["excess_units"] = excess_units_list
    df["capital_at_risk"] = capital_at_risk_list
    df["annual_holding_cost"] = holding_cost_list

    return df
