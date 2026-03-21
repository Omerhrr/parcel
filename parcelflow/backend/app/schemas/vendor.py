from datetime import datetime
"""
Vendor Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from decimal import Decimal

from app.schemas.base import BaseSchema, PaginatedResponse


class VendorCreate(BaseModel):
    """Create vendor request"""
    name: str = Field(..., min_length=2, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Nigeria"
    business_type: Optional[str] = None
    tax_id: Optional[str] = None
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    settlement_cycle: str = "weekly"
    settlement_day: int = 5
    notes: Optional[str] = None


class VendorUpdate(BaseModel):
    """Update vendor request"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    code: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    business_type: Optional[str] = None
    tax_id: Optional[str] = None
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    settlement_cycle: Optional[str] = None
    settlement_day: Optional[int] = None
    is_active: Optional[int] = None
    notes: Optional[str] = None


class VendorResponse(BaseSchema):
    """Full vendor response"""
    id: int
    business_id: int
    name: str
    code: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    business_type: Optional[str] = None
    tax_id: Optional[str] = None
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    remittance_fee: Decimal = Decimal("0")
    settlement_cycle: str
    settlement_day: int
    is_active: int
    api_key: Optional[str] = None  # For vendor portal access
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class VendorListResponse(PaginatedResponse):
    """Paginated vendor list"""
    items: List[VendorResponse]


class VendorBalanceResponse(BaseSchema):
    """Vendor balance information"""
    vendor_id: int
    vendor_name: str
    current_balance: Decimal
    last_remittance_date: Optional[str] = None
    pending_orders: int
    total_credit: Decimal
    total_debit: Decimal
