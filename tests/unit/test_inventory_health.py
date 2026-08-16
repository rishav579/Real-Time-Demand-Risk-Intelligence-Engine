"""Unit tests for SKU x Location inventory health, ADD30, DoS, and 5-tier risk classification."""

from datetime import date
import pytest
from sqlalchemy import create_engine

from src.analytics.inventory_health import (
    InventoryRiskCategory,
    classify_inventory_risk,
    compute_inventory_health,
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


def test_classify_inventory_risk_all_five_categories():
    """Verify classification logic explicitly covers all five distinct risk boundaries."""
    lt = 7  # 7-day standard lead time

    # 1. CRITICAL: DoS <= lead_time
    assert classify_inventory_risk(dos=0.0, lead_time_days=lt) == InventoryRiskCategory.CRITICAL
    assert classify_inventory_risk(dos=5.0, lead_time_days=lt) == InventoryRiskCategory.CRITICAL
    assert classify_inventory_risk(dos=7.0, lead_time_days=lt) == InventoryRiskCategory.CRITICAL

    # 2. LOW_BUFFER: lead_time < DoS <= 1.5 * lead_time (7 < DoS <= 10.5)
    assert classify_inventory_risk(dos=7.1, lead_time_days=lt) == InventoryRiskCategory.LOW_BUFFER
    assert classify_inventory_risk(dos=10.5, lead_time_days=lt) == InventoryRiskCategory.LOW_BUFFER

    # 3. HEALTHY: 1.5 * lead_time < DoS <= 45 (10.5 < DoS <= 45)
    assert classify_inventory_risk(dos=10.6, lead_time_days=lt) == InventoryRiskCategory.HEALTHY
    assert classify_inventory_risk(dos=25.0, lead_time_days=lt) == InventoryRiskCategory.HEALTHY
    assert classify_inventory_risk(dos=45.0, lead_time_days=lt) == InventoryRiskCategory.HEALTHY

    # 4. ELEVATED_BUFFER: 45 < DoS <= 90
    assert classify_inventory_risk(dos=45.1, lead_time_days=lt) == InventoryRiskCategory.ELEVATED_BUFFER
    assert classify_inventory_risk(dos=75.0, lead_time_days=lt) == InventoryRiskCategory.ELEVATED_BUFFER
    assert classify_inventory_risk(dos=90.0, lead_time_days=lt) == InventoryRiskCategory.ELEVATED_BUFFER

    # 5. EXCESS: DoS > 90
    assert classify_inventory_risk(dos=90.1, lead_time_days=lt) == InventoryRiskCategory.EXCESS
    assert classify_inventory_risk(dos=350.0, lead_time_days=lt) == InventoryRiskCategory.EXCESS


def test_inventory_health_as_of_date_determinism(populated_engine):
    """Verify inventory health resolves automatically to latest available date in dataset (2026-12-31)."""
    df = compute_inventory_health(populated_engine)

    # 5 locations x 15 SKUs = 75 node positions
    assert len(df) == 75

    as_of_dates = df["as_of_date"].unique()
    assert len(as_of_dates) == 1
    # Check either string or date object equals 2026-12-31
    assert str(as_of_dates[0]) == "2026-12-31"


def test_inventory_health_metrics_calculations(populated_engine):
    """Verify ADD30, available stock, DoS, and risk category validity across all rows."""
    df = compute_inventory_health(populated_engine)

    valid_categories = {c.value for c in InventoryRiskCategory}

    for _, row in df.iterrows():
        assert row["available_stock"] == row["on_hand_qty"] - row["reserved_qty"]
        assert row["add_30d"] >= 0.0
        assert row["days_of_supply"] >= 0.0
        assert row["risk_category"] in valid_categories
        assert row["stockout_days_365d"] >= row["stockout_days_30d"]


def test_planted_slow_mover_excess_classification(populated_engine):
    """Verify planted slow-moving industrial cleaner PRD-HOU-003 receives EXCESS classification."""
    df = compute_inventory_health(populated_engine)

    # Filter for PRD-HOU-003 at retail stores
    slow_store_rows = df[(df["product_id"] == "PRD-HOU-003") & (df["location_type"] == "STORE")]
    assert len(slow_store_rows) == 4

    for _, row in slow_store_rows.iterrows():
        assert row["days_of_supply"] > 90.0
        assert row["risk_category"] == InventoryRiskCategory.EXCESS.value
