"""Deterministic data quality and contract validation suite for synthetic enterprise datasets.

Provides comprehensive validation across:
1. Schema & Completeness (no unexpected missing columns or mandatory nulls)
2. Uniqueness (primary and natural composite keys)
3. Referential Integrity (all foreign keys resolve to dimension records)
4. Value & Range Constraints (costs, prices, quantities, scores, discounts)
5. Date Sequence Consistency (order <= promised <= actual, start <= end)
6. Cross-Column Business Logic (fulfillment arithmetic, inventory balances, stockout flags)
7. Table-Level Sanity (non-empty master catalogs)
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from src.data.generator import SyntheticDataset


class CheckStatus(str, Enum):
    """Execution status of an individual quality check."""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class CheckSeverity(str, Enum):
    """Severity level dictating ingestion policy."""
    CRITICAL = "CRITICAL"  # Mandatory rule: failure blocks ingestion
    WARNING = "WARNING"    # Informational warning: non-blocking


@dataclass(frozen=True)
class QualityCheckResult:
    """Detailed result of an individual data quality check."""
    check_name: str
    category: str
    status: CheckStatus
    severity: CheckSeverity
    measured_value: str
    expected_rule: str
    affected_count: int = 0
    message: str = ""
    sample_failures: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class QualityReport:
    """Structured aggregate report of all executed quality checks."""
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    overall_status: CheckStatus
    is_ingestable: bool
    check_details: List[QualityCheckResult]

    @property
    def pass_rate(self) -> float:
        """Percentage of checks that passed."""
        return (self.passed_checks / self.total_checks * 100.0) if self.total_checks > 0 else 0.0

    def print_summary(self) -> None:
        """Print a human-readable CLI summary table of the quality report."""
        print("\n" + "=" * 80)
        print(" DATA QUALITY & CONTRACT VALIDATION REPORT")
        print("=" * 80)
        print(f" Overall Status : {self.overall_status.value}")
        print(f" Ingestable     : {'YES (Ready for Storage)' if self.is_ingestable else 'NO (Ingestion Blocked)'}")
        print(f" Pass Rate      : {self.pass_rate:.1f}% ({self.passed_checks}/{self.total_checks} checks passed)")
        print(f" Failed Checks  : {self.failed_checks}")
        print(f" Warnings       : {self.warning_checks}")
        print("-" * 80)
        print(f"{'Category':<22} | {'Check Name':<32} | {'Status':<6} | {'Severity':<8}")
        print("-" * 80)
        for r in self.check_details:
            print(f"{r.category:<22} | {r.check_name:<32} | {r.status.value:<6} | {r.severity.value:<8}")
            if r.status != CheckStatus.PASS:
                print(f"   --> {r.message} (Affected: {r.affected_count})")
                for sample in r.sample_failures[:3]:
                    print(f"       Sample: {sample}")
        print("=" * 80 + "\n")


class DataQualityValidator:
    """Engine executing deterministic data quality validations on synthetic enterprise datasets."""

    def __init__(self, dataset: SyntheticDataset):
        self.dataset = dataset
        self.results: List[QualityCheckResult] = []

    def run_all_checks(self) -> QualityReport:
        """Execute all data quality check suites and compile final QualityReport."""
        self.results = []

        # 1. Table-Level Sanity & Completeness
        self._check_table_sanity()

        # 2. Uniqueness & Primary Key Integrity
        self._check_uniqueness()

        # 3. Referential Integrity
        self._check_referential_integrity()

        # 4. Range & Value Constraints
        self._check_value_ranges()

        # 5. Date Sequence Consistency
        self._check_date_consistency()

        # 6. Cross-Column Business Logic
        self._check_business_logic()

        # Compile Aggregate Summary
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAIL)
        warnings = sum(1 for r in self.results if r.status == CheckStatus.WARN)

        # Ingestion policy: Any CRITICAL check failure blocks ingestion
        is_ingestable = (failed == 0)
        overall_status = CheckStatus.PASS if failed == 0 and warnings == 0 else (CheckStatus.FAIL if failed > 0 else CheckStatus.WARN)

        return QualityReport(
            total_checks=total,
            passed_checks=passed,
            failed_checks=failed,
            warning_checks=warnings,
            overall_status=overall_status,
            is_ingestable=is_ingestable,
            check_details=self.results,
        )

    # -------------------------------------------------------------------------
    # 1. Table Sanity Checks
    # -------------------------------------------------------------------------
    def _check_table_sanity(self) -> None:
        """Verify master tables and facts are populated and contain no empty tables."""
        tables = self.dataset.summary_counts()
        for table_name, count in tables.items():
            if count == 0:
                self.results.append(QualityCheckResult(
                    check_name=f"non_empty_{table_name}",
                    category="Table Sanity",
                    status=CheckStatus.FAIL,
                    severity=CheckSeverity.CRITICAL,
                    measured_value="0 rows",
                    expected_rule="Row count > 0",
                    affected_count=1,
                    message=f"Table {table_name} is unexpectedly empty.",
                ))
            else:
                self.results.append(QualityCheckResult(
                    check_name=f"non_empty_{table_name}",
                    category="Table Sanity",
                    status=CheckStatus.PASS,
                    severity=CheckSeverity.CRITICAL,
                    measured_value=f"{count:,} rows",
                    expected_rule="Row count > 0",
                ))

    # -------------------------------------------------------------------------
    # 2. Uniqueness Checks
    # -------------------------------------------------------------------------
    def _check_uniqueness(self) -> None:
        """Verify primary and declared unique natural keys."""
        # A. Products (product_id PK, sku UK)
        p_ids = [p.get("product_id") for p in self.dataset.products]
        p_skus = [p.get("sku") for p in self.dataset.products]
        self._evaluate_uniqueness("pk_products_product_id", "Uniqueness", p_ids)
        self._evaluate_uniqueness("uk_products_sku", "Uniqueness", p_skus)

        # B. Locations (location_id PK, location_code UK)
        l_ids = [l.get("location_id") for l in self.dataset.locations]
        l_codes = [l.get("location_code") for l in self.dataset.locations]
        self._evaluate_uniqueness("pk_locations_location_id", "Uniqueness", l_ids)
        self._evaluate_uniqueness("uk_locations_location_code", "Uniqueness", l_codes)

        # C. Suppliers (supplier_id PK)
        s_ids = [s.get("supplier_id") for s in self.dataset.suppliers]
        self._evaluate_uniqueness("pk_suppliers_supplier_id", "Uniqueness", s_ids)

        # D. Promotions (promotion_id PK, promo_code UK)
        promo_ids = [pr.get("promotion_id") for pr in self.dataset.promotions]
        promo_codes = [pr.get("promo_code") for pr in self.dataset.promotions]
        self._evaluate_uniqueness("pk_promotions_promotion_id", "Uniqueness", promo_ids)
        self._evaluate_uniqueness("uk_promotions_promo_code", "Uniqueness", promo_codes)

        # E. Calendar (date_key PK)
        date_keys = [c.get("date_key") for c in self.dataset.calendar]
        self._evaluate_uniqueness("pk_calendar_date_key", "Uniqueness", date_keys)

        # F. Sales Transactions (transaction_id PK)
        tx_ids = [tx.get("transaction_id") for tx in self.dataset.sales_transactions]
        self._evaluate_uniqueness("pk_sales_transaction_id", "Uniqueness", tx_ids)

        # G. Inventory Snapshots (snapshot_id PK, composite unique key: (snapshot_date, product_id, location_id))
        snap_ids = [sn.get("snapshot_id") for sn in self.dataset.inventory_snapshots]
        snap_composite = [
            (sn.get("snapshot_date"), sn.get("product_id"), sn.get("location_id"))
            for sn in self.dataset.inventory_snapshots
        ]
        self._evaluate_uniqueness("pk_inventory_snapshot_id", "Uniqueness", snap_ids)
        self._evaluate_uniqueness("uk_inventory_snapshot_composite", "Uniqueness", snap_composite)

        # H. Supplier Deliveries (po_id PK)
        po_ids = [po.get("po_id") for po in self.dataset.supplier_deliveries]
        self._evaluate_uniqueness("pk_supplier_deliveries_po_id", "Uniqueness", po_ids)

    def _evaluate_uniqueness(self, check_name: str, category: str, keys: List[Any]) -> None:
        """Helper to evaluate duplicate occurrences in a list of keys."""
        seen: Set[Any] = set()
        duplicates: List[Any] = []
        for k in keys:
            if k in seen:
                duplicates.append(k)
            else:
                seen.add(k)

        if duplicates:
            self.results.append(QualityCheckResult(
                check_name=check_name,
                category=category,
                status=CheckStatus.FAIL,
                severity=CheckSeverity.CRITICAL,
                measured_value=f"{len(duplicates)} duplicate keys",
                expected_rule="All keys must be strictly unique (0 duplicates)",
                affected_count=len(duplicates),
                message=f"Duplicate primary/unique keys found for {check_name}.",
                sample_failures=[str(d) for d in duplicates[:3]],
            ))
        else:
            self.results.append(QualityCheckResult(
                check_name=check_name,
                category=category,
                status=CheckStatus.PASS,
                severity=CheckSeverity.CRITICAL,
                measured_value=f"{len(keys):,} unique keys",
                expected_rule="All keys strictly unique",
            ))

    # -------------------------------------------------------------------------
    # 3. Referential Integrity Checks
    # -------------------------------------------------------------------------
    def _check_referential_integrity(self) -> None:
        """Verify foreign key references resolve to parent dimension records."""
        valid_products: Set[str] = {p["product_id"] for p in self.dataset.products}
        valid_locations: Set[str] = {l["location_id"] for l in self.dataset.locations}
        valid_suppliers: Set[str] = {s["supplier_id"] for s in self.dataset.suppliers}
        valid_promotions: Set[str] = {pr["promotion_id"] for pr in self.dataset.promotions}
        valid_dates: Set[date] = {c["date_key"] for c in self.dataset.calendar}

        # A. Sales Transactions FKs
        sales_prod_orphans = [
            tx["transaction_id"] for tx in self.dataset.sales_transactions
            if tx.get("product_id") not in valid_products
        ]
        self._evaluate_orphans("fk_sales_product_id", "Referential Integrity", sales_prod_orphans)

        sales_loc_orphans = [
            tx["transaction_id"] for tx in self.dataset.sales_transactions
            if tx.get("location_id") not in valid_locations
        ]
        self._evaluate_orphans("fk_sales_location_id", "Referential Integrity", sales_loc_orphans)

        sales_date_orphans = [
            tx["transaction_id"] for tx in self.dataset.sales_transactions
            if tx.get("transaction_date") not in valid_dates
        ]
        self._evaluate_orphans("fk_sales_transaction_date", "Referential Integrity", sales_date_orphans)

        sales_promo_orphans = [
            tx["transaction_id"] for tx in self.dataset.sales_transactions
            if tx.get("promotion_id") is not None and tx.get("promotion_id") not in valid_promotions
        ]
        self._evaluate_orphans("fk_sales_promotion_id", "Referential Integrity", sales_promo_orphans)

        # B. Inventory Snapshots FKs
        inv_prod_orphans = [
            sn["snapshot_id"] for sn in self.dataset.inventory_snapshots
            if sn.get("product_id") not in valid_products
        ]
        self._evaluate_orphans("fk_inventory_product_id", "Referential Integrity", inv_prod_orphans)

        inv_loc_orphans = [
            sn["snapshot_id"] for sn in self.dataset.inventory_snapshots
            if sn.get("location_id") not in valid_locations
        ]
        self._evaluate_orphans("fk_inventory_location_id", "Referential Integrity", inv_loc_orphans)

        inv_date_orphans = [
            sn["snapshot_id"] for sn in self.dataset.inventory_snapshots
            if sn.get("snapshot_date") not in valid_dates
        ]
        self._evaluate_orphans("fk_inventory_snapshot_date", "Referential Integrity", inv_date_orphans)

        # C. Supplier Deliveries FKs
        po_sup_orphans = [
            po["po_id"] for po in self.dataset.supplier_deliveries
            if po.get("supplier_id") not in valid_suppliers
        ]
        self._evaluate_orphans("fk_po_supplier_id", "Referential Integrity", po_sup_orphans)

        po_prod_orphans = [
            po["po_id"] for po in self.dataset.supplier_deliveries
            if po.get("product_id") not in valid_products
        ]
        self._evaluate_orphans("fk_po_product_id", "Referential Integrity", po_prod_orphans)

        po_loc_orphans = [
            po["po_id"] for po in self.dataset.supplier_deliveries
            if po.get("destination_location_id") not in valid_locations
        ]
        self._evaluate_orphans("fk_po_destination_location_id", "Referential Integrity", po_loc_orphans)

        po_date_orphans = [
            po["po_id"] for po in self.dataset.supplier_deliveries
            if po.get("order_date") not in valid_dates
        ]
        self._evaluate_orphans("fk_po_order_date", "Referential Integrity", po_date_orphans)

    def _evaluate_orphans(self, check_name: str, category: str, orphans: List[str]) -> None:
        """Helper to evaluate orphan foreign key records."""
        if orphans:
            self.results.append(QualityCheckResult(
                check_name=check_name,
                category=category,
                status=CheckStatus.FAIL,
                severity=CheckSeverity.CRITICAL,
                measured_value=f"{len(orphans)} orphan records",
                expected_rule="All foreign keys must resolve to parent records",
                affected_count=len(orphans),
                message=f"Foreign key violations detected in {check_name}.",
                sample_failures=orphans[:3],
            ))
        else:
            self.results.append(QualityCheckResult(
                check_name=check_name,
                category=category,
                status=CheckStatus.PASS,
                severity=CheckSeverity.CRITICAL,
                measured_value="0 orphans",
                expected_rule="All foreign keys resolve to parent records",
            ))

    # -------------------------------------------------------------------------
    # 4. Range & Value Constraints
    # -------------------------------------------------------------------------
    def _check_value_ranges(self) -> None:
        """Verify numerical domains and non-negativity."""
        # Product unit prices >= cost and cost > 0
        price_cost_violations = [
            p["product_id"] for p in self.dataset.products
            if p.get("unit_cost", 0) <= 0 or p.get("unit_price", 0) < p.get("unit_cost", 0)
        ]
        self._record_check(
            check_name="product_price_covers_cost",
            category="Value Ranges",
            failures=price_cost_violations,
            expected="unit_cost > 0 AND unit_price >= unit_cost",
        )

        # Supplier reliability in [0.0, 1.0]
        sup_rel_violations = [
            s["supplier_id"] for s in self.dataset.suppliers
            if not (0.0 <= s.get("reliability_score", -1.0) <= 1.0)
        ]
        self._record_check(
            check_name="supplier_reliability_range",
            category="Value Ranges",
            failures=sup_rel_violations,
            expected="0.0 <= reliability_score <= 1.0",
        )

        # Sales transaction non-negative quantities & positive revenue
        sales_qty_violations = [
            tx["transaction_id"] for tx in self.dataset.sales_transactions
            if tx.get("units_demanded", -1) < 0 or tx.get("units_sold", -1) < 0 or tx.get("total_revenue", -1.0) < 0
        ]
        self._record_check(
            check_name="sales_quantities_nonnegative",
            category="Value Ranges",
            failures=sales_qty_violations,
            expected="units_demanded >= 0, units_sold >= 0, revenue >= 0",
        )

        # Inventory non-negative on-hand and in-transit
        inv_qty_violations = [
            sn["snapshot_id"] for sn in self.dataset.inventory_snapshots
            if sn.get("on_hand_qty", -1) < 0 or sn.get("in_transit_qty", -1) < 0 or sn.get("reserved_qty", -1) < 0
        ]
        self._record_check(
            check_name="inventory_quantities_nonnegative",
            category="Value Ranges",
            failures=inv_qty_violations,
            expected="on_hand_qty >= 0, in_transit_qty >= 0, reserved_qty >= 0",
        )

    # -------------------------------------------------------------------------
    # 5. Date Sequence Consistency
    # -------------------------------------------------------------------------
    def _check_date_consistency(self) -> None:
        """Verify chronological ordering on promotional and purchase order dates."""
        # Promotions start_date <= end_date
        promo_date_violations = [
            pr["promotion_id"] for pr in self.dataset.promotions
            if pr.get("start_date") is not None and pr.get("end_date") is not None and pr["start_date"] > pr["end_date"]
        ]
        self._record_check(
            check_name="promotion_date_sequence",
            category="Date Consistency",
            failures=promo_date_violations,
            expected="start_date <= end_date",
        )

        # PO dates: order_date <= promised_delivery_date and order_date <= actual_delivery_date
        po_date_violations = [
            po["po_id"] for po in self.dataset.supplier_deliveries
            if po.get("order_date") is not None and (
                po.get("promised_delivery_date") < po["order_date"]
                or (po.get("actual_delivery_date") is not None and po["actual_delivery_date"] < po["order_date"])
            )
        ]
        self._record_check(
            check_name="purchase_order_date_sequence",
            category="Date Consistency",
            failures=po_date_violations,
            expected="order_date <= promised_delivery_date AND order_date <= actual_delivery_date",
        )

    # -------------------------------------------------------------------------
    # 6. Cross-Column Business Logic
    # -------------------------------------------------------------------------
    def _check_business_logic(self) -> None:
        """Verify domain-specific multi-column invariants."""
        # Sales fulfillment arithmetic: units_sold <= units_demanded AND unfulfilled == demanded - sold
        fulfillment_violations = [
            tx["transaction_id"] for tx in self.dataset.sales_transactions
            if tx.get("units_sold", 0) > tx.get("units_demanded", 0)
            or tx.get("unfulfilled_units", -1) != (tx.get("units_demanded", 0) - tx.get("units_sold", 0))
        ]
        self._record_check(
            check_name="sales_fulfillment_arithmetic",
            category="Business Logic",
            failures=fulfillment_violations,
            expected="units_sold <= units_demanded AND unfulfilled == demanded - sold",
        )

        # Inventory balance: available_qty == on_hand_qty - reserved_qty
        inv_balance_violations = [
            sn["snapshot_id"] for sn in self.dataset.inventory_snapshots
            if sn.get("available_qty") != (sn.get("on_hand_qty", 0) - sn.get("reserved_qty", 0))
        ]
        self._record_check(
            check_name="inventory_available_balance",
            category="Business Logic",
            failures=inv_balance_violations,
            expected="available_qty == on_hand_qty - reserved_qty",
        )

        # Stockout flag accuracy: stockout_flag == (1 if on_hand == 0 else 0)
        stockout_flag_violations = [
            sn["snapshot_id"] for sn in self.dataset.inventory_snapshots
            if (sn.get("on_hand_qty", 0) == 0 and sn.get("stockout_flag") != 1)
            or (sn.get("on_hand_qty", 0) > 0 and sn.get("stockout_flag") != 0)
        ]
        self._record_check(
            check_name="stockout_flag_consistency",
            category="Business Logic",
            failures=stockout_flag_violations,
            expected="stockout_flag == 1 iff on_hand_qty == 0",
        )

    def _record_check(self, check_name: str, category: str, failures: List[str], expected: str) -> None:
        """Helper to record check result based on failure list."""
        if failures:
            self.results.append(QualityCheckResult(
                check_name=check_name,
                category=category,
                status=CheckStatus.FAIL,
                severity=CheckSeverity.CRITICAL,
                measured_value=f"{len(failures)} violating records",
                expected_rule=expected,
                affected_count=len(failures),
                message=f"Validation failed for {check_name}.",
                sample_failures=failures[:3],
            ))
        else:
            self.results.append(QualityCheckResult(
                check_name=check_name,
                category=category,
                status=CheckStatus.PASS,
                severity=CheckSeverity.CRITICAL,
                measured_value="0 violations",
                expected_rule=expected,
            ))


def validate_dataset(dataset: SyntheticDataset) -> QualityReport:
    """Validate a synthetic enterprise dataset and return structured QualityReport."""
    validator = DataQualityValidator(dataset)
    return validator.run_all_checks()
