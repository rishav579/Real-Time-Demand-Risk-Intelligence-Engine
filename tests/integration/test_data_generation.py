"""Integration tests for deterministic data generation, database seeding, and foreign key integrity."""

from datetime import date
from sqlalchemy import create_engine, select, text

from src.data.generator import DataGenerator, seed_database
from src.data.schema import (
    calendar_dim,
    inventory_snapshots,
    locations,
    products,
    promotions,
    sales_transactions,
    supplier_deliveries,
    suppliers,
)


def test_seed_database_and_foreign_key_integrity():
    """Verify database seeding and SQLite PRAGMA foreign_key_check returns zero violations."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=90)

    counts = seed_database(engine, dataset, recreate_tables=True)

    assert counts["calendar_dim"] == 90
    assert counts["products"] == 15
    assert counts["locations"] == 5
    assert counts["sales_transactions"] == 90 * 4 * 15

    # Verify foreign key integrity using SQLite built-in checker
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON;"))
        fk_violations = conn.execute(text("PRAGMA foreign_key_check;")).fetchall()
        assert len(fk_violations) == 0, f"Foreign key violations detected: {fk_violations}"


def test_sql_relational_queries():
    """Verify relational joins work seamlessly across generated facts and dimensions."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=60)
    seed_database(engine, dataset, recreate_tables=True)

    with engine.connect() as conn:
        # Join sales_transactions with products and calendar_dim
        query = text("""
            SELECT 
                p.category,
                c.month_name,
                SUM(s.units_sold) AS total_sold,
                SUM(s.total_revenue) AS total_revenue
            FROM sales_transactions s
            JOIN products p ON s.product_id = p.product_id
            JOIN calendar_dim c ON s.transaction_date = c.date_key
            GROUP BY p.category, c.month_name
            ORDER BY total_revenue DESC
        """)
        results = conn.execute(query).fetchall()
        assert len(results) > 0
        for row in results:
            assert row.total_sold > 0
            assert row.total_revenue > 0


def test_inventory_continuity_and_availability():
    """Verify available_qty = on_hand_qty - reserved_qty holds across all DB rows."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    generator = DataGenerator(seed=42)
    dataset = generator.generate(start_date=date(2026, 1, 1), num_days=30)
    seed_database(engine, dataset, recreate_tables=True)

    with engine.connect() as conn:
        # Query any inconsistent inventory row
        inconsistent = conn.execute(text("""
            SELECT snapshot_id 
            FROM inventory_snapshots 
            WHERE available_qty != (on_hand_qty - reserved_qty)
               OR (on_hand_qty = 0 AND stockout_flag != 1)
               OR (on_hand_qty > 0 AND stockout_flag != 0)
        """)).fetchall()

        assert len(inconsistent) == 0, f"Found {len(inconsistent)} inconsistent inventory snapshots"
