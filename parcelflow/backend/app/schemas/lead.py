from datetime import datetime
"""
Lead Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

from app.schemas.base import BaseSchema, PaginatedResponse


class LeadCreate(BaseModel):
    """Create lead request"""
    name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=5, max_length=50)
    email: Optional[EmailStr] = None
    company_name: Optional[str] = None
    company_size: Optional[int] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    product_interest: Optional[str] = None
    service_interest: Optional[str] = None
    estimated_value: Optional[str] = None
    source: str = "other"
    source_details: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    next_follow_up: Optional[str] = None
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    """Update lead request"""
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    company_name: Optional[str] = None
    company_size: Optional[int] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    product_interest: Optional[str] = None
    service_interest: Optional[str] = None
    estimated_value: Optional[str] = None
    source: Optional[str] = None
    source_details: Optional[str] = None
    status: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    next_follow_up: Optional[str] = None
    last_contact: Optional[str] = None
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class LeadResponse(BaseSchema):
    """Full lead response"""
    id: int
    business_id: int
    name: str
    phone: str
    email: Optional[str] = None
    company_name: Optional[str] = None
    company_size: Optional[int] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    product_interest: Optional[str] = None
    service_interest: Optional[str] = None
    estimated_value: Optional[str] = None
    source: str
    source_details: Optional[str] = None
    status: str
    assigned_to_user_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    next_follow_up: Optional[str] = None
    last_contact: Optional[str] = None
    converted_at: Optional[str] = None
    converted_to_order_id: Optional[int] = None
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LeadListResponse(PaginatedResponse):
    """Paginated lead list"""
    items: List[LeadResponse]


class LeadConversionRequest(BaseModel):
    """Convert lead to order"""
    convert_to_order: bool = True
    create_order_data: Optional[dict] = None
    notes: Optional[str] = None
