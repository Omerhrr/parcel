"""
Vendor Models
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Table, Numeric
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import TimestampMixin


# Many-to-Many relationship table for Vendor-User
vendor_user_association = Table(
    "vendor_user_association",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("vendor_id", Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
)


class Vendor(Base, TimestampMixin):
    """
    Vendor entity - business partners who supply products.
    Vendors have limited access to view their own inventory and orders.
    Supports remittance fee calculation for logistics services.
    """
    __tablename__ = "vendors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Vendor information
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)  # Short code
    
    # Contact
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="Nigeria")
    
    # Business details
    business_type = Column(String(100), nullable=True)  # Retailer, Wholesaler, Manufacturer
    tax_id = Column(String(100), nullable=True)
    
    # Banking details for remittances
    bank_name = Column(String(100), nullable=True)
    account_name = Column(String(255), nullable=True)
    account_number = Column(String(50), nullable=True)
    
    # Remittance fee - logistics fee per order (deducted from vendor payment)
    remittance_fee = Column(Numeric(12, 2), default=0)  # Fixed fee per order for same customer
    
    # Status
    is_active = Column(Integer, default=1)
    
    # API Access for vendor portal
    api_key = Column(String(64), nullable=True, unique=True, index=True)  # For vendor portal authentication
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Settlement settings
    settlement_cycle = Column(String(50), default="weekly")  # daily, weekly, monthly
    settlement_day = Column(Integer, default=5)  # Day of week/month for settlement
    
    # Relationships
    business = relationship("Business", back_populates="vendors")
    products = relationship("Product", back_populates="vendor")
    orders = relationship("Order", back_populates="vendor")
    users = relationship(
        "User",
        secondary=vendor_user_association,
        backref="vendor_associations"
    )
    waybills = relationship("Waybill", back_populates="vendor")
    ledger_entries = relationship("VendorLedger", back_populates="vendor")
    remittances = relationship("Remittance", back_populates="vendor")
    
    def __repr__(self):
        return f"<Vendor(id={self.id}, name='{self.name}')>"
    
    @property
    def is_available(self) -> bool:
        """Check if vendor is active"""
        return self.is_active == 1
    
    @staticmethod
    def generate_api_key():
        """Generate a secure API key for vendor portal access"""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return 'vp_' + ''.join(secrets.choice(alphabet) for _ in range(32))


class VendorUser(Base, TimestampMixin):
    """
    VendorUser entity - links users to vendors.
    Provides vendor portal access to specific users.
    """
    __tablename__ = "vendor_users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Access level
    access_level = Column(String(50), default="viewer")  # admin, editor, viewer
    
    # Permissions specific to this vendor user
    can_view_inventory = Column(Integer, default=1)
    can_view_orders = Column(Integer, default=1)
    can_view_deliveries = Column(Integer, default=1)
    can_view_remittance = Column(Integer, default=1)
    
    # Relationships
    vendor = relationship("Vendor")
    user = relationship("User")
    
    def __repr__(self):
        return f"<VendorUser(id={self.id}, vendor_id={self.vendor_id}, user_id={self.user_id})>"
