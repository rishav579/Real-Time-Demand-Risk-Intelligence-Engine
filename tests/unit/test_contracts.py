"""Unit tests for Pydantic data contracts and validation constraints."""

from datetime import date
import pytest
from pydantic import ValidationError

from src.models.contracts import (
    CalendarDimContract,
    InventorySnapshotContract,
    LocationContract,
    LocationType,
    POStatus,
    ProductContract,
    PromotionContract,
    SalesTransactionContract,
    SupplierContract,
    SupplierDeliveryContract,
)


def test_product_contract_valid():
    """Verify valid product contract passes validation."""
    prod = ProductContract(
        product_id="PRD-001",
        sku="SKU-BEV-001",
        name="Organic Cold Brew Coffee 12oz",
        category="Beverages",
        subcategory="Ready to Drink",
        unit_cost=1.85,
        unit_price=3.99,
        reorder_point_units=100,
        min_order_qty=24,
        standard_lead_time_days=5,
    )
    assert prod.product_id == "PRD-001"
    assert prod.unit_price > prod.unit_cost


def test_product_contract_invalid_price_less_than_cost():
    """Verify product fails validation when selling price is below unit cost."""
    with pytest.raises(ValidationError, match="unit_price .* must be >= unit_cost"):
        ProductContract(
            product_id="PRD-002",
            sku="SKU-ERR-001",
            name="Loss Leader Error",
            category="Beverages",
            subcategory="Ready to Drink",
            unit_cost=10.00,
            unit_price=5.00,
        )


def test_location_contract_valid():
    """Verify valid location contract for Store and DC."""
    store = LocationContract(
        location_id="LOC-ST-01",
        location_code="ST-NYC-01",
        location_name="Midtown Flagship Store",
        location_type=LocationType.STORE,
        region="Northeast",
        city="New York",
        state="NY",
        storage_capacity_units=5000,
    )
    assert store.location_type == LocationType.STORE
    assert store.storage_capacity_units == 5000


def test_supplier_contract_valid():
    """Verify valid supplier contract and reliability score bounds."""
    supplier = SupplierContract(
        supplier_id="SUP-001",
        supplier_name="Global Beverage Bottlers",
        country="US",
        reliability_score=0.94,
        default_lead_time_days=6,
    )
    assert supplier.reliability_score == 0.94


def test_supplier_contract_invalid_score():
    """Verify supplier fails when reliability score is out of [0, 1] range."""
    with pytest.raises(ValidationError):
        SupplierContract(
            supplier_id="SUP-002",
            supplier_name="Bad Score Supplier",
            reliability_score=1.5,
            default_lead_time_days=6,
        )


def test_promotion_contract_valid():
    """Verify valid promotion date ranges and discount bounds."""
    promo = PromotionContract(
        promotion_id="PRM-SUMMER-26",
        promo_code="SUMMER26",
        promo_name="Summer Beverage Kickoff",
        promo_type="PERCENTAGE_DISCOUNT",
        discount_pct=0.20,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 14),
    )
    assert promo.discount_pct == 0.20


def test_promotion_contract_invalid_dates():
    """Verify promotion validation rejects start_date > end_date."""
    with pytest.raises(ValidationError, match="end_date .* cannot precede start_date"):
        PromotionContract(
            promotion_id="PRM-ERR",
            promo_code="ERR26",
            promo_name="Invalid Dates",
            promo_type="DISCOUNT",
            discount_pct=0.10,
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 1),
        )


def test_calendar_dim_contract_valid():
    """Verify calendar dimension contract instantiates cleanly."""
    cal = CalendarDimContract(
        date_key=date(2026, 6, 15),
        day_of_week=0,
        day_name="Monday",
        month=6,
        month_name="June",
        quarter=2,
        year=2026,
        is_weekend=False,
        is_holiday=False,
    )
    assert cal.year == 2026
    assert not cal.is_weekend


def test_sales_transaction_contract_valid():
    """Verify sales transaction validates matching sold and unfulfilled units."""
    tx = SalesTransactionContract(
        transaction_id="TX-1001",
        transaction_date=date(2026, 6, 15),
        product_id="PRD-001",
        location_id="LOC-ST-01",
        units_demanded=10,
        units_sold=8,
        unfulfilled_units=2,
        unit_selling_price=3.99,
        discount_pct=0.0,
        total_revenue=31.92,
    )
    assert tx.units_demanded == 10
    assert tx.units_sold == 8
    assert tx.unfulfilled_units == 2


def test_sales_transaction_contract_mismatch_unfulfilled():
    """Verify sales transaction rejects mismatched unfulfilled arithmetic."""
    with pytest.raises(ValidationError, match="unfulfilled_units .* must equal"):
        SalesTransactionContract(
            transaction_id="TX-1002",
            transaction_date=date(2026, 6, 15),
            product_id="PRD-001",
            location_id="LOC-ST-01",
            units_demanded=10,
            units_sold=8,
            unfulfilled_units=0,  # Invalid: should be 2
            unit_selling_price=3.99,
            total_revenue=31.92,
        )


def test_inventory_snapshot_contract_valid():
    """Verify inventory snapshot validation for available quantity and stockout flag."""
    snap = InventorySnapshotContract(
        snapshot_id="SNP-20260615-001",
        snapshot_date=date(2026, 6, 15),
        product_id="PRD-001",
        location_id="LOC-ST-01",
        on_hand_qty=150,
        in_transit_qty=48,
        reserved_qty=10,
        available_qty=140,
        stockout_flag=0,
    )
    assert snap.available_qty == 140
    assert snap.stockout_flag == 0


def test_inventory_snapshot_stockout_flag_enforcement():
    """Verify stockout_flag must be 1 when on_hand_qty is 0."""
    with pytest.raises(ValidationError, match="stockout_flag .* must be 1"):
        InventorySnapshotContract(
            snapshot_id="SNP-20260615-002",
            snapshot_date=date(2026, 6, 15),
            product_id="PRD-001",
            location_id="LOC-ST-01",
            on_hand_qty=0,
            in_transit_qty=0,
            reserved_qty=0,
            available_qty=0,
            stockout_flag=0,  # Invalid: must be 1 when on_hand == 0
        )


def test_supplier_delivery_contract_valid():
    """Verify supplier delivery contract with valid status and dates."""
    po = SupplierDeliveryContract(
        po_id="PO-9001",
        supplier_id="SUP-001",
        product_id="PRD-001",
        destination_location_id="LOC-ST-01",
        order_date=date(2026, 6, 1),
        promised_delivery_date=date(2026, 6, 7),
        actual_delivery_date=date(2026, 6, 9),
        qty_ordered=100,
        qty_received=100,
        lead_time_days=8,
        delay_days=2,
        po_status=POStatus.DELIVERED,
    )
    assert po.po_status == POStatus.DELIVERED
    assert po.delay_days == 2
