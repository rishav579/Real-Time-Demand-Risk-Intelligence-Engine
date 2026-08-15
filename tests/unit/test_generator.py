"""Unit tests for deterministic enterprise data generator and planted business signals."""

from datetime import date
import pytest

from src.data.generator import DataGenerator


@pytest.fixture(scope="module")
def dataset_seed_42():
    """Cached dataset generated with seed 42."""
    generator = DataGenerator(seed=42)
    return generator.generate(start_date=date(2026, 1, 1), num_days=365)


def test_generator_determinism():
    """Verify same seed produces 100% identical logical data."""
    gen1 = DataGenerator(seed=42)
    data1 = gen1.generate(num_days=30)

    gen2 = DataGenerator(seed=42)
    data2 = gen2.generate(num_days=30)

    assert data1.summary_counts() == data2.summary_counts()
    assert data1.sales_transactions == data2.sales_transactions
    assert data1.inventory_snapshots == data2.inventory_snapshots
    assert data1.supplier_deliveries == data2.supplier_deliveries


def test_generator_different_seed_variability():
    """Verify different seeds produce different pseudo-random transaction values and replenishment timing."""
    gen1 = DataGenerator(seed=42)
    data1 = gen1.generate(num_days=30)

    gen2 = DataGenerator(seed=99)
    data2 = gen2.generate(num_days=30)

    # Topology and snapshot counts remain identical
    c1 = data1.summary_counts()
    c2 = data2.summary_counts()
    for key in ("calendar_dim", "products", "locations", "suppliers", "promotions", "sales_transactions", "inventory_snapshots"):
        assert c1[key] == c2[key]

    # Transaction values vary due to different noise streams
    assert data1.sales_transactions != data2.sales_transactions


def test_table_row_counts_stable(dataset_seed_42):
    """Verify expected entity row counts over a 365-day calendar horizon."""
    counts = dataset_seed_42.summary_counts()
    assert counts["calendar_dim"] == 365
    assert counts["products"] == 15
    assert counts["locations"] == 5
    assert counts["suppliers"] == 4
    assert counts["promotions"] == 3
    assert counts["sales_transactions"] == 365 * 4 * 15  # 4 stores * 15 SKUs * 365 days = 21,900
    assert counts["inventory_snapshots"] == 365 * 5 * 15  # 5 facilities * 15 SKUs * 365 days = 27,375
    assert counts["supplier_deliveries"] > 1000


def test_planted_promotional_demand_lift(dataset_seed_42):
    """Verify planted promotion PRM-SUMMER-26 generates ~+35% demand lift on target SKU within same season."""
    promo_start = date(2026, 6, 1)
    promo_end = date(2026, 6, 14)
    target_sku = "PRD-BEV-001"

    promo_demand = []
    non_promo_june_demand = []

    for tx in dataset_seed_42.sales_transactions:
        if tx["product_id"] == target_sku:
            tx_date = tx["transaction_date"]
            if promo_start <= tx_date <= promo_end:
                promo_demand.append(tx["units_demanded"])
            elif date(2026, 6, 15) <= tx_date <= date(2026, 6, 30):
                non_promo_june_demand.append(tx["units_demanded"])

    avg_promo = sum(promo_demand) / len(promo_demand)
    avg_non_promo = sum(non_promo_june_demand) / len(non_promo_june_demand)
    observed_lift = (avg_promo - avg_non_promo) / avg_non_promo

    # Expected ~+35% isolated promotional lift (e.g. 28% to 42%)
    assert 0.28 <= observed_lift <= 0.45, f"Observed promotional lift was {observed_lift:.2%}"


def test_planted_supplier_delay(dataset_seed_42):
    """Verify planted supplier delay (+9 days) exists for PRD-BEV-001 at LOC-ST-01."""
    delayed_pos = [
        po for po in dataset_seed_42.supplier_deliveries
        if po["product_id"] == "PRD-BEV-001"
        and po["destination_location_id"] == "LOC-ST-01"
        and po["delay_days"] == 9
    ]

    assert len(delayed_pos) >= 1, "Planted 9-day supplier delay PO not found"
    sample_po = delayed_pos[0]
    expected_diff = (sample_po["actual_delivery_date"] - sample_po["promised_delivery_date"]).days
    assert expected_diff == 9


def test_planted_stockout_causal_chain(dataset_seed_42):
    """Verify that promotional demand + supplier delay produced unfulfilled demand and stockouts."""
    target_sku = "PRD-BEV-001"
    target_store = "LOC-ST-01"

    # Find stockout snapshots during late May / early June 2026
    stockout_snapshots = [
        snap for snap in dataset_seed_42.inventory_snapshots
        if snap["product_id"] == target_sku
        and snap["location_id"] == target_store
        and date(2026, 6, 1) <= snap["snapshot_date"] <= date(2026, 6, 15)
        and snap["stockout_flag"] == 1
    ]

    # Find unfulfilled sales transactions during same period
    unfulfilled_sales = [
        tx for tx in dataset_seed_42.sales_transactions
        if tx["product_id"] == target_sku
        and tx["location_id"] == target_store
        and date(2026, 6, 1) <= tx["transaction_date"] <= date(2026, 6, 15)
        and tx["unfulfilled_units"] > 0
    ]

    assert len(stockout_snapshots) > 0, "No inventory stockouts detected during crisis window"
    assert len(unfulfilled_sales) > 0, "No unfulfilled sales demand recorded during crisis window"


def test_regional_seasonal_divergence(dataset_seed_42):
    """Verify South region has higher summer demand for seasonal items than winter."""
    target_sku = "PRD-SEA-001"  # Electrolyte drink
    south_store = "LOC-ST-03"    # Miami

    summer_demand = [
        tx["units_demanded"] for tx in dataset_seed_42.sales_transactions
        if tx["product_id"] == target_sku
        and tx["location_id"] == south_store
        and date(2026, 6, 1) <= tx["transaction_date"] <= date(2026, 8, 31)
    ]

    winter_demand = [
        tx["units_demanded"] for tx in dataset_seed_42.sales_transactions
        if tx["product_id"] == target_sku
        and tx["location_id"] == south_store
        and (tx["transaction_date"] < date(2026, 3, 1) or tx["transaction_date"] >= date(2026, 11, 1))
    ]

    avg_summer = sum(summer_demand) / len(summer_demand)
    avg_winter = sum(winter_demand) / len(winter_demand)

    assert avg_summer > avg_winter * 1.30, f"Summer demand ({avg_summer:.1f}) not significantly higher than winter ({avg_winter:.1f})"


def test_slow_moving_capital_drag(dataset_seed_42):
    """Verify slow moving SKU PRD-HOU-003 exhibits sparse demand and high inventory holdings."""
    slow_sku = "PRD-HOU-003"

    total_demanded = sum(
        tx["units_demanded"] for tx in dataset_seed_42.sales_transactions
        if tx["product_id"] == slow_sku
    )
    # 4 stores * 365 days = 1460 store-days
    avg_daily_demand = total_demanded / 1460

    # Slow mover demand should be < 0.50 units per day on average
    assert avg_daily_demand < 0.50

    # Check that average on-hand stock is substantially higher than daily demand
    avg_stock = sum(
        snap["on_hand_qty"] for snap in dataset_seed_42.inventory_snapshots
        if snap["product_id"] == slow_sku and snap["location_id"].startswith("LOC-ST")
    ) / 1460

    days_of_supply = avg_stock / max(0.01, avg_daily_demand)
    assert days_of_supply > 60, f"Expected >60 days of supply for slow mover, got {days_of_supply:.1f}"


def test_stable_baseline_product(dataset_seed_42):
    """Verify staple product PRD-BEV-003 maintains stable non-zero demand with minimal stockouts."""
    staple_sku = "PRD-BEV-003"

    stockouts = [
        snap for snap in dataset_seed_42.inventory_snapshots
        if snap["product_id"] == staple_sku and snap["stockout_flag"] == 1
    ]

    # Baseline product should experience zero or near-zero stockout days
    assert len(stockouts) == 0, f"Stable baseline SKU experienced unexpected stockouts: {len(stockouts)}"
