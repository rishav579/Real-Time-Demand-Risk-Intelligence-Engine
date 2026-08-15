"""Integration tests for SQLAlchemy schema DDL creation and relational constraints."""

from datetime import date
from sqlalchemy import create_engine, inspect, select
from src.data.schema import (
    calendar_dim,
    create_all_tables,
    drop_all_tables,
    get_metadata,
    inventory_snapshots,
    locations,
    products,
    promotions,
    sales_transactions,
    supplier_deliveries,
    suppliers,
)


def test_schema_ddl_creation_and_teardown():
    """Verify that all 8 tables, constraints, and indexes can be created in SQLite."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # 1. Create tables
    create_all_tables(engine)
    
    inspector = inspect(engine)
    created_tables = set(inspector.get_table_names())
    
    expected_tables = {
        "products",
        "locations",
        "suppliers",
        "promotions",
        "calendar_dim",
        "sales_transactions",
        "inventory_snapshots",
        "supplier_deliveries",
    }
    
    assert expected_tables.issubset(created_tables), f"Missing tables: {expected_tables - created_tables}"
    
    # 2. Inspect product table columns
    prod_cols = {c["name"] for c in inspector.get_columns("products")}
    assert {"product_id", "sku", "unit_cost", "unit_price", "reorder_point_units"}.issubset(prod_cols)
    
    # 3. Test insert and query on dimension and fact tables
    with engine.begin() as conn:
        # Insert calendar record
        conn.execute(
            calendar_dim.insert().values(
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
        )
        
        # Insert product record
        conn.execute(
            products.insert().values(
                product_id="PRD-001",
                sku="SKU-BEV-001",
                name="Cold Brew Coffee",
                category="Beverages",
                subcategory="RTD",
                unit_cost=1.50,
                unit_price=3.50,
                reorder_point_units=50,
                min_order_qty=20,
                standard_lead_time_days=5,
                is_active=True,
            )
        )
        
        # Insert location record
        conn.execute(
            locations.insert().values(
                location_id="LOC-001",
                location_code="NYC-01",
                location_name="Downtown Store",
                location_type="STORE",
                region="Northeast",
                city="New York",
                state="NY",
                storage_capacity_units=10000,
                is_active=True,
            )
        )
        
        # Insert fact snapshot record
        conn.execute(
            inventory_snapshots.insert().values(
                snapshot_id="SNP-001",
                snapshot_date=date(2026, 6, 15),
                product_id="PRD-001",
                location_id="LOC-001",
                on_hand_qty=120,
                in_transit_qty=0,
                reserved_qty=10,
                available_qty=110,
                stockout_flag=0,
            )
        )
        
        # Query fact snapshot
        result = conn.execute(
            select(inventory_snapshots.c.available_qty).where(
                inventory_snapshots.c.snapshot_id == "SNP-001"
            )
        ).scalar()
        assert result == 110
        
    # 4. Drop tables
    drop_all_tables(engine)
    inspector_after = inspect(engine)
    assert len(inspector_after.get_table_names()) == 0
