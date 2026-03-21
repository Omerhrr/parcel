"""
Authentication Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime

from app.schemas.base import BaseSchema


def validate_password_strength(password: str) -> str:
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
    common_passwords = ['password', 'password123', '123456', '12345678', 'qwerty', 'abc123']
    if password.lower() in common_passwords:
        raise ValueError("Password is too common. Please choose a stronger password")
    return password


class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds
    business_id: Optional[int] = None
    branch_id: Optional[int] = None
    roles: List[str] = []
    permissions: List[str] = []


class TokenData(BaseModel):
    """Data encoded in JWT token"""
    user_id: Optional[int] = None
    business_id: Optional[int] = None
    branch_id: Optional[int] = None
    roles: List[str] = []
    permissions: List[str] = []
    exp: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class LoginResponse(BaseSchema):
    """Login response with token and user data"""
    token: Token
    user: "UserBrief"
    business: "BusinessBrief"
    branch: Optional["BranchBrief"] = None


class UserBrief(BaseSchema):
    """Brief user info for nested responses"""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    status: str
    avatar_url: Optional[str] = None


class BusinessBrief(BaseSchema):
    """Brief business info for nested responses"""
    id: int
    name: str
    slug: str
    plan: str
    status: str


class BranchBrief(BaseSchema):
    """Brief branch info for nested responses"""
    id: int
    name: str
    code: Optional[str] = None
    city: Optional[str] = None
    currency: str


class RegisterRequest(BaseModel):
    """Registration request for new business"""
    # Business info
    business_name: str = Field(..., min_length=2, max_length=255)
    business_email: EmailStr
    business_phone: Optional[str] = None
    
    # User info (first admin)
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=8)
    
    # Terms
    accept_terms: bool = True
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        return validate_password_strength(v)


class RegisterResponse(BaseSchema):
    """Registration response"""
    business: BusinessBrief
    user: UserBrief
    message: str


class PasswordResetRequest(BaseModel):
    """Request password reset"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token"""
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        return validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """Change password (authenticated)"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        return validate_password_strength(v)


class RefreshTokenRequest(BaseModel):
    """Refresh access token"""
    refresh_token: str


# Update forward references
LoginResponse.model_rebuild()
