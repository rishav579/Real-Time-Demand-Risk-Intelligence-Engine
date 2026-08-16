"""Deterministic root-cause attribution engine for inventory risks.

Decomposes operational anomalies into an actionable, prioritized 6-category hierarchy:
1. DEMAND_SURGE: Forward forecast demand > 1.25x historical demand baseline (promotional or seasonal spike).
2. SUPPLIER_DELAY: Upstream supplier lead-time delay >= 2 days or late open PO.
3. UNDER_REPLENISHED: Inventory position <= ROP with zero in-transit replenishment POs placed.
4. INSUFFICIENT_SAFETY_BUFFER: High demand/lead-time variance consumed available safety stock.
5. SLOW_MOVING_DRAG: Excess capital locked in Class Z intermittent / long-tail catalog items.
6. OVER_ORDER_EXCESS: Excess inventory on fast/medium velocity items due to excessive lot sizing.
7. NOMINAL_STABLE: Balanced inventory position with low stockout and excess risk.
"""

from enum import Enum
from typing import Dict, List, Optional
import pandas as pd


class RootCauseCategory(str, Enum):
    """Deterministic root-cause attribution categories."""
    DEMAND_SURGE = "DEMAND_SURGE"
    SUPPLIER_DELAY = "SUPPLIER_DELAY"
    UNDER_REPLENISHED = "UNDER_REPLENISHED"
    INSUFFICIENT_SAFETY_BUFFER = "INSUFFICIENT_SAFETY_BUFFER"
    SLOW_MOVING_DRAG = "SLOW_MOVING_DRAG"
    OVER_ORDER_EXCESS = "OVER_ORDER_EXCESS"
    NOMINAL_STABLE = "NOMINAL_STABLE"


def attribute_node_root_cause(
    stockout_risk_tier: str,
    is_excess: bool,
    xyz_class: str,
    forecast_avg_demand: float,
    historical_avg_demand: float,
    in_transit_units: float,
    reorder_triggered: bool,
    supplier_delay_days: float = 0.0,
) -> RootCauseCategory:
    """Determine the primary operational root cause for a single SKU x Location node."""
    # 1. Check Stockout Risks
    if stockout_risk_tier in ("CRITICAL", "HIGH"):
        # Check Demand Surge (forward forecast > 1.25x historical demand)
        if historical_avg_demand > 0 and (forecast_avg_demand / historical_avg_demand) > 1.25:
            return RootCauseCategory.DEMAND_SURGE

        # Check Supplier Inbound Latency
        if supplier_delay_days >= 2.0:
            return RootCauseCategory.SUPPLIER_DELAY

        # Check Under-Replenishment (breached ROP but no PO in pipeline)
        if reorder_triggered and in_transit_units <= 0:
            return RootCauseCategory.UNDER_REPLENISHED

        # Otherwise Insufficient Safety Buffer
        return RootCauseCategory.INSUFFICIENT_SAFETY_BUFFER

    # 2. Check Excess Inventory Risks
    if is_excess:
        if xyz_class == "Z":
            return RootCauseCategory.SLOW_MOVING_DRAG
        else:
            return RootCauseCategory.OVER_ORDER_EXCESS

    # 3. Nominal Stable
    return RootCauseCategory.NOMINAL_STABLE


def compute_root_cause_attribution(
    risk_scored_df: pd.DataFrame,
    historical_demand_map: Optional[Dict[str, float]] = None,
    supplier_delay_map: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Enrich risk-scored DataFrame with deterministic root-cause attribution categories.

    Args:
        risk_scored_df: DataFrame from compute_risk_scoring.
        historical_demand_map: Map of (location_id, product_id) to 30-day historical average daily demand.
        supplier_delay_map: Map of supplier_id or product_id to average delay days.

    Returns:
        DataFrame enriched with root_cause and root_cause_explanation.
    """
    df = risk_scored_df.copy()
    hist_map = historical_demand_map or {}
    sup_delay_map = supplier_delay_map or {}

    root_causes = []
    explanations = []

    for _, row in df.iterrows():
        loc_id = row["location_id"]
        prod_id = row["product_id"]
        sup_id = row.get("supplier_id", "")
        tier = str(row["stockout_risk_tier"])
        is_ex = bool(row["is_excess"])
        xyz = str(row.get("xyz_class", "X"))
        fc_avg = float(row["avg_daily_forecast"])
        hist_avg = hist_map.get(f"{loc_id}_{prod_id}", fc_avg)
        in_transit = float(row["in_transit_units"])
        reorder_trig = bool(row["reorder_triggered"])
        sup_delay = sup_delay_map.get(sup_id, sup_delay_map.get(prod_id, 0.0))

        rc = attribute_node_root_cause(
            stockout_risk_tier=tier,
            is_excess=is_ex,
            xyz_class=xyz,
            forecast_avg_demand=fc_avg,
            historical_avg_demand=hist_avg,
            in_transit_units=in_transit,
            reorder_triggered=reorder_trig,
            supplier_delay_days=sup_delay,
        )

        if rc == RootCauseCategory.DEMAND_SURGE:
            expl = f"Forward demand ({fc_avg:.1f} u/d) surged above baseline ({hist_avg:.1f} u/d) due to promotional lift or seasonal peak."
        elif rc == RootCauseCategory.SUPPLIER_DELAY:
            expl = f"Upstream supplier delivery delay ({sup_delay:.1f} days) depleted on-hand buffer before replenishment arrival."
        elif rc == RootCauseCategory.UNDER_REPLENISHED:
            expl = f"Net inventory position ({row['inventory_position']:.0f} units) breached ROP ({row['reorder_point']:.0f} units) with zero open inbound POs."
        elif rc == RootCauseCategory.INSUFFICIENT_SAFETY_BUFFER:
            expl = f"Combined demand and lead-time variance exceeded static safety stock buffer ({row['safety_stock']:.0f} units)."
        elif rc == RootCauseCategory.SLOW_MOVING_DRAG:
            expl = f"Long-tail Class Z SKU with {row['days_of_supply_forecast']:.0f} days of supply locking up ${row['capital_at_risk']:.2f} working capital."
        elif rc == RootCauseCategory.OVER_ORDER_EXCESS:
            expl = f"Excess inventory holding ({row['days_of_supply_forecast']:.0f} DoS) exceeding 45-day operational target by {row['excess_units']:.0f} units."
        else:
            expl = f"Balanced position with {row['days_of_supply_forecast']:.0f} days of supply and healthy buffer coverage."

        root_causes.append(rc.value)
        explanations.append(expl)

    df["root_cause"] = root_causes
    df["root_cause_explanation"] = explanations

    return df
