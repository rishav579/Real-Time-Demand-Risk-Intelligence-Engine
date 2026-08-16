"""Prescriptive replenishment action and explainable recommendation engine.

Generates actionable operational recommendations:
1. DC_TRANSFER: Expedited lateral transfer from Central DC (LOC-DC-01) with 2-day lead time when DC has surplus stock (> 2 * DC Safety Stock).
2. PURCHASE_ORDER: Direct supplier reorder to target inventory position S when transfer is unavailable or for DC replenishment.
3. HOLD_ORDER / PROMOTION_CANDIDATE: Pauses replenishment on excess inventory (> 90 DoS) and flags markdown bundling opportunities.

Enforces explainable decision support with quantitative metrics, root-cause attribution, and natural language rationale.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, List, Optional
import math
import pandas as pd


class ActionType(str, Enum):
    """Prescriptive operational action types."""
    DC_TRANSFER = "DC_TRANSFER"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    HOLD_ORDER = "HOLD_ORDER"
    PROMOTION_CANDIDATE = "PROMOTION_CANDIDATE"


class PriorityTier(str, Enum):
    """Action execution priority tiers."""
    URGENT = "URGENT"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class ActionRecommendation:
    """Consolidated prescriptive action recommendation with explainable audit trail."""
    recommendation_id: str
    created_date: date
    location_id: str
    location_name: str
    product_id: str
    sku: str
    product_name: str
    abc_xyz_segment: str
    action_type: ActionType
    priority_tier: PriorityTier
    current_available_stock: float
    forecast_daily_demand: float
    days_to_runout: float
    safety_stock: float
    reorder_point: float
    recommended_qty: int
    source_identifier: str
    root_cause: str
    rationale_text: str


def generate_prescriptive_recommendations(
    attributed_risk_df: pd.DataFrame,
    dc_location_id: str = "LOC-DC-01",
    expedited_transfer_lead_time_days: int = 2,
) -> pd.DataFrame:
    """Generate prioritized, explainable prescriptive recommendations for all risk-triggered nodes.

    Args:
        attributed_risk_df: DataFrame output from compute_root_cause_attribution.
        dc_location_id: Central DC location identifier.
        expedited_transfer_lead_time_days: Expedited transfer transit time.

    Returns:
        DataFrame containing prioritized ActionRecommendations.
    """
    df = attributed_risk_df.copy()

    # Build DC inventory surplus map: available stock - 2 * safety stock
    dc_rows = df[df["location_id"] == dc_location_id].set_index("product_id")
    dc_surplus_map: Dict[str, float] = {}
    for prod_id, dc_row in dc_rows.iterrows():
        avail = float(dc_row["starting_available_stock"])
        ss = float(dc_row["safety_stock"])
        surplus = max(0.0, avail - (2.0 * ss))
        dc_surplus_map[str(prod_id)] = surplus

    recommendations: List[Dict] = []
    rec_counter = 1

    for _, row in df.iterrows():
        loc_id = row["location_id"]
        loc_type = row["location_type"]
        prod_id = row["product_id"]
        tier = str(row["stockout_risk_tier"])
        is_ex = bool(row["is_excess"])
        reorder_trig = bool(row["reorder_triggered"])
        abc = str(row.get("abc_class", "A"))
        abc_xyz = str(row.get("abc_xyz_segment", "AX"))
        dtr = float(row["days_to_runout"])
        lt = int(row["standard_lead_time_days"])
        avail = float(row["starting_available_stock"])
        inv_pos = float(row["inventory_position"])
        target_s = float(row["target_inventory_level"])
        d_avg = float(row["avg_daily_forecast"])
        rc = str(row["root_cause"])
        as_of = row["as_of_date"]

        # Net deficit to target position
        deficit = max(0.0, target_s - inv_pos)

        # 1. Evaluate Stockout Replenishment (Triggered or Critical/High Risk)
        if reorder_trig or tier in ("CRITICAL", "HIGH"):
            # Check if Store and DC has surplus stock for expedited transfer
            dc_surplus = dc_surplus_map.get(prod_id, 0.0)
            if loc_type == "STORE" and tier == "CRITICAL" and dc_surplus >= 10.0:
                # DC Lateral Transfer
                transfer_qty = int(math.ceil(min(deficit, dc_surplus)))
                if transfer_qty > 0:
                    dc_surplus_map[prod_id] -= transfer_qty  # update available surplus
                    action_type = ActionType.DC_TRANSFER
                    source_id = dc_location_id
                    priority = PriorityTier.URGENT if abc == "A" else PriorityTier.HIGH
                    rationale = (
                        f"CRITICAL stockout in {dtr:.1f} days (under standard LT of {lt}d). "
                        f"Expedited DC transfer of {transfer_qty} units from {dc_location_id} (2-day transit) "
                        f"mitigates runout without supplier latency. Root Cause: {rc}."
                    )
                    recommendations.append({
                        "recommendation_id": f"REC-{as_of.strftime('%Y%m%d') if isinstance(as_of, date) else as_of}-{rec_counter:03d}",
                        "created_date": as_of,
                        "location_id": loc_id,
                        "location_name": row["location_name"],
                        "product_id": prod_id,
                        "sku": row["sku"],
                        "product_name": row["product_name"],
                        "abc_xyz_segment": abc_xyz,
                        "action_type": action_type.value,
                        "priority_tier": priority.value,
                        "current_available_stock": avail,
                        "forecast_daily_demand": d_avg,
                        "days_to_runout": dtr,
                        "safety_stock": row["safety_stock"],
                        "reorder_point": row["reorder_point"],
                        "recommended_qty": transfer_qty,
                        "source_identifier": source_id,
                        "root_cause": rc,
                        "rationale_text": rationale,
                    })
                    rec_counter += 1
                    continue

            # Otherwise Supplier Purchase Order
            po_qty = int(math.ceil(deficit))
            if po_qty > 0:
                action_type = ActionType.PURCHASE_ORDER
                source_id = row.get("supplier_id", "PRIMARY_SUPPLIER")
                if tier == "CRITICAL":
                    priority = PriorityTier.URGENT if abc == "A" else PriorityTier.HIGH
                elif tier == "HIGH":
                    priority = PriorityTier.HIGH if abc == "A" else PriorityTier.MEDIUM
                else:
                    priority = PriorityTier.MEDIUM

                rationale = (
                    f"Inventory position ({inv_pos:.0f} units) breached ROP ({row['reorder_point']:.0f} units). "
                    f"Recommend PO for {po_qty} units to restore buffer to target level {target_s:.0f} units. "
                    f"Root Cause: {rc}."
                )
                recommendations.append({
                    "recommendation_id": f"REC-{as_of.strftime('%Y%m%d') if isinstance(as_of, date) else as_of}-{rec_counter:03d}",
                    "created_date": as_of,
                    "location_id": loc_id,
                    "location_name": row["location_name"],
                    "product_id": prod_id,
                    "sku": row["sku"],
                    "product_name": row["product_name"],
                    "abc_xyz_segment": abc_xyz,
                    "action_type": action_type.value,
                    "priority_tier": priority.value,
                    "current_available_stock": avail,
                    "forecast_daily_demand": d_avg,
                    "days_to_runout": dtr,
                    "safety_stock": row["safety_stock"],
                    "reorder_point": row["reorder_point"],
                    "recommended_qty": po_qty,
                    "source_identifier": source_id,
                    "root_cause": rc,
                    "rationale_text": rationale,
                })
                rec_counter += 1
                continue

        # 2. Evaluate Excess Inventory Actions
        if is_ex:
            action_type = ActionType.PROMOTION_CANDIDATE if abc in ("A", "B") else ActionType.HOLD_ORDER
            priority = PriorityTier.LOW
            rationale = (
                f"Excess stock position with {row['days_of_supply_forecast']:.0f} Days of Supply "
                f"({row['excess_units']:.0f} excess units, ${row['capital_at_risk']:.2f} capital at risk). "
                f"Pause replenishment orders and evaluate markdown / bundling. Root Cause: {rc}."
            )
            recommendations.append({
                "recommendation_id": f"REC-{as_of.strftime('%Y%m%d') if isinstance(as_of, date) else as_of}-{rec_counter:03d}",
                "created_date": as_of,
                "location_id": loc_id,
                "location_name": row["location_name"],
                "product_id": prod_id,
                "sku": row["sku"],
                "product_name": row["product_name"],
                "abc_xyz_segment": abc_xyz,
                "action_type": action_type.value,
                "priority_tier": priority.value,
                "current_available_stock": avail,
                "forecast_daily_demand": d_avg,
                "days_to_runout": dtr,
                "safety_stock": row["safety_stock"],
                "reorder_point": row["reorder_point"],
                "recommended_qty": 0,
                "source_identifier": "INVENTORY_HOLD",
                "root_cause": rc,
                "rationale_text": rationale,
            })
            rec_counter += 1

    rec_df = pd.DataFrame(recommendations)
    if len(rec_df) == 0:
        return pd.DataFrame()

    # Prioritize: URGENT -> HIGH -> MEDIUM -> LOW
    priority_order = {"URGENT": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}
    rec_df["priority_rank"] = rec_df["priority_tier"].map(priority_order)
    return rec_df.sort_values(["priority_rank", "days_to_runout"]).drop(columns=["priority_rank"]).reset_index(drop=True)
