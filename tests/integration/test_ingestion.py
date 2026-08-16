"""Integration tests for ingestion boundary, validation gating, and rejection policies."""

import copy
from datetime import date
import pytest
from sqlalchemy import create_engine, inspect, text

from src.data.generator import DataGenerator, SyntheticDataset
from src.data.ingestion import DataQualityError, ingest_dataset, run_ingestion_pipeline


@pytest.fixture
def clean_dataset() -> SyntheticDataset:
    """Generate a clean 30-day synthetic dataset for ingestion testing."""
    generator = DataGenerator(seed=42)
    return generator.generate(start_date=date(2026, 1, 1), num_days=30)


def test_successful_ingestion_of_valid_data(clean_dataset):
    """Verify that a valid dataset passes quality checks and ingests completely into SQLite."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    report, counts = ingest_dataset(dataset=clean_dataset, engine=engine, strict=True, recreate_tables=True)

    assert report.is_ingestable is True
    assert report.failed_checks == 0
    assert counts["calendar_dim"] == 30
    assert counts["products"] == 15
    assert counts["locations"] == 5
    assert counts["sales_transactions"] == 30 * 4 * 15

    # Verify rows in actual database
    with engine.connect() as conn:
        prod_count = conn.execute(text("SELECT COUNT(*) FROM products;")).scalar()
        sales_count = conn.execute(text("SELECT COUNT(*) FROM sales_transactions;")).scalar()
        assert prod_count == 15
        assert sales_count == 30 * 4 * 15


def test_rejection_of_corrupted_data_strict_mode(clean_dataset):
    """Verify that strict mode raises DataQualityError on corrupted data and rejects database load."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Corrupt dataset with an orphan foreign key in sales
    corrupted_sales = copy.deepcopy(clean_dataset.sales_transactions)
    corrupted_sales[0]["product_id"] = "PRD-ORPHAN-KEY"

    corrupted_dataset = SyntheticDataset(
        calendar=clean_dataset.calendar,
        products=clean_dataset.products,
        locations=clean_dataset.locations,
        suppliers=clean_dataset.suppliers,
        promotions=clean_dataset.promotions,
        sales_transactions=corrupted_sales,
        inventory_snapshots=clean_dataset.inventory_snapshots,
        supplier_deliveries=clean_dataset.supplier_deliveries,
    )

    with pytest.raises(DataQualityError) as exc_info:
        ingest_dataset(dataset=corrupted_dataset, engine=engine, strict=True, recreate_tables=True)

    assert exc_info.value.report.is_ingestable is False
    assert exc_info.value.report.failed_checks >= 1

    # Verify database was not populated
    inspector = inspect(engine)
    assert len(inspector.get_table_names()) == 0 or inspector.get_table_names() == []


def test_non_strict_ingestion_rejection(clean_dataset):
    """Verify non-strict mode returns empty counts and failed report without raising exception."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Corrupt dataset with negative unit price
    corrupted_products = copy.deepcopy(clean_dataset.products)
    corrupted_products[0]["unit_price"] = -5.0

    corrupted_dataset = SyntheticDataset(
        calendar=clean_dataset.calendar,
        products=corrupted_products,
        locations=clean_dataset.locations,
        suppliers=clean_dataset.suppliers,
        promotions=clean_dataset.promotions,
        sales_transactions=clean_dataset.sales_transactions,
        inventory_snapshots=clean_dataset.inventory_snapshots,
        supplier_deliveries=clean_dataset.supplier_deliveries,
    )

    report, counts = ingest_dataset(dataset=corrupted_dataset, engine=engine, strict=False, recreate_tables=True)

    assert report.is_ingestable is False
    assert report.failed_checks >= 1
    assert counts == {}


def test_run_ingestion_pipeline_end_to_end():
    """Verify run_ingestion_pipeline executes full generate -> validate -> load cycle."""
    report, counts = run_ingestion_pipeline(
        seed=42,
        target_db_url="sqlite:///:memory:",
        num_days=14,
    )

    assert report.is_ingestable is True
    assert report.pass_rate == 100.0
    assert counts["calendar_dim"] == 14
    assert counts["products"] == 15
    assert counts["sales_transactions"] == 14 * 4 * 15
