"""
Base Schema with common fields
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any, Dict
from enum import Enum


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,  # Pydantic v2 equivalent of orm_mode
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
        }
    )


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = 1
    page_size: int = 20
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database query"""
        return self.page_size


class PaginatedResponse(BaseModel):
    """Base paginated response"""
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def calculate_total_pages(cls, total: int, page_size: int) -> int:
        """Calculate total pages"""
        if total == 0:
            return 0
        return (total + page_size - 1) // page_size


class ErrorResponse(BaseModel):
    """Error response schema"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Success response schema"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None
