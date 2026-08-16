"""Forecast-aware inventory simulation and dynamic runout date calculation engine.

Simulates daily inventory trajectories per SKU x Location node:
- Starting net available stock = on_hand_qty - reserved_qty
- Consumes 30-day daily point forecasts from the champion LightGBM model
- Beyond 30 days, projects the trailing 7-day average forecast flat up to max_simulation_days
- Accounts for scheduled in-transit purchase order arrival dates
- Calculates exact Days-to-Runout (DTR) and distinguishes between:
  * Runout within 30-day horizon (DTR <= 30)
  * Projected runout beyond 30-day horizon (30 < DTR <= max_simulation_days) via trailing-7-day continuation
  * No runout within extended horizon (DTR = inf or > max_simulation_days)
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class DailySimulationStep:
    """Detailed state for a single day of inventory simulation."""
    day_index: int
    simulated_date: date
    starting_stock: float
    inbound_receipts: float
    forecast_demand: float
    ending_stock: float
    is_stockout: bool


@dataclass(frozen=True)
class RunoutSimulationResult:
    """Consolidated inventory runout simulation outcome for a SKU x Location node."""
    location_id: str
    product_id: str
    as_of_date: date
    starting_available_stock: float
    in_transit_units: float
    lead_time_days: int
    forecast_demand_30d: float
    avg_daily_forecast: float
    days_to_runout: float
    runout_date: Optional[date]
    runout_horizon_category: str  # "WITHIN_30D", "BEYOND_30D_PROJECTION", "NO_RUNOUT"
    trajectory: List[DailySimulationStep]


def simulate_node_runout(
    location_id: str,
    product_id: str,
    as_of_date: date,
    starting_stock: float,
    lead_time_days: int,
    daily_forecasts: List[float],
    scheduled_inbound: Optional[Dict[int, float]] = None,
    max_simulation_days: int = 180,
) -> RunoutSimulationResult:
    """Execute discrete daily balance simulation for a single SKU x Location node.

    Args:
        location_id: Facility identifier.
        product_id: Product SKU identifier.
        as_of_date: Starting simulation date.
        starting_stock: Net available stock (on_hand - reserved) at t0.
        lead_time_days: Standard supplier replenishment lead time.
        daily_forecasts: List of daily forecast values (length up to 30).
        scheduled_inbound: Map of day_index (1-based) to inbound delivery units.
        max_simulation_days: Maximum extended simulation horizon for slow-moving runout projection.

    Returns:
        RunoutSimulationResult with exact runout date and trajectory.
    """
    inbound_map = scheduled_inbound or {}
    total_in_transit = sum(inbound_map.values())

    # Build daily demand stream for max_simulation_days
    # Use 30-day forecast directly, then project trailing 7-day average flat
    num_fc_days = len(daily_forecasts)
    if num_fc_days == 0:
        daily_demand_stream = [0.0] * max_simulation_days
    elif num_fc_days >= 30:
        trailing_7d_avg = float(np.mean(daily_forecasts[-7:]))
        daily_demand_stream = list(daily_forecasts[:30]) + [trailing_7d_avg] * (max_simulation_days - 30)
    else:
        trailing_avg = float(np.mean(daily_forecasts))
        daily_demand_stream = list(daily_forecasts) + [trailing_avg] * (max_simulation_days - len(daily_forecasts))

    current_stock = float(starting_stock)
    trajectory: List[DailySimulationStep] = []
    days_to_runout: float = float("inf")
    runout_date: Optional[date] = None

    for day_idx in range(1, max_simulation_days + 1):
        sim_date = as_of_date + timedelta(days=day_idx)
        inbound_qty = float(inbound_map.get(day_idx, 0.0))
        demand_qty = max(0.0, float(daily_demand_stream[day_idx - 1]))

        start_bal = current_stock
        end_bal = start_bal + inbound_qty - demand_qty
        is_so = end_bal <= 0.0

        trajectory.append(
            DailySimulationStep(
                day_index=day_idx,
                simulated_date=sim_date,
                starting_stock=round(start_bal, 2),
                inbound_receipts=round(inbound_qty, 2),
                forecast_demand=round(demand_qty, 2),
                ending_stock=round(end_bal, 2),
                is_stockout=is_so,
            )
        )

        if is_so and days_to_runout == float("inf"):
            # Fractional day estimation within the step
            if demand_qty > 0:
                fractional_day = min(1.0, max(0.0, (start_bal + inbound_qty) / demand_qty))
                days_to_runout = round((day_idx - 1) + fractional_day, 1)
            else:
                days_to_runout = float(day_idx)
            runout_date = sim_date

        current_stock = max(0.0, end_bal)

    # Classify horizon category
    if days_to_runout <= 30.0:
        horizon_category = "WITHIN_30D"
    elif days_to_runout <= max_simulation_days:
        horizon_category = "BEYOND_30D_PROJECTION"
    else:
        horizon_category = "NO_RUNOUT"

    fc_30d = float(sum(daily_demand_stream[:30]))
    avg_d = round(fc_30d / 30.0, 2) if fc_30d > 0 else 0.01

    return RunoutSimulationResult(
        location_id=location_id,
        product_id=product_id,
        as_of_date=as_of_date,
        starting_available_stock=round(starting_stock, 2),
        in_transit_units=round(total_in_transit, 2),
        lead_time_days=lead_time_days,
        forecast_demand_30d=round(fc_30d, 2),
        avg_daily_forecast=avg_d,
        days_to_runout=days_to_runout,
        runout_date=runout_date,
        runout_horizon_category=horizon_category,
        trajectory=trajectory,
    )


def simulate_network_runout(
    engine: Engine,
    predictions_df: pd.DataFrame,
    as_of_date: Optional[date] = None,
    max_simulation_days: int = 180,
) -> pd.DataFrame:
    """Run discrete inventory runout simulation across all active facility-SKU nodes in the network.

    Args:
        engine: Database engine with relational snapshots and POs.
        predictions_df: DataFrame containing daily point forecasts [transaction_date, location_id, product_id, y_pred].
        as_of_date: Reference analysis date (defaults to MAX date in DB).
        max_simulation_days: Maximum horizon for trailing-7-day continuation.

    Returns:
        DataFrame summarizing simulation runout metrics per node.
    """
    with engine.connect() as conn:
        if as_of_date is None:
            max_date_str = conn.execute(text("SELECT MAX(snapshot_date) FROM inventory_snapshots;")).scalar()
            analysis_date = date.fromisoformat(str(max_date_str))
        else:
            analysis_date = as_of_date

        # Query snapshot starting positions
        snap_query = text("""
            SELECT 
                s.location_id,
                l.location_name,
                l.location_type,
                s.product_id,
                p.sku,
                p.name AS product_name,
                p.category,
                p.unit_cost,
                p.unit_price,
                p.standard_lead_time_days,
                s.on_hand_qty,
                s.reserved_qty,
                s.available_qty AS available_stock,
                s.in_transit_qty
            FROM inventory_snapshots s
            JOIN locations l ON s.location_id = l.location_id
            JOIN products p ON s.product_id = p.product_id
            WHERE s.snapshot_date = :as_of_date
            ORDER BY s.location_id, s.product_id;
        """)
        snap_df = pd.read_sql_query(snap_query, conn, params={"as_of_date": analysis_date})

        # Query open in-transit POs with promised delivery dates
        po_query = text("""
            SELECT 
                po.destination_location_id AS location_id,
                po.product_id,
                po.promised_delivery_date,
                po.qty_ordered,
                po.qty_received
            FROM supplier_deliveries po
            WHERE po.po_status IN ('PLACED', 'IN_TRANSIT')
               OR (po.po_status = 'DELIVERED' AND po.actual_delivery_date > :as_of_date);
        """)
        open_pos_df = pd.read_sql_query(po_query, conn, params={"as_of_date": analysis_date})

    results = []
    for _, row in snap_df.iterrows():
        loc_id = row["location_id"]
        prod_id = row["product_id"]
        avail_stock = float(row["available_stock"])
        lt = int(row["standard_lead_time_days"])

        # Extract daily point forecasts for this node sorted chronologically
        node_fc = predictions_df[
            (predictions_df["location_id"] == loc_id) & (predictions_df["product_id"] == prod_id)
        ].sort_values("transaction_date")
        daily_fc_values = node_fc["y_pred"].tolist()

        # If location is DC and has no direct store forecasts, sum downstream store forecasts
        if row["location_type"] == "DC" and len(daily_fc_values) == 0:
            dc_fc = predictions_df[predictions_df["product_id"] == prod_id].groupby("transaction_date")["y_pred"].sum().tolist()
            daily_fc_values = dc_fc

        # Map scheduled inbound arrivals by day index
        inbound_map: Dict[int, float] = {}
        node_pos = open_pos_df[(open_pos_df["location_id"] == loc_id) & (open_pos_df["product_id"] == prod_id)]
        for _, po_row in node_pos.iterrows():
            prom_date = date.fromisoformat(str(po_row["promised_delivery_date"]))
            arrival_day_idx = (prom_date - analysis_date).days
            if 1 <= arrival_day_idx <= max_simulation_days:
                inbound_map[arrival_day_idx] = inbound_map.get(arrival_day_idx, 0.0) + float(po_row["qty_ordered"])

        sim_res = simulate_node_runout(
            location_id=loc_id,
            product_id=prod_id,
            as_of_date=analysis_date,
            starting_stock=avail_stock,
            lead_time_days=lt,
            daily_forecasts=daily_fc_values,
            scheduled_inbound=inbound_map,
            max_simulation_days=max_simulation_days,
        )

        results.append({
            "as_of_date": sim_res.as_of_date,
            "location_id": loc_id,
            "location_name": row["location_name"],
            "location_type": row["location_type"],
            "product_id": prod_id,
            "sku": row["sku"],
            "product_name": row["product_name"],
            "category": row["category"],
            "unit_cost": float(row["unit_cost"]),
            "unit_price": float(row["unit_price"]),
            "standard_lead_time_days": lt,
            "starting_available_stock": sim_res.starting_available_stock,
            "in_transit_units": sim_res.in_transit_units,
            "forecast_demand_30d": sim_res.forecast_demand_30d,
            "avg_daily_forecast": sim_res.avg_daily_forecast,
            "days_to_runout": sim_res.days_to_runout,
            "runout_date": sim_res.runout_date,
            "runout_horizon_category": sim_res.runout_horizon_category,
        })

    return pd.DataFrame(results)
