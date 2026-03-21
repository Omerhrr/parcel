"""
Warehouse Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from app.schemas.base import BaseSchema, PaginatedResponse


class WarehouseBase(BaseModel):
    """Base warehouse fields"""
    name: str = Field(..., min_length=2, max_length=255)
    code: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Nigeria"
    manager_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    capacity_sqm: Optional[int] = None
    max_items: Optional[int] = None


class WarehouseCreate(WarehouseBase):
    """Create warehouse request"""
    branch_id: Optional[int] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None


class WarehouseUpdate(BaseModel):
    """Update warehouse request"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    code: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    manager_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    capacity_sqm: Optional[int] = None
    max_items: Optional[int] = None
    status: Optional[str] = None
    branch_id: Optional[int] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None


class WarehouseResponse(BaseSchema):
    """Full warehouse response"""
    id: int
    business_id: int
    branch_id: Optional[int] = None
    name: str
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    manager_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    capacity_sqm: Optional[int] = None
    max_items: Optional[int] = None
    status: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WarehouseListResponse(PaginatedResponse):
    """Paginated warehouse list"""
    items: list[WarehouseResponse]
