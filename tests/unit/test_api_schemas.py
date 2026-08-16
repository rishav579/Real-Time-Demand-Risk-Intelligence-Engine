"""Unit tests for API Pydantic schemas and serialization contracts."""

from datetime import date
import pytest

from src.api.schemas import (
    ExecutiveSummaryResponse,
    ForecastItemResponse,
    ForecastResponse,
    HealthResponse,
    InventoryItemResponse,
    InventoryResponse,
    RecommendationItemResponse,
    RecommendationResponse,
    RiskItemResponse,
    RiskResponse,
)


def test_health_response_schema():
    """Verify HealthResponse schema validation."""
    data = {
        "status": "healthy",
        "engine_version": "1.0.0",
        "as_of_date": date(2026, 12, 31),
        "database_connected": True,
        "liveness": True,
        "readiness": True,
    }
    resp = HealthResponse(**data)
    assert resp.status == "healthy"
    assert resp.as_of_date == date(2026, 12, 31)
    assert resp.liveness is True
    assert resp.readiness is True


def test_executive_summary_schema():
    """Verify ExecutiveSummaryResponse schema validation."""
    data = {
        "as_of_date": date(2026, 12, 31),
        "total_locations": 5,
        "total_products": 15,
        "total_node_positions": 75,
        "critical_stockout_risks": 26,
        "high_stockout_risks": 8,
        "medium_stockout_risks": 8,
        "low_stockout_risks": 33,
        "total_capital_at_risk": 6134.40,
        "total_annual_holding_cost": 1226.88,
        "champion_model_name": "LightGBM",
        "champion_model_wape": 0.1097,
        "total_recommendations": 48,
        "dc_transfer_recommendations": 12,
        "purchase_order_recommendations": 29,
        "hold_order_recommendations": 7,
        "urgent_priority_recommendations": 24,
    }
    resp = ExecutiveSummaryResponse(**data)
    assert resp.total_node_positions == 75
    assert resp.champion_model_wape == 0.1097


def test_recommendation_item_schema():
    """Verify RecommendationItemResponse schema validation."""
    data = {
        "recommendation_id": "REC-20261231-001",
        "created_date": date(2026, 12, 31),
        "location_id": "LOC-ST-01",
        "location_name": "Midtown Manhattan Store",
        "product_id": "PRD-BEV-001",
        "sku": "SKU-BEV-001",
        "product_name": "Cold Brew Coffee 12oz",
        "abc_xyz_segment": "AX",
        "action_type": "DC_TRANSFER",
        "priority_tier": "URGENT",
        "current_available_stock": 5.0,
        "forecast_daily_demand": 10.0,
        "days_to_runout": 0.5,
        "safety_stock": 25.0,
        "reorder_point": 95.0,
        "recommended_qty": 332,
        "source_identifier": "LOC-DC-01",
        "root_cause": "DEMAND_SURGE",
        "rationale_text": "Expedited transfer from DC.",
    }
    rec = RecommendationItemResponse(**data)
    assert rec.recommendation_id == "REC-20261231-001"
    assert rec.action_type == "DC_TRANSFER"
