from datetime import datetime
"""
Product Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal

from app.schemas.base import BaseSchema, PaginatedResponse


class ProductPriceCreate(BaseModel):
    """Create product price tier for pricing matrix"""
    min_quantity: int = Field(default=1, ge=1)
    max_quantity: Optional[int] = None
    price: Decimal = Field(default=Decimal("0"))
    total_price: Optional[Decimal] = None
    is_buy_x_get_y: bool = False
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    label: Optional[str] = None
    priority: int = Field(default=0)


class ProductPriceUpdate(BaseModel):
    """Update product price tier"""
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    is_buy_x_get_y: Optional[bool] = None
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    label: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class ProductPriceResponse(BaseSchema):
    """Product price tier response"""
    id: int
    product_id: int
    min_quantity: int
    max_quantity: Optional[int] = None
    price: Decimal
    total_price: Optional[Decimal] = None
    is_buy_x_get_y: int
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    label: Optional[str] = None
    priority: int
    is_active: int
    created_at: datetime
    updated_at: datetime


class ProductCreate(BaseModel):
    """Create product request"""
    vendor_id: Optional[int] = None
    name: str = Field(..., min_length=2, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    weight: Optional[Decimal] = None
    length: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    cost_price: Decimal = Decimal("0")
    selling_price: Decimal = Decimal("0")
    pricing_type: str = Field(default="fixed", pattern="^(fixed|matrix)$")
    image_url: Optional[str] = None
    price_tiers: Optional[List[ProductPriceCreate]] = None


class ProductUpdate(BaseModel):
    """Update product request"""
    vendor_id: Optional[int] = None
    name: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    weight: Optional[Decimal] = None
    length: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    pricing_type: Optional[str] = Field(None, pattern="^(fixed|matrix)$")
    image_url: Optional[str] = None
    is_active: Optional[int] = None
    price_tiers: Optional[List[ProductPriceCreate]] = None


class ProductResponse(BaseSchema):
    """Full product response"""
    id: int
    business_id: int
    vendor_id: Optional[int] = None
    name: str
    sku: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    weight: Optional[Decimal] = None
    length: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    cost_price: Decimal
    selling_price: Decimal
    pricing_type: str = "fixed"
    is_active: int
    image_url: Optional[str] = None
    pricing_matrix: List[ProductPriceResponse] = []
    created_at: datetime
    updated_at: datetime


class ProductListResponse(PaginatedResponse):
    """Paginated product list"""
    items: List[ProductResponse]


class ProductBrief(BaseSchema):
    """Brief product info"""
    id: int
    name: str
    sku: Optional[str] = None
    selling_price: Decimal
    pricing_type: str = "fixed"


class PriceCalculationRequest(BaseModel):
    """Request to calculate price for quantity"""
    product_id: int
    quantity: int = Field(..., ge=1)


class PriceCalculationResponse(BaseModel):
    """Response with calculated price"""
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    applied_tier: Optional[str] = None
    discount_percent: Optional[Decimal] = None
