"""
Dispatch Model - Delivery dispatch records
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, Numeric
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin


class DispatchStatus(str, enum.Enum):
    """Status of a dispatch"""
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"
    FAILED = "failed"
    RETURNED = "returned"


class Dispatch(Base, TimestampMixin):
    """
    Dispatch entity - assignment of waybill to agent for delivery.
    Tracks the delivery journey from warehouse to receiver.
    """
    __tablename__ = "dispatches"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Agent assignment
    agent_id = Column(Integer, ForeignKey("logistic_agents.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    
    # Dispatch times
    dispatched_at = Column(String(50), nullable=True)  # DateTime
    estimated_delivery = Column(String(50), nullable=True)  # DateTime
    completed_at = Column(String(50), nullable=True)  # DateTime when completed
    
    # Status
    status = Column(Enum(DispatchStatus), default=DispatchStatus.ASSIGNED, nullable=False)
    
    # Attempt tracking
    attempt_count = Column(Integer, default=0)
    last_attempt_at = Column(String(50), nullable=True)
    
    # Route information
    route_notes = Column(Text, nullable=True)
    distance_km = Column(Numeric(10, 2), nullable=True)
    
    # Failure information
    failure_reason = Column(Text, nullable=True)
    
    # Relationships
    waybill = relationship("Waybill", back_populates="dispatches")
    agent = relationship("LogisticAgent", back_populates="dispatches")
    vehicle = relationship("Vehicle", back_populates="dispatches")
    
    def __repr__(self):
        return f"<Dispatch(id={self.id}, waybill_id={self.waybill_id}, status='{self.status.value}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if dispatch is still active"""
        return self.status in [DispatchStatus.ASSIGNED, DispatchStatus.IN_TRANSIT]
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            DispatchStatus.ASSIGNED: "Assigned",
            DispatchStatus.IN_TRANSIT: "In Transit",
            DispatchStatus.COMPLETED: "Completed",
            DispatchStatus.FAILED: "Failed",
            DispatchStatus.RETURNED: "Returned"
        }
        return status_map.get(self.status, self.status.value)
