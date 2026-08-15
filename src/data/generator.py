"""Deterministic synthetic enterprise data generator with planted business signals.

Generates realistic telemetry for multi-location retail and distribution:
- Master data: products, locations, suppliers, promotions, calendar dimension
- Transaction telemetry: sales transactions with promotional & seasonal demand
- Inventory telemetry: daily periodic snapshot balances with stockout flags
- Inbound supply chain: purchase orders with lead time delays
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config.settings import get_settings
from src.data.schema import (
    calendar_dim,
    create_all_tables,
    drop_all_tables,
    inventory_snapshots,
    locations,
    products,
    promotions,
    sales_transactions,
    supplier_deliveries,
    suppliers,
)
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


@dataclass(frozen=True)
class SyntheticDataset:
    """Container for all generated synthetic enterprise entities."""
    calendar: List[Dict[str, Any]]
    products: List[Dict[str, Any]]
    locations: List[Dict[str, Any]]
    suppliers: List[Dict[str, Any]]
    promotions: List[Dict[str, Any]]
    sales_transactions: List[Dict[str, Any]]
    inventory_snapshots: List[Dict[str, Any]]
    supplier_deliveries: List[Dict[str, Any]]

    def summary_counts(self) -> Dict[str, int]:
        """Return row counts across all generated tables."""
        return {
            "calendar_dim": len(self.calendar),
            "products": len(self.products),
            "locations": len(self.locations),
            "suppliers": len(self.suppliers),
            "promotions": len(self.promotions),
            "sales_transactions": len(self.sales_transactions),
            "inventory_snapshots": len(self.inventory_snapshots),
            "supplier_deliveries": len(self.supplier_deliveries),
        }


class DataGenerator:
    """Deterministic enterprise data generator with planted causal dynamics."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate(
        self,
        start_date: date = date(2026, 1, 1),
        num_days: int = 365,
    ) -> SyntheticDataset:
        """Generate full synthetic enterprise dataset."""
        # 1. Dimensions and Master Catalog
        calendar_rows = self._generate_calendar(start_date, num_days)
        product_rows = self._generate_products()
        location_rows = self._generate_locations()
        supplier_rows = self._generate_suppliers()
        promotion_rows = self._generate_promotions(start_date)

        # 2. Daily Sales & Supply Telemetry Simulation
        sales_rows, snapshot_rows, delivery_rows = self._simulate_sales_and_inventory(
            calendar_rows=calendar_rows,
            product_rows=product_rows,
            location_rows=location_rows,
            supplier_rows=supplier_rows,
            promotion_rows=promotion_rows,
        )

        return SyntheticDataset(
            calendar=calendar_rows,
            products=product_rows,
            locations=location_rows,
            suppliers=supplier_rows,
            promotions=promotion_rows,
            sales_transactions=sales_rows,
            inventory_snapshots=snapshot_rows,
            supplier_deliveries=delivery_rows,
        )

    def _generate_calendar(self, start_date: date, num_days: int) -> List[Dict[str, Any]]:
        """Generate calendar dimension records."""
        calendar = []
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        month_names = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        # Explicit holiday dates for year 2026
        holidays_2026 = {
            date(2026, 1, 1): "New Year's Day",
            date(2026, 5, 25): "Memorial Day",
            date(2026, 7, 4): "Independence Day",
            date(2026, 9, 7): "Labor Day",
            date(2026, 11, 26): "Thanksgiving",
            date(2026, 12, 25): "Christmas Day",
        }

        for i in range(num_days):
            current_date = start_date + timedelta(days=i)
            dow = current_date.weekday()
            is_weekend = dow in (5, 6)
            is_holiday = current_date in holidays_2026
            holiday_name = holidays_2026.get(current_date)
            quarter = (current_date.month - 1) // 3 + 1

            row = {
                "date_key": current_date,
                "day_of_week": dow,
                "day_name": day_names[dow],
                "month": current_date.month,
                "month_name": month_names[current_date.month],
                "quarter": quarter,
                "year": current_date.year,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "holiday_name": holiday_name,
            }
            # Contract validation
            CalendarDimContract(**row)
            calendar.append(row)

        return calendar

    def _generate_products(self) -> List[Dict[str, Any]]:
        """Generate SKU catalog spanning high-velocity, seasonal, staple, and slow-moving items."""
        # Defined catalog with distinct operational archetypes
        catalog_defs = [
            # High Velocity & Promo Target (Beverages)
            ("PRD-BEV-001", "SKU-BEV-001", "Cold Brew Coffee 12oz", "Beverages", "Ready to Drink", 1.80, 3.99, 120, 48, 5, "HIGH_VELOCITY"),
            ("PRD-BEV-002", "SKU-BEV-002", "Organic Sparkling Water Lime 6pk", "Beverages", "Carbonated", 2.20, 4.99, 100, 36, 6, "MEDIUM_VELOCITY"),
            ("PRD-BEV-003", "SKU-BEV-003", "Classic Mineral Water 1L", "Beverages", "Still Water", 0.75, 1.99, 80, 24, 4, "STABLE_BASELINE"),
            ("PRD-BEV-004", "SKU-BEV-004", "Artisan Kombucha Ginger 16oz", "Beverages", "Functional", 2.10, 4.49, 60, 24, 7, "MEDIUM_VELOCITY"),
            # Snacks
            ("PRD-SNK-001", "SKU-SNK-001", "Artisan Sea Salt Kettle Chips 8oz", "Snacks", "Chips & Crisps", 1.40, 3.49, 110, 40, 5, "HIGH_VELOCITY"),
            ("PRD-SNK-002", "SKU-SNK-002", "Roasted Almonds with Sea Salt 10oz", "Snacks", "Nuts & Seeds", 3.80, 7.99, 50, 20, 8, "MEDIUM_VELOCITY"),
            ("PRD-SNK-003", "SKU-SNK-003", "Organic Dark Chocolate Bar 72%", "Snacks", "Confectionery", 1.60, 3.79, 70, 30, 6, "MEDIUM_VELOCITY"),
            ("PRD-SNK-004", "SKU-SNK-004", "Protein Trail Mix 12oz", "Snacks", "Nuts & Seeds", 4.10, 8.49, 45, 15, 7, "MEDIUM_VELOCITY"),
            # Seasonal Summer Items
            ("PRD-SEA-001", "SKU-SEA-001", "Electrolyte Hydration Drink 32oz", "Beverages", "Sports Nutrition", 1.10, 2.79, 90, 36, 6, "SUMMER_SEASONAL"),
            ("PRD-SEA-002", "SKU-SEA-002", "Sunscreen Lotion SPF 50 6oz", "Personal Care", "Sun Care", 4.50, 9.99, 40, 12, 10, "SUMMER_SEASONAL"),
            # Household & Slow Movers (Capital Drag)
            ("PRD-HOU-001", "SKU-HOU-001", "Eco-Friendly Dish Soap 24oz", "Household", "Cleaning Supplies", 1.90, 4.29, 60, 24, 6, "STABLE_BASELINE"),
            ("PRD-HOU-002", "SKU-HOU-002", "Recycled Paper Towels 6pk", "Household", "Paper Goods", 4.20, 8.99, 75, 24, 5, "STABLE_BASELINE"),
            ("PRD-HOU-003", "SKU-HOU-003", "Industrial Floor Degreaser 1Gal", "Household", "Specialty Cleaning", 12.00, 24.99, 15, 60, 14, "SLOW_MOVER_DRAG"),
            ("PRD-HOU-004", "SKU-HOU-004", "Heavy Duty Steel Polish 16oz", "Household", "Specialty Cleaning", 6.50, 14.99, 15, 48, 12, "SLOW_MOVER_DRAG"),
            # Personal Care
            ("PRD-PER-001", "SKU-PER-001", "Gentle Hydrating Facial Cleanser 8oz", "Personal Care", "Skin Care", 5.20, 11.99, 40, 16, 7, "MEDIUM_VELOCITY"),
        ]

        products_list = []
        for p_id, sku, name, cat, subcat, cost, price, rop, moq, lt, archetype in catalog_defs:
            row = {
                "product_id": p_id,
                "sku": sku,
                "name": name,
                "category": cat,
                "subcategory": subcat,
                "unit_cost": cost,
                "unit_price": price,
                "reorder_point_units": rop,
                "min_order_qty": moq,
                "standard_lead_time_days": lt,
                "is_active": True,
            }
            # Contract validation
            ProductContract(**row)
            # Attach archetype metadata temporarily for generator logic
            row["_archetype"] = archetype
            products_list.append(row)

        return products_list

    def _generate_locations(self) -> List[Dict[str, Any]]:
        """Generate network topology: 1 Distribution Center and 4 Retail Stores."""
        loc_defs = [
            ("LOC-DC-01", "DC-CENTRAL", "Central Regional Distribution Center", LocationType.DISTRIBUTION_CENTER, "Midwest", "Chicago", "IL", 100000),
            ("LOC-ST-01", "ST-NYC-01", "Midtown Manhattan Store", LocationType.STORE, "Northeast", "New York", "NY", 8000),
            ("LOC-ST-02", "ST-BOS-01", "Downtown Boston Store", LocationType.STORE, "Northeast", "Boston", "MA", 6000),
            ("LOC-ST-03", "ST-MIA-01", "Miami South Beach Store", LocationType.STORE, "South", "Miami", "FL", 7500),
            ("LOC-ST-04", "ST-SEA-01", "Seattle Pike Place Store", LocationType.STORE, "West", "Seattle", "WA", 6500),
        ]

        locations_list = []
        for loc_id, code, name, ltype, region, city, state, cap in loc_defs:
            row = {
                "location_id": loc_id,
                "location_code": code,
                "location_name": name,
                "location_type": ltype.value,
                "region": region,
                "city": city,
                "state": state,
                "storage_capacity_units": cap,
                "is_active": True,
            }
            LocationContract(
                location_id=loc_id,
                location_code=code,
                location_name=name,
                location_type=ltype,
                region=region,
                city=city,
                state=state,
                storage_capacity_units=cap,
                is_active=True,
            )
            locations_list.append(row)

        return locations_list

    def _generate_suppliers(self) -> List[Dict[str, Any]]:
        """Generate supplier master data with reliability and lead-time characteristics."""
        sup_defs = [
            ("SUP-001", "Apex Beverage Bottlers Co", "US", 0.96, 5),
            ("SUP-002", "Artisan Snackcraft Foods", "US", 0.78, 6),  # Subject to planted delay
            ("SUP-003", "Pacific Coast Essentials", "US", 0.92, 7),
            ("SUP-004", "National Industrial Cleaners", "US", 0.88, 14),
        ]

        suppliers_list = []
        for s_id, name, country, rel, lt in sup_defs:
            row = {
                "supplier_id": s_id,
                "supplier_name": name,
                "country": country,
                "reliability_score": rel,
                "default_lead_time_days": lt,
                "is_active": True,
            }
            SupplierContract(**row)
            suppliers_list.append(row)

        return suppliers_list

    def _generate_promotions(self, start_date: date) -> List[Dict[str, Any]]:
        """Generate promotional campaigns with explicit date windows."""
        promo_defs = [
            ("PRM-SUMMER-26", "SUMMER26", "Summer Refreshment Promo", "PERCENTAGE_DISCOUNT", 0.20, date(2026, 6, 1), date(2026, 6, 14)),
            ("PRM-FALL-26", "FALL26", "Fall Harvest Snack Blitz", "PERCENTAGE_DISCOUNT", 0.15, date(2026, 9, 14), date(2026, 9, 27)),
            ("PRM-HOLIDAY-26", "HOLIDAY26", "Holiday Entertaining Event", "PERCENTAGE_DISCOUNT", 0.25, date(2026, 12, 10), date(2026, 12, 24)),
        ]

        promotions_list = []
        for p_id, code, name, ptype, disc, sdate, edate in promo_defs:
            row = {
                "promotion_id": p_id,
                "promo_code": code,
                "promo_name": name,
                "promo_type": ptype,
                "discount_pct": disc,
                "start_date": sdate,
                "end_date": edate,
                "is_active": True,
            }
            PromotionContract(**row)
            promotions_list.append(row)

        return promotions_list

    def _simulate_sales_and_inventory(
        self,
        calendar_rows: List[Dict[str, Any]],
        product_rows: List[Dict[str, Any]],
        location_rows: List[Dict[str, Any]],
        supplier_rows: List[Dict[str, Any]],
        promotion_rows: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Simulate daily customer demand, stockouts, and inbound supply chain replenishment."""
        sales_records: List[Dict[str, Any]] = []
        snapshot_records: List[Dict[str, Any]] = []
        delivery_records: List[Dict[str, Any]] = []

        stores = [loc for loc in location_rows if loc["location_type"] == LocationType.STORE.value]
        dc = next(loc for loc in location_rows if loc["location_type"] == LocationType.DISTRIBUTION_CENTER.value)

        # Mapping products to suppliers
        prod_supplier_map = {
            "PRD-BEV-001": "SUP-001",
            "PRD-BEV-002": "SUP-001",
            "PRD-BEV-003": "SUP-001",
            "PRD-BEV-004": "SUP-001",
            "PRD-SNK-001": "SUP-002",
            "PRD-SNK-002": "SUP-002",
            "PRD-SNK-003": "SUP-002",
            "PRD-SNK-004": "SUP-002",
            "PRD-SEA-001": "SUP-001",
            "PRD-SEA-002": "SUP-003",
            "PRD-HOU-001": "SUP-003",
            "PRD-HOU-002": "SUP-003",
            "PRD-HOU-003": "SUP-004",
            "PRD-HOU-004": "SUP-004",
            "PRD-PER-001": "SUP-003",
        }

        # Initialize current stock levels for each location-product pair
        current_on_hand: Dict[Tuple[str, str], int] = {}
        in_transit_pipeline: List[Dict[str, Any]] = []

        for p in product_rows:
            p_id = p["product_id"]
            archetype = p["_archetype"]
            for loc in location_rows:
                l_id = loc["location_id"]
                l_type = loc["location_type"]
                if l_type == LocationType.DISTRIBUTION_CENTER.value:
                    initial_stock = 1500 if archetype == "HIGH_VELOCITY" else (300 if archetype == "SLOW_MOVER_DRAG" else 800)
                else:
                    initial_stock = 250 if archetype == "HIGH_VELOCITY" else (120 if archetype == "SLOW_MOVER_DRAG" else 150)
                current_on_hand[(l_id, p_id)] = initial_stock

        po_counter = 1
        tx_counter = 1

        # Planted stockout crisis parameters:
        # Target: PRD-BEV-001 at LOC-ST-01 during PRM-SUMMER-26 (2026-06-01 to 2026-06-14)
        # We order a PO around 2026-05-24 with SUP-001/002, inject a 9-day delay, so it arrives late (June 11 instead of June 2).

        for day_idx, cal in enumerate(calendar_rows):
            current_date: date = cal["date_key"]
            dow = cal["day_of_week"]
            is_weekend = cal["is_weekend"]
            month = cal["month"]

            # 1. Process Inbound Deliveries Arriving Today
            arrived_pos = [po for po in in_transit_pipeline if po["actual_delivery_date"] == current_date]
            for po in arrived_pos:
                loc_id = po["destination_location_id"]
                p_id = po["product_id"]
                current_on_hand[(loc_id, p_id)] += po["qty_received"]
                po["po_status"] = POStatus.DELIVERED.value
                # Clean up contract
                del po["_created_day"]
                delivery_records.append(po)

            in_transit_pipeline = [po for po in in_transit_pipeline if po["po_status"] != POStatus.DELIVERED.value]

            # 2. Process Daily Sales Demand at Each Retail Store
            for store in stores:
                s_id = store["location_id"]
                region = store["region"]

                for prod in product_rows:
                    p_id = prod["product_id"]
                    archetype = prod["_archetype"]
                    unit_price = prod["unit_price"]
                    reorder_point = prod["reorder_point_units"]
                    moq = prod["min_order_qty"]
                    lead_time = prod["standard_lead_time_days"]
                    supplier_id = prod_supplier_map[p_id]

                    # Determine active promotion
                    active_promo_id: Optional[str] = None
                    discount_pct = 0.0
                    for promo in promotion_rows:
                        if promo["start_date"] <= current_date <= promo["end_date"]:
                            # Targeted promotions
                            if promo["promotion_id"] == "PRM-SUMMER-26" and p_id in ("PRD-BEV-001", "PRD-SEA-001", "PRD-SEA-002"):
                                active_promo_id = promo["promotion_id"]
                                discount_pct = promo["discount_pct"]
                            elif promo["promotion_id"] == "PRM-FALL-26" and p_id in ("PRD-SNK-001", "PRD-SNK-003"):
                                active_promo_id = promo["promotion_id"]
                                discount_pct = promo["discount_pct"]
                            elif promo["promotion_id"] == "PRM-HOLIDAY-26" and p_id in ("PRD-SNK-002", "PRD-BEV-002", "PRD-HOU-001"):
                                active_promo_id = promo["promotion_id"]
                                discount_pct = promo["discount_pct"]

                    # Base demand calculation
                    if archetype == "HIGH_VELOCITY":
                        base_lambda = 28.0
                    elif archetype == "MEDIUM_VELOCITY":
                        base_lambda = 14.0
                    elif archetype == "STABLE_BASELINE":
                        base_lambda = 10.0
                    elif archetype == "SUMMER_SEASONAL":
                        base_lambda = 12.0
                    elif archetype == "SLOW_MOVER_DRAG":
                        base_lambda = 0.25
                    else:
                        base_lambda = 8.0

                    # Weekend factor
                    weekend_multiplier = 1.35 if is_weekend else 0.90

                    # Regional & Seasonal multiplier
                    season_multiplier = 1.0
                    if region == "South":
                        # Strong summer demand (June - August)
                        if month in (5, 6, 7, 8):
                            season_multiplier = 1.45 if archetype in ("HIGH_VELOCITY", "SUMMER_SEASONAL") else 1.20
                        elif month in (11, 12, 1, 2):
                            season_multiplier = 0.85
                    elif region == "Northeast":
                        if month in (6, 7, 8):
                            season_multiplier = 1.15
                        elif month in (1, 2):
                            season_multiplier = 0.80
                    elif region == "West":
                        season_multiplier = 1.05

                    # Promotional Demand Lift (+35% targeted lift)
                    promo_multiplier = 1.35 if active_promo_id is not None else 1.0

                    expected_demand = base_lambda * weekend_multiplier * season_multiplier * promo_multiplier

                    # Add deterministic pseudo-random variance
                    demand_noise = self.rng.gauss(0.0, 0.12 * max(1.0, expected_demand))
                    demanded_units = max(0, int(round(expected_demand + demand_noise)))

                    if archetype == "SLOW_MOVER_DRAG":
                        # Sparse Bernoulli-Poisson demand for slow movers
                        demanded_units = 1 if self.rng.random() < 0.20 else 0

                    # Fulfill demand against current on-hand stock
                    available_on_hand = current_on_hand[(s_id, p_id)]
                    sold_units = min(demanded_units, available_on_hand)
                    unfulfilled = demanded_units - sold_units

                    # Decrement inventory
                    current_on_hand[(s_id, p_id)] -= sold_units

                    # Calculate revenue
                    net_price = round(unit_price * (1.0 - discount_pct), 2)
                    gross_revenue = round(sold_units * net_price, 2)

                    tx_row = {
                        "transaction_id": f"TX-{tx_counter:07d}",
                        "transaction_date": current_date,
                        "product_id": p_id,
                        "location_id": s_id,
                        "promotion_id": active_promo_id,
                        "units_demanded": demanded_units,
                        "units_sold": sold_units,
                        "unfulfilled_units": unfulfilled,
                        "unit_selling_price": net_price,
                        "discount_pct": discount_pct,
                        "total_revenue": gross_revenue,
                    }
                    SalesTransactionContract(**tx_row)
                    sales_records.append(tx_row)
                    tx_counter += 1

                    # 3. Replenishment Order Logic (Trigger PO when inventory <= ROP)
                    # Check pending pipeline units for this store/SKU
                    pipeline_qty = sum(
                        po["qty_ordered"]
                        for po in in_transit_pipeline
                        if po["destination_location_id"] == s_id and po["product_id"] == p_id
                    )

                    effective_stock = current_on_hand[(s_id, p_id)] + pipeline_qty

                    # Check reorder trigger
                    if effective_stock <= reorder_point:
                        # Order quantity
                        order_qty = max(moq, reorder_point * 2 - effective_stock)
                        order_qty = int(math.ceil(order_qty / moq) * moq)

                        promised_delivery = current_date + timedelta(days=lead_time)

                        # Planted Supplier Delay Signal:
                        # For SUP-002 or during late-May PO for PRD-BEV-001 at LOC-ST-01, inject +9 days delay
                        is_planted_delay = False
                        delay_days = 0

                        if p_id == "PRD-BEV-001" and s_id == "LOC-ST-01" and date(2026, 5, 20) <= current_date <= date(2026, 6, 2):
                            is_planted_delay = True
                            delay_days = 9
                        elif supplier_id == "SUP-002" and self.rng.random() < 0.35:
                            # Natural supplier delay for unreliable SUP-002
                            delay_days = self.rng.randint(2, 5)

                        actual_lead_time = lead_time + delay_days
                        actual_delivery = current_date + timedelta(days=actual_lead_time)

                        po_record = {
                            "po_id": f"PO-{po_counter:06d}",
                            "supplier_id": supplier_id,
                            "product_id": p_id,
                            "destination_location_id": s_id,
                            "order_date": current_date,
                            "promised_delivery_date": promised_delivery,
                            "actual_delivery_date": actual_delivery,
                            "qty_ordered": order_qty,
                            "qty_received": order_qty,
                            "lead_time_days": actual_lead_time,
                            "delay_days": delay_days,
                            "po_status": POStatus.IN_TRANSIT.value,
                            "_created_day": current_date,
                        }
                        in_transit_pipeline.append(po_record)
                        po_counter += 1

            # 4. Generate Daily Inventory Snapshots for All Facilities (Stores + DC)
            for loc in location_rows:
                l_id = loc["location_id"]
                for prod in product_rows:
                    p_id = prod["product_id"]
                    on_hand = current_on_hand[(l_id, p_id)]

                    in_transit = sum(
                        po["qty_ordered"]
                        for po in in_transit_pipeline
                        if po["destination_location_id"] == l_id and po["product_id"] == p_id
                    )

                    # Reserved quantity (nominal buffer for in-flight transactions)
                    reserved = min(on_hand, self.rng.randint(0, 3) if on_hand > 10 else 0)
                    available = on_hand - reserved
                    stockout_flag = 1 if on_hand == 0 else 0

                    snap_id = f"SNP-{current_date.strftime('%Y%m%d')}-{l_id[-5:]}-{p_id[-7:]}"

                    snap_row = {
                        "snapshot_id": snap_id,
                        "snapshot_date": current_date,
                        "product_id": p_id,
                        "location_id": l_id,
                        "on_hand_qty": on_hand,
                        "in_transit_qty": in_transit,
                        "reserved_qty": reserved,
                        "available_qty": available,
                        "stockout_flag": stockout_flag,
                    }
                    InventorySnapshotContract(**snap_row)
                    snapshot_records.append(snap_row)

        # Wrap up any remaining POs still in transit at simulation horizon end
        for po in in_transit_pipeline:
            # Mark open status if delivered past end date
            if po["actual_delivery_date"] > calendar_rows[-1]["date_key"]:
                po["actual_delivery_date"] = None
                po["lead_time_days"] = None
                po["delay_days"] = None
                po["qty_received"] = 0
                po["po_status"] = POStatus.IN_TRANSIT.value
            else:
                po["po_status"] = POStatus.DELIVERED.value
            del po["_created_day"]
            delivery_records.append(po)

        # Strip temporary metadata from products before returning
        for p in product_rows:
            if "_archetype" in p:
                del p["_archetype"]

        return sales_records, snapshot_records, delivery_records


def seed_database(engine: Engine, dataset: SyntheticDataset, recreate_tables: bool = True) -> Dict[str, int]:
    """Insert synthetic dataset into database tables using bulk insertions."""
    if recreate_tables:
        drop_all_tables(engine)
        create_all_tables(engine)

    with engine.begin() as conn:
        # Enable SQLite foreign key enforcement
        if engine.dialect.name == "sqlite":
            conn.execute(text("PRAGMA foreign_keys = ON;"))

        # Dependency-safe bulk insertion order
        conn.execute(calendar_dim.insert(), dataset.calendar)
        conn.execute(products.insert(), dataset.products)
        conn.execute(locations.insert(), dataset.locations)
        conn.execute(suppliers.insert(), dataset.suppliers)
        conn.execute(promotions.insert(), dataset.promotions)
        conn.execute(sales_transactions.insert(), dataset.sales_transactions)
        conn.execute(inventory_snapshots.insert(), dataset.inventory_snapshots)
        conn.execute(supplier_deliveries.insert(), dataset.supplier_deliveries)

    return dataset.summary_counts()


def run_generation(seed: int = 42, target_db_url: Optional[str] = None) -> SyntheticDataset:
    """Entrypoint function to generate dataset, seed database, and report metrics."""
    settings = get_settings()
    db_url = target_db_url or settings.database_url

    print(f"Generating deterministic enterprise data with seed={seed}...")
    generator = DataGenerator(seed=seed)
    dataset = generator.generate()

    engine = create_engine(db_url, echo=False)
    counts = seed_database(engine, dataset, recreate_tables=True)

    print("\n--- Seeding Complete: Table Summary ---")
    for table_name, count in counts.items():
        print(f"  {table_name:25s}: {count:,} rows")

    return dataset


if __name__ == "__main__":
    run_generation()
