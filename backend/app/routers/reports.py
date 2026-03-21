"""
Reports Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional, List
import io
import csv
import json

from app.database import get_db
from app.models.user import User
from app.models.waybill import Waybill, WaybillStatus
from app.models.order import Order, OrderStatus
from app.models.agent import LogisticAgent
from app.models.vendor import Vendor
from app.models.dispatch import Dispatch, DispatchStatus
from app.models.delivery import Delivery
from app.models.accounting import Expense, AgentRemittance, RemittanceStatus
from app.schemas.base import BaseSchema
from app.utils.auth import get_current_user
from app.utils.exports import (
    create_sales_excel, create_delivery_excel, create_agent_excel,
    create_vendor_excel, create_expense_excel,
    PDFExporter
)

router = APIRouter()


# ==================== REPORT SCHEMAS ====================

class DateRangeReport(BaseSchema):
    start_date: date
    end_date: date


class SalesReportItem(BaseSchema):
    date: str
    orders: int
    revenue: float
    delivery_fees: float
    cod_collected: float


class SalesReport(BaseSchema):
    items: List[SalesReportItem]
    total_orders: int
    total_revenue: float
    total_delivery_fees: float
    total_cod: float
    average_order_value: float


class DeliveryReportItem(BaseSchema):
    date: str
    total: int
    delivered: int
    failed: int
    returned: int
    success_rate: float


class DeliveryReport(BaseSchema):
    items: List[DeliveryReportItem]
    total_deliveries: int
    total_successful: int
    total_failed: int
    overall_success_rate: float
    average_delivery_time_hours: Optional[float]


class AgentPerformanceItem(BaseSchema):
    agent_id: int
    agent_name: str
    total_deliveries: int
    successful: int
    failed: int
    success_rate: float
    rating: float
    cod_collected: float
    commissions_earned: float


class AgentPerformanceReport(BaseSchema):
    items: List[AgentPerformanceItem]
    period_start: date
    period_end: date


class VendorSettlementItem(BaseSchema):
    vendor_id: int
    vendor_name: str
    total_orders: int
    total_value: float
    commission_rate: float
    commission_amount: float
    amount_due: float
    amount_paid: float
    balance: float


class VendorSettlementReport(BaseSchema):
    items: List[VendorSettlementItem]
    total_commissions: float
    total_due: float
    total_paid: float


class ExpenseSummaryItem(BaseSchema):
    category: str
    total_amount: float
    count: int
    percentage: float


class ExpenseReport(BaseSchema):
    items: List[ExpenseSummaryItem]
    total_expenses: float
    period_start: date
    period_end: date


# ==================== SALES REPORT ====================

@router.get("/sales", response_model=SalesReport)
async def get_sales_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    branch_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sales report for a date range"""
    if not current_user.has_permission("reports.view"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    business_id = current_user.business_id
    
    # Build query
    query = db.query(Order).filter(
        Order.business_id == business_id,
        Order.created_at >= datetime.combine(start_date, datetime.min.time()),
        Order.created_at <= datetime.combine(end_date, datetime.max.time())
    )
    
    if branch_id:
        query = query.filter(Order.branch_id == branch_id)
    
    # Get daily breakdown
    daily_stats = []
    current_date = start_date
    total_orders = 0
    total_revenue = 0
    total_delivery_fees = 0
    total_cod = 0
    
    while current_date <= end_date:
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = datetime.combine(current_date, datetime.max.time())
        
        day_orders = db.query(Order).filter(
            Order.business_id == business_id,
            Order.created_at >= day_start,
            Order.created_at <= day_end,
            Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED])
        )
        
        if branch_id:
            day_orders = day_orders.filter(Order.branch_id == branch_id)
        
        orders_count = day_orders.count()
        revenue = day_orders.with_entities(func.sum(Order.total_amount)).scalar() or 0
        delivery_fees = day_orders.with_entities(func.sum(Order.delivery_fee)).scalar() or 0
        
        # COD collected for this day
        cod = db.query(func.sum(Delivery.cod_amount)).filter(
            Delivery.business_id == business_id,
            Delivery.delivered_at >= day_start,
            Delivery.delivered_at <= day_end,
            Delivery.cod_collected == True
        ).scalar() or 0
        
        daily_stats.append(SalesReportItem(
            date=current_date.isoformat(),
            orders=orders_count,
            revenue=float(revenue),
            delivery_fees=float(delivery_fees),
            cod_collected=float(cod)
        ))
        
        total_orders += orders_count
        total_revenue += float(revenue)
        total_delivery_fees += float(delivery_fees)
        total_cod += float(cod)
        
        current_date += timedelta(days=1)
    
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    return SalesReport(
        items=daily_stats,
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_delivery_fees=total_delivery_fees,
        total_cod=total_cod,
        average_order_value=avg_order_value
    )


# ==================== DELIVERY REPORT ====================

@router.get("/deliveries", response_model=DeliveryReport)
async def get_delivery_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    agent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get delivery performance report"""
    if not current_user.has_permission("reports.view"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    business_id = current_user.business_id
    
    # Daily breakdown
    daily_stats = []
    current_date = start_date
    total_deliveries = 0
    total_successful = 0
    total_failed = 0
    
    while current_date <= end_date:
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = datetime.combine(current_date, datetime.max.time())
        
        # Query dispatches for this day
        query = db.query(Dispatch).join(Waybill).filter(
            Waybill.business_id == business_id,
            Dispatch.created_at >= day_start,
            Dispatch.created_at <= day_end
        )
        
        if agent_id:
            query = query.filter(Dispatch.agent_id == agent_id)
        
        day_total = query.count()
        day_delivered = query.filter(Dispatch.status == DispatchStatus.COMPLETED).count()
        day_failed = query.filter(Dispatch.status == DispatchStatus.FAILED).count()
        day_returned = query.filter(Dispatch.status == DispatchStatus.RETURNED).count()
        
        success_rate = (day_delivered / day_total * 100) if day_total > 0 else 0
        
        daily_stats.append(DeliveryReportItem(
            date=current_date.isoformat(),
            total=day_total,
            delivered=day_delivered,
            failed=day_failed,
            returned=day_returned,
            success_rate=round(success_rate, 1)
        ))
        
        total_deliveries += day_total
        total_successful += day_delivered
        total_failed += day_failed
        
        current_date += timedelta(days=1)
    
    overall_success_rate = (total_successful / total_deliveries * 100) if total_deliveries > 0 else 0
    
    # Calculate average delivery time
    completed_dispatches = db.query(Dispatch).join(Waybill).filter(
        Waybill.business_id == business_id,
        Dispatch.status == DispatchStatus.COMPLETED,
        Dispatch.created_at >= datetime.combine(start_date, datetime.min.time()),
        Dispatch.completed_at.isnot(None)
    ).all()
    
    avg_time = None
    if completed_dispatches:
        total_hours = 0
        for d in completed_dispatches:
            if d.created_at and d.completed_at:
                delta = d.completed_at - d.created_at
                total_hours += delta.total_seconds() / 3600
        avg_time = total_hours / len(completed_dispatches)
    
    return DeliveryReport(
        items=daily_stats,
        total_deliveries=total_deliveries,
        total_successful=total_successful,
        total_failed=total_failed,
        overall_success_rate=round(overall_success_rate, 1),
        average_delivery_time_hours=round(avg_time, 1) if avg_time else None
    )


# ==================== AGENT PERFORMANCE REPORT ====================

@router.get("/agents", response_model=AgentPerformanceReport)
async def get_agent_performance_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get agent performance report"""
    if not current_user.has_permission("reports.view"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    business_id = current_user.business_id
    
    # Get all agents
    agents = db.query(LogisticAgent).filter(
        LogisticAgent.business_id == business_id
    ).all()
    
    items = []
    
    for agent in agents:
        # Get dispatches for this agent in date range
        dispatches = db.query(Dispatch).join(Waybill).filter(
            Waybill.business_id == business_id,
            Dispatch.agent_id == agent.id,
            Dispatch.created_at >= datetime.combine(start_date, datetime.min.time()),
            Dispatch.created_at <= datetime.combine(end_date, datetime.max.time())
        ).all()
        
        total = len(dispatches)
        successful = sum(1 for d in dispatches if d.status == DispatchStatus.COMPLETED)
        failed = sum(1 for d in dispatches if d.status == DispatchStatus.FAILED)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        # COD collected
        deliveries = db.query(Delivery).filter(
            Delivery.agent_id == agent.id,
            Delivery.business_id == business_id,
            Delivery.delivered_at >= datetime.combine(start_date, datetime.min.time()),
            Delivery.delivered_at <= datetime.combine(end_date, datetime.max.time())
        ).all()
        
        cod_collected = sum(float(d.cod_amount or 0) for d in deliveries if d.cod_collected)
        
        # Commission calculation (simplified)
        commissions = float(agent.commission_rate or 0) * successful
        
        items.append(AgentPerformanceItem(
            agent_id=agent.id,
            agent_name=agent.name,
            total_deliveries=total,
            successful=successful,
            failed=failed,
            success_rate=round(success_rate, 1),
            rating=float(agent.rating or 0),
            cod_collected=cod_collected,
            commissions_earned=commissions
        ))
    
    # Sort by successful deliveries
    items.sort(key=lambda x: x.successful, reverse=True)
    
    return AgentPerformanceReport(
        items=items,
        period_start=start_date,
        period_end=end_date
    )


# ==================== VENDOR SETTLEMENT REPORT ====================

@router.get("/vendors", response_model=VendorSettlementReport)
async def get_vendor_settlement_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get vendor settlement report"""
    if not current_user.has_permission("reports.view"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    business_id = current_user.business_id
    
    # Get vendors
    vendors = db.query(Vendor).filter(
        Vendor.business_id == business_id,
        Vendor.is_active == True
    ).all()
    
    items = []
    total_commissions = 0
    total_due = 0
    total_paid = 0
    
    for vendor in vendors:
        # Get orders for this vendor
        orders = db.query(Order).filter(
            Order.business_id == business_id,
            # Assuming vendor_id is stored somewhere - simplified
            Order.created_at >= datetime.combine(start_date, datetime.min.time()),
            Order.created_at <= datetime.combine(end_date, datetime.max.time()),
            Order.status == OrderStatus.DELIVERED
        ).all()
        
        total_value = sum(float(o.total_amount or 0) for o in orders)
        commission_rate = float(vendor.settlement_cycle or 0) / 100 if vendor.settlement_cycle else 0.1  # Default 10%
        commission_amount = total_value * commission_rate
        amount_due = total_value - commission_amount
        
        # Get paid amounts from ledger
        # Simplified - would need actual vendor ledger integration
        
        balance = amount_due  # Assuming no payments yet for simplicity
        
        items.append(VendorSettlementItem(
            vendor_id=vendor.id,
            vendor_name=vendor.name,
            total_orders=len(orders),
            total_value=total_value,
            commission_rate=commission_rate * 100,
            commission_amount=commission_amount,
            amount_due=amount_due,
            amount_paid=0,
            balance=balance
        ))
        
        total_commissions += commission_amount
        total_due += amount_due
    
    return VendorSettlementReport(
        items=items,
        total_commissions=total_commissions,
        total_due=total_due,
        total_paid=total_paid
    )


# ==================== EXPENSE REPORT ====================

@router.get("/expenses", response_model=ExpenseReport)
async def get_expense_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get expense summary report"""
    if not current_user.has_permission("reports.view"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    business_id = current_user.business_id
    
    # Get expenses grouped by category
    expenses_by_category = db.query(
        Expense.category,
        func.sum(Expense.amount).label('total'),
        func.count(Expense.id).label('count')
    ).filter(
        Expense.business_id == business_id,
        Expense.expense_date >= datetime.combine(start_date, datetime.min.time()),
        Expense.expense_date <= datetime.combine(end_date, datetime.max.time())
    ).group_by(Expense.category).all()
    
    total_expenses = sum(float(e.total or 0) for e in expenses_by_category)
    
    items = []
    for exp in expenses_by_category:
        amount = float(exp.total or 0)
        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        
        items.append(ExpenseSummaryItem(
            category=exp.category or 'Uncategorized',
            total_amount=amount,
            count=exp.count,
            percentage=round(percentage, 1)
        ))
    
    # Sort by amount
    items.sort(key=lambda x: x.total_amount, reverse=True)
    
    return ExpenseReport(
        items=items,
        total_expenses=total_expenses,
        period_start=start_date,
        period_end=end_date
    )


# ==================== EXPORT FUNCTIONALITY ====================

@router.get("/export/sales")
async def export_sales_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    branch_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export sales report as CSV"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get the report data
    report = await get_sales_report(start_date, end_date, branch_id, current_user, db)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Date', 'Orders', 'Revenue', 'Delivery Fees', 'COD Collected'])
    
    # Data rows
    for item in report.items:
        writer.writerow([
            item.date,
            item.orders,
            item.revenue,
            item.delivery_fees,
            item.cod_collected
        ])
    
    # Totals row
    writer.writerow([])
    writer.writerow(['TOTALS', report.total_orders, report.total_revenue, 
                     report.total_delivery_fees, report.total_cod])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="sales_report_{start_date}_{end_date}.csv"'
        }
    )


@router.get("/export/agents")
async def export_agent_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export agent performance report as CSV"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get the report data
    report = await get_agent_performance_report(start_date, end_date, current_user, db)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Agent ID', 'Agent Name', 'Total Deliveries', 'Successful', 
                     'Failed', 'Success Rate (%)', 'Rating', 'COD Collected', 'Commissions'])
    
    # Data rows
    for item in report.items:
        writer.writerow([
            item.agent_id,
            item.agent_name,
            item.total_deliveries,
            item.successful,
            item.failed,
            item.success_rate,
            item.rating,
            item.cod_collected,
            item.commissions_earned
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="agent_report_{start_date}_{end_date}.csv"'
        }
    )


# ==================== EXCEL EXPORT ENDPOINTS ====================

@router.get("/export/sales/excel")
async def export_sales_excel(
    start_date: date = Query(...),
    end_date: date = Query(...),
    branch_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export sales report as Excel (XLSX)"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get the report data
    report = await get_sales_report(start_date, end_date, branch_id, current_user, db)
    
    # Convert to dict for export utility
    report_dict = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'total_orders': report.total_orders,
        'total_revenue': report.total_revenue,
        'total_delivery_fees': report.total_delivery_fees,
        'total_cod': report.total_cod,
        'average_order_value': report.average_order_value,
        'items': [
            {
                'date': item.date,
                'orders': item.orders,
                'revenue': item.revenue,
                'delivery_fees': item.delivery_fees,
                'cod_collected': item.cod_collected
            }
            for item in report.items
        ]
    }
    
    # Get business name
    business_name = current_user.business.name if current_user.business else "ParcelFlow"
    
    # Generate Excel
    excel_bytes = create_sales_excel(report_dict, business_name)
    
    return Response(
        content=excel_bytes,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename="sales_report_{start_date}_{end_date}.xlsx"'
        }
    )


@router.get("/export/deliveries/excel")
async def export_deliveries_excel(
    start_date: date = Query(...),
    end_date: date = Query(...),
    agent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export delivery performance report as Excel (XLSX)"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get the report data
    report = await get_delivery_report(start_date, end_date, agent_id, current_user, db)
    
    # Convert to dict for export utility
    report_dict = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'total_deliveries': report.total_deliveries,
        'total_successful': report.total_successful,
        'total_failed': report.total_failed,
        'overall_success_rate': report.overall_success_rate,
        'average_delivery_time_hours': report.average_delivery_time_hours,
        'items': [
            {
                'date': item.date,
                'total': item.total,
                'delivered': item.delivered,
                'failed': item.failed,
                'returned': item.returned,
                'success_rate': item.success_rate
            }
            for item in report.items
        ]
    }
    
    business_name = current_user.business.name if current_user.business else "ParcelFlow"
    excel_bytes = create_delivery_excel(report_dict, business_name)
    
    return Response(
        content=excel_bytes,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename="delivery_report_{start_date}_{end_date}.xlsx"'
        }
    )


@router.get("/export/agents/excel")
async def export_agents_excel(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export agent performance report as Excel (XLSX)"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    report = await get_agent_performance_report(start_date, end_date, current_user, db)
    
    report_dict = {
        'period_start': report.period_start.isoformat(),
        'period_end': report.period_end.isoformat(),
        'items': [
            {
                'agent_name': item.agent_name,
                'total_deliveries': item.total_deliveries,
                'successful': item.successful,
                'failed': item.failed,
                'success_rate': item.success_rate,
                'rating': item.rating,
                'cod_collected': item.cod_collected,
                'commissions_earned': item.commissions_earned
            }
            for item in report.items
        ]
    }
    
    business_name = current_user.business.name if current_user.business else "ParcelFlow"
    excel_bytes = create_agent_excel(report_dict, business_name)
    
    return Response(
        content=excel_bytes,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename="agent_report_{start_date}_{end_date}.xlsx"'
        }
    )


@router.get("/export/vendors/excel")
async def export_vendors_excel(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export vendor settlement report as Excel (XLSX)"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    report = await get_vendor_settlement_report(start_date, end_date, current_user, db)
    
    report_dict = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'total_commissions': report.total_commissions,
        'total_due': report.total_due,
        'total_paid': report.total_paid,
        'items': [
            {
                'vendor_name': item.vendor_name,
                'total_orders': item.total_orders,
                'total_value': item.total_value,
                'commission_rate': item.commission_rate,
                'commission_amount': item.commission_amount,
                'amount_due': item.amount_due,
                'amount_paid': item.amount_paid,
                'balance': item.balance
            }
            for item in report.items
        ]
    }
    
    business_name = current_user.business.name if current_user.business else "ParcelFlow"
    excel_bytes = create_vendor_excel(report_dict, business_name)
    
    return Response(
        content=excel_bytes,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename="vendor_report_{start_date}_{end_date}.xlsx"'
        }
    )


@router.get("/export/expenses/excel")
async def export_expenses_excel(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export expense report as Excel (XLSX)"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    report = await get_expense_report(start_date, end_date, current_user, db)
    
    report_dict = {
        'period_start': report.period_start.isoformat(),
        'period_end': report.period_end.isoformat(),
        'total_expenses': report.total_expenses,
        'items': [
            {
                'category': item.category,
                'total_amount': item.total_amount,
                'count': item.count,
                'percentage': item.percentage
            }
            for item in report.items
        ]
    }
    
    business_name = current_user.business.name if current_user.business else "ParcelFlow"
    excel_bytes = create_expense_excel(report_dict, business_name)
    
    return Response(
        content=excel_bytes,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={
            'Content-Disposition': f'attachment; filename="expense_report_{start_date}_{end_date}.xlsx"'
        }
    )


# ==================== PDF EXPORT ENDPOINTS ====================

@router.get("/export/sales/pdf")
async def export_sales_pdf(
    start_date: date = Query(...),
    end_date: date = Query(...),
    branch_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export sales report as PDF"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    report = await get_sales_report(start_date, end_date, branch_id, current_user, db)
    
    report_dict = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'total_orders': report.total_orders,
        'total_revenue': report.total_revenue,
        'total_delivery_fees': report.total_delivery_fees,
        'total_cod': report.total_cod,
        'average_order_value': report.average_order_value,
        'items': [
            {
                'date': item.date,
                'orders': item.orders,
                'revenue': item.revenue,
                'delivery_fees': item.delivery_fees,
                'cod_collected': item.cod_collected
            }
            for item in report.items
        ]
    }
    
    business_name = current_user.business.name if current_user.business else "ParcelFlow"
    
    pdf_exporter = PDFExporter()
    pdf_bytes = pdf_exporter.generate_sales_report(report_dict, business_name)
    
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="sales_report_{start_date}_{end_date}.pdf"'
        }
    )


@router.get("/export/deliveries/pdf")
async def export_deliveries_pdf(
    start_date: date = Query(...),
    end_date: date = Query(...),
    agent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export delivery performance report as PDF"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    report = await get_delivery_report(start_date, end_date, agent_id, current_user, db)
    
    report_dict = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'total_deliveries': report.total_deliveries,
        'total_successful': report.total_successful,
        'total_failed': report.total_failed,
        'overall_success_rate': report.overall_success_rate,
        'average_delivery_time_hours': report.average_delivery_time_hours,
        'items': [
            {
                'date': item.date,
                'total': item.total,
                'delivered': item.delivered,
                'failed': item.failed,
                'returned': item.returned,
                'success_rate': item.success_rate
            }
            for item in report.items
        ]
    }
    
    business_name = current_user.business.name if current_user.business else "ParcelFlow"
    
    pdf_exporter = PDFExporter()
    pdf_bytes = pdf_exporter.generate_delivery_report(report_dict, business_name)
    
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="delivery_report_{start_date}_{end_date}.pdf"'
        }
    )


@router.get("/export/agents/pdf")
async def export_agents_pdf(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export agent performance report as PDF"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    report = await get_agent_performance_report(start_date, end_date, current_user, db)
    
    report_dict = {
        'period_start': report.period_start.isoformat(),
        'period_end': report.period_end.isoformat(),
        'items': [
            {
                'agent_name': item.agent_name,
                'total_deliveries': item.total_deliveries,
                'successful': item.successful,
                'failed': item.failed,
                'success_rate': item.success_rate,
                'rating': item.rating,
                'cod_collected': item.cod_collected,
                'commissions_earned': item.commissions_earned
            }
            for item in report.items
        ]
    }
    
    business_name = current_user.business.name if current_user.business else "ParcelFlow"
    
    pdf_exporter = PDFExporter()
    pdf_bytes = pdf_exporter.generate_agent_report(report_dict, business_name)
    
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="agent_report_{start_date}_{end_date}.pdf"'
        }
    )


@router.get("/export/vendors/pdf")
async def export_vendors_pdf(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export vendor settlement report as PDF"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    report = await get_vendor_settlement_report(start_date, end_date, current_user, db)
    
    report_dict = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'total_commissions': report.total_commissions,
        'total_due': report.total_due,
        'total_paid': report.total_paid,
        'items': [
            {
                'vendor_name': item.vendor_name,
                'total_orders': item.total_orders,
                'total_value': item.total_value,
                'commission_rate': item.commission_rate,
                'commission_amount': item.commission_amount,
                'amount_due': item.amount_due,
                'amount_paid': item.amount_paid,
                'balance': item.balance
            }
            for item in report.items
        ]
    }
    
    business_name = current_user.business.name if current_user.business else "ParcelFlow"
    
    pdf_exporter = PDFExporter()
    pdf_bytes = pdf_exporter.generate_vendor_report(report_dict, business_name)
    
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="vendor_report_{start_date}_{end_date}.pdf"'
        }
    )


@router.get("/export/expenses/pdf")
async def export_expenses_pdf(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export expense report as PDF"""
    if not current_user.has_permission("reports.export"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    report = await get_expense_report(start_date, end_date, current_user, db)
    
    report_dict = {
        'period_start': report.period_start.isoformat(),
        'period_end': report.period_end.isoformat(),
        'total_expenses': report.total_expenses,
        'items': [
            {
                'category': item.category,
                'total_amount': item.total_amount,
                'count': item.count,
                'percentage': item.percentage
            }
            for item in report.items
        ]
    }
    
    business_name = current_user.business.name if current_user.business else "ParcelFlow"
    
    pdf_exporter = PDFExporter()
    pdf_bytes = pdf_exporter.generate_expense_report(report_dict, business_name)
    
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="expense_report_{start_date}_{end_date}.pdf"'
        }
    )
