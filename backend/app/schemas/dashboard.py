"""
Dashboard Schemas
ParcelFlow - Multi-tenant Logistics Platform
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from decimal import Decimal

from app.schemas.base import BaseSchema


class DashboardStats(BaseSchema):
    """General dashboard statistics"""
    # Orders
    orders_today: int
    orders_pending: int
    orders_completed: int
    orders_total_value: Decimal
    
    # Deliveries
    deliveries_pending: int
    deliveries_in_transit: int
    deliveries_completed: int
    deliveries_failed: int
    
    # Inventory
    total_products: int
    low_stock_items: int
    inventory_value: Decimal
    
    # Financial
    revenue_today: Decimal
    revenue_month: Decimal
    expenses_today: Decimal
    expenses_month: Decimal


class LogisticsDashboard(BaseSchema):
    """Logistics dashboard data"""
    # Summary stats
    total_waybills: int
    pending_pickups: int
    at_warehouse: int
    out_for_delivery: int
    delivered_today: int
    failed_today: int
    
    # Performance
    average_delivery_time: Optional[float] = None  # hours
    delivery_success_rate: float
    
    # By status breakdown
    status_breakdown: Dict[str, int]
    
    # By shipment type
    shipment_type_breakdown: Dict[str, int]
    
    # Agent performance
    top_agents: List[Dict[str, Any]]
    
    # Pending assignments
    unassigned_deliveries: int
    available_agents: int


class FinancialDashboard(BaseSchema):
    """Financial dashboard data"""
    # Revenue
    total_revenue_today: Decimal
    total_revenue_week: Decimal
    total_revenue_month: Decimal
    
    # Cash flow
    cash_collected_today: Decimal
    agent_unremitted_cash: Decimal
    bank_balance: Decimal
    
    # Expenses
    total_expenses_today: Decimal
    total_expenses_month: Decimal
    
    # Vendor balances
    total_vendor_balance: Decimal
    pending_remittances: int
    pending_remittance_amount: Decimal
    
    # Revenue breakdown
    revenue_by_payment_method: Dict[str, Decimal]
    
    # Expense breakdown
    expenses_by_category: Dict[str, Decimal]
    
    # Trends (last 7 days)
    daily_revenue: List[Dict[str, Any]]
    daily_expenses: List[Dict[str, Any]]


class AgentDashboard(BaseSchema):
    """Agent-specific dashboard data"""
    # Today's assignments
    deliveries_today: int
    completed_today: int
    pending_today: int
    failed_today: int
    
    # Performance
    success_rate: float
    rating: Decimal
    
    # Collections
    cash_collected: Decimal
    cash_remitted: Decimal
    unremitted_cash: Decimal
    
    # Recent deliveries
    recent_deliveries: List[Dict[str, Any]]


class VendorDashboard(BaseSchema):
    """Vendor portal dashboard data"""
    # Products
    total_products: int
    total_inventory: int
    low_stock_alerts: int
    
    # Orders
    pending_orders: int
    completed_orders: int
    total_sales: Decimal
    
    # Deliveries
    in_transit: int
    delivered: int
    
    # Financials
    current_balance: Decimal
    last_remittance: Optional[str] = None
    pending_remittance: Decimal
