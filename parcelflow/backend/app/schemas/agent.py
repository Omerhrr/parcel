from datetime import datetime
"""
Agent and Vehicle Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from decimal import Decimal

from app.schemas.base import BaseSchema, PaginatedResponse


class AgentCreate(BaseModel):
    """Create agent request"""
    branch_id: Optional[int] = None
    user_id: Optional[int] = None
    name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    employee_id: Optional[str] = None
    national_id: Optional[str] = None
    vehicle_type: str = "bike"
    vehicle_id: Optional[int] = None
    status: str = "available"
    base_salary: Decimal = Decimal("0")
    commission_rate: Decimal = Decimal("0")
    notes: Optional[str] = None


class AgentUpdate(BaseModel):
    """Update agent request"""
    branch_id: Optional[int] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    employee_id: Optional[str] = None
    national_id: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_id: Optional[int] = None
    status: Optional[str] = None
    base_salary: Optional[Decimal] = None
    commission_rate: Optional[Decimal] = None
    notes: Optional[str] = None


class AgentResponse(BaseSchema):
    """Full agent response"""
    id: int
    business_id: int
    branch_id: Optional[int] = None
    user_id: Optional[int] = None
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    employee_id: Optional[str] = None
    national_id: Optional[str] = None
    vehicle_type: str
    vehicle_id: Optional[int] = None
    status: str
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    rating: Decimal
    base_salary: Decimal
    commission_rate: Decimal
    current_latitude: Optional[str] = None
    current_longitude: Optional[str] = None
    last_location_update: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AgentListResponse(PaginatedResponse):
    """Paginated agent list"""
    items: List[AgentResponse]


class VehicleCreate(BaseModel):
    """Create vehicle request"""
    branch_id: Optional[int] = None
    name: str = Field(..., min_length=2, max_length=255)
    registration_number: Optional[str] = None
    vehicle_type: str = "bike"
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    max_weight_kg: Optional[Decimal] = None
    max_volume_cbm: Optional[Decimal] = None
    status: str = "available"
    is_owned: int = 1
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    insurance_expiry: Optional[str] = None
    license_expiry: Optional[str] = None
    notes: Optional[str] = None


class VehicleUpdate(BaseModel):
    """Update vehicle request"""
    name: Optional[str] = None
    registration_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    max_weight_kg: Optional[Decimal] = None
    max_volume_cbm: Optional[Decimal] = None
    status: Optional[str] = None
    is_owned: Optional[int] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    insurance_expiry: Optional[str] = None
    license_expiry: Optional[str] = None
    notes: Optional[str] = None


class VehicleResponse(BaseSchema):
    """Full vehicle response"""
    id: int
    business_id: int
    branch_id: Optional[int] = None
    name: str
    registration_number: Optional[str] = None
    vehicle_type: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    max_weight_kg: Optional[Decimal] = None
    max_volume_cbm: Optional[Decimal] = None
    status: str
    is_owned: int
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    insurance_expiry: Optional[str] = None
    license_expiry: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
