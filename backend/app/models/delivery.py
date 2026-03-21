"""
Delivery Confirmation Model
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, Numeric
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, TenantMixin


class DeliveryStatus(str, enum.Enum):
    """Final delivery status"""
    DELIVERED = "delivered"
    FAILED = "failed"
    PARTIAL = "partial"  # Partial delivery
    RETURNED = "returned"


class DeliveryConfirmation(Base, TimestampMixin):
    """
    DeliveryConfirmation entity - proof of delivery.
    Records the final delivery details including signature and photos.
    """
    __tablename__ = "delivery_confirmations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Delivery agent
    agent_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Delivery details
    delivered_at = Column(String(50), nullable=True)  # DateTime
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.DELIVERED, nullable=False)
    
    # Receiver information
    receiver_name = Column(String(255), nullable=True)
    receiver_relationship = Column(String(50), nullable=True)  # self, family, neighbor, security
    receiver_id_type = Column(String(50), nullable=True)  # ID card type
    receiver_id_number = Column(String(100), nullable=True)
    
    # Proof of delivery
    receiver_signature = Column(Text, nullable=True)  # Base64 encoded signature
    receiver_signature_svg = Column(Text, nullable=True)  # SVG signature (text-based, stored directly)
    proof_photo_url = Column(String(500), nullable=True)
    
    # Location
    delivery_latitude = Column(String(20), nullable=True)
    delivery_longitude = Column(String(20), nullable=True)
    
    # Payment collection (for COD)
    cod_collected = Column(Integer, default=0)  # 0 = No, 1 = Yes
    cod_amount = Column(Numeric(12, 2), default=0)
    payment_method = Column(String(50), nullable=True)  # cash, transfer, pos
    
    # Notes
    delivery_notes = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    # Relationships
    waybill = relationship("Waybill", back_populates="delivery_confirmation")
    agent = relationship("User")
    
    def __repr__(self):
        return f"<DeliveryConfirmation(id={self.id}, waybill_id={self.waybill_id}, status='{self.status.value}')>"
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            DeliveryStatus.DELIVERED: "Delivered",
            DeliveryStatus.FAILED: "Failed",
            DeliveryStatus.PARTIAL: "Partial Delivery",
            DeliveryStatus.RETURNED: "Returned"
        }
        return status_map.get(self.status, self.status.value)


class Delivery(Base, TimestampMixin, TenantMixin):
    """
    Delivery entity - simplified delivery record for reporting.
    Links deliveries directly to business and agent for easy querying.
    """
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    waybill_id = Column(Integer, ForeignKey("waybills.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Agent who made the delivery
    agent_id = Column(Integer, ForeignKey("logistic_agents.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Delivery details
    delivered_at = Column(String(50), nullable=True)  # DateTime
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.DELIVERED, nullable=False)
    
    # COD collection
    cod_collected = Column(Integer, default=0)  # 0 = No, 1 = Yes
    cod_amount = Column(Numeric(12, 2), default=0)
    
    # Receiver info
    receiver_name = Column(String(255), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    waybill = relationship("Waybill", backref="deliveries")
    agent = relationship("LogisticAgent")
    
    def __repr__(self):
        return f"<Delivery(id={self.id}, waybill_id={self.waybill_id}, status='{self.status.value}')>"
