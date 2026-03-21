"""
Bulk Operations Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


class BulkStatusUpdateRequest(BaseModel):
    """Request for bulk status update"""
    ids: List[int] = Field(..., min_items=1, max_items=100, description="List of IDs to update")
    status: str = Field(..., description="New status to set")
    notes: Optional[str] = Field(None, description="Optional notes for the status change")


class BulkDispatchAssignRequest(BaseModel):
    """Request for bulk dispatch assignment"""
    dispatch_ids: List[int] = Field(..., min_items=1, max_items=50, description="List of dispatch IDs")
    agent_id: int = Field(..., description="Agent ID to assign")


class BulkImportWaybillItem(BaseModel):
    """Single waybill import item"""
    sender_name: str
    sender_phone: str
    sender_email: Optional[str] = None
    sender_address: Optional[str] = None
    sender_city: Optional[str] = None
    receiver_name: str
    receiver_phone: str
    receiver_email: Optional[str] = None
    receiver_address: str
    receiver_city: Optional[str] = None
    receiver_landmark: Optional[str] = None
    item_description: Optional[str] = None
    quantity: int = 1
    weight: Optional[float] = None
    declared_value: float = 0
    delivery_fee: float = 0
    cod_amount: float = 0
    payment_type: str = "cod"
    shipment_type: str = "warehouse_delivery"
    vendor_id: Optional[int] = None
    notes: Optional[str] = None


class BulkImportOrderItem(BaseModel):
    """Single order import item"""
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    delivery_address: str
    delivery_city: Optional[str] = None
    delivery_state: Optional[str] = None
    delivery_landmark: Optional[str] = None
    subtotal: float = 0
    delivery_fee: float = 0
    discount: float = 0
    tax: float = 0
    payment_method: str = "cod"
    notes: Optional[str] = None
    items: List[Dict[str, Any]] = []


class BulkImportAgentItem(BaseModel):
    """Single agent import item"""
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    employee_id: Optional[str] = None
    national_id: Optional[str] = None
    vehicle_type: str = "bike"
    status: str = "available"
    branch_id: Optional[int] = None
    notes: Optional[str] = None


class BulkImportWaybillRequest(BaseModel):
    """Request for bulk waybill import"""
    waybills: List[BulkImportWaybillItem] = Field(..., max_items=100)
    branch_id: Optional[int] = None


class BulkImportOrderRequest(BaseModel):
    """Request for bulk order import"""
    orders: List[BulkImportOrderItem] = Field(..., max_items=100)
    branch_id: Optional[int] = None


class BulkImportAgentRequest(BaseModel):
    """Request for bulk agent import"""
    agents: List[BulkImportAgentItem] = Field(..., max_items=100)


class BulkOperationResult(BaseModel):
    """Result of a single item in bulk operation"""
    id: Optional[int] = None
    identifier: Optional[str] = None  # waybill_number, order_number, etc.
    success: bool
    error: Optional[str] = None


class BulkOperationResponse(BaseModel):
    """Response for bulk operations"""
    success: bool
    total_requested: int
    success_count: int
    failure_count: int
    results: List[BulkOperationResult]
    message: str


class BulkExportRequest(BaseModel):
    """Request for bulk export"""
    ids: Optional[List[int]] = None
    status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    search: Optional[str] = None
    format: str = "csv"
