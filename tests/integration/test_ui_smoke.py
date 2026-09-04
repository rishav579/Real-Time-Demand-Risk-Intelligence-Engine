"""Smoke test for Streamlit dashboard data providers and views."""

from datetime import date
import pytest
from sqlalchemy import create_engine

from src.api.service import IntelligenceService
from src.data.generator import DataGenerator
from src.data.ingestion import ingest_dataset


@pytest.fixture(scope="module")
def ui_service():
    """Create initialized service for UI smoke tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)

    service = IntelligenceService(engine=engine, as_of_date=date(2026, 12, 31))
    service.initialize()
    return service


def test_ui_data_feeds_build_cleanly(ui_service):
    """Verify all dashboard view data feeds construct without NaN errors or missing fields."""
    summary = ui_service.get_executive_summary()
    assert summary["total_node_positions"] == 75

    # 1. Executive overview data feeds
    urgent_recs = ui_service.get_recommendations(priority_tier="URGENT")
    assert len(urgent_recs) > 0

    # 2. Forecast explorer data feeds
    forecasts = ui_service.get_forecasts(location_id="LOC-ST-01", product_id="PRD-BEV-001", horizon_days=30)
    assert len(forecasts) == 30
    assert not forecasts[["y_true", "y_pred"]].isna().any().any()

    # 3. Risk explorer data feeds
    risks = ui_service.get_risk_positions()
    assert len(risks) == 75
    assert not risks["stockout_risk_score"].isna().any()

    # 4. Recommendation center data feeds
    all_recs = ui_service.get_recommendations()
    assert not all_recs.empty
    assert not all_recs.isna().any().any()

    expected_cols = [
        "recommendation_id", "created_date", "location_id", "location_name",
        "product_id", "sku", "product_name", "abc_xyz_segment", "action_type",
        "priority_tier", "current_available_stock", "forecast_daily_demand",
        "days_to_runout", "safety_stock", "reorder_point", "recommended_qty",
        "source_identifier", "root_cause", "rationale_text"
    ]
    for col in expected_cols:
        assert col in all_recs.columns

    assert set(all_recs["action_type"].unique()).issubset({"DC_TRANSFER", "PURCHASE_ORDER", "HOLD_ORDER", "PROMOTION_CANDIDATE"})
    assert set(all_recs["priority_tier"].unique()).issubset({"URGENT", "HIGH", "MEDIUM", "LOW"})

    # Verify every recommendation maps directly to a valid risk trigger condition
    triggered_nodes = set(
        zip(
            risks[risks["reorder_triggered"] | risks["stockout_risk_tier"].isin(["CRITICAL", "HIGH"]) | risks["is_excess"]]["location_id"],
            risks[risks["reorder_triggered"] | risks["stockout_risk_tier"].isin(["CRITICAL", "HIGH"]) | risks["is_excess"]]["product_id"],
        )
    )
    rec_nodes = set(zip(all_recs["location_id"], all_recs["product_id"]))
    assert rec_nodes.issubset(triggered_nodes)

    # 5. SKU Drilldown feeds
    node_risk = risks[(risks["location_id"] == "LOC-ST-01") & (risks["product_id"] == "PRD-BEV-001")].iloc[0]
    assert node_risk["days_to_runout"] >= 0.0
