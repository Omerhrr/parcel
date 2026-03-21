"""
Stock Request Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.schemas.base import BaseSchema, PaginatedResponse


class StockRequestCreate(BaseModel):
    """Create stock inbound request"""
    warehouse_id: Optional[int] = None  # Optional - admin will assign when confirming
    product_id: int  # Required - vendor selects from their linked products
    quantity: int = Field(..., ge=1)
    unit_cost: Decimal = Decimal("0")
    expected_delivery_date: Optional[str] = None
    notes: Optional[str] = None


class StockRequestUpdate(BaseModel):
    """Update stock inbound request"""
    warehouse_id: Optional[int] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    quantity: Optional[int] = None
    unit_cost: Optional[Decimal] = None
    expected_delivery_date: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    notes: Optional[str] = None


class StockRequestReview(BaseModel):
    """Admin review of stock request"""
    status: str  # approved or rejected
    review_notes: Optional[str] = None
    warehouse_id: Optional[int] = None  # Can assign/change warehouse


class StockRequestReception(BaseModel):
    """Confirm stock reception"""
    received_quantity: int
    reception_notes: Optional[str] = None


class StockRequestResponse(BaseSchema):
    """Stock request response"""
    id: int
    business_id: int
    vendor_id: int
    warehouse_id: Optional[int] = None
    product_id: Optional[int] = None

    request_number: str
    quantity: int
    unit_cost: Decimal

    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_description: Optional[str] = None

    status: str

    expected_delivery_date: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None

    reviewed_by: Optional[int] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None

    received_by: Optional[int] = None
    received_at: Optional[str] = None
    received_quantity: Optional[int] = None
    reception_notes: Optional[str] = None

    notes: Optional[str] = None
    vendor_notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    # Related info
    vendor_name: Optional[str] = None
    warehouse_name: Optional[str] = None
    product_name_resolved: Optional[str] = None


class StockRequestListResponse(PaginatedResponse):
    """Paginated stock request list"""
    items: List[StockRequestResponse]
