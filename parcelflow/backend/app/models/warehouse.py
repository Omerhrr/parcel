"""
Warehouse Models - Warehouses and Processing
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, TenantMixin


class WarehouseStatus(str, enum.Enum):
    """Warehouse operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class ProcessingStatus(str, enum.Enum):
    """Status of warehouse processing"""
    RECEIVED = "received"
    SORTED = "sorted"
    READY_FOR_DISPATCH = "ready_for_dispatch"
    DISPATCHED = "dispatched"


class Warehouse(Base, TimestampMixin, TenantMixin):
    """
    Warehouse entity - storage facility for a business.
    Warehouses belong to branches and store inventory.
    """
    __tablename__ = "warehouses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    
    name = Column(String(255), nullable=False)
    code = Column(String(20), nullable=True)  # Short code
    
    # Location
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="Nigeria")
    
    # Contact
    manager_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Capacity
    capacity_sqm = Column(Integer, nullable=True)  # Square meters
    max_items = Column(Integer, nullable=True)
    
    # Status
    status = Column(Enum(WarehouseStatus), default=WarehouseStatus.ACTIVE, nullable=False)
    
    # Coordinates
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    
    # Relationships
    business = relationship("Business", back_populates="warehouses")
    branch = relationship("Branch", back_populates="warehouses")
    inventory = relationship("Inventory", back_populates="warehouse", cascade="all, delete-orphan")
    stock_movements = relationship("StockMovement", foreign_keys="StockMovement.warehouse_id", back_populates="warehouse")
    processing_records = relationship("WarehouseProcessing", back_populates="warehouse")
    
    def __repr__(self):
        return f"<Warehouse(id={self.id}, name='{self.name}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if warehouse is operational"""
        return self.status == WarehouseStatus.ACTIVE


class WarehouseProcessing(Base, TimestampMixin):
    """
    WarehouseProcessing entity - tracks items moving through warehouse.
    Records when waybills arrive at and leave the warehouse.
    """
    __tablename__ = "warehouse_processing"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Receipt information
    received_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    received_at = Column(String(50), nullable=True)  # DateTime
    
    # Processing
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.RECEIVED, nullable=False)
    sorted_at = Column(String(50), nullable=True)  # DateTime
    ready_at = Column(String(50), nullable=True)  # DateTime
    dispatched_at = Column(String(50), nullable=True)  # DateTime
    
    # Notes
    notes = Column(Text, nullable=True)
    damage_notes = Column(Text, nullable=True)
    
    # Bin/Location in warehouse
    bin_location = Column(String(50), nullable=True)
    
    # Relationships
    waybill = relationship("Waybill", back_populates="warehouse_processing")
    warehouse = relationship("Warehouse", back_populates="processing_records")
    received_by_user = relationship("User")
    
    def __repr__(self):
        return f"<WarehouseProcessing(id={self.id}, waybill_id={self.waybill_id}, status='{self.status.value}')>"
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            ProcessingStatus.RECEIVED: "Received",
            ProcessingStatus.SORTED: "Sorted",
            ProcessingStatus.READY_FOR_DISPATCH: "Ready for Dispatch",
            ProcessingStatus.DISPATCHED: "Dispatched"
        }
        return status_map.get(self.status, self.status.value)
