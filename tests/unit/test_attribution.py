"""Unit tests for deterministic 6-category root-cause attribution."""

import pytest

from src.risk.attribution import (
    RootCauseCategory,
    attribute_node_root_cause,
)


def test_demand_surge_root_cause_attribution():
    """Verify DEMAND_SURGE is attributed when forward forecast exceeds 1.25x baseline."""
    rc = attribute_node_root_cause(
        stockout_risk_tier="CRITICAL",
        is_excess=False,
        xyz_class="X",
        forecast_avg_demand=25.0,
        historical_avg_demand=15.0,  # 25/15 = 1.67x (> 1.25x)
        in_transit_units=0.0,
        reorder_triggered=True,
    )
    assert rc == RootCauseCategory.DEMAND_SURGE


def test_supplier_delay_root_cause_attribution():
    """Verify SUPPLIER_DELAY is attributed when upstream latency is >= 2 days."""
    rc = attribute_node_root_cause(
        stockout_risk_tier="CRITICAL",
        is_excess=False,
        xyz_class="X",
        forecast_avg_demand=15.0,
        historical_avg_demand=15.0,
        in_transit_units=50.0,
        reorder_triggered=True,
        supplier_delay_days=3.5,
    )
    assert rc == RootCauseCategory.SUPPLIER_DELAY


def test_under_replenished_root_cause_attribution():
    """Verify UNDER_REPLENISHED is attributed when ROP is breached with 0 in-transit POs."""
    rc = attribute_node_root_cause(
        stockout_risk_tier="CRITICAL",
        is_excess=False,
        xyz_class="X",
        forecast_avg_demand=15.0,
        historical_avg_demand=15.0,
        in_transit_units=0.0,
        reorder_triggered=True,
        supplier_delay_days=0.0,
    )
    assert rc == RootCauseCategory.UNDER_REPLENISHED


def test_slow_moving_drag_and_excess_attribution():
    """Verify SLOW_MOVING_DRAG on Class Z excess and OVER_ORDER_EXCESS on Class X/Y excess."""
    rc_z = attribute_node_root_cause(
        stockout_risk_tier="LOW",
        is_excess=True,
        xyz_class="Z",
        forecast_avg_demand=0.2,
        historical_avg_demand=0.2,
        in_transit_units=0.0,
        reorder_triggered=False,
    )
    assert rc_z == RootCauseCategory.SLOW_MOVING_DRAG

    rc_x = attribute_node_root_cause(
        stockout_risk_tier="LOW",
        is_excess=True,
        xyz_class="X",
        forecast_avg_demand=20.0,
        historical_avg_demand=20.0,
        in_transit_units=0.0,
        reorder_triggered=False,
    )
    assert rc_x == RootCauseCategory.OVER_ORDER_EXCESS


def test_nominal_stable_attribution():
    """Verify NOMINAL_STABLE is attributed when stockout and excess risks are absent."""
    rc = attribute_node_root_cause(
        stockout_risk_tier="LOW",
        is_excess=False,
        xyz_class="X",
        forecast_avg_demand=10.0,
        historical_avg_demand=10.0,
        in_transit_units=0.0,
        reorder_triggered=False,
    )
    assert rc == RootCauseCategory.NOMINAL_STABLE
