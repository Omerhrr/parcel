"""
Dashboard Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.models.waybill import Waybill, WaybillStatus
from app.models.order import Order, OrderStatus
from app.models.agent import LogisticAgent, AgentStatus
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.accounting import Expense
from app.models.dispatch import Dispatch, DispatchStatus
from app.schemas.dashboard import DashboardStats, LogisticsDashboard, FinancialDashboard
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/overview", response_model=DashboardStats)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard overview statistics"""
    business_id = current_user.business_id
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    month_start = datetime.combine(today.replace(day=1), datetime.min.time())
    
    # Orders today
    orders_today = db.query(Order).filter(
        Order.business_id == business_id,
        Order.created_at >= today_start
    ).count()
    
    # Pending orders
    orders_pending = db.query(Order).filter(
        Order.business_id == business_id,
        Order.status == OrderStatus.PENDING
    ).count()
    
    # Completed orders today
    orders_completed = db.query(Order).filter(
        Order.business_id == business_id,
        Order.status == OrderStatus.DELIVERED,
        Order.delivered_at >= today_start
    ).count()
    
    # Total order value
    orders_total_value = db.query(func.sum(Order.total_amount)).filter(
        Order.business_id == business_id,
        Order.status == OrderStatus.DELIVERED
    ).scalar() or 0
    
    # Deliveries
    deliveries_pending = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status == WaybillStatus.CREATED
    ).count()
    
    deliveries_in_transit = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status.in_([
            WaybillStatus.PICKED_UP,
            WaybillStatus.AT_WAREHOUSE,
            WaybillStatus.OUT_FOR_DELIVERY
        ])
    ).count()
    
    deliveries_completed = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status == WaybillStatus.DELIVERED
    ).count()
    
    deliveries_failed = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status.in_([WaybillStatus.FAILED, WaybillStatus.RETURNED])
    ).count()
    
    # Inventory stats
    total_products = db.query(Product).filter(
        Product.business_id == business_id,
        Product.is_active == True
    ).count()
    
    # Low stock items (products with quantity < 10)
    low_stock_items = db.query(Inventory).join(Product).filter(
        Product.business_id == business_id,
        Inventory.quantity < 10,
        Inventory.quantity > 0
    ).count()
    
    # Inventory value (using Product.cost_price)
    inventory_value = db.query(
        func.sum(Inventory.quantity * Product.cost_price)
    ).join(Product).filter(
        Product.business_id == business_id
    ).scalar() or 0
    
    # Revenue today
    revenue_today = db.query(func.sum(Order.total_amount)).filter(
        Order.business_id == business_id,
        Order.created_at >= today_start,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED])
    ).scalar() or 0
    
    # Revenue this month
    revenue_month = db.query(func.sum(Order.total_amount)).filter(
        Order.business_id == business_id,
        Order.created_at >= month_start,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED])
    ).scalar() or 0
    
    # Expenses today
    expenses_today = db.query(func.sum(Expense.amount)).filter(
        Expense.business_id == business_id,
        Expense.expense_date >= today_start
    ).scalar() or 0
    
    # Expenses this month
    expenses_month = db.query(func.sum(Expense.amount)).filter(
        Expense.business_id == business_id,
        Expense.expense_date >= month_start
    ).scalar() or 0
    
    return DashboardStats(
        orders_today=orders_today,
        orders_pending=orders_pending,
        orders_completed=orders_completed,
        orders_total_value=Decimal(str(orders_total_value)),
        deliveries_pending=deliveries_pending,
        deliveries_in_transit=deliveries_in_transit,
        deliveries_completed=deliveries_completed,
        deliveries_failed=deliveries_failed,
        total_products=total_products,
        low_stock_items=low_stock_items,
        inventory_value=Decimal(str(inventory_value)),
        revenue_today=Decimal(str(revenue_today)),
        revenue_month=Decimal(str(revenue_month)),
        expenses_today=Decimal(str(expenses_today)),
        expenses_month=Decimal(str(expenses_month))
    )


@router.get("/logistics", response_model=LogisticsDashboard)
async def get_logistics_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get logistics dashboard data"""
    business_id = current_user.business_id
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    # Waybill counts by status
    total_waybills = db.query(Waybill).filter(
        Waybill.business_id == business_id
    ).count()
    
    pending_pickups = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status == WaybillStatus.PICKUP_SCHEDULED
    ).count()
    
    at_warehouse = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status == WaybillStatus.AT_WAREHOUSE
    ).count()
    
    out_for_delivery = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status == WaybillStatus.OUT_FOR_DELIVERY
    ).count()
    
    delivered_today = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status == WaybillStatus.DELIVERED,
        Waybill.updated_at >= today_start
    ).count()
    
    failed_today = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status == WaybillStatus.FAILED,
        Waybill.updated_at >= today_start
    ).count()
    
    # Status breakdown
    status_counts = db.query(
        Waybill.status,
        func.count(Waybill.id)
    ).filter(
        Waybill.business_id == business_id
    ).group_by(Waybill.status).all()
    
    status_breakdown = {s.value: c for s, c in status_counts}
    
    # Shipment type breakdown
    shipment_counts = db.query(
        Waybill.shipment_type,
        func.count(Waybill.id)
    ).filter(
        Waybill.business_id == business_id
    ).group_by(Waybill.shipment_type).all()
    
    shipment_type_breakdown = {s.value: c for s, c in shipment_counts}
    
    # Calculate delivery success rate
    total_completed = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status.in_([WaybillStatus.DELIVERED, WaybillStatus.FAILED, WaybillStatus.RETURNED])
    ).count()
    
    successful = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status == WaybillStatus.DELIVERED
    ).count()
    
    delivery_success_rate = (successful / total_completed * 100) if total_completed > 0 else 0.0
    
    # Calculate average delivery time (from created to delivered)
    # This is a simplified calculation
    avg_time_query = db.query(
        func.avg(
            func.extract('epoch', Waybill.updated_at) - func.extract('epoch', Waybill.created_at)
        )
    ).filter(
        Waybill.business_id == business_id,
        Waybill.status == WaybillStatus.DELIVERED,
        Waybill.updated_at.isnot(None)
    ).scalar()
    
    # Convert seconds to hours
    average_delivery_time = (avg_time_query / 3600) if avg_time_query else None
    
    # Top performing agents
    top_agents_query = db.query(
        LogisticAgent,
        func.count(Dispatch.id).label('total_deliveries')
    ).join(Dispatch).filter(
        LogisticAgent.business_id == business_id,
        Dispatch.status == DispatchStatus.COMPLETED
    ).group_by(LogisticAgent.id).order_by(func.count(Dispatch.id).desc()).limit(5).all()
    
    top_agents = []
    for agent, total in top_agents_query:
        top_agents.append({
            'id': agent.id,
            'name': agent.name,
            'completed': total,
            'success_rate': agent.success_rate,
            'rating': float(agent.rating) if agent.rating else 0.0
        })
    
    # Available agents
    available_agents = db.query(LogisticAgent).filter(
        LogisticAgent.business_id == business_id,
        LogisticAgent.status == AgentStatus.AVAILABLE
    ).count()
    
    # Active agents (on delivery)
    active_agents = db.query(LogisticAgent).filter(
        LogisticAgent.business_id == business_id,
        LogisticAgent.status == AgentStatus.BUSY
    ).count()
    
    # Scheduled today
    scheduled_today = db.query(Waybill).filter(
        Waybill.business_id == business_id,
        Waybill.status == WaybillStatus.PICKUP_SCHEDULED
    ).count()
    
    return LogisticsDashboard(
        total_waybills=total_waybills,
        pending_pickups=pending_pickups,
        at_warehouse=at_warehouse,
        out_for_delivery=out_for_delivery,
        delivered_today=delivered_today,
        failed_today=failed_today,
        average_delivery_time=average_delivery_time,
        delivery_success_rate=round(delivery_success_rate, 1),
        status_breakdown=status_breakdown,
        shipment_type_breakdown=shipment_type_breakdown,
        top_agents=top_agents,
        unassigned_deliveries=pending_pickups + at_warehouse,
        available_agents=available_agents + active_agents
    )


@router.get("/financial", response_model=FinancialDashboard)
async def get_financial_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get financial dashboard data"""
    business_id = current_user.business_id
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Revenue calculations
    # Today
    revenue_today = db.query(func.sum(Order.total_amount)).filter(
        Order.business_id == business_id,
        Order.created_at >= today_start,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED])
    ).scalar() or 0
    
    # This week
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    revenue_week = db.query(func.sum(Order.total_amount)).filter(
        Order.business_id == business_id,
        Order.created_at >= week_start_dt,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED])
    ).scalar() or 0
    
    # This month
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    revenue_month = db.query(func.sum(Order.total_amount)).filter(
        Order.business_id == business_id,
        Order.created_at >= month_start_dt,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED])
    ).scalar() or 0
    
    # COD collected today (from deliveries)
    from app.models.delivery import Delivery
    cash_collected_today = db.query(func.sum(Delivery.cod_amount)).filter(
        Delivery.business_id == business_id,
        Delivery.cod_collected == True,
        Delivery.delivered_at >= today_start
    ).scalar() or 0
    
    # Agent unremitted cash (pending remittances)
    from app.models.accounting import AgentRemittance, RemittanceStatus
    unremitted = db.query(func.sum(AgentRemittance.amount)).filter(
        AgentRemittance.business_id == business_id,
        AgentRemittance.status == RemittanceStatus.PENDING
    ).scalar() or 0
    
    # Expenses
    expenses_today = db.query(func.sum(Expense.amount)).filter(
        Expense.business_id == business_id,
        Expense.expense_date >= today_start
    ).scalar() or 0
    
    expenses_month = db.query(func.sum(Expense.amount)).filter(
        Expense.business_id == business_id,
        Expense.expense_date >= month_start_dt
    ).scalar() or 0
    
    # Expenses by category
    expense_categories = db.query(
        Expense.category,
        func.sum(Expense.amount)
    ).filter(
        Expense.business_id == business_id,
        Expense.expense_date >= month_start_dt
    ).group_by(Expense.category).all()
    
    expenses_by_category = {cat or 'Other': float(amt) for cat, amt in expense_categories}
    
    # Revenue by payment method
    payment_method_revenue = db.query(
        Order.payment_method,
        func.sum(Order.total_amount)
    ).filter(
        Order.business_id == business_id,
        Order.created_at >= month_start_dt,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED])
    ).group_by(Order.payment_method).all()
    
    revenue_by_payment_method = {}
    for method, amount in payment_method_revenue:
        method_name = method.value if hasattr(method, 'value') else str(method)
        revenue_by_payment_method[method_name] = float(amount)
    
    # Daily revenue (last 7 days)
    daily_revenue = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        day_revenue = db.query(func.sum(Order.total_amount)).filter(
            Order.business_id == business_id,
            Order.created_at >= day_start,
            Order.created_at <= day_end,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED])
        ).scalar() or 0
        
        daily_revenue.append({
            'date': day.isoformat(),
            'amount': float(day_revenue)
        })
    
    # Daily expenses (last 7 days)
    daily_expenses = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        day_expense = db.query(func.sum(Expense.amount)).filter(
            Expense.business_id == business_id,
            Expense.expense_date >= day_start,
            Expense.expense_date <= day_end
        ).scalar() or 0
        
        daily_expenses.append({
            'date': day.isoformat(),
            'amount': float(day_expense)
        })
    
    # Pending remittances count
    pending_remittances = db.query(AgentRemittance).filter(
        AgentRemittance.business_id == business_id,
        AgentRemittance.status == RemittanceStatus.PENDING
    ).count()
    
    return FinancialDashboard(
        total_revenue_today=Decimal(str(revenue_today)),
        total_revenue_week=Decimal(str(revenue_week)),
        total_revenue_month=Decimal(str(revenue_month)),
        cash_collected_today=Decimal(str(cash_collected_today)),
        agent_unremitted_cash=Decimal(str(unremitted)),
        bank_balance=Decimal('0'),  # Would need bank integration
        total_expenses_today=Decimal(str(expenses_today)),
        total_expenses_month=Decimal(str(expenses_month)),
        total_vendor_balance=Decimal('0'),  # Would need vendor balance calculation
        pending_remittances=pending_remittances,
        pending_remittance_amount=Decimal(str(unremitted)),
        revenue_by_payment_method=revenue_by_payment_method,
        expenses_by_category=expenses_by_category,
        daily_revenue=daily_revenue,
        daily_expenses=daily_expenses
    )
