"""
Business Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.schemas.base import BaseSchema, PaginatedResponse


class BusinessBase(BaseModel):
    """Base business fields"""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Nigeria"


class BusinessCreate(BusinessBase):
    """Create business request"""
    slug: str = Field(..., min_length=2, max_length=100)


class BusinessUpdate(BaseModel):
    """Update business request"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    plan: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    settings: Optional[str] = None


class EmailSettingsUpdate(BaseModel):
    """Email settings update request"""
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None  # Note: Will be stored encrypted in production
    smtp_use_tls: Optional[bool] = True
    email_from_name: Optional[str] = None
    email_from_address: Optional[str] = None
    email_enabled: Optional[bool] = True


class EmailSettingsResponse(BaseModel):
    """Email settings response"""
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_use_tls: bool = True
    email_from_name: str = "ParcelFlow"
    email_from_address: Optional[str] = None
    email_enabled: bool = True
    is_configured: bool = False  # Read-only, indicates if SMTP is configured


class BusinessResponse(BaseSchema):
    """Full business response"""
    id: int
    name: str
    slug: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: str
    plan: str
    status: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class BusinessListResponse(PaginatedResponse):
    """Paginated business list"""
    items: list[BusinessResponse]
