"""
User Model
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Optional
import enum

from app.database import Base
from app.models.base import TimestampMixin
from app.models.role import user_roles


class UserStatus(str, enum.Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"


class User(Base, TimestampMixin):
    """
    User entity - represents a person who can access the system.
    Users belong to a business and optionally to a specific branch.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Profile information
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    password_hash = Column(String(255), nullable=False)
    
    # Avatar
    avatar_url = Column(String(500), nullable=True)
    
    # Status
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    is_verified = Column(Boolean, default=False)
    
    # Authentication
    last_login = Column(String(50), nullable=True)  # DateTime as string
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(String(50), nullable=True)  # DateTime as string
    
    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(String(50), nullable=True)
    
    # Email verification
    email_verification_token = Column(String(255), nullable=True)
    
    # Profile settings
    timezone = Column(String(50), default="Africa/Lagos")
    language = Column(String(10), default="en")
    
    # Relationships
    business = relationship("Business", back_populates="users")
    branch = relationship("Branch", back_populates="users")
    roles = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin"
    )
    
    # Operational relationships
    created_orders = relationship("Order", foreign_keys="Order.created_by_user_id", back_populates="created_by")
    assigned_orders = relationship("OrderAssignment", foreign_keys="OrderAssignment.assigned_to_user_id", back_populates="assigned_user")
    created_leads = relationship("Lead", foreign_keys="Lead.created_by_user_id", back_populates="created_by")
    assigned_leads = relationship("Lead", foreign_keys="Lead.assigned_to_user_id", back_populates="assigned_to")
    
    # Notifications
    notifications = relationship("Notification", back_populates="user", order_by="desc(Notification.created_at)")
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if user account is active"""
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_locked(self) -> bool:
        """Check if account is temporarily locked"""
        if not self.locked_until:
            return False
        try:
            locked_time = datetime.fromisoformat(self.locked_until)
            return datetime.utcnow() < locked_time
        except (ValueError, TypeError):
            return False
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return any(r.name == role_name for r in self.roles)
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission through any of their roles"""
        # Super admin has all permissions
        if self.has_role("super_admin"):
            return True
        
        for role in self.roles:
            if role.has_permission(permission_name) or role.has_permission("*"):
                return True
        return False
    
    def get_all_permissions(self) -> List[str]:
        """Get all unique permissions from all roles"""
        permissions = set()
        for role in self.roles:
            permissions.update(role.get_permission_names())
        return list(permissions)
    
    def get_primary_role_name(self) -> Optional[str]:
        """Get the name of the user's primary (first) role"""
        if self.roles:
            return self.roles[0].display_name
        return None
    
    def set_password(self, plain_password: str):
        """Hash and set password"""
        import bcrypt
        self.password_hash = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, plain_password: str) -> bool:
        """Verify password against stored hash"""
        import bcrypt
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except Exception:
            return False
