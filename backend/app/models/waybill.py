"""
Waybill Model - Core logistics document
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, Numeric, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base
from app.models.base import TimestampMixin, TenantMixin


class ShipmentType(str, enum.Enum):
    """Type of shipment"""
    WAREHOUSE_DELIVERY = "warehouse_delivery"
    PICKUP_DELIVERY = "pickup_delivery"
    DROPOFF_DELIVERY = "dropoff_delivery"


class PaymentType(str, enum.Enum):
    """Payment method for delivery"""
    COD = "cod"  # Cash on Delivery
    PREPAID = "prepaid"
    INVOICE = "invoice"


class WaybillStatus(str, enum.Enum):
    """Status of a waybill/shipment"""
    CREATED = "created"
    PICKUP_SCHEDULED = "pickup_scheduled"
    PICKED_UP = "picked_up"
    AT_WAREHOUSE = "at_warehouse"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class Waybill(Base, TimestampMixin, TenantMixin):
    """
    Waybill entity - the core logistics document.
    Represents a shipment with sender, receiver, and item details.
    """
    __tablename__ = "waybills"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    waybill_number = Column(String(50), nullable=False, unique=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Shipment type
    shipment_type = Column(Enum(ShipmentType), default=ShipmentType.WAREHOUSE_DELIVERY, nullable=False)
    
    # Sender information
    sender_name = Column(String(255), nullable=False)
    sender_phone = Column(String(50), nullable=False)
    sender_email = Column(String(255), nullable=True)
    sender_address = Column(Text, nullable=True)
    sender_city = Column(String(100), nullable=True)
    pickup_latitude = Column(String(20), nullable=True)  # GPS coordinates for pickup
    pickup_longitude = Column(String(20), nullable=True)
    
    # Receiver information
    receiver_name = Column(String(255), nullable=False)
    receiver_phone = Column(String(50), nullable=False)
    receiver_email = Column(String(255), nullable=True)
    receiver_address = Column(Text, nullable=False)
    receiver_city = Column(String(100), nullable=True)
    receiver_landmark = Column(String(255), nullable=True)
    delivery_latitude = Column(String(20), nullable=True)  # GPS coordinates for delivery
    delivery_longitude = Column(String(20), nullable=True)
    
    # Item details
    item_description = Column(Text, nullable=True)
    quantity = Column(Integer, default=1)
    weight = Column(Numeric(10, 2), nullable=True)  # in kg
    dimensions = Column(String(100), nullable=True)  # LxWxH in cm
    
    # Value and pricing
    declared_value = Column(Numeric(12, 2), default=0)
    delivery_fee = Column(Numeric(12, 2), default=0)
    insurance_fee = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), default=0)
    
    # Payment
    payment_type = Column(Enum(PaymentType), default=PaymentType.COD, nullable=False)
    cod_amount = Column(Numeric(12, 2), default=0)  # Cash on delivery amount
    
    # Status
    status = Column(Enum(WaybillStatus), default=WaybillStatus.CREATED, nullable=False, index=True)
    
    # Vendor (if applicable)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)
    
    # Order reference (if created from an order)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    special_instructions = Column(Text, nullable=True)
    
    # Estimated delivery
    estimated_delivery_date = Column(String(50), nullable=True)
    
    # Relationships
    business = relationship("Business", foreign_keys=[business_id])
    branch = relationship("Branch", back_populates="waybills")
    vendor = relationship("Vendor", back_populates="waybills")
    order = relationship("Order", back_populates="waybills")
    
    pickup = relationship("Pickup", back_populates="waybill", uselist=False, cascade="all, delete-orphan")
    dropoff = relationship("Dropoff", back_populates="waybill", uselist=False, cascade="all, delete-orphan")
    warehouse_processing = relationship("WarehouseProcessing", back_populates="waybill", uselist=False, cascade="all, delete-orphan")
    dispatches = relationship("Dispatch", back_populates="waybill", cascade="all, delete-orphan")
    delivery_confirmation = relationship("DeliveryConfirmation", back_populates="waybill", uselist=False, cascade="all, delete-orphan")
    tracking_events = relationship("TrackingEvent", back_populates="waybill", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Waybill(id={self.id}, number='{self.waybill_number}', status='{self.status.value}')>"
    
    @staticmethod
    def generate_waybill_number(branch_code: str = None) -> str:
        """Generate a unique waybill number"""
        import random
        import string
        prefix = branch_code or "PF"
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"{prefix}-{timestamp}-{random_part}"
    
    @property
    def is_delivered(self) -> bool:
        """Check if waybill is delivered"""
        return self.status == WaybillStatus.DELIVERED
    
    @property
    def is_in_transit(self) -> bool:
        """Check if waybill is in transit"""
        transit_statuses = [
            WaybillStatus.PICKED_UP,
            WaybillStatus.AT_WAREHOUSE,
            WaybillStatus.OUT_FOR_DELIVERY
        ]
        return self.status in transit_statuses
    
    @property
    def is_failed(self) -> bool:
        """Check if delivery failed"""
        return self.status in [WaybillStatus.FAILED, WaybillStatus.RETURNED]
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            WaybillStatus.CREATED: "Created",
            WaybillStatus.PICKUP_SCHEDULED: "Pickup Scheduled",
            WaybillStatus.PICKED_UP: "Picked Up",
            WaybillStatus.AT_WAREHOUSE: "At Warehouse",
            WaybillStatus.OUT_FOR_DELIVERY: "Out for Delivery",
            WaybillStatus.DELIVERED: "Delivered",
            WaybillStatus.FAILED: "Delivery Failed",
            WaybillStatus.RETURNED: "Returned",
            WaybillStatus.CANCELLED: "Cancelled"
        }
        return status_map.get(self.status, self.status.value)
