"""
Branch Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from app.schemas.base import BaseSchema, PaginatedResponse


class BranchBase(BaseModel):
    """Base branch fields"""
    name: str = Field(..., min_length=2, max_length=255)
    code: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Nigeria"
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    currency: str = "NGN"
    timezone: str = "Africa/Lagos"


class BranchCreate(BranchBase):
    """Create branch request"""
    is_headquarters: bool = False
    latitude: Optional[str] = None
    longitude: Optional[str] = None


class BranchUpdate(BaseModel):
    """Update branch request"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    code: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    status: Optional[str] = None
    is_headquarters: Optional[bool] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None


class BranchResponse(BaseSchema):
    """Full branch response"""
    id: int
    business_id: int
    name: str
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    currency: str
    timezone: str
    status: str
    is_headquarters: int
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BranchListResponse(PaginatedResponse):
    """Paginated branch list"""
    items: list[BranchResponse]
