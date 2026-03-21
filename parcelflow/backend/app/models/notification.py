"""
Notification Model
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base
from app.schemas.base import BaseSchema


class NotificationType(str, enum.Enum):
    """Notification types"""
    WAYBILL_CREATED = "waybill_created"
    WAYBILL_DISPATCHED = "waybill_dispatched"
    WAYBILL_DELIVERED = "waybill_delivered"
    WAYBILL_FAILED = "waybill_failed"
    PICKUP_ASSIGNED = "pickup_assigned"
    PICKUP_COMPLETED = "pickup_completed"
    DELIVERY_ASSIGNED = "delivery_assigned"
    DELIVERY_COMPLETED = "delivery_completed"
    ORDER_NEW = "order_new"
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_CANCELLED = "order_cancelled"
    AGENT_ASSIGNED = "agent_assigned"
    LOW_STOCK = "low_stock"
    PAYMENT_RECEIVED = "payment_received"
    REMINDER = "reminder"
    SYSTEM = "system"
    CUSTOM = "custom"


class NotificationPriority(str, enum.Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """Notification model"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    
    # Recipient
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # None = broadcast to all
    agent_id = Column(Integer, ForeignKey("logistic_agents.id"), nullable=True, index=True)  # Agent notifications
    
    # Notification details
    notification_type = Column(Enum(NotificationType), default=NotificationType.SYSTEM, nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)
    
    # Related entity (polymorphic)
    related_entity_type = Column(String(50), nullable=True)  # e.g., 'waybill', 'order', 'dispatch'
    related_entity_id = Column(Integer, nullable=True)
    
    # Action link
    action_url = Column(String(500), nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)
    
    # Delivery status
    sent_email = Column(Boolean, default=False)
    sent_sms = Column(Boolean, default=False)
    sent_push = Column(Boolean, default=False)
    
    # Expiry
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    @property
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False


class NotificationPreference(Base):
    """User notification preferences"""
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Enable/disable channels
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    in_app_enabled = Column(Boolean, default=True)
    
    # Notification type preferences
    notify_waybill_updates = Column(Boolean, default=True)
    notify_pickup_assignments = Column(Boolean, default=True)
    notify_delivery_assignments = Column(Boolean, default=True)
    notify_order_updates = Column(Boolean, default=True)
    notify_stock_alerts = Column(Boolean, default=True)
    notify_payment_updates = Column(Boolean, default=True)
    notify_system = Column(Boolean, default=True)
    
    # Quiet hours (UTC)
    quiet_hours_start = Column(Integer, default=22)  # 10 PM
    quiet_hours_end = Column(Integer, default=7)  # 7 AM
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Schemas
class NotificationBase(BaseSchema):
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    related_entity_type: str | None = None
    related_entity_id: int | None = None
    action_url: str | None = None


class NotificationCreate(NotificationBase):
    user_id: int | None = None
    agent_id: int | None = None
    expires_at: datetime | None = None


class NotificationResponse(NotificationBase):
    id: int
    business_id: int
    user_id: int | None
    agent_id: int | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    expires_at: datetime | None
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseSchema):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int


class NotificationPreferenceResponse(BaseSchema):
    email_enabled: bool
    sms_enabled: bool
    push_enabled: bool
    in_app_enabled: bool
    notify_waybill_updates: bool
    notify_pickup_assignments: bool
    notify_delivery_assignments: bool
    notify_order_updates: bool
    notify_stock_alerts: bool
    notify_payment_updates: bool
    notify_system: bool
    quiet_hours_start: int
    quiet_hours_end: int
    
    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseSchema):
    email_enabled: bool | None = None
    sms_enabled: bool | None = None
    push_enabled: bool | None = None
    in_app_enabled: bool | None = None
    notify_waybill_updates: bool | None = None
    notify_pickup_assignments: bool | None = None
    notify_delivery_assignments: bool | None = None
    notify_order_updates: bool | None = None
    notify_stock_alerts: bool | None = None
    notify_payment_updates: bool | None = None
    notify_system: bool | None = None
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None
