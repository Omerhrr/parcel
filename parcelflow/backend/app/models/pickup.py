"""
Pickup Model - Scheduled pickups
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, DateTime
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin


class PickupStatus(str, enum.Enum):
    """Status of a pickup"""
    SCHEDULED = "scheduled"
    AGENT_ASSIGNED = "agent_assigned"
    IN_PROGRESS = "in_progress"
    PICKED_UP = "picked_up"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Pickup(Base, TimestampMixin):
    """
    Pickup entity - scheduled pickup of items from sender.
    Used for pickup_delivery shipment type.
    """
    __tablename__ = "pickups"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Pickup location
    pickup_address = Column(Text, nullable=False)
    pickup_city = Column(String(100), nullable=True)
    pickup_landmark = Column(String(255), nullable=True)
    
    # Contact
    pickup_contact_name = Column(String(255), nullable=True)
    pickup_contact_phone = Column(String(50), nullable=True)
    
    # Schedule
    scheduled_date = Column(String(50), nullable=True)  # Date
    scheduled_time_from = Column(String(10), nullable=True)  # HH:MM
    scheduled_time_to = Column(String(10), nullable=True)  # HH:MM
    
    # Agent assignment
    agent_id = Column(Integer, ForeignKey("logistic_agents.id", ondelete="SET NULL"), nullable=True)
    
    # Status
    status = Column(Enum(PickupStatus), default=PickupStatus.SCHEDULED, nullable=False)
    
    # Actual pickup
    actual_pickup_time = Column(String(50), nullable=True)  # DateTime
    
    # Notes
    notes = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    # Relationships
    waybill = relationship("Waybill", back_populates="pickup")
    agent = relationship("LogisticAgent", back_populates="pickups")
    
    def __repr__(self):
        return f"<Pickup(id={self.id}, waybill_id={self.waybill_id}, status='{self.status.value}')>"
    
    @property
    def is_completed(self) -> bool:
        """Check if pickup is completed"""
        return self.status == PickupStatus.PICKED_UP
    
    @property
    def is_pending(self) -> bool:
        """Check if pickup is pending"""
        return self.status in [PickupStatus.SCHEDULED, PickupStatus.AGENT_ASSIGNED]
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            PickupStatus.SCHEDULED: "Scheduled",
            PickupStatus.AGENT_ASSIGNED: "Agent Assigned",
            PickupStatus.IN_PROGRESS: "In Progress",
            PickupStatus.PICKED_UP: "Picked Up",
            PickupStatus.FAILED: "Failed",
            PickupStatus.CANCELLED: "Cancelled"
        }
        return status_map.get(self.status, self.status.value)
