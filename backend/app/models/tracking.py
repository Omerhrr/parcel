"""
Tracking Event Model - Public tracking timeline
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TimestampMixin


class TrackingEvent(Base, TimestampMixin):
    """
    TrackingEvent entity - individual events in shipment tracking.
    Creates a timeline viewable by customers on the public tracking portal.
    """
    __tablename__ = "tracking_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Event details
    status = Column(String(50), nullable=False)  # Matches waybill status
    title = Column(String(255), nullable=False)  # Short title
    description = Column(Text, nullable=True)  # Detailed description
    
    # Location
    location = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Additional info
    actor_name = Column(String(255), nullable=True)  # Who performed the action
    actor_role = Column(String(50), nullable=True)  # Agent, Staff, System
    
    # Visibility
    is_public = Column(Integer, default=1)  # 1 = visible to customer, 0 = internal only
    
    # Relationships
    waybill = relationship("Waybill", back_populates="tracking_events")
    
    def __repr__(self):
        return f"<TrackingEvent(id={self.id}, waybill_id={self.waybill_id}, status='{self.status}')>"
    
    def to_timeline_dict(self) -> dict:
        """Convert to timeline format for public display"""
        from datetime import datetime
        created = datetime.fromisoformat(self.created_at) if self.created_at else datetime.utcnow()
        return {
            "status": self.status,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "timestamp": created.isoformat(),
            "date": created.strftime("%Y-%m-%d"),
            "time": created.strftime("%H:%M")
        }
