from datetime import datetime
"""
Waybill Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from decimal import Decimal

from app.schemas.base import BaseSchema, PaginatedResponse


class SenderInfo(BaseModel):
    """Sender information"""
    sender_name: str
    sender_phone: str
    sender_email: Optional[EmailStr] = None
    sender_address: Optional[str] = None
    sender_city: Optional[str] = None
    pickup_latitude: Optional[str] = None
    pickup_longitude: Optional[str] = None


class ReceiverInfo(BaseModel):
    """Receiver information"""
    receiver_name: str
    receiver_phone: str
    receiver_email: Optional[EmailStr] = None
    receiver_address: str
    receiver_city: Optional[str] = None
    receiver_landmark: Optional[str] = None
    delivery_latitude: Optional[str] = None
    delivery_longitude: Optional[str] = None


class ItemInfo(BaseModel):
    """Item information"""
    item_description: Optional[str] = None
    quantity: int = 1
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None


class PricingInfo(BaseModel):
    """Pricing information"""
    declared_value: Decimal = Decimal("0")
    delivery_fee: Decimal = Decimal("0")
    insurance_fee: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")


class WaybillCreate(SenderInfo, ReceiverInfo, ItemInfo, PricingInfo):
    """Create waybill request"""
    branch_id: Optional[int] = None
    shipment_type: str = "warehouse_delivery"
    payment_type: str = "cod"
    cod_amount: Decimal = Decimal("0")
    vendor_id: Optional[int] = None
    order_id: Optional[int] = None
    notes: Optional[str] = None
    special_instructions: Optional[str] = None
    estimated_delivery_date: Optional[str] = None


class WaybillUpdate(BaseModel):
    """Update waybill request"""
    branch_id: Optional[int] = None
    shipment_type: Optional[str] = None
    
    sender_name: Optional[str] = None
    sender_phone: Optional[str] = None
    sender_email: Optional[EmailStr] = None
    sender_address: Optional[str] = None
    sender_city: Optional[str] = None
    pickup_latitude: Optional[str] = None
    pickup_longitude: Optional[str] = None
    
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    receiver_email: Optional[EmailStr] = None
    receiver_address: Optional[str] = None
    receiver_city: Optional[str] = None
    receiver_landmark: Optional[str] = None
    delivery_latitude: Optional[str] = None
    delivery_longitude: Optional[str] = None
    
    item_description: Optional[str] = None
    quantity: Optional[int] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None
    
    declared_value: Optional[Decimal] = None
    delivery_fee: Optional[Decimal] = None
    insurance_fee: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    
    payment_type: Optional[str] = None
    cod_amount: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    special_instructions: Optional[str] = None


class TrackingEventResponse(BaseSchema):
    """Tracking event for timeline"""
    id: int
    status: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    is_public: int
    created_at: datetime


class WaybillResponse(BaseSchema):
    """Full waybill response"""
    id: int
    waybill_number: str
    business_id: int
    branch_id: Optional[int] = None
    
    shipment_type: str
    payment_type: str
    
    # Sender
    sender_name: str
    sender_phone: str
    sender_email: Optional[str] = None
    sender_address: Optional[str] = None
    sender_city: Optional[str] = None
    pickup_latitude: Optional[str] = None
    pickup_longitude: Optional[str] = None
    
    # Receiver
    receiver_name: str
    receiver_phone: str
    receiver_email: Optional[str] = None
    receiver_address: str
    receiver_city: Optional[str] = None
    receiver_landmark: Optional[str] = None
    delivery_latitude: Optional[str] = None
    delivery_longitude: Optional[str] = None
    
    # Item
    item_description: Optional[str] = None
    quantity: int
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None
    
    # Pricing
    declared_value: Decimal
    delivery_fee: Decimal
    insurance_fee: Decimal
    total_amount: Decimal
    cod_amount: Decimal
    
    # Status
    status: str
    
    # References
    vendor_id: Optional[int] = None
    order_id: Optional[int] = None
    
    # Notes
    notes: Optional[str] = None
    special_instructions: Optional[str] = None
    estimated_delivery_date: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    # Related data (optional)
    tracking_events: List[TrackingEventResponse] = []


class WaybillListResponse(PaginatedResponse):
    """Paginated waybill list"""
    items: List[WaybillResponse]


class WaybillTrackingResponse(BaseSchema):
    """Public tracking response"""
    waybill_number: str
    status: str
    status_display: str
    sender_name: str
    receiver_name: str
    receiver_address: str
    receiver_city: Optional[str] = None
    estimated_delivery: Optional[str] = None
    timeline: List[TrackingEventResponse]


class WaybillStatusUpdate(BaseModel):
    """Update waybill status"""
    status: str
    location: Optional[str] = None
    notes: Optional[str] = None
