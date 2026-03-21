from datetime import datetime
"""
Order Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from decimal import Decimal

from app.schemas.base import BaseSchema, PaginatedResponse


class OrderItemCreate(BaseModel):
    """Create order item"""
    product_id: Optional[int] = None
    product_name: str
    product_sku: Optional[str] = None
    quantity: int = Field(..., ge=1)
    unit_price: Decimal  # Will be calculated from pricing matrix if product_id provided
    discount: Decimal = Decimal("0")
    notes: Optional[str] = None


class OrderItemResponse(BaseSchema):
    """Order item response"""
    id: int
    order_id: int
    product_id: Optional[int] = None
    product_name: str
    product_sku: Optional[str] = None
    quantity: int
    unit_price: Decimal
    discount: Decimal
    total: Decimal
    notes: Optional[str] = None


class OrderCreate(BaseModel):
    """Create order request"""
    branch_id: Optional[int] = None
    vendor_id: Optional[int] = None  # Primary vendor for this order
    
    # Customer
    customer_name: str
    customer_phone: str
    customer_email: Optional[EmailStr] = None
    
    # Delivery
    delivery_address: str
    delivery_city: Optional[str] = None
    delivery_state: Optional[str] = None
    delivery_landmark: Optional[str] = None
    
    # Items
    items: List[OrderItemCreate]
    
    # Pricing
    delivery_fee: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    
    # Remittance (logistics fee)
    remittance_fee: Decimal = Decimal("0")  # Fee per order, same for same customer regardless of items
    
    # Payment
    payment_method: str = "cod"
    
    # Source
    source: Optional[str] = None
    landing_page_id: Optional[str] = None
    
    # Notes
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    """Update order request"""
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    delivery_address: Optional[str] = None
    delivery_city: Optional[str] = None
    delivery_state: Optional[str] = None
    delivery_landmark: Optional[str] = None
    delivery_fee: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    remittance_fee: Optional[Decimal] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class OrderResponse(BaseSchema):
    """Full order response"""
    id: int
    order_number: str
    business_id: int
    branch_id: Optional[int] = None
    vendor_id: Optional[int] = None
    
    # Customer
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    
    # Delivery
    delivery_address: str
    delivery_city: Optional[str] = None
    delivery_state: Optional[str] = None
    delivery_landmark: Optional[str] = None
    
    # Amounts
    subtotal: Decimal
    delivery_fee: Decimal
    discount: Decimal
    tax: Decimal
    total_amount: Decimal
    
    # Remittance
    remittance_fee: Decimal = Decimal("0")
    vendor_amount: Decimal = Decimal("0")
    remittance_status: str = "pending"
    
    # Payment
    payment_method: str
    payment_status: str
    payment_reference: Optional[str] = None
    paid_at: Optional[str] = None
    
    # Status
    status: str
    
    # Source
    source: Optional[str] = None
    landing_page_id: Optional[str] = None
    
    # Dates
    confirmed_at: Optional[str] = None
    shipped_at: Optional[str] = None
    delivered_at: Optional[str] = None
    remitted_at: Optional[str] = None
    
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    # Related
    items: List[OrderItemResponse] = []


class OrderListResponse(PaginatedResponse):
    """Paginated order list"""
    items: List[OrderResponse]


class OrderAssignmentCreate(BaseModel):
    """Assign order to user"""
    assigned_to_user_id: int
    assignment_type: str = "delivery"
    notes: Optional[str] = None


class PriceCalculationRequest(BaseModel):
    """Request to calculate price for a product"""
    product_id: int
    quantity: int = Field(..., ge=1)


class PriceCalculationResponse(BaseModel):
    """Response with calculated price"""
    product_id: int
    product_name: str
    vendor_id: Optional[int] = None
    vendor_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    applied_tier_label: Optional[str] = None
    is_buy_x_get_y: bool = False
    free_quantity: int = 0
