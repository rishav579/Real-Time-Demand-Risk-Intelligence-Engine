"""Integration tests for the complete predictive risk and prescriptive replenishment pipeline."""

from datetime import date
import pandas as pd
import pytest
from sqlalchemy import create_engine

from src.analytics.marts import build_all_marts
from src.data.generator import DataGenerator
from src.data.ingestion import ingest_dataset
from src.forecasting.features import build_forecasting_dataset
from src.forecasting.model import LightGBMDemandForecaster
from src.forecasting.splits import create_temporal_splits
from src.risk.attribution import compute_root_cause_attribution
from src.risk.recommendations import generate_prescriptive_recommendations
from src.risk.risk_scoring import compute_risk_scoring
from src.risk.safety_stock import compute_node_reorder_points
from src.risk.simulation import simulate_network_runout


@pytest.fixture(scope="module")
def trained_forecaster_and_engine():
    """Populate database and train LightGBM forecaster to produce 30-day forecast predictions."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)
    build_all_marts(engine, persist_to_db=True)

    # Train model and generate forecasts on test set
    feat_df = build_forecasting_dataset(engine)
    train_df, val_df, test_df = create_temporal_splits(feat_df)
    model = LightGBMDemandForecaster(random_state=42).fit(train_df, val_df)
    preds = model.predict(test_df, horizon_days=30)

    return engine, preds


def test_complete_end_to_end_risk_and_replenishment_pipeline(trained_forecaster_and_engine):
    """Execute end-to-end predictive risk and prescriptive action pipeline on all 75 nodes."""
    engine, preds = trained_forecaster_and_engine
    as_of = date(2026, 12, 31)

    # 1. Runout Simulation
    sim_df = simulate_network_runout(engine=engine, predictions_df=preds, as_of_date=as_of)
    assert len(sim_df) == 75, "Expected all 75 SKU x Location node positions"
    assert set(sim_df["runout_horizon_category"].unique()).issubset(
        {"WITHIN_30D", "BEYOND_30D_PROJECTION", "NO_RUNOUT"}
    )

    # 2. Safety Stock & ROP
    rop_df = compute_node_reorder_points(sim_df, engine=engine)
    assert len(rop_df) == 75
    assert (rop_df["safety_stock"] > 0).all()
    assert (rop_df["reorder_point"] > rop_df["safety_stock"]).all()

    # 3. Risk Scoring & Capital-at-Risk
    risk_df = compute_risk_scoring(rop_df)
    assert len(risk_df) == 75
    assert set(risk_df["stockout_risk_tier"].unique()).issubset(
        {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    )
    assert (risk_df["stockout_risk_score"] >= 0.0).all()
    assert (risk_df["stockout_risk_score"] <= 100.0).all()

    # 4. Root-Cause Attribution
    attr_df = compute_root_cause_attribution(risk_df)
    assert len(attr_df) == 75
    valid_root_causes = {
        "DEMAND_SURGE", "SUPPLIER_DELAY", "UNDER_REPLENISHED",
        "INSUFFICIENT_SAFETY_BUFFER", "SLOW_MOVING_DRAG",
        "OVER_ORDER_EXCESS", "NOMINAL_STABLE"
    }
    assert set(attr_df["root_cause"].unique()).issubset(valid_root_causes)

    # 5. Prescriptive Recommendations
    recs_df = generate_prescriptive_recommendations(attr_df)
    assert len(recs_df) > 0

    expected_rec_cols = [
        "recommendation_id", "created_date", "location_id", "location_name",
        "product_id", "sku", "product_name", "abc_xyz_segment", "action_type",
        "priority_tier", "current_available_stock", "forecast_daily_demand",
        "days_to_runout", "safety_stock", "reorder_point", "recommended_qty",
        "source_identifier", "root_cause", "rationale_text"
    ]
    for col in expected_rec_cols:
        assert col in recs_df.columns, f"Missing recommendation column: {col}"

    # Verify priority tier ordering
    priority_ranks = recs_df["priority_tier"].map({"URGENT": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4})
    assert priority_ranks.is_monotonic_increasing

    # Verify slow mover CZ generates excess holding recommendation
    cz_recs = recs_df[recs_df["product_id"] == "PRD-HOU-003"]
    assert len(cz_recs) > 0
    assert (cz_recs["root_cause"] == "SLOW_MOVING_DRAG").all()
