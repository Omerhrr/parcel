"""
Order and Order Item Models
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Numeric, Text
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, TenantMixin


class OrderStatus(str, enum.Enum):
    """Status of an order"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class PaymentStatus(str, enum.Enum):
    """Payment status"""
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    REFUNDED = "refunded"
    FAILED = "failed"


class PaymentMethod(str, enum.Enum):
    """Payment methods"""
    COD = "cod"  # Cash on Delivery
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    WALLET = "wallet"


class Order(Base, TimestampMixin, TenantMixin):
    """
    Order entity - customer orders.
    Orders contain multiple items and can generate waybills.
    Supports vendor remittance fee calculation.
    """
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True, index=True)  # Primary vendor for this order
    
    # Customer information
    customer_name = Column(String(255), nullable=False)
    customer_phone = Column(String(50), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_id = Column(Integer, nullable=True)  # Future CRM - no FK constraint yet
    
    # Delivery address
    delivery_address = Column(Text, nullable=False)
    delivery_city = Column(String(100), nullable=True)
    delivery_state = Column(String(100), nullable=True)
    delivery_landmark = Column(String(255), nullable=True)
    
    # Amounts
    subtotal = Column(Numeric(12, 2), default=0)
    delivery_fee = Column(Numeric(12, 2), default=0)
    discount = Column(Numeric(12, 2), default=0)
    tax = Column(Numeric(12, 2), default=0)
    total_amount = Column(Numeric(12, 2), default=0)
    
    # Remittance (Logistics fee deducted from vendor payment)
    remittance_fee = Column(Numeric(12, 2), default=0)  # Logistics/delivery fee per order
    vendor_amount = Column(Numeric(12, 2), default=0)  # Amount to be remitted to vendor (total - remittance_fee)
    
    # Payment
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.COD, nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    payment_reference = Column(String(255), nullable=True)
    paid_at = Column(String(50), nullable=True)
    
    # Status
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    
    # Source
    source = Column(String(50), nullable=True)  # website, landing_page, api, manual
    landing_page_id = Column(String(100), nullable=True)  # WordPress landing page reference
    
    # User tracking
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Dates
    confirmed_at = Column(String(50), nullable=True)
    shipped_at = Column(String(50), nullable=True)
    delivered_at = Column(String(50), nullable=True)
    
    # Remittance tracking
    remittance_status = Column(String(20), default="pending")  # pending, processed, paid
    remitted_at = Column(String(50), nullable=True)
    remittance_id = Column(Integer, ForeignKey("remittances.id", ondelete="SET NULL"), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Relationships
    branch = relationship("Branch", back_populates="orders")
    vendor = relationship("Vendor", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    assignments = relationship("OrderAssignment", back_populates="order", cascade="all, delete-orphan")
    waybills = relationship("Waybill", back_populates="order")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_orders")
    remittance = relationship("Remittance", foreign_keys=[remittance_id])
    
    def __repr__(self):
        return f"<Order(id={self.id}, number='{self.order_number}', status='{self.status.value}')>"
    
    @staticmethod
    def generate_order_number(branch_code: str = None) -> str:
        """Generate a unique order number"""
        from datetime import datetime
        import random
        import string
        prefix = branch_code or "ORD"
        timestamp = datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.digits, k=5))
        return f"{prefix}-{timestamp}-{random_part}"
    
    @property
    def is_paid(self) -> bool:
        """Check if order is paid"""
        return self.payment_status == PaymentStatus.PAID
    
    @property
    def is_completed(self) -> bool:
        """Check if order is completed"""
        return self.status == OrderStatus.DELIVERED
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            OrderStatus.PENDING: "Pending",
            OrderStatus.CONFIRMED: "Confirmed",
            OrderStatus.PROCESSING: "Processing",
            OrderStatus.SHIPPED: "Shipped",
            OrderStatus.DELIVERED: "Delivered",
            OrderStatus.CANCELLED: "Cancelled",
            OrderStatus.RETURNED: "Returned"
        }
        return status_map.get(self.status, self.status.value)


class OrderItem(Base, TimestampMixin):
    """
    OrderItem entity - individual items in an order.
    """
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    
    # Item details (snapshot at order time)
    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100), nullable=True)
    
    # Quantity and price
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(12, 2), default=0, nullable=False)
    discount = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), default=0)  # quantity * unit_price - discount
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product='{self.product_name}')>"


class OrderAssignment(Base, TimestampMixin):
    """
    OrderAssignment entity - tracks who is assigned to handle an order.
    """
    __tablename__ = "order_assignments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Assignment
    assigned_to_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(String(50), nullable=True)
    
    # Assignment type
    assignment_type = Column(String(50), default="delivery")  # delivery, pickup, processing
    
    # Status
    status = Column(String(50), default="assigned")  # assigned, in_progress, completed
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="assignments")
    assigned_user = relationship("User", foreign_keys=[assigned_to_user_id], back_populates="assigned_orders")
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id])
    
    def __repr__(self):
        return f"<OrderAssignment(id={self.id}, order_id={self.order_id})>"
