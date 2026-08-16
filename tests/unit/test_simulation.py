"""Unit tests for inventory simulation and runout date calculation."""

from datetime import date, timedelta
import pytest

from src.risk.simulation import (
    RunoutSimulationResult,
    simulate_node_runout,
)


def test_simulation_runout_within_30d_horizon():
    """Verify simulation accurately calculates exact runout day within the 30-day forecast window."""
    as_of = date(2026, 12, 31)
    # Starting stock = 50, constant daily demand = 10 -> runs out at day 5
    daily_forecasts = [10.0] * 30

    res = simulate_node_runout(
        location_id="LOC-ST-01",
        product_id="PRD-BEV-001",
        as_of_date=as_of,
        starting_stock=50.0,
        lead_time_days=7,
        daily_forecasts=daily_forecasts,
    )

    assert res.days_to_runout == 5.0
    assert res.runout_date == as_of + timedelta(days=5)
    assert res.runout_horizon_category == "WITHIN_30D"
    assert len(res.trajectory) == 180
    assert res.trajectory[4].ending_stock == 0.0
    assert res.trajectory[4].is_stockout is True


def test_simulation_projected_runout_beyond_30d_horizon():
    """Verify simulation projects runout beyond 30 days using the trailing-7-day flat continuation."""
    as_of = date(2026, 12, 31)
    # Starting stock = 400, daily demand = 10 -> runs out at day 40 (beyond 30d window)
    daily_forecasts = [10.0] * 30

    res = simulate_node_runout(
        location_id="LOC-ST-01",
        product_id="PRD-BEV-001",
        as_of_date=as_of,
        starting_stock=400.0,
        lead_time_days=7,
        daily_forecasts=daily_forecasts,
        max_simulation_days=180,
    )

    assert res.days_to_runout == 40.0
    assert res.runout_date == as_of + timedelta(days=40)
    assert res.runout_horizon_category == "BEYOND_30D_PROJECTION"


def test_simulation_no_runout_within_extended_horizon():
    """Verify slow-moving SKU with immense stock does not run out within 180 days."""
    as_of = date(2026, 12, 31)
    # Starting stock = 100, daily demand = 0.2 -> 500 days of stock
    daily_forecasts = [0.2] * 30

    res = simulate_node_runout(
        location_id="LOC-ST-01",
        product_id="PRD-HOU-003",
        as_of_date=as_of,
        starting_stock=100.0,
        lead_time_days=14,
        daily_forecasts=daily_forecasts,
        max_simulation_days=180,
    )

    assert res.days_to_runout == float("inf")
    assert res.runout_date is None
    assert res.runout_horizon_category == "NO_RUNOUT"


def test_simulation_inbound_po_delivery_extension():
    """Verify scheduled inbound deliveries replenish stock and extend runout date."""
    as_of = date(2026, 12, 31)
    # Stock 30, demand 10/day (would run out at day 3), but 100 units arrive at day 2
    daily_forecasts = [10.0] * 30
    scheduled_inbound = {2: 100.0}

    res = simulate_node_runout(
        location_id="LOC-ST-01",
        product_id="PRD-BEV-001",
        as_of_date=as_of,
        starting_stock=30.0,
        lead_time_days=7,
        daily_forecasts=daily_forecasts,
        scheduled_inbound=scheduled_inbound,
    )

    # Initial 30 - 10 (day 1) = 20. Day 2: 20 + 100 - 10 = 110. Days to run out: 1 + (120/10) = 13
    assert res.days_to_runout == 13.0
    assert res.runout_horizon_category == "WITHIN_30D"
    assert res.in_transit_units == 100.0
