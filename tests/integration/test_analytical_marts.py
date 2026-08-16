"""Integration tests for analytical data marts creation, database persistence, and relational joins."""

from datetime import date
import pytest
from sqlalchemy import create_engine, inspect, text

from src.analytics.marts import build_all_marts, compute_daily_product_velocity
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


def test_build_all_marts_returns_expected_dataframes_and_persists(populated_engine):
    """Verify build_all_marts generates and persists all 5 analytical marts into SQLite."""
    marts = build_all_marts(populated_engine, persist_to_db=True)

    expected_marts = {
        "mart_daily_product_velocity",
        "mart_abc_xyz_segmentation",
        "mart_supplier_performance",
        "mart_supplier_sku_lead_times",
        "mart_inventory_health",
    }

    assert expected_marts.issubset(set(marts.keys()))

    # Verify table row counts in returned DataFrames
    assert len(marts["mart_daily_product_velocity"]) == 365 * 4 * 15  # 21,900
    assert len(marts["mart_abc_xyz_segmentation"]) == 15
    assert len(marts["mart_supplier_performance"]) == 4
    assert len(marts["mart_supplier_sku_lead_times"]) >= 13
    assert len(marts["mart_inventory_health"]) == 5 * 15  # 75

    # Verify tables actually exist in SQLite
    inspector = inspect(populated_engine)
    db_tables = set(inspector.get_table_names())
    assert expected_marts.issubset(db_tables), f"Missing database tables: {expected_marts - db_tables}"


def test_relational_cross_mart_sql_queries(populated_engine):
    """Verify relational SQL queries can join analytical marts with core entities seamlessly."""
    build_all_marts(populated_engine, persist_to_db=True)

    with populated_engine.connect() as conn:
        # Join inventory health with ABC/XYZ segmentation
        query = text("""
            SELECT 
                h.location_id,
                h.product_id,
                s.abc_xyz_segment,
                h.days_of_supply,
                h.risk_category
            FROM mart_inventory_health h
            JOIN mart_abc_xyz_segmentation s ON h.product_id = s.product_id
            WHERE h.risk_category = 'EXCESS'
            ORDER BY h.days_of_supply DESC;
        """)
        results = conn.execute(query).fetchall()
        assert len(results) > 0
        for row in results:
            assert row.days_of_supply > 90.0
            assert row.risk_category == "EXCESS"


def test_daily_product_velocity_completeness(populated_engine):
    """Verify mart_daily_product_velocity covers full calendar and store coverage without null revenue."""
    df = compute_daily_product_velocity(populated_engine)

    assert len(df) == 21900
    assert df["total_revenue"].isna().sum() == 0
    assert df["units_sold"].isna().sum() == 0
    assert (df["units_sold"] <= df["units_demanded"]).all()
