"""
Inventory and Stock Movement Models
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Numeric, Text
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin


class MovementType(str, enum.Enum):
    """Type of stock movement"""
    IN = "in"  # Stock received
    OUT = "out"  # Stock sold/used
    TRANSFER = "transfer"  # Moved between warehouses
    RETURN = "return"  # Customer return
    ADJUSTMENT = "adjustment"  # Manual adjustment
    DAMAGE = "damage"  # Damaged goods


class Inventory(Base, TimestampMixin):
    """
    Inventory entity - stock levels per product per warehouse per vendor.
    Tracks current quantity of each product in each warehouse.
    Supports vendor-specific inventory tracking within company warehouses.
    """
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)  # Vendor who owns this stock
    
    # Quantity
    quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0)  # Reserved for pending orders
    available_quantity = Column(Integer, default=0)  # quantity - reserved_quantity
    
    # Reorder settings
    reorder_level = Column(Integer, default=10)
    max_level = Column(Integer, nullable=True)
    
    # Location in warehouse
    bin_location = Column(String(50), nullable=True)
    
    # Relationships
    product = relationship("Product", back_populates="inventory")
    warehouse = relationship("Warehouse", back_populates="inventory")
    vendor = relationship("Vendor")
    
    def __repr__(self):
        return f"<Inventory(id={self.id}, product_id={self.product_id}, qty={self.quantity})>"
    
    def update_available(self):
        """Update available quantity"""
        self.available_quantity = self.quantity - self.reserved_quantity
    
    @property
    def needs_reorder(self) -> bool:
        """Check if stock is below reorder level"""
        return self.quantity <= self.reorder_level


class StockMovement(Base, TimestampMixin):
    """
    StockMovement entity - records all stock changes.
    Provides audit trail for inventory changes.
    """
    __tablename__ = "stock_movements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Movement details
    movement_type = Column(Enum(MovementType), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    # Reference - what caused this movement
    reference_type = Column(String(50), nullable=True)  # order, waybill, adjustment, etc.
    reference_id = Column(Integer, nullable=True)  # ID of the reference entity
    
    # For transfers
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True)
    
    # Quantity after movement
    balance_after = Column(Integer, nullable=True)
    
    # Cost tracking
    unit_cost = Column(Numeric(12, 2), nullable=True)
    total_cost = Column(Numeric(12, 2), nullable=True)
    
    # Who performed the movement
    performed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    product = relationship("Product", back_populates="stock_movements")
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id], back_populates="stock_movements")
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    user = relationship("User")
    
    def __repr__(self):
        return f"<StockMovement(id={self.id}, type='{self.movement_type.value}', qty={self.quantity})>"
    
    def get_movement_type_display(self) -> str:
        """Get human-readable movement type"""
        type_map = {
            MovementType.IN: "Stock In",
            MovementType.OUT: "Stock Out",
            MovementType.TRANSFER: "Transfer",
            MovementType.RETURN: "Return",
            MovementType.ADJUSTMENT: "Adjustment",
            MovementType.DAMAGE: "Damage"
        }
        return type_map.get(self.movement_type, self.movement_type.value)
