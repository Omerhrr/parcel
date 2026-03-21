"""
Accounting Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal

from app.schemas.base import BaseSchema, PaginatedResponse


class ExpenseCreate(BaseModel):
    """Create expense request"""
    branch_id: Optional[int] = None
    category: str = "other"
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    expense_date: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None


class ExpenseUpdate(BaseModel):
    """Update expense request"""
    branch_id: Optional[int] = None
    category: Optional[str] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = None
    expense_date: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None


class ExpenseResponse(BaseSchema):
    """Expense response"""
    id: int
    business_id: int
    branch_id: Optional[int] = None
    category: str
    amount: Decimal
    description: Optional[str] = None
    expense_date: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    recorded_by_user_id: Optional[int] = None
    approved_by_user_id: Optional[int] = None
    approved_at: Optional[str] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ExpenseListResponse(PaginatedResponse):
    """Paginated expense list"""
    items: List[ExpenseResponse]


class TransactionResponse(BaseSchema):
    """Transaction response"""
    id: int
    account_id: int
    business_id: int
    transaction_type: str
    amount: Decimal
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    description: Optional[str] = None
    transaction_date: Optional[str] = None
    recorded_by_user_id: Optional[int] = None
    balance_after: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(PaginatedResponse):
    """Paginated transaction list"""
    items: List[TransactionResponse]


class RemittanceCreate(BaseModel):
    """Create remittance request"""
    vendor_id: int
    amount: Decimal = Field(..., gt=0)
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_date: Optional[str] = None
    notes: Optional[str] = None


class RemittanceResponse(BaseSchema):
    """Remittance response"""
    id: int
    vendor_id: int
    business_id: int
    amount: Decimal
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_date: Optional[str] = None
    status: str
    approved_by_user_id: Optional[int] = None
    approved_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RemittanceCreate(BaseModel):
    """Create remittance request"""
    vendor_id: int
    amount: Decimal = Field(..., gt=0)
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    payment_date: Optional[str] = None
    notes: Optional[str] = None


class RemittanceListResponse(PaginatedResponse):
    """Paginated remittance list"""
    items: List[RemittanceResponse]


class AgentCollectionResponse(BaseSchema):
    """Agent collection response"""
    id: int
    business_id: int
    agent_id: Optional[int] = None
    order_id: Optional[int] = None
    waybill_id: Optional[int] = None
    amount_collected: Decimal
    collection_date: Optional[str] = None
    remitted: int
    remitted_at: Optional[str] = None
    remittance_reference: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AgentRemittanceResponse(BaseSchema):
    """Agent remittance response"""
    id: int
    business_id: int
    agent_id: Optional[int] = None
    amount: Decimal
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    collected_at: Optional[str] = None
    remitted_at: Optional[str] = None
    status: str
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AgentRemittanceListResponse(PaginatedResponse):
    """Paginated agent remittance list"""
    items: List[AgentRemittanceResponse]


class ExpenseListResponse(PaginatedResponse):
    """Paginated expense list"""
    items: List[ExpenseResponse]
