"""Unit tests for prescriptive recommendations (DC Transfers, POs, and Priority Ranking)."""

from datetime import date
import pandas as pd
import pytest

from src.risk.recommendations import (
    ActionType,
    PriorityTier,
    generate_prescriptive_recommendations,
)


@pytest.fixture
def sample_risk_df():
    """Create sample attributed risk DataFrame covering DC, critical stores, and excess nodes."""
    return pd.DataFrame([
        # 1. DC Node with Surplus Stock (Available = 500, SS = 50 -> Surplus = 400)
        {
            "as_of_date": date(2026, 12, 31),
            "location_id": "LOC-DC-01",
            "location_name": "Central Distribution Center",
            "location_type": "DC",
            "product_id": "PRD-BEV-001",
            "sku": "SKU-BEV-001",
            "product_name": "Cold Brew Coffee 12oz",
            "abc_class": "A",
            "xyz_class": "X",
            "abc_xyz_segment": "AX",
            "standard_lead_time_days": 7,
            "starting_available_stock": 500.0,
            "in_transit_units": 0.0,
            "forecast_demand_30d": 600.0,
            "avg_daily_forecast": 20.0,
            "days_to_runout": 25.0,
            "stockout_risk_score": 0.0,
            "stockout_risk_tier": "LOW",
            "is_excess": False,
            "days_of_supply_forecast": 25.0,
            "excess_units": 0.0,
            "capital_at_risk": 0.0,
            "safety_stock": 50.0,
            "reorder_point": 190.0,
            "inventory_position": 500.0,
            "target_inventory_level": 470.0,
            "reorder_triggered": False,
            "root_cause": "NOMINAL_STABLE",
            "supplier_id": "SUP-001",
        },
        # 2. Store Node facing CRITICAL Stockout on Class A SKU (Stock = 5, LT = 7, DTR = 0.5)
        {
            "as_of_date": date(2026, 12, 31),
            "location_id": "LOC-ST-01",
            "location_name": "Downtown Metro Store",
            "location_type": "STORE",
            "product_id": "PRD-BEV-001",
            "sku": "SKU-BEV-001",
            "product_name": "Cold Brew Coffee 12oz",
            "abc_class": "A",
            "xyz_class": "X",
            "abc_xyz_segment": "AX",
            "standard_lead_time_days": 7,
            "starting_available_stock": 5.0,
            "in_transit_units": 0.0,
            "forecast_demand_30d": 300.0,
            "avg_daily_forecast": 10.0,
            "days_to_runout": 0.5,
            "stockout_risk_score": 92.86,
            "stockout_risk_tier": "CRITICAL",
            "is_excess": False,
            "days_of_supply_forecast": 0.5,
            "excess_units": 0.0,
            "capital_at_risk": 0.0,
            "safety_stock": 25.0,
            "reorder_point": 95.0,
            "inventory_position": 5.0,
            "target_inventory_level": 235.0,
            "reorder_triggered": True,
            "root_cause": "DEMAND_SURGE",
            "supplier_id": "SUP-001",
        },
        # 3. Store Node with Excess Stock on Class C SKU
        {
            "as_of_date": date(2026, 12, 31),
            "location_id": "LOC-ST-02",
            "location_name": "Suburban Center",
            "location_type": "STORE",
            "product_id": "PRD-HOU-003",
            "sku": "SKU-HOU-003",
            "product_name": "Industrial Floor Degreaser 1Gal",
            "abc_class": "C",
            "xyz_class": "Z",
            "abc_xyz_segment": "CZ",
            "standard_lead_time_days": 14,
            "starting_available_stock": 80.0,
            "in_transit_units": 0.0,
            "forecast_demand_30d": 6.0,
            "avg_daily_forecast": 0.2,
            "days_to_runout": 400.0,
            "stockout_risk_score": 0.0,
            "stockout_risk_tier": "LOW",
            "is_excess": True,
            "days_of_supply_forecast": 400.0,
            "excess_units": 71.0,
            "capital_at_risk": 994.0,
            "safety_stock": 5.0,
            "reorder_point": 7.8,
            "inventory_position": 80.0,
            "target_inventory_level": 10.6,
            "reorder_triggered": False,
            "root_cause": "SLOW_MOVING_DRAG",
            "supplier_id": "SUP-004",
        }
    ])


def test_dc_transfer_recommendation_generation(sample_risk_df):
    """Verify DC_TRANSFER is recommended for CRITICAL store stockout when DC has surplus stock."""
    recs = generate_prescriptive_recommendations(sample_risk_df)

    assert len(recs) == 2  # 1 critical store transfer + 1 excess hold
    transfer_rec = recs[recs["action_type"] == ActionType.DC_TRANSFER.value].iloc[0]

    assert transfer_rec["location_id"] == "LOC-ST-01"
    assert transfer_rec["product_id"] == "PRD-BEV-001"
    assert transfer_rec["priority_tier"] == PriorityTier.URGENT.value
    assert transfer_rec["source_identifier"] == "LOC-DC-01"
    assert transfer_rec["recommended_qty"] > 0
    assert "DC transfer" in transfer_rec["rationale_text"]


def test_priority_ranking_urgent_before_low(sample_risk_df):
    """Verify recommendations are sorted with URGENT priority preceding LOW priority."""
    recs = generate_prescriptive_recommendations(sample_risk_df)

    priorities = recs["priority_tier"].tolist()
    assert priorities == ["URGENT", "LOW"]
