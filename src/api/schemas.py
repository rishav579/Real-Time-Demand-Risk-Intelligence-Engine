"""Pydantic API request and response schemas for decision intelligence service."""

from datetime import date
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """API health and service status response."""
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    engine_version: str = Field(..., json_schema_extra={"example": "1.0.0"})
    as_of_date: date = Field(..., json_schema_extra={"example": "2026-12-31"})
    database_connected: bool = Field(..., json_schema_extra={"example": True})
    liveness: bool = Field(default=True, json_schema_extra={"example": True})
    readiness: bool = Field(default=True, json_schema_extra={"example": True})


class ExecutiveSummaryResponse(BaseModel):
    """Executive KPI summary across network inventory, risks, forecasts, and recommendations."""
    as_of_date: date
    total_locations: int
    total_products: int
    total_node_positions: int
    critical_stockout_risks: int
    high_stockout_risks: int
    medium_stockout_risks: int
    low_stockout_risks: int
    total_capital_at_risk: float
    total_annual_holding_cost: float
    champion_model_name: str
    champion_model_wape: float
    total_recommendations: int
    dc_transfer_recommendations: int
    purchase_order_recommendations: int
    hold_order_recommendations: int
    urgent_priority_recommendations: int


class ForecastItemResponse(BaseModel):
    """Point demand forecast item for a single date, location, and SKU."""
    model_config = ConfigDict(from_attributes=True)

    transaction_date: date
    location_id: str
    product_id: str
    y_true: float
    y_pred: float
    model_name: str
    horizon_days: int


class ForecastResponse(BaseModel):
    """Forecast query response."""
    total_items: int
    horizon_days: int
    items: List[ForecastItemResponse]


class RiskItemResponse(BaseModel):
    """Predictive stockout and excess risk position for a SKU x Location node."""
    model_config = ConfigDict(from_attributes=True)

    as_of_date: date
    location_id: str
    location_name: str
    location_type: str
    product_id: str
    sku: str
    product_name: str
    category: str
    abc_xyz_segment: str
    standard_lead_time_days: int
    starting_available_stock: float
    in_transit_units: float
    inventory_position: float
    safety_stock: float
    reorder_point: float
    target_inventory_level: float
    avg_daily_forecast: float
    days_to_runout: float
    runout_horizon_category: str
    stockout_risk_score: float
    stockout_risk_tier: str
    is_excess: bool
    days_of_supply_forecast: float
    excess_units: float
    capital_at_risk: float
    annual_holding_cost: float
    root_cause: str
    root_cause_explanation: str


class RiskResponse(BaseModel):
    """Operational risk positions response."""
    total_positions: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_capital_at_risk: float
    positions: List[RiskItemResponse]


class InventoryItemResponse(BaseModel):
    """Inventory snapshot and stock health item."""
    model_config = ConfigDict(from_attributes=True)

    as_of_date: date
    location_id: str
    location_name: str
    location_type: str
    product_id: str
    sku: str
    product_name: str
    category: str
    on_hand_qty: int
    in_transit_qty: int
    reserved_qty: int
    available_stock: int
    standard_lead_time_days: int
    add_30d: float
    days_of_supply: float
    risk_category: str


class InventoryResponse(BaseModel):
    """Inventory health response."""
    total_items: int
    items: List[InventoryItemResponse]


class RecommendationItemResponse(BaseModel):
    """Prescriptive recommendation action item with explainable audit trail."""
    model_config = ConfigDict(from_attributes=True)

    recommendation_id: str
    created_date: date
    location_id: str
    location_name: str
    product_id: str
    sku: str
    product_name: str
    abc_xyz_segment: str
    action_type: str
    priority_tier: str
    current_available_stock: float
    forecast_daily_demand: float
    days_to_runout: float
    safety_stock: float
    reorder_point: float
    recommended_qty: int
    source_identifier: str
    root_cause: str
    rationale_text: str


class RecommendationResponse(BaseModel):
    """Prescriptive recommendations query response."""
    total_recommendations: int
    urgent_count: int
    high_count: int
    medium_count: int
    low_count: int
    recommendations: List[RecommendationItemResponse]
