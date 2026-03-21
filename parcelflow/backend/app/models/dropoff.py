"""
Dropoff Model - Items dropped off at branch/warehouse
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TimestampMixin


class Dropoff(Base, TimestampMixin):
    """
    Dropoff entity - items dropped off directly at a branch/warehouse.
    Used for dropoff_delivery shipment type.
    """
    __tablename__ = "dropoffs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    
    # Who received the dropoff
    received_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    received_at = Column(String(50), nullable=True)  # DateTime
    
    # Dropoff details
    dropoff_notes = Column(Text, nullable=True)
    condition_on_receipt = Column(String(50), nullable=True)  # good, damaged, etc.
    
    # Relationships
    waybill = relationship("Waybill", back_populates="dropoff")
    branch = relationship("Branch")
    received_by = relationship("User")
    
    def __repr__(self):
        return f"<Dropoff(id={self.id}, waybill_id={self.waybill_id})>"
