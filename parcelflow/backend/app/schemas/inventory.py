from datetime import datetime
"""
Inventory Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal

from app.schemas.base import BaseSchema, PaginatedResponse


class ProductBrief(BaseSchema):
    """Brief product info for nested responses"""
    id: int
    name: str
    sku: Optional[str] = None


class WarehouseBrief(BaseSchema):
    """Brief warehouse info for nested responses"""
    id: int
    name: str
    code: Optional[str] = None


class InventoryUpdate(BaseModel):
    """Update inventory request"""
    quantity: Optional[int] = None
    reserved_quantity: Optional[int] = None
    reorder_level: Optional[int] = None
    max_level: Optional[int] = None
    bin_location: Optional[str] = None


class InventoryResponse(BaseSchema):
    """Inventory response"""
    id: int
    product_id: int
    warehouse_id: int
    quantity: int
    reserved_quantity: int
    available_quantity: int
    reorder_level: int
    max_level: Optional[int] = None
    bin_location: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Nested objects for display
    product: Optional[ProductBrief] = None
    warehouse: Optional[WarehouseBrief] = None


class InventoryListResponse(PaginatedResponse):
    """Paginated inventory list"""
    items: List[InventoryResponse]


class StockMovementCreate(BaseModel):
    """Create stock movement request"""
    product_id: int
    warehouse_id: int
    movement_type: str  # in, out, transfer, return, adjustment, damage
    quantity: int = Field(..., ge=1)
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    from_warehouse_id: Optional[int] = None
    to_warehouse_id: Optional[int] = None
    unit_cost: Optional[Decimal] = None
    notes: Optional[str] = None


class StockMovementResponse(BaseSchema):
    """Stock movement response"""
    id: int
    product_id: int
    warehouse_id: Optional[int] = None
    movement_type: str
    quantity: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    from_warehouse_id: Optional[int] = None
    to_warehouse_id: Optional[int] = None
    balance_after: Optional[int] = None
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    performed_by: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Nested objects for display
    product: Optional[ProductBrief] = None
    warehouse: Optional[WarehouseBrief] = None


class StockMovementListResponse(PaginatedResponse):
    """Paginated stock movement list"""
    items: List[StockMovementResponse]
