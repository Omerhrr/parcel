"""
User Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime

from app.schemas.base import BaseSchema, PaginatedResponse


def validate_user_password(password: str) -> str:
    """Validate password meets security requirements"""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 128:
        raise ValueError("Password must be less than 128 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    # Check for common passwords
    common_passwords = ['password', 'password123', '123456', '12345678', 'qwerty', 'abc123', 'Password1']
    if password.lower() in [p.lower() for p in common_passwords]:
        raise ValueError("Password is too common. Please choose a stronger password")
    return password


class UserBase(BaseModel):
    """Base user fields"""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    status: str = "pending"
    timezone: str = "Africa/Lagos"
    language: str = "en"


class UserCreate(UserBase):
    """Create user request"""
    password: str = Field(..., min_length=8)
    branch_id: Optional[int] = None
    role_ids: List[int] = []
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return validate_user_password(v)


class UserUpdate(BaseModel):
    """Update user request"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    branch_id: Optional[int] = None
    status: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    role_ids: Optional[List[int]] = None


class UserPasswordUpdate(BaseModel):
    """Update password request"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        return validate_user_password(v)


class RoleBrief(BaseSchema):
    """Brief role info"""
    id: int
    name: str
    display_name: str


class UserResponse(BaseSchema):
    """Full user response"""
    id: int
    business_id: int
    branch_id: Optional[int] = None
    name: str
    email: str
    phone: Optional[str] = None
    status: str
    is_verified: bool
    avatar_url: Optional[str] = None
    timezone: str
    language: str
    last_login: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    roles: List[RoleBrief] = []
    branch: Optional["BranchBrief"] = None


class UserListResponse(PaginatedResponse):
    """Paginated user list"""
    items: List[UserResponse]


class UserBriefResponse(BaseSchema):
    """Brief user info for nested responses"""
    id: int
    name: str
    email: str
    phone: Optional[str] = None


# Forward references
from app.schemas.auth import BranchBrief
UserResponse.model_rebuild()
