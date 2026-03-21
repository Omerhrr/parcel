"""
Role Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.schemas.base import BaseSchema, PaginatedResponse


class RoleBase(BaseModel):
    """Base role fields"""
    name: str = Field(..., min_length=2, max_length=50)
    display_name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Create role request"""
    permission_ids: List[int] = []


class RoleUpdate(BaseModel):
    """Update role request"""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class PermissionResponse(BaseSchema):
    """Permission response"""
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    module: Optional[str] = None


class RoleResponse(BaseSchema):
    """Full role response"""
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    is_system: int
    created_at: datetime
    updated_at: datetime
    permissions: List[PermissionResponse] = []


class RoleBrief(BaseModel):
    """Brief role info for nested responses"""
    id: int
    name: str
    display_name: str


class RoleListResponse(PaginatedResponse):
    """Paginated role list"""
    items: List[RoleResponse]
