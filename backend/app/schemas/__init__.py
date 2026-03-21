"""
Pydantic Schemas - Data validation and serialization
ParcelFlow - Multi-tenant Logistics Platform
"""
from app.schemas.base import BaseSchema
from app.schemas.auth import (
    Token, TokenData, LoginRequest, LoginResponse,
    PasswordResetRequest, PasswordResetConfirm,
    RegisterRequest, RegisterResponse
)
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    UserPasswordUpdate
)
from app.schemas.business import (
    BusinessCreate, BusinessUpdate, BusinessResponse,
    BusinessListResponse
)
from app.schemas.branch import (
    BranchCreate, BranchUpdate, BranchResponse,
    BranchListResponse
)
from app.schemas.waybill import (
    WaybillCreate, WaybillUpdate, WaybillResponse,
    WaybillListResponse, WaybillTrackingResponse
)
from app.schemas.order import (
    OrderCreate, OrderUpdate, OrderResponse,
    OrderListResponse, OrderItemCreate, OrderItemResponse
)
from app.schemas.vendor import (
    VendorCreate, VendorUpdate, VendorResponse,
    VendorListResponse
)
from app.schemas.agent import (
    AgentCreate, AgentUpdate, AgentResponse,
    AgentListResponse, VehicleCreate, VehicleResponse
)
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductListResponse
)
from app.schemas.inventory import (
    InventoryResponse, InventoryUpdate,
    StockMovementCreate, StockMovementResponse
)
from app.schemas.lead import (
    LeadCreate, LeadUpdate, LeadResponse,
    LeadListResponse
)
from app.schemas.accounting import (
    ExpenseCreate, ExpenseResponse,
    TransactionResponse, RemittanceCreate, RemittanceResponse
)
from app.schemas.dashboard import (
    DashboardStats, LogisticsDashboard,
    FinancialDashboard
)
from app.schemas.audit import (
    AuditLogCreate, AuditLogResponse, AuditLogListResponse,
    AuditLogDiffResponse, AuditLogFilter, AuditStatsResponse
)

__all__ = [
    # Base
    "BaseSchema",
    # Auth
    "Token", "TokenData", "LoginRequest", "LoginResponse",
    "PasswordResetRequest", "PasswordResetConfirm",
    "RegisterRequest", "RegisterResponse",
    # User
    "UserCreate", "UserUpdate", "UserResponse", "UserListResponse",
    "UserPasswordUpdate",
    # Business
    "BusinessCreate", "BusinessUpdate", "BusinessResponse",
    "BusinessListResponse",
    # Branch
    "BranchCreate", "BranchUpdate", "BranchResponse",
    "BranchListResponse",
    # Waybill
    "WaybillCreate", "WaybillUpdate", "WaybillResponse",
    "WaybillListResponse", "WaybillTrackingResponse",
    # Order
    "OrderCreate", "OrderUpdate", "OrderResponse",
    "OrderListResponse", "OrderItemCreate", "OrderItemResponse",
    # Vendor
    "VendorCreate", "VendorUpdate", "VendorResponse",
    "VendorListResponse",
    # Agent
    "AgentCreate", "AgentUpdate", "AgentResponse",
    "AgentListResponse", "VehicleCreate", "VehicleResponse",
    # Product
    "ProductCreate", "ProductUpdate", "ProductResponse",
    "ProductListResponse",
    # Inventory
    "InventoryResponse", "InventoryUpdate",
    "StockMovementCreate", "StockMovementResponse",
    # Lead
    "LeadCreate", "LeadUpdate", "LeadResponse",
    "LeadListResponse",
    # Accounting
    "ExpenseCreate", "ExpenseResponse",
    "TransactionResponse", "RemittanceCreate", "RemittanceResponse",
    # Dashboard
    "DashboardStats", "LogisticsDashboard", "FinancialDashboard",
    # Audit
    "AuditLogCreate", "AuditLogResponse", "AuditLogListResponse",
    "AuditLogDiffResponse", "AuditLogFilter", "AuditStatsResponse",
]
