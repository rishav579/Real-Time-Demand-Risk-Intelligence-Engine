"""Supplier scorecard and lead-time variance analytics engine.

Calculates:
- Operational fulfillment metrics: total POs, delivered POs, On-Time In-Full (OTIF) rates
- Quality & Lead-time statistics: Average lead time, lead time standard deviation, max delay
- Financial & Volume metrics: Total units ordered, received, fill rate, and total inbound spend
- Supplier x SKU granular performance profiles
"""

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def compute_supplier_scorecards(engine: Engine) -> pd.DataFrame:
    """Compute comprehensive supplier fulfillment scorecards and lead-time variance.

    Definitions:
    - on_time: delay_days <= 0
    - in_full: qty_received >= qty_ordered
    - otif: on_time AND in_full

    Returns:
        DataFrame with columns:
        [supplier_id, supplier_name, total_pos, delivered_pos, on_time_pos, in_full_pos,
         otif_pos, on_time_rate, in_full_rate, otif_rate, avg_lead_time_days, avg_delay_days,
         max_delay_days, lead_time_stddev, total_units_ordered, total_units_received,
         fill_rate, total_inbound_spend]
    """
    po_query = text("""
        SELECT 
            s.supplier_id,
            s.supplier_name,
            po.po_id,
            po.product_id,
            p.unit_cost,
            po.po_status,
            po.qty_ordered,
            po.qty_received,
            po.lead_time_days,
            po.delay_days
        FROM suppliers s
        LEFT JOIN supplier_deliveries po ON s.supplier_id = po.supplier_id
        LEFT JOIN products p ON po.product_id = p.product_id
        ORDER BY s.supplier_id, po.order_date;
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(po_query, conn)

    scorecards = []
    for (s_id, s_name), group in df.groupby(["supplier_id", "supplier_name"]):
        # Remove null PO rows if supplier has zero POs
        valid_pos = group.dropna(subset=["po_id"])
        total_pos = len(valid_pos)

        delivered_pos = valid_pos[valid_pos["po_status"] == "DELIVERED"]
        delivered_count = len(delivered_pos)

        if delivered_count > 0:
            on_time_mask = delivered_pos["delay_days"] <= 0
            in_full_mask = delivered_pos["qty_received"] >= delivered_pos["qty_ordered"]
            otif_mask = on_time_mask & in_full_mask

            on_time_count = int(on_time_mask.sum())
            in_full_count = int(in_full_mask.sum())
            otif_count = int(otif_mask.sum())

            on_time_rate = round(on_time_count / delivered_count, 4)
            in_full_rate = round(in_full_count / delivered_count, 4)
            otif_rate = round(otif_count / delivered_count, 4)

            lead_times = delivered_pos["lead_time_days"].dropna().values
            delays = delivered_pos["delay_days"].dropna().values

            avg_lt = round(float(lead_times.mean()), 2) if len(lead_times) > 0 else 0.0
            lt_std = round(float(np.std(lead_times, ddof=0)), 2) if len(lead_times) > 0 else 0.0
            avg_delay = round(float(delays.mean()), 2) if len(delays) > 0 else 0.0
            max_delay = int(delays.max()) if len(delays) > 0 else 0

            tot_ordered = int(valid_pos["qty_ordered"].sum())
            tot_received = int(valid_pos["qty_received"].sum())
            fill_rate = round(tot_received / tot_ordered, 4) if tot_ordered > 0 else 1.0

            # Inbound spend: qty_received * unit_cost
            spend = float((delivered_pos["qty_received"] * delivered_pos["unit_cost"]).sum())
            total_inbound_spend = round(spend, 2)
        else:
            on_time_count = in_full_count = otif_count = 0
            on_time_rate = in_full_rate = otif_rate = 0.0
            avg_lt = lt_std = avg_delay = 0.0
            max_delay = 0
            tot_ordered = tot_received = 0
            fill_rate = 0.0
            total_inbound_spend = 0.0

        scorecards.append({
            "supplier_id": s_id,
            "supplier_name": s_name,
            "total_pos": total_pos,
            "delivered_pos": delivered_count,
            "on_time_pos": on_time_count,
            "in_full_pos": in_full_count,
            "otif_pos": otif_count,
            "on_time_rate": on_time_rate,
            "in_full_rate": in_full_rate,
            "otif_rate": otif_rate,
            "avg_lead_time_days": avg_lt,
            "avg_delay_days": avg_delay,
            "max_delay_days": max_delay,
            "lead_time_stddev": lt_std,
            "total_units_ordered": tot_ordered,
            "total_units_received": tot_received,
            "fill_rate": fill_rate,
            "total_inbound_spend": total_inbound_spend,
        })

    return pd.DataFrame(scorecards).sort_values("total_inbound_spend", ascending=False).reset_index(drop=True)


def compute_supplier_sku_lead_times(engine: Engine) -> pd.DataFrame:
    """Compute granular supplier x SKU lead-time variance profiles."""
    query = text("""
        SELECT 
            s.supplier_id,
            s.supplier_name,
            p.product_id,
            p.sku,
            p.name AS product_name,
            COUNT(po.po_id) AS delivered_pos,
            ROUND(AVG(po.lead_time_days), 2) AS avg_lead_time_days,
            ROUND(AVG(po.delay_days), 2) AS avg_delay_days,
            MAX(po.delay_days) AS max_delay_days,
            SUM(po.qty_received) AS total_units_received
        FROM supplier_deliveries po
        JOIN suppliers s ON po.supplier_id = s.supplier_id
        JOIN products p ON po.product_id = p.product_id
        WHERE po.po_status = 'DELIVERED'
        GROUP BY s.supplier_id, s.supplier_name, p.product_id, p.sku, p.name
        ORDER BY s.supplier_id, p.product_id;
    """)

    with engine.connect() as conn:
        return pd.read_sql_query(query, conn)
