"""SQLAlchemy relational schema definitions and DDL management."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)
from sqlalchemy.engine import Engine

# Global naming convention for constraints and indexes
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)

# 1. Products Master
products = Table(
    "products",
    metadata,
    Column("product_id", String(64), primary_key=True),
    Column("sku", String(64), nullable=False, unique=True),
    Column("name", String(255), nullable=False),
    Column("category", String(64), nullable=False, index=True),
    Column("subcategory", String(64), nullable=False),
    Column("unit_cost", Float, nullable=False),
    Column("unit_price", Float, nullable=False),
    Column("reorder_point_units", Integer, nullable=False, default=50),
    Column("min_order_qty", Integer, nullable=False, default=10),
    Column("standard_lead_time_days", Integer, nullable=False, default=7),
    Column("is_active", Boolean, nullable=False, default=True),
    CheckConstraint("unit_cost > 0", name="unit_cost_positive"),
    CheckConstraint("unit_price >= unit_cost", name="unit_price_covers_cost"),
    CheckConstraint("min_order_qty >= 1", name="min_order_qty_positive"),
)

# 2. Locations Master
locations = Table(
    "locations",
    metadata,
    Column("location_id", String(64), primary_key=True),
    Column("location_code", String(32), nullable=False, unique=True),
    Column("location_name", String(255), nullable=False),
    Column("location_type", String(32), nullable=False),  # STORE or DC
    Column("region", String(64), nullable=False, index=True),
    Column("city", String(128), nullable=False),
    Column("state", String(64), nullable=False),
    Column("storage_capacity_units", Integer, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True),
    CheckConstraint("storage_capacity_units > 0", name="capacity_positive"),
)

# 3. Suppliers Master
suppliers = Table(
    "suppliers",
    metadata,
    Column("supplier_id", String(64), primary_key=True),
    Column("supplier_name", String(255), nullable=False),
    Column("country", String(64), nullable=False, default="US"),
    Column("reliability_score", Float, nullable=False),
    Column("default_lead_time_days", Integer, nullable=False, default=7),
    Column("is_active", Boolean, nullable=False, default=True),
    CheckConstraint("reliability_score >= 0.0 AND reliability_score <= 1.0", name="reliability_range"),
)

# 4. Promotions Master
promotions = Table(
    "promotions",
    metadata,
    Column("promotion_id", String(64), primary_key=True),
    Column("promo_code", String(32), nullable=False, unique=True),
    Column("promo_name", String(255), nullable=False),
    Column("promo_type", String(64), nullable=False),
    Column("discount_pct", Float, nullable=False, default=0.0),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date, nullable=False),
    Column("is_active", Boolean, nullable=False, default=True),
    CheckConstraint("discount_pct >= 0.0 AND discount_pct <= 1.0", name="discount_range"),
    CheckConstraint("end_date >= start_date", name="promo_date_range_valid"),
)

# 5. Calendar Dimension
calendar_dim = Table(
    "calendar_dim",
    metadata,
    Column("date_key", Date, primary_key=True),
    Column("day_of_week", Integer, nullable=False),
    Column("day_name", String(10), nullable=False),
    Column("month", Integer, nullable=False),
    Column("month_name", String(15), nullable=False),
    Column("quarter", Integer, nullable=False),
    Column("year", Integer, nullable=False),
    Column("is_weekend", Boolean, nullable=False),
    Column("is_holiday", Boolean, nullable=False, default=False),
    Column("holiday_name", String(128), nullable=True),
)

# 6. Sales Transactions (Fact)
sales_transactions = Table(
    "sales_transactions",
    metadata,
    Column("transaction_id", String(64), primary_key=True),
    Column("transaction_date", Date, ForeignKey("calendar_dim.date_key"), nullable=False, index=True),
    Column("product_id", String(64), ForeignKey("products.product_id"), nullable=False, index=True),
    Column("location_id", String(64), ForeignKey("locations.location_id"), nullable=False, index=True),
    Column("promotion_id", String(64), ForeignKey("promotions.promotion_id"), nullable=True),
    Column("units_demanded", Integer, nullable=False),
    Column("units_sold", Integer, nullable=False),
    Column("unfulfilled_units", Integer, nullable=False, default=0),
    Column("unit_selling_price", Float, nullable=False),
    Column("discount_pct", Float, nullable=False, default=0.0),
    Column("total_revenue", Float, nullable=False),
    CheckConstraint("units_demanded >= 0", name="units_demanded_nonneg"),
    CheckConstraint("units_sold >= 0", name="units_sold_nonneg"),
    CheckConstraint("units_sold <= units_demanded", name="sold_lte_demanded"),
    CheckConstraint("unfulfilled_units == units_demanded - units_sold", name="unfulfilled_units_exact"),
    Index("ix_sales_date_product_location", "transaction_date", "product_id", "location_id"),
)

# 7. Inventory Snapshots (Daily Periodic Snapshot Fact)
inventory_snapshots = Table(
    "inventory_snapshots",
    metadata,
    Column("snapshot_id", String(64), primary_key=True),
    Column("snapshot_date", Date, ForeignKey("calendar_dim.date_key"), nullable=False, index=True),
    Column("product_id", String(64), ForeignKey("products.product_id"), nullable=False, index=True),
    Column("location_id", String(64), ForeignKey("locations.location_id"), nullable=False, index=True),
    Column("on_hand_qty", Integer, nullable=False),
    Column("in_transit_qty", Integer, nullable=False, default=0),
    Column("reserved_qty", Integer, nullable=False, default=0),
    Column("available_qty", Integer, nullable=False),
    Column("stockout_flag", Integer, nullable=False, default=0),
    CheckConstraint("on_hand_qty >= 0", name="on_hand_nonneg"),
    CheckConstraint("in_transit_qty >= 0", name="in_transit_nonneg"),
    CheckConstraint("reserved_qty >= 0", name="reserved_nonneg"),
    CheckConstraint("available_qty == on_hand_qty - reserved_qty", name="available_qty_exact"),
    Index("ix_inv_snapshot_date_product_location", "snapshot_date", "product_id", "location_id", unique=True),
)

# 8. Supplier Deliveries / Purchase Orders (Accumulating Snapshot Fact)
supplier_deliveries = Table(
    "supplier_deliveries",
    metadata,
    Column("po_id", String(64), primary_key=True),
    Column("supplier_id", String(64), ForeignKey("suppliers.supplier_id"), nullable=False, index=True),
    Column("product_id", String(64), ForeignKey("products.product_id"), nullable=False, index=True),
    Column("destination_location_id", String(64), ForeignKey("locations.location_id"), nullable=False, index=True),
    Column("order_date", Date, ForeignKey("calendar_dim.date_key"), nullable=False, index=True),
    Column("promised_delivery_date", Date, nullable=False),
    Column("actual_delivery_date", Date, nullable=True),
    Column("qty_ordered", Integer, nullable=False),
    Column("qty_received", Integer, nullable=False, default=0),
    Column("lead_time_days", Integer, nullable=True),
    Column("delay_days", Integer, nullable=True),
    Column("po_status", String(32), nullable=False, default="PENDING"),
    CheckConstraint("qty_ordered > 0", name="qty_ordered_positive"),
    CheckConstraint("qty_received >= 0", name="qty_received_nonneg"),
    Index("ix_po_supplier_product", "supplier_id", "product_id"),
)


def get_metadata() -> MetaData:
    """Return the global SQLAlchemy MetaData containing all tables."""
    return metadata


def create_all_tables(engine: Engine) -> None:
    """Create all relational tables in the target database engine."""
    metadata.create_all(bind=engine)


def drop_all_tables(engine: Engine) -> None:
    """Drop all relational tables in the target database engine."""
    metadata.drop_all(bind=engine)
