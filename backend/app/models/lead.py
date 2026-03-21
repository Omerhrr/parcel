"""
Lead Model - Sales leads management
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.models.base import TimestampMixin, TenantMixin


class LeadStatus(str, enum.Enum):
    """Status of a sales lead"""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CONVERTED = "converted"
    REJECTED = "rejected"
    LOST = "lost"


class LeadSource(str, enum.Enum):
    """Source of the lead"""
    WEBSITE = "website"
    LANDING_PAGE = "landing_page"
    PHONE = "phone"
    EMAIL = "email"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    WALK_IN = "walk_in"
    OTHER = "other"


class Lead(Base, TimestampMixin, TenantMixin):
    """
    Lead entity - potential customers for the sales team.
    Leads can be converted to customers/orders.
    """
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Lead information
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    
    # Company/Business (for B2B)
    company_name = Column(String(255), nullable=True)
    company_size = Column(Integer, nullable=True)
    industry = Column(String(100), nullable=True)
    
    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    
    # Interest
    product_interest = Column(String(255), nullable=True)  # Product they're interested in
    service_interest = Column(String(255), nullable=True)  # Service they're interested in
    estimated_value = Column(String(50), nullable=True)  # Estimated order value
    
    # Source
    source = Column(Enum(LeadSource), default=LeadSource.OTHER, nullable=False)
    source_details = Column(Text, nullable=True)  # Additional source info
    
    # Status
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW, nullable=False, index=True)
    
    # Assignment
    assigned_to_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Follow-up
    next_follow_up = Column(String(50), nullable=True)  # Date
    last_contact = Column(String(50), nullable=True)  # DateTime
    
    # Conversion
    converted_at = Column(String(50), nullable=True)
    converted_to_customer_id = Column(Integer, nullable=True)  # Future: Customer ID
    converted_to_order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Relationships
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id], back_populates="assigned_leads")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_leads")
    converted_order = relationship("Order", foreign_keys=[converted_to_order_id])
    
    def __repr__(self):
        return f"<Lead(id={self.id}, name='{self.name}', status='{self.status.value}')>"
    
    @property
    def is_converted(self) -> bool:
        """Check if lead is converted"""
        return self.status == LeadStatus.CONVERTED
    
    @property
    def is_active(self) -> bool:
        """Check if lead is still active"""
        active_statuses = [LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED, 
                          LeadStatus.PROPOSAL, LeadStatus.NEGOTIATION]
        return self.status in active_statuses
    
    def get_status_display(self) -> str:
        """Get human-readable status"""
        status_map = {
            LeadStatus.NEW: "New",
            LeadStatus.CONTACTED: "Contacted",
            LeadStatus.QUALIFIED: "Qualified",
            LeadStatus.PROPOSAL: "Proposal Sent",
            LeadStatus.NEGOTIATION: "Negotiation",
            LeadStatus.CONVERTED: "Converted",
            LeadStatus.REJECTED: "Rejected",
            LeadStatus.LOST: "Lost"
        }
        return status_map.get(self.status, self.status.value)
    
    def get_source_display(self) -> str:
        """Get human-readable source"""
        source_map = {
            LeadSource.WEBSITE: "Website",
            LeadSource.LANDING_PAGE: "Landing Page",
            LeadSource.PHONE: "Phone Call",
            LeadSource.EMAIL: "Email",
            LeadSource.REFERRAL: "Referral",
            LeadSource.SOCIAL_MEDIA: "Social Media",
            LeadSource.WALK_IN: "Walk In",
            LeadSource.OTHER: "Other"
        }
        return source_map.get(self.source, self.source.value)
