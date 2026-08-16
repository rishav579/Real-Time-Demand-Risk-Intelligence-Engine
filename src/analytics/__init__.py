"""Analytics, segmentation, supplier intelligence, and data marts package."""

from src.analytics.inventory_health import (
    InventoryRiskCategory,
    classify_inventory_risk,
    compute_inventory_health,
)
from src.analytics.marts import (
    build_all_marts,
    compute_daily_product_velocity,
)
from src.analytics.segmentation import (
    ABCClass,
    SKUSegmentationResult,
    XYZClass,
    compute_abc_xyz_segmentation,
)
from src.analytics.supplier import (
    compute_supplier_scorecards,
    compute_supplier_sku_lead_times,
)

__all__ = [
    # Segmentation
    "ABCClass",
    "XYZClass",
    "SKUSegmentationResult",
    "compute_abc_xyz_segmentation",
    # Supplier Intelligence
    "compute_supplier_scorecards",
    "compute_supplier_sku_lead_times",
    # Inventory Health & Risk
    "InventoryRiskCategory",
    "classify_inventory_risk",
    "compute_inventory_health",
    # Data Marts
    "compute_daily_product_velocity",
    "build_all_marts",
]
