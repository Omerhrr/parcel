"""
Base Model with common fields and mixins
ParcelFlow - Multi-tenant Logistics Platform
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import declared_attr


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps"""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class TenantMixin:
    """Mixin to add multi-tenant fields (business_id, branch_id)"""
    
    @declared_attr
    def business_id(cls):
        from sqlalchemy import Column, Integer, ForeignKey
        return Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    @declared_attr
    def branch_id(cls):
        from sqlalchemy import Column, Integer, ForeignKey
        return Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)


class BaseModel:
    """Base model with primary key"""
    
    id = Column(Integer, primary_key=True, autoincrement=True)
