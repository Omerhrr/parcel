"""
Logistics Schemas - Pickups, Dispatches, Deliveries
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from app.schemas.base import BaseSchema, PaginatedResponse


# ============== PICKUP SCHEMAS ==============

class PickupBase(BaseModel):
    """Base pickup fields"""
    pickup_address: str
    pickup_city: Optional[str] = None
    pickup_landmark: Optional[str] = None
    pickup_contact_name: Optional[str] = None
    pickup_contact_phone: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time_from: Optional[str] = None
    scheduled_time_to: Optional[str] = None
    notes: Optional[str] = None


class PickupCreate(PickupBase):
    """Create pickup request"""
    waybill_id: int
    agent_id: Optional[int] = None


class PickupUpdate(BaseModel):
    """Update pickup request"""
    pickup_address: Optional[str] = None
    pickup_city: Optional[str] = None
    pickup_landmark: Optional[str] = None
    pickup_contact_name: Optional[str] = None
    pickup_contact_phone: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time_from: Optional[str] = None
    scheduled_time_to: Optional[str] = None
    agent_id: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class PickupResponse(BaseSchema):
    """Pickup response"""
    id: int
    waybill_id: int
    waybill_number: Optional[str] = None
    pickup_address: str
    pickup_city: Optional[str] = None
    pickup_landmark: Optional[str] = None
    pickup_contact_name: Optional[str] = None
    pickup_contact_phone: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time_from: Optional[str] = None
    scheduled_time_to: Optional[str] = None
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    status: str
    actual_pickup_time: Optional[str] = None
    notes: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PickupListResponse(PaginatedResponse):
    """Paginated pickup list"""
    items: List[PickupResponse]


# ============== DISPATCH SCHEMAS ==============

class DispatchWaybillInfo(BaseModel):
    """Waybill info for dispatch response"""
    id: int
    waybill_number: str
    sender_name: str
    sender_phone: str
    sender_address: Optional[str] = None
    sender_city: Optional[str] = None
    pickup_latitude: Optional[str] = None
    pickup_longitude: Optional[str] = None
    receiver_name: str
    receiver_phone: str
    receiver_address: str
    receiver_city: Optional[str] = None
    receiver_landmark: Optional[str] = None
    delivery_latitude: Optional[str] = None
    delivery_longitude: Optional[str] = None
    cod_amount: Optional[Decimal] = None


class DispatchAgentInfo(BaseModel):
    """Agent info for dispatch response"""
    id: int
    name: str
    phone: Optional[str] = None
    vehicle_type: Optional[str] = None
    current_latitude: Optional[str] = None
    current_longitude: Optional[str] = None


class DispatchBase(BaseModel):
    """Base dispatch fields"""
    agent_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    estimated_delivery: Optional[str] = None
    route_notes: Optional[str] = None
    distance_km: Optional[Decimal] = None


class DispatchCreate(DispatchBase):
    """Create dispatch request"""
    waybill_id: int


class DispatchUpdate(BaseModel):
    """Update dispatch request"""
    agent_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    status: Optional[str] = None
    estimated_delivery: Optional[str] = None
    route_notes: Optional[str] = None
    distance_km: Optional[Decimal] = None
    failure_reason: Optional[str] = None


class DispatchResponse(BaseSchema):
    """Dispatch response"""
    id: int
    waybill_id: int
    waybill_number: Optional[str] = None
    waybill: Optional[DispatchWaybillInfo] = None
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    agent: Optional[DispatchAgentInfo] = None
    vehicle_id: Optional[int] = None
    dispatched_at: Optional[str] = None
    estimated_delivery: Optional[str] = None
    status: str
    attempt_count: int
    last_attempt_at: Optional[str] = None
    route_notes: Optional[str] = None
    distance_km: Optional[Decimal] = None
    failure_reason: Optional[str] = None
    cod_amount: Optional[Decimal] = None
    attempts: Optional[List[dict]] = None
    created_at: datetime
    updated_at: datetime


class DispatchListResponse(PaginatedResponse):
    """Paginated dispatch list"""
    items: List[DispatchResponse]


# ============== DELIVERY CONFIRMATION SCHEMAS ==============

class DeliveryConfirmationBase(BaseModel):
    """Base delivery confirmation fields"""
    receiver_name: Optional[str] = None
    receiver_relationship: Optional[str] = None
    receiver_id_type: Optional[str] = None
    receiver_id_number: Optional[str] = None
    delivery_notes: Optional[str] = None


class DeliveryConfirmationCreate(DeliveryConfirmationBase):
    """Create delivery confirmation request"""
    waybill_id: int
    agent_id: Optional[int] = None
    status: str = "delivered"
    delivered_at: Optional[str] = None
    cod_collected: bool = False
    cod_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    delivery_latitude: Optional[str] = None
    delivery_longitude: Optional[str] = None
    receiver_signature: Optional[str] = None
    receiver_signature_svg: Optional[str] = None  # SVG signature (text-based)
    proof_photo_url: Optional[str] = None


class DeliveryConfirmationUpdate(BaseModel):
    """Update delivery confirmation request"""
    receiver_name: Optional[str] = None
    receiver_relationship: Optional[str] = None
    receiver_id_type: Optional[str] = None
    receiver_id_number: Optional[str] = None
    status: Optional[str] = None
    delivery_notes: Optional[str] = None
    failure_reason: Optional[str] = None


class DeliveryConfirmationResponse(BaseSchema):
    """Delivery confirmation response"""
    id: int
    waybill_id: int
    waybill_number: Optional[str] = None
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    delivered_at: Optional[str] = None
    status: str
    receiver_name: Optional[str] = None
    receiver_relationship: Optional[str] = None
    receiver_id_type: Optional[str] = None
    receiver_id_number: Optional[str] = None
    receiver_signature: Optional[str] = None
    receiver_signature_svg: Optional[str] = None  # SVG signature (text-based)
    proof_photo_url: Optional[str] = None
    delivery_latitude: Optional[str] = None
    delivery_longitude: Optional[str] = None
    cod_collected: int
    cod_amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    delivery_notes: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============== DROPOFF SCHEMAS ==============

class DropoffBase(BaseModel):
    """Base dropoff fields"""
    branch_id: Optional[int] = None
    dropoff_notes: Optional[str] = None
    condition_on_receipt: Optional[str] = None


class DropoffCreate(DropoffBase):
    """Create dropoff request"""
    waybill_id: int
    received_by_user_id: Optional[int] = None


class DropoffResponse(BaseSchema):
    """Dropoff response"""
    id: int
    waybill_id: int
    waybill_number: Optional[str] = None
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None
    received_by_user_id: Optional[int] = None
    received_by_name: Optional[str] = None
    received_at: Optional[str] = None
    dropoff_notes: Optional[str] = None
    condition_on_receipt: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============== WAREHOUSE PROCESSING SCHEMAS ==============

class WarehouseProcessingBase(BaseModel):
    """Base warehouse processing fields"""
    warehouse_id: Optional[int] = None
    bin_location: Optional[str] = None
    notes: Optional[str] = None
    damage_notes: Optional[str] = None


class WarehouseProcessingCreate(WarehouseProcessingBase):
    """Create warehouse processing request"""
    waybill_id: int
    received_by: Optional[int] = None


class WarehouseProcessingUpdate(BaseModel):
    """Update warehouse processing request"""
    warehouse_id: Optional[int] = None
    status: Optional[str] = None
    bin_location: Optional[str] = None
    notes: Optional[str] = None
    damage_notes: Optional[str] = None


class WarehouseProcessingResponse(BaseSchema):
    """Warehouse processing response"""
    id: int
    waybill_id: int
    waybill_number: Optional[str] = None
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    received_by: Optional[int] = None
    received_by_name: Optional[str] = None
    received_at: Optional[str] = None
    status: str
    sorted_at: Optional[str] = None
    ready_at: Optional[str] = None
    dispatched_at: Optional[str] = None
    bin_location: Optional[str] = None
    notes: Optional[str] = None
    damage_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
