"""Unit tests for supplier scorecard metrics, OTIF fulfillment, and lead-time variance."""

from datetime import date
import pytest
from sqlalchemy import create_engine

from src.analytics.supplier import (
    compute_supplier_scorecards,
    compute_supplier_sku_lead_times,
)
from src.data.generator import DataGenerator
from src.data.ingestion import ingest_dataset


@pytest.fixture(scope="module")
def populated_engine():
    """Create in-memory SQLite database populated with 365-day Seed 42 dataset."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=365)
    ingest_dataset(dataset=dataset, engine=engine, strict=True, recreate_tables=True)
    return engine


def test_supplier_scorecard_metrics_structure(populated_engine):
    """Verify all 4 suppliers are scored with valid non-negative operational and financial metrics."""
    df = compute_supplier_scorecards(populated_engine)

    assert len(df) == 4, "Expected all 4 suppliers in scorecard"
    expected_cols = [
        "supplier_id", "supplier_name", "total_pos", "delivered_pos",
        "on_time_pos", "in_full_pos", "otif_pos", "on_time_rate",
        "in_full_rate", "otif_rate", "avg_lead_time_days", "avg_delay_days",
        "max_delay_days", "lead_time_stddev", "total_units_ordered",
        "total_units_received", "fill_rate", "total_inbound_spend"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing expected scorecard column: {col}"

    for _, row in df.iterrows():
        assert row["total_pos"] >= row["delivered_pos"]
        assert row["delivered_pos"] >= row["on_time_pos"]
        assert row["delivered_pos"] >= row["in_full_pos"]
        assert row["delivered_pos"] >= row["otif_pos"]
        assert 0.0 <= row["on_time_rate"] <= 1.0
        assert 0.0 <= row["in_full_rate"] <= 1.0
        assert 0.0 <= row["otif_rate"] <= 1.0
        assert row["otif_rate"] <= row["on_time_rate"]
        assert row["otif_rate"] <= row["in_full_rate"]
        assert row["total_inbound_spend"] >= 0.0
        assert 0.0 <= row["fill_rate"] <= 1.0


def test_planted_supplier_delay_scorecard_impact(populated_engine):
    """Verify planted supplier delays correctly degrade SUP-002 on-time rate and max delay."""
    df = compute_supplier_scorecards(populated_engine).set_index("supplier_id")

    # SUP-001 (Apex Beverage Bottlers) has 9-day delay on planted crisis PO
    sup1 = df.loc["SUP-001"]
    assert sup1["max_delay_days"] == 9

    # SUP-002 (Artisan Snackcraft) has lower reliability and natural delay jitter
    sup2 = df.loc["SUP-002"]
    assert sup2["on_time_rate"] < 0.90, f"Expected lower on-time rate for SUP-002, got {sup2['on_time_rate']}"
    assert sup2["avg_delay_days"] > 0.0


def test_supplier_sku_lead_time_granularity(populated_engine):
    """Verify supplier x SKU lead-time breakdowns are correctly populated for delivered lines."""
    df = compute_supplier_sku_lead_times(populated_engine)

    assert len(df) >= 13, "Expected delivered catalog product-supplier combinations"
    assert "avg_lead_time_days" in df.columns
    assert "max_delay_days" in df.columns
    assert "total_units_received" in df.columns
    assert (df["delivered_pos"] > 0).all()
