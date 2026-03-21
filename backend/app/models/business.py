"""
Business Model - Tenant entity for multi-tenant architecture
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base
from app.models.base import TimestampMixin


class SubscriptionPlan(str, enum.Enum):
    """Subscription plans for businesses"""
    TRIAL = "trial"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class BusinessStatus(str, enum.Enum):
    """Business account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class Business(Base, TimestampMixin):
    """
    Business entity - represents a tenant in the multi-tenant system.
    Each business can have multiple branches and users.
    """
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    
    # Address information
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, default="Nigeria")
    
    # Subscription
    plan = Column(Enum(SubscriptionPlan), default=SubscriptionPlan.TRIAL, nullable=False)
    status = Column(Enum(BusinessStatus), default=BusinessStatus.ACTIVE, nullable=False)
    
    # Subscription dates
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    
    # Settings (JSON-like storage for flexible config)
    settings = Column(Text, nullable=True)  # JSON string for business-specific settings
    
    # Logo and branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True, default="#3B82F6")
    
    # Relationships
    branches = relationship("Branch", back_populates="business", cascade="all, delete-orphan")
    users = relationship("User", back_populates="business", cascade="all, delete-orphan")
    vendors = relationship("Vendor", back_populates="business", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="business", cascade="all, delete-orphan")
    warehouses = relationship("Warehouse", back_populates="business", cascade="all, delete-orphan")
    agents = relationship("LogisticAgent", back_populates="business", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="business", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Business(id={self.id}, name='{self.name}', plan='{self.plan.value}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if business account is active"""
        return self.status == BusinessStatus.ACTIVE
    
    @property
    def is_subscription_valid(self) -> bool:
        """Check if subscription is still valid"""
        if self.plan == SubscriptionPlan.TRIAL:
            return True  # Trial doesn't expire in dev
        if not self.subscription_end:
            return True
        return datetime.utcnow() < self.subscription_end
