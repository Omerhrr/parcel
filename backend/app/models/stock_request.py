"""
Stock Inbound Request Model
ParcelFlow - Multi-tenant Logistics Platform

Vendors can submit stock inbound requests that need admin confirmation
before the stock enters the warehouse inventory.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Numeric, Enum
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin


class StockRequestStatus(str, enum.Enum):
    """Status of stock inbound request"""
    PENDING = "pending"        # Awaiting admin review
    APPROVED = "approved"      # Admin approved, awaiting delivery
    RECEIVED = "received"      # Stock received in warehouse
    REJECTED = "rejected"      # Admin rejected the request
    CANCELLED = "cancelled"    # Vendor cancelled the request


class StockInboundRequest(Base, TimestampMixin):
    """
    Stock Inbound Request - Vendor submits request to send products to warehouse.
    Must be confirmed by admin before stock enters inventory.
    """
    __tablename__ = "stock_inbound_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)

    # Request details
    request_number = Column(String(50), nullable=False, unique=True, index=True)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(12, 2), default=0)

    # Product details (can be manually entered if product not in system)
    product_name = Column(String(255), nullable=True)
    product_sku = Column(String(100), nullable=True)
    product_description = Column(Text, nullable=True)

    # Status
    status = Column(Enum(StockRequestStatus), default=StockRequestStatus.PENDING, nullable=False)

    # Shipping info
    expected_delivery_date = Column(String(50), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    carrier = Column(String(100), nullable=True)

    # Admin review
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(String(50), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Reception confirmation
    received_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    received_at = Column(String(50), nullable=True)
    received_quantity = Column(Integer, nullable=True)  # Actual quantity received
    reception_notes = Column(Text, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)
    vendor_notes = Column(Text, nullable=True)  # Notes from vendor

    # Relationships
    business = relationship("Business")
    vendor = relationship("Vendor", backref="stock_requests")
    warehouse = relationship("Warehouse")
    product = relationship("Product")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    receiver = relationship("User", foreign_keys=[received_by])

    def __repr__(self):
        return f"<StockInboundRequest(id={self.id}, request_number='{self.request_number}', status='{self.status}')>"

    @staticmethod
    def generate_request_number():
        """Generate a unique request number"""
        import random
        import string
        prefix = "SIR"
        suffix = ''.join(random.choices(string.digits, k=8))
        return f"{prefix}{suffix}"
