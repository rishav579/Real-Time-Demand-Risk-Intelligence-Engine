"""Unit tests for data quality validation checks and corrupted fixture detection."""

import copy
from datetime import date
import pytest

from src.data.generator import DataGenerator, SyntheticDataset
from src.data.quality import CheckStatus, DataQualityValidator, validate_dataset


@pytest.fixture
def base_dataset() -> SyntheticDataset:
    """Generate a lightweight 14-day synthetic dataset for quality testing."""
    generator = DataGenerator(seed=42)
    return generator.generate(start_date=date(2026, 1, 1), num_days=14)


def test_valid_dataset_passes_all_checks(base_dataset):
    """Verify that a clean generated dataset passes 100% of data quality checks."""
    report = validate_dataset(base_dataset)
    assert report.overall_status == CheckStatus.PASS
    assert report.is_ingestable is True
    assert report.failed_checks == 0
    assert report.warning_checks == 0
    assert report.pass_rate == 100.0
    assert report.total_checks >= 35


def test_detect_duplicate_primary_key(base_dataset):
    """Verify detector catches duplicate product_id primary key."""
    corrupted_products = copy.deepcopy(base_dataset.products)
    corrupted_products.append(copy.deepcopy(corrupted_products[0]))

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=corrupted_products,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=base_dataset.sales_transactions,
        inventory_snapshots=base_dataset.inventory_snapshots,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    assert report.overall_status == CheckStatus.FAIL
    assert report.is_ingestable is False

    pk_check = next(r for r in report.check_details if r.check_name == "pk_products_product_id")
    assert pk_check.status == CheckStatus.FAIL
    assert pk_check.affected_count == 1


def test_detect_duplicate_composite_inventory_key(base_dataset):
    """Verify detector catches duplicate (snapshot_date, product_id, location_id) composite key."""
    corrupted_snaps = copy.deepcopy(base_dataset.inventory_snapshots)
    dup = copy.deepcopy(corrupted_snaps[0])
    dup["snapshot_id"] = "SNP-DUP-UNIQUE-ID"  # Different PK, same composite key
    corrupted_snaps.append(dup)

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=base_dataset.products,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=base_dataset.sales_transactions,
        inventory_snapshots=corrupted_snaps,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    composite_check = next(r for r in report.check_details if r.check_name == "uk_inventory_snapshot_composite")
    assert composite_check.status == CheckStatus.FAIL
    assert composite_check.affected_count == 1


def test_detect_orphan_foreign_key_sales(base_dataset):
    """Verify detector catches sales transaction referencing non-existent product_id."""
    corrupted_sales = copy.deepcopy(base_dataset.sales_transactions)
    corrupted_sales[0]["product_id"] = "PRD-DOES-NOT-EXIST"

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=base_dataset.products,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=corrupted_sales,
        inventory_snapshots=base_dataset.inventory_snapshots,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    fk_check = next(r for r in report.check_details if r.check_name == "fk_sales_product_id")
    assert fk_check.status == CheckStatus.FAIL
    assert fk_check.affected_count == 1


def test_detect_orphan_foreign_key_po(base_dataset):
    """Verify detector catches supplier delivery referencing non-existent supplier_id."""
    corrupted_pos = copy.deepcopy(base_dataset.supplier_deliveries)
    corrupted_pos[0]["supplier_id"] = "SUP-NON-EXISTENT"

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=base_dataset.products,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=base_dataset.sales_transactions,
        inventory_snapshots=base_dataset.inventory_snapshots,
        supplier_deliveries=corrupted_pos,
    )

    report = validate_dataset(corrupted_dataset)
    fk_check = next(r for r in report.check_details if r.check_name == "fk_po_supplier_id")
    assert fk_check.status == CheckStatus.FAIL
    assert fk_check.affected_count == 1


def test_detect_price_below_cost(base_dataset):
    """Verify detector catches product selling price below unit cost."""
    corrupted_prods = copy.deepcopy(base_dataset.products)
    corrupted_prods[0]["unit_cost"] = 10.00
    corrupted_prods[0]["unit_price"] = 4.00

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=corrupted_prods,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=base_dataset.sales_transactions,
        inventory_snapshots=base_dataset.inventory_snapshots,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    check = next(r for r in report.check_details if r.check_name == "product_price_covers_cost")
    assert check.status == CheckStatus.FAIL
    assert check.affected_count == 1


def test_detect_invalid_supplier_reliability(base_dataset):
    """Verify detector catches out-of-bounds supplier reliability score."""
    corrupted_sups = copy.deepcopy(base_dataset.suppliers)
    corrupted_sups[0]["reliability_score"] = 1.45

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=base_dataset.products,
        locations=base_dataset.locations,
        suppliers=corrupted_sups,
        promotions=base_dataset.promotions,
        sales_transactions=base_dataset.sales_transactions,
        inventory_snapshots=base_dataset.inventory_snapshots,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    check = next(r for r in report.check_details if r.check_name == "supplier_reliability_range")
    assert check.status == CheckStatus.FAIL
    assert check.affected_count == 1


def test_detect_negative_sales_quantity(base_dataset):
    """Verify detector catches negative sales demanded units."""
    corrupted_sales = copy.deepcopy(base_dataset.sales_transactions)
    corrupted_sales[0]["units_demanded"] = -5

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=base_dataset.products,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=corrupted_sales,
        inventory_snapshots=base_dataset.inventory_snapshots,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    check = next(r for r in report.check_details if r.check_name == "sales_quantities_nonnegative")
    assert check.status == CheckStatus.FAIL
    assert check.affected_count == 1


def test_detect_invalid_promotion_date_order(base_dataset):
    """Verify detector catches promotional start_date > end_date."""
    corrupted_promos = copy.deepcopy(base_dataset.promotions)
    corrupted_promos[0]["start_date"] = date(2026, 6, 20)
    corrupted_promos[0]["end_date"] = date(2026, 6, 10)

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=base_dataset.products,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=corrupted_promos,
        sales_transactions=base_dataset.sales_transactions,
        inventory_snapshots=base_dataset.inventory_snapshots,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    check = next(r for r in report.check_details if r.check_name == "promotion_date_sequence")
    assert check.status == CheckStatus.FAIL
    assert check.affected_count == 1


def test_detect_invalid_po_date_order(base_dataset):
    """Verify detector catches purchase order promised delivery preceding order date."""
    corrupted_pos = copy.deepcopy(base_dataset.supplier_deliveries)
    corrupted_pos[0]["order_date"] = date(2026, 5, 20)
    corrupted_pos[0]["promised_delivery_date"] = date(2026, 5, 10)

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=base_dataset.products,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=base_dataset.sales_transactions,
        inventory_snapshots=base_dataset.inventory_snapshots,
        supplier_deliveries=corrupted_pos,
    )

    report = validate_dataset(corrupted_dataset)
    check = next(r for r in report.check_details if r.check_name == "purchase_order_date_sequence")
    assert check.status == CheckStatus.FAIL
    assert check.affected_count == 1


def test_detect_sales_fulfillment_arithmetic_violation(base_dataset):
    """Verify detector catches unfulfilled_units arithmetic mismatch."""
    corrupted_sales = copy.deepcopy(base_dataset.sales_transactions)
    corrupted_sales[0]["units_demanded"] = 10
    corrupted_sales[0]["units_sold"] = 6
    corrupted_sales[0]["unfulfilled_units"] = 1  # Invalid: should be 4

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=base_dataset.products,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=corrupted_sales,
        inventory_snapshots=base_dataset.inventory_snapshots,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    check = next(r for r in report.check_details if r.check_name == "sales_fulfillment_arithmetic")
    assert check.status == CheckStatus.FAIL
    assert check.affected_count == 1


def test_detect_inventory_balance_arithmetic_violation(base_dataset):
    """Verify detector catches available_qty != on_hand - reserved balance discrepancy."""
    corrupted_snaps = copy.deepcopy(base_dataset.inventory_snapshots)
    corrupted_snaps[0]["on_hand_qty"] = 100
    corrupted_snaps[0]["reserved_qty"] = 10
    corrupted_snaps[0]["available_qty"] = 85  # Invalid: should be 90

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=base_dataset.products,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=base_dataset.sales_transactions,
        inventory_snapshots=corrupted_snaps,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    check = next(r for r in report.check_details if r.check_name == "inventory_available_balance")
    assert check.status == CheckStatus.FAIL
    assert check.affected_count == 1


def test_detect_stockout_flag_inconsistency(base_dataset):
    """Verify detector catches stockout_flag=0 when on_hand_qty=0."""
    corrupted_snaps = copy.deepcopy(base_dataset.inventory_snapshots)
    corrupted_snaps[0]["on_hand_qty"] = 0
    corrupted_snaps[0]["reserved_qty"] = 0
    corrupted_snaps[0]["available_qty"] = 0
    corrupted_snaps[0]["stockout_flag"] = 0  # Invalid: must be 1

    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=base_dataset.products,
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=base_dataset.sales_transactions,
        inventory_snapshots=corrupted_snaps,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    check = next(r for r in report.check_details if r.check_name == "stockout_flag_consistency")
    assert check.status == CheckStatus.FAIL
    assert check.affected_count == 1


def test_detect_empty_table_sanity(base_dataset):
    """Verify detector flags empty table as critical table sanity failure."""
    corrupted_dataset = SyntheticDataset(
        calendar=base_dataset.calendar,
        products=[],  # Empty products table
        locations=base_dataset.locations,
        suppliers=base_dataset.suppliers,
        promotions=base_dataset.promotions,
        sales_transactions=base_dataset.sales_transactions,
        inventory_snapshots=base_dataset.inventory_snapshots,
        supplier_deliveries=base_dataset.supplier_deliveries,
    )

    report = validate_dataset(corrupted_dataset)
    check = next(r for r in report.check_details if r.check_name == "non_empty_products")
    assert check.status == CheckStatus.FAIL
    assert report.is_ingestable is False
