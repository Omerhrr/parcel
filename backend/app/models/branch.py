"""
Branch Model - Physical locations for a business
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin


class BranchStatus(str, enum.Enum):
    """Branch operational status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class Branch(Base, TimestampMixin):
    """
    Branch entity - represents a physical location/office of a business.
    Each branch can have its own timezone, currency, and settings.
    """
    __tablename__ = "branches"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    code = Column(String(20), nullable=True)  # Short code for the branch
    
    # Location details
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False, default="Nigeria")
    postal_code = Column(String(20), nullable=True)
    
    # Contact
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Regional settings
    currency = Column(String(3), nullable=False, default="NGN")
    timezone = Column(String(50), nullable=False, default="Africa/Lagos")
    
    # Operational settings
    status = Column(Enum(BranchStatus), default=BranchStatus.ACTIVE, nullable=False)
    is_headquarters = Column(Integer, default=0)  # 0 = No, 1 = Yes
    
    # Coordinates for mapping
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    
    # Relationships
    business = relationship("Business", back_populates="branches")
    users = relationship("User", back_populates="branch")
    warehouses = relationship("Warehouse", back_populates="branch")
    agents = relationship("LogisticAgent", back_populates="branch")
    waybills = relationship("Waybill", back_populates="branch")
    orders = relationship("Order", back_populates="branch")
    expenses = relationship("Expense", back_populates="branch")
    
    def __repr__(self):
        return f"<Branch(id={self.id}, name='{self.name}', business_id={self.business_id})>"
    
    @property
    def is_active(self) -> bool:
        """Check if branch is operational"""
        return self.status == BranchStatus.ACTIVE
    
    @property
    def full_address(self) -> str:
        """Get full formatted address"""
        parts = [self.address, self.city, self.state, self.country]
        return ", ".join(filter(None, parts))
