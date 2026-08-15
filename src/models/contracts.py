"""Pydantic data contracts for core domain entities in the demand & risk engine."""

from datetime import date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class LocationType(str, Enum):
    """Types of facilities within the distribution network."""
    STORE = "STORE"
    DISTRIBUTION_CENTER = "DC"


class POStatus(str, Enum):
    """Purchase Order fulfillment lifecycle status."""
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class ProductContract(BaseModel):
    """Contract for product / SKU master data."""
    model_config = ConfigDict(frozen=True)

    product_id: str = Field(..., min_length=3, max_length=64, description="Unique product identifier")
    sku: str = Field(..., min_length=3, max_length=64, description="Stock Keeping Unit code")
    name: str = Field(..., min_length=1, max_length=255, description="Product display name")
    category: str = Field(..., min_length=1, max_length=64, description="Primary product category")
    subcategory: str = Field(..., min_length=1, max_length=64, description="Product subcategory")
    unit_cost: float = Field(..., gt=0.0, description="Cost of goods sold per unit ($)")
    unit_price: float = Field(..., gt=0.0, description="Retail selling price per unit ($)")
    reorder_point_units: int = Field(default=50, ge=0, description="Minimum inventory threshold before triggering reorder")
    min_order_qty: int = Field(default=10, ge=1, description="Supplier minimum batch order size")
    standard_lead_time_days: int = Field(default=7, ge=1, description="Standard supplier fulfillment lead time in days")
    is_active: bool = Field(default=True, description="Active SKU catalog status")

    @model_validator(mode="after")
    def validate_price_exceeds_cost(self) -> "ProductContract":
        """Ensure unit price covers standard unit cost."""
        if self.unit_price < self.unit_cost:
            raise ValueError(f"unit_price ({self.unit_price}) must be >= unit_cost ({self.unit_cost})")
        return self


class LocationContract(BaseModel):
    """Contract for store and warehouse locations."""
    model_config = ConfigDict(frozen=True)

    location_id: str = Field(..., min_length=3, max_length=64, description="Unique location identifier")
    location_code: str = Field(..., min_length=2, max_length=32, description="Short facility code")
    location_name: str = Field(..., min_length=1, max_length=255, description="Facility descriptive name")
    location_type: LocationType = Field(..., description="Facility operational type: STORE or DC")
    region: str = Field(..., min_length=2, max_length=64, description="Geographic region")
    city: str = Field(..., min_length=1, max_length=128, description="City location")
    state: str = Field(..., min_length=2, max_length=64, description="State/Province")
    storage_capacity_units: int = Field(..., gt=0, description="Maximum total unit storage capacity")
    is_active: bool = Field(default=True, description="Active facility status")


class SupplierContract(BaseModel):
    """Contract for upstream vendors and suppliers."""
    model_config = ConfigDict(frozen=True)

    supplier_id: str = Field(..., min_length=3, max_length=64, description="Unique supplier identifier")
    supplier_name: str = Field(..., min_length=1, max_length=255, description="Vendor business name")
    country: str = Field(default="US", min_length=2, max_length=64, description="Country of origin")
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Historical On-Time In-Full fulfillment rate (0.0 to 1.0)")
    default_lead_time_days: int = Field(..., ge=1, description="Nominal fulfillment lead time in days")
    is_active: bool = Field(default=True, description="Active supplier status")


class PromotionContract(BaseModel):
    """Contract for promotional campaigns and markdowns."""
    model_config = ConfigDict(frozen=True)

    promotion_id: str = Field(..., min_length=3, max_length=64, description="Unique promotion identifier")
    promo_code: str = Field(..., min_length=2, max_length=32, description="Marketing promotion code")
    promo_name: str = Field(..., min_length=1, max_length=255, description="Campaign descriptive name")
    promo_type: str = Field(..., min_length=1, max_length=64, description="Type: PERCENTAGE_DISCOUNT, BOGO, SEASONAL_EVENT")
    discount_pct: float = Field(default=0.0, ge=0.0, le=1.0, description="Fractional discount percentage applied")
    start_date: date = Field(..., description="Campaign start date")
    end_date: date = Field(..., description="Campaign end date")
    is_active: bool = Field(default=True, description="Active promotion flag")

    @model_validator(mode="after")
    def validate_date_range(self) -> "PromotionContract":
        """Ensure campaign end date is on or after start date."""
        if self.end_date < self.start_date:
            raise ValueError(f"end_date ({self.end_date}) cannot precede start_date ({self.start_date})")
        return self


class CalendarDimContract(BaseModel):
    """Contract for calendar and temporal dimension."""
    model_config = ConfigDict(frozen=True)

    date_key: date = Field(..., description="Calendar date primary key")
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    day_name: str = Field(..., min_length=3, max_length=10, description="Monday through Sunday")
    month: int = Field(..., ge=1, le=12, description="Month of year (1-12)")
    month_name: str = Field(..., min_length=3, max_length=15, description="January through December")
    quarter: int = Field(..., ge=1, le=4, description="Fiscal / Calendar Quarter (1-4)")
    year: int = Field(..., ge=2020, le=2040, description="Calendar year")
    is_weekend: bool = Field(..., description="Flag indicating Saturday/Sunday")
    is_holiday: bool = Field(default=False, description="Flag indicating commercial/public holiday")
    holiday_name: Optional[str] = Field(default=None, max_length=128, description="Holiday name if applicable")


class SalesTransactionContract(BaseModel):
    """Contract for point-of-sale customer demand and transaction records."""
    model_config = ConfigDict(frozen=True)

    transaction_id: str = Field(..., min_length=3, max_length=64, description="Unique transaction identifier")
    transaction_date: date = Field(..., description="Transaction execution date")
    product_id: str = Field(..., min_length=3, max_length=64, description="FK to products")
    location_id: str = Field(..., min_length=3, max_length=64, description="FK to locations")
    promotion_id: Optional[str] = Field(default=None, max_length=64, description="Optional FK to active promotion")
    units_demanded: int = Field(..., ge=0, description="Total units demanded by customer")
    units_sold: int = Field(..., ge=0, description="Units actually fulfilled and sold")
    unfulfilled_units: int = Field(default=0, ge=0, description="Unfulfilled demand due to stockout (units_demanded - units_sold)")
    unit_selling_price: float = Field(..., ge=0.0, description="Net price charged per unit after discount")
    discount_pct: float = Field(default=0.0, ge=0.0, le=1.0, description="Discount rate applied")
    total_revenue: float = Field(..., ge=0.0, description="Total transaction gross revenue ($)")

    @model_validator(mode="after")
    def validate_fulfillment_and_revenue(self) -> "SalesTransactionContract":
        """Verify fulfilled units do not exceed demanded units and unfulfilled balance aligns."""
        if self.units_sold > self.units_demanded:
            raise ValueError(f"units_sold ({self.units_sold}) cannot exceed units_demanded ({self.units_demanded})")
        expected_unfulfilled = self.units_demanded - self.units_sold
        if self.unfulfilled_units != expected_unfulfilled:
            raise ValueError(
                f"unfulfilled_units ({self.unfulfilled_units}) must equal demanded ({self.units_demanded}) - sold ({self.units_sold})"
            )
        return self


class InventorySnapshotContract(BaseModel):
    """Contract for daily end-of-day inventory balance snapshots."""
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(..., min_length=3, max_length=64, description="Unique snapshot identifier")
    snapshot_date: date = Field(..., description="Daily snapshot date")
    product_id: str = Field(..., min_length=3, max_length=64, description="FK to products")
    location_id: str = Field(..., min_length=3, max_length=64, description="FK to locations")
    on_hand_qty: int = Field(..., ge=0, description="Physical units present in facility")
    in_transit_qty: int = Field(default=0, ge=0, description="Units in inbound pipeline from suppliers or transfers")
    reserved_qty: int = Field(default=0, ge=0, description="Units committed to pending customer orders")
    available_qty: int = Field(..., description="Net available units for immediate fulfillment (on_hand - reserved)")
    stockout_flag: int = Field(default=0, ge=0, le=1, description="Binary flag indicating stockout condition (1 if on_hand == 0)")

    @model_validator(mode="after")
    def validate_inventory_balance(self) -> "InventorySnapshotContract":
        """Verify available quantity and stockout flag consistency."""
        expected_available = self.on_hand_qty - self.reserved_qty
        if self.available_qty != expected_available:
            raise ValueError(
                f"available_qty ({self.available_qty}) must equal on_hand ({self.on_hand_qty}) - reserved ({self.reserved_qty})"
            )
        expected_stockout = 1 if self.on_hand_qty == 0 else 0
        if self.stockout_flag != expected_stockout:
            raise ValueError(
                f"stockout_flag ({self.stockout_flag}) must be {expected_stockout} when on_hand_qty is {self.on_hand_qty}"
            )
        return self


class SupplierDeliveryContract(BaseModel):
    """Contract for inbound supplier purchase orders and deliveries."""
    model_config = ConfigDict(frozen=True)

    po_id: str = Field(..., min_length=3, max_length=64, description="Unique purchase order identifier")
    supplier_id: str = Field(..., min_length=3, max_length=64, description="FK to suppliers")
    product_id: str = Field(..., min_length=3, max_length=64, description="FK to products")
    destination_location_id: str = Field(..., min_length=3, max_length=64, description="FK to receiving facility")
    order_date: date = Field(..., description="Date purchase order was issued to supplier")
    promised_delivery_date: date = Field(..., description="Target delivery date agreed by supplier")
    actual_delivery_date: Optional[date] = Field(default=None, description="Actual gate arrival date (null if pending)")
    qty_ordered: int = Field(..., gt=0, description="Units ordered on PO")
    qty_received: int = Field(default=0, ge=0, description="Units physically received at gate")
    lead_time_days: Optional[int] = Field(default=None, ge=0, description="Total days from order to delivery")
    delay_days: Optional[int] = Field(default=None, description="Days delivered past promised date (>0 means late)")
    po_status: POStatus = Field(default=POStatus.PENDING, description="Current purchase order status")

    @model_validator(mode="after")
    def validate_dates_and_status(self) -> "SupplierDeliveryContract":
        """Verify delivery dates and status consistency."""
        if self.promised_delivery_date < self.order_date:
            raise ValueError("promised_delivery_date cannot be earlier than order_date")
        if self.actual_delivery_date is not None:
            if self.actual_delivery_date < self.order_date:
                raise ValueError("actual_delivery_date cannot be earlier than order_date")
            if self.po_status == POStatus.PENDING:
                raise ValueError("po_status cannot be PENDING when actual_delivery_date is recorded")
        return self
