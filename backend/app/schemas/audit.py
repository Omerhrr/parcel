"""
Audit Log Schemas - Data validation and serialization
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.schemas.base import BaseSchema, PaginatedResponse


class AuditLogCreate(BaseModel):
    """Schema for creating an audit log entry"""
    business_id: Optional[int] = None
    user_id: Optional[int] = None
    action: str = Field(..., max_length=50)
    entity_type: str = Field(..., max_length=100)
    entity_id: int
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogResponse(BaseSchema):
    """Schema for audit log response"""
    id: int
    business_id: Optional[int] = None
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: int
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime
    
    # Computed fields
    action_display: Optional[str] = None
    entity_display: Optional[str] = None
    
    # Related user info (optional)
    user_name: Optional[str] = None
    user_email: Optional[str] = None


class AuditLogListResponse(PaginatedResponse):
    """Schema for paginated audit log list response"""
    items: List[AuditLogResponse]


class AuditLogDiffResponse(BaseSchema):
    """Schema for audit log diff response"""
    id: int
    action: str
    entity_type: str
    entity_id: int
    timestamp: datetime
    description: Optional[str] = None
    
    # Diff information
    added: Dict[str, Any] = {}
    removed: Dict[str, Any] = {}
    changed: Dict[str, Dict[str, Any]] = {}
    
    # Related user info
    user_name: Optional[str] = None


class AuditLogFilter(BaseModel):
    """Schema for audit log filtering"""
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    user_id: Optional[int] = None
    action: Optional[str] = None
    business_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = None


class AuditStatsResponse(BaseSchema):
    """Schema for audit statistics"""
    total_logs: int
    logs_today: int
    logs_this_week: int
    logs_this_month: int
    
    # Top actions
    top_actions: List[Dict[str, Any]] = []
    
    # Top entities
    top_entity_types: List[Dict[str, Any]] = []
    
    # Top users
    top_users: List[Dict[str, Any]] = []
