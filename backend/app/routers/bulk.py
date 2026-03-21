"""
Bulk Operations Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional, List
import csv
import io
import json
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.waybill import Waybill, WaybillStatus, ShipmentType, PaymentType
from app.models.order import Order, OrderStatus, PaymentStatus, PaymentMethod
from app.models.agent import LogisticAgent, AgentStatus, VehicleType
from app.models.dispatch import Dispatch, DispatchStatus
from app.models.tracking import TrackingEvent
from app.schemas.bulk import (
    BulkStatusUpdateRequest, BulkDispatchAssignRequest,
    BulkImportWaybillRequest, BulkImportOrderRequest, BulkImportAgentRequest,
    BulkOperationResponse, BulkOperationResult, BulkExportRequest
)
from app.utils.auth import get_current_user

router = APIRouter()


# ============== BULK STATUS UPDATES ==============

@router.post("/waybills/status", response_model=BulkOperationResponse)
async def bulk_update_waybill_status(
    request: BulkStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update status for multiple waybills"""
    if not current_user.has_permission("orders.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    results = []
    success_count = 0
    
    # Validate status
    valid_statuses = [s.value for s in WaybillStatus]
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid values: {valid_statuses}")
    
    for waybill_id in request.ids:
        try:
            query = db.query(Waybill).filter(Waybill.id == waybill_id)
            
            if not current_user.has_role("super_admin"):
                if current_user.business_id:
                    query = query.filter(Waybill.business_id == current_user.business_id)
            
            waybill = query.first()
            
            if not waybill:
                results.append(BulkOperationResult(
                    id=waybill_id,
                    success=False,
                    error="Waybill not found"
                ))
                continue
            
            old_status = waybill.status.value
            waybill.status = WaybillStatus(request.status)
            
            # Create tracking event
            status_titles = {
                "pickup_scheduled": "Pickup Scheduled",
                "picked_up": "Picked Up",
                "at_warehouse": "Arrived at Warehouse",
                "out_for_delivery": "Out for Delivery",
                "delivered": "Delivered",
                "failed": "Delivery Failed",
                "returned": "Returned",
                "cancelled": "Cancelled"
            }
            
            tracking = TrackingEvent(
                waybill_id=waybill.id,
                status=request.status,
                title=status_titles.get(request.status, request.status.replace("_", " ").title()),
                description=request.notes or f"Status updated from {old_status} to {request.status} (bulk update)",
                is_public=1
            )
            db.add(tracking)
            
            results.append(BulkOperationResult(
                id=waybill_id,
                identifier=waybill.waybill_number,
                success=True
            ))
            success_count += 1
            
        except Exception as e:
            results.append(BulkOperationResult(
                id=waybill_id,
                success=False,
                error=str(e)
            ))
    
    db.commit()
    
    return BulkOperationResponse(
        success=success_count > 0,
        total_requested=len(request.ids),
        success_count=success_count,
        failure_count=len(request.ids) - success_count,
        results=results,
        message=f"Updated {success_count} of {len(request.ids)} waybills"
    )


@router.post("/orders/status", response_model=BulkOperationResponse)
async def bulk_update_order_status(
    request: BulkStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update status for multiple orders"""
    if not current_user.has_permission("orders.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    results = []
    success_count = 0
    
    # Validate status
    valid_statuses = [s.value for s in OrderStatus]
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid values: {valid_statuses}")
    
    for order_id in request.ids:
        try:
            query = db.query(Order).filter(Order.id == order_id)
            
            if not current_user.has_role("super_admin"):
                if current_user.business_id:
                    query = query.filter(Order.business_id == current_user.business_id)
            
            order = query.first()
            
            if not order:
                results.append(BulkOperationResult(
                    id=order_id,
                    success=False,
                    error="Order not found"
                ))
                continue
            
            order.status = OrderStatus(request.status)
            
            if request.notes:
                order.notes = f"{order.notes or ''}\n{request.notes}".strip()
            
            results.append(BulkOperationResult(
                id=order_id,
                identifier=order.order_number,
                success=True
            ))
            success_count += 1
            
        except Exception as e:
            results.append(BulkOperationResult(
                id=order_id,
                success=False,
                error=str(e)
            ))
    
    db.commit()
    
    return BulkOperationResponse(
        success=success_count > 0,
        total_requested=len(request.ids),
        success_count=success_count,
        failure_count=len(request.ids) - success_count,
        results=results,
        message=f"Updated {success_count} of {len(request.ids)} orders"
    )


@router.post("/dispatches/assign", response_model=BulkOperationResponse)
async def bulk_assign_dispatches(
    request: BulkDispatchAssignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign multiple dispatches to an agent"""
    if not current_user.has_permission("deliveries.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    results = []
    success_count = 0
    
    # Verify agent exists and belongs to user's business
    agent_query = db.query(LogisticAgent).filter(LogisticAgent.id == request.agent_id)
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            agent_query = agent_query.filter(LogisticAgent.business_id == current_user.business_id)
    
    agent = agent_query.first()
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not found")
    
    for dispatch_id in request.dispatch_ids:
        try:
            query = db.query(Dispatch).filter(Dispatch.id == dispatch_id)
            
            dispatch = query.first()
            
            if not dispatch:
                results.append(BulkOperationResult(
                    id=dispatch_id,
                    success=False,
                    error="Dispatch not found"
                ))
                continue
            
            # Verify waybill belongs to user's business
            waybill = db.query(Waybill).filter(Waybill.id == dispatch.waybill_id).first()
            if not current_user.has_role("super_admin"):
                if not waybill or waybill.business_id != current_user.business_id:
                    results.append(BulkOperationResult(
                        id=dispatch_id,
                        success=False,
                        error="Access denied"
                    ))
                    continue
            
            dispatch.agent_id = request.agent_id
            if dispatch.status == DispatchStatus.ASSIGNED:
                dispatch.status = DispatchStatus.ASSIGNED
            
            results.append(BulkOperationResult(
                id=dispatch_id,
                identifier=waybill.waybill_number if waybill else None,
                success=True
            ))
            success_count += 1
            
        except Exception as e:
            results.append(BulkOperationResult(
                id=dispatch_id,
                success=False,
                error=str(e)
            ))
    
    db.commit()
    
    return BulkOperationResponse(
        success=success_count > 0,
        total_requested=len(request.dispatch_ids),
        success_count=success_count,
        failure_count=len(request.dispatch_ids) - success_count,
        results=results,
        message=f"Assigned {success_count} of {len(request.dispatch_ids)} dispatches to {agent.name}"
    )


# ============== BULK IMPORT ==============

@router.post("/waybills/import", response_model=BulkOperationResponse)
async def bulk_import_waybills(
    request: BulkImportWaybillRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import waybills from JSON data"""
    if not current_user.has_permission("orders.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if not current_user.business_id:
        raise HTTPException(status_code=400, detail="User must be associated with a business")
    
    results = []
    success_count = 0
    
    for item in request.waybills:
        try:
            # Generate waybill number
            branch_code = None
            if request.branch_id:
                from app.models.branch import Branch
                branch = db.query(Branch).filter(Branch.id == request.branch_id).first()
                branch_code = branch.code if branch else None
            
            waybill_number = Waybill.generate_waybill_number(branch_code)
            
            # Validate payment type
            try:
                payment_type = PaymentType(item.payment_type)
            except ValueError:
                payment_type = PaymentType.COD
            
            # Validate shipment type
            try:
                shipment_type = ShipmentType(item.shipment_type)
            except ValueError:
                shipment_type = ShipmentType.WAREHOUSE_DELIVERY
            
            waybill = Waybill(
                business_id=current_user.business_id,
                branch_id=request.branch_id,
                waybill_number=waybill_number,
                shipment_type=shipment_type,
                sender_name=item.sender_name,
                sender_phone=item.sender_phone,
                sender_email=item.sender_email,
                sender_address=item.sender_address,
                sender_city=item.sender_city,
                receiver_name=item.receiver_name,
                receiver_phone=item.receiver_phone,
                receiver_email=item.receiver_email,
                receiver_address=item.receiver_address,
                receiver_city=item.receiver_city,
                receiver_landmark=item.receiver_landmark,
                item_description=item.item_description,
                quantity=item.quantity,
                weight=item.weight,
                declared_value=item.declared_value,
                delivery_fee=item.delivery_fee,
                total_amount=item.delivery_fee,
                payment_type=payment_type,
                cod_amount=item.cod_amount,
                vendor_id=item.vendor_id,
                notes=item.notes
            )
            
            db.add(waybill)
            db.flush()
            
            # Create tracking event
            tracking = TrackingEvent(
                waybill_id=waybill.id,
                status="created",
                title="Waybill Created",
                description=f"Waybill {waybill_number} has been created via bulk import",
                is_public=1
            )
            db.add(tracking)
            
            results.append(BulkOperationResult(
                id=waybill.id,
                identifier=waybill_number,
                success=True
            ))
            success_count += 1
            
        except Exception as e:
            results.append(BulkOperationResult(
                identifier=f"{item.sender_name} -> {item.receiver_name}",
                success=False,
                error=str(e)
            ))
    
    db.commit()
    
    return BulkOperationResponse(
        success=success_count > 0,
        total_requested=len(request.waybills),
        success_count=success_count,
        failure_count=len(request.waybills) - success_count,
        results=results,
        message=f"Imported {success_count} of {len(request.waybills)} waybills"
    )


@router.post("/orders/import", response_model=BulkOperationResponse)
async def bulk_import_orders(
    request: BulkImportOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import orders from JSON data"""
    if not current_user.has_permission("orders.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if not current_user.business_id:
        raise HTTPException(status_code=400, detail="User must be associated with a business")
    
    results = []
    success_count = 0
    
    for item in request.orders:
        try:
            order_number = Order.generate_order_number()
            
            # Validate payment method
            try:
                payment_method = PaymentMethod(item.payment_method)
            except ValueError:
                payment_method = PaymentMethod.COD
            
            total_amount = item.subtotal + item.delivery_fee + item.tax - item.discount
            
            order = Order(
                business_id=current_user.business_id,
                branch_id=request.branch_id,
                order_number=order_number,
                customer_name=item.customer_name,
                customer_phone=item.customer_phone,
                customer_email=item.customer_email,
                delivery_address=item.delivery_address,
                delivery_city=item.delivery_city,
                delivery_state=item.delivery_state,
                delivery_landmark=item.delivery_landmark,
                subtotal=item.subtotal,
                delivery_fee=item.delivery_fee,
                discount=item.discount,
                tax=item.tax,
                total_amount=total_amount,
                payment_method=payment_method,
                notes=item.notes,
                source="bulk_import",
                created_by_user_id=current_user.id
            )
            
            db.add(order)
            db.flush()
            
            # Create order items if provided
            for item_data in item.items:
                from app.models.order import OrderItem
                order_item = OrderItem(
                    order_id=order.id,
                    product_name=item_data.get('product_name', 'Unknown'),
                    product_sku=item_data.get('product_sku'),
                    quantity=item_data.get('quantity', 1),
                    unit_price=item_data.get('unit_price', 0),
                    discount=item_data.get('discount', 0),
                    total=item_data.get('quantity', 1) * item_data.get('unit_price', 0) - item_data.get('discount', 0)
                )
                db.add(order_item)
            
            results.append(BulkOperationResult(
                id=order.id,
                identifier=order_number,
                success=True
            ))
            success_count += 1
            
        except Exception as e:
            results.append(BulkOperationResult(
                identifier=f"{item.customer_name} - {item.customer_phone}",
                success=False,
                error=str(e)
            ))
    
    db.commit()
    
    return BulkOperationResponse(
        success=success_count > 0,
        total_requested=len(request.orders),
        success_count=success_count,
        failure_count=len(request.orders) - success_count,
        results=results,
        message=f"Imported {success_count} of {len(request.orders)} orders"
    )


@router.post("/agents/import", response_model=BulkOperationResponse)
async def bulk_import_agents(
    request: BulkImportAgentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import agents from JSON data"""
    if not current_user.has_permission("settings.manage"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if not current_user.business_id:
        raise HTTPException(status_code=400, detail="User must be associated with a business")
    
    results = []
    success_count = 0
    
    for item in request.agents:
        try:
            # Validate status
            try:
                agent_status = AgentStatus(item.status)
            except ValueError:
                agent_status = AgentStatus.AVAILABLE
            
            # Validate vehicle type
            try:
                vehicle_type = VehicleType(item.vehicle_type)
            except ValueError:
                vehicle_type = VehicleType.BIKE
            
            agent = LogisticAgent(
                business_id=current_user.business_id,
                branch_id=item.branch_id,
                name=item.name,
                phone=item.phone,
                email=item.email,
                employee_id=item.employee_id,
                national_id=item.national_id,
                vehicle_type=vehicle_type,
                status=agent_status,
                notes=item.notes
            )
            
            db.add(agent)
            db.flush()
            
            results.append(BulkOperationResult(
                id=agent.id,
                identifier=item.name,
                success=True
            ))
            success_count += 1
            
        except Exception as e:
            results.append(BulkOperationResult(
                identifier=item.name,
                success=False,
                error=str(e)
            ))
    
    db.commit()
    
    return BulkOperationResponse(
        success=success_count > 0,
        total_requested=len(request.agents),
        success_count=success_count,
        failure_count=len(request.agents) - success_count,
        results=results,
        message=f"Imported {success_count} of {len(request.agents)} agents"
    )


# ============== CSV IMPORT ENDPOINTS ==============

@router.post("/waybills/import-csv", response_model=BulkOperationResponse)
async def bulk_import_waybills_csv(
    file: UploadFile = File(...),
    branch_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import waybills from CSV file"""
    if not current_user.has_permission("orders.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if not current_user.business_id:
        raise HTTPException(status_code=400, detail="User must be associated with a business")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    decoded = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    results = []
    success_count = 0
    
    for row in reader:
        try:
            branch_code = None
            if branch_id:
                from app.models.branch import Branch
                branch = db.query(Branch).filter(Branch.id == branch_id).first()
                branch_code = branch.code if branch else None
            
            waybill_number = Waybill.generate_waybill_number(branch_code)
            
            waybill = Waybill(
                business_id=current_user.business_id,
                branch_id=branch_id,
                waybill_number=waybill_number,
                shipment_type=ShipmentType(row.get('shipment_type', 'warehouse_delivery')),
                sender_name=row.get('sender_name', ''),
                sender_phone=row.get('sender_phone', ''),
                sender_email=row.get('sender_email'),
                sender_address=row.get('sender_address'),
                sender_city=row.get('sender_city'),
                receiver_name=row.get('receiver_name', ''),
                receiver_phone=row.get('receiver_phone', ''),
                receiver_email=row.get('receiver_email'),
                receiver_address=row.get('receiver_address', ''),
                receiver_city=row.get('receiver_city'),
                receiver_landmark=row.get('receiver_landmark'),
                item_description=row.get('item_description'),
                quantity=int(row.get('quantity', 1)),
                weight=float(row.get('weight')) if row.get('weight') else None,
                declared_value=float(row.get('declared_value', 0)),
                delivery_fee=float(row.get('delivery_fee', 0)),
                total_amount=float(row.get('delivery_fee', 0)),
                payment_type=PaymentType(row.get('payment_type', 'cod')),
                cod_amount=float(row.get('cod_amount', 0)),
                notes=row.get('notes')
            )
            
            db.add(waybill)
            db.flush()
            
            tracking = TrackingEvent(
                waybill_id=waybill.id,
                status="created",
                title="Waybill Created",
                description=f"Waybill {waybill_number} has been created via CSV import",
                is_public=1
            )
            db.add(tracking)
            
            results.append(BulkOperationResult(
                id=waybill.id,
                identifier=waybill_number,
                success=True
            ))
            success_count += 1
            
        except Exception as e:
            results.append(BulkOperationResult(
                identifier=row.get('sender_name', 'Unknown'),
                success=False,
                error=str(e)
            ))
    
    db.commit()
    
    return BulkOperationResponse(
        success=success_count > 0,
        total_requested=len(results),
        success_count=success_count,
        failure_count=len(results) - success_count,
        results=results,
        message=f"Imported {success_count} of {len(results)} waybills from CSV"
    )


@router.post("/orders/import-csv", response_model=BulkOperationResponse)
async def bulk_import_orders_csv(
    file: UploadFile = File(...),
    branch_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import orders from CSV file"""
    if not current_user.has_permission("orders.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if not current_user.business_id:
        raise HTTPException(status_code=400, detail="User must be associated with a business")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    decoded = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    results = []
    success_count = 0
    
    for row in reader:
        try:
            order_number = Order.generate_order_number()
            
            subtotal = float(row.get('subtotal', 0))
            delivery_fee = float(row.get('delivery_fee', 0))
            discount = float(row.get('discount', 0))
            tax = float(row.get('tax', 0))
            
            order = Order(
                business_id=current_user.business_id,
                branch_id=branch_id,
                order_number=order_number,
                customer_name=row.get('customer_name', ''),
                customer_phone=row.get('customer_phone', ''),
                customer_email=row.get('customer_email'),
                delivery_address=row.get('delivery_address', ''),
                delivery_city=row.get('delivery_city'),
                delivery_state=row.get('delivery_state'),
                delivery_landmark=row.get('delivery_landmark'),
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                discount=discount,
                tax=tax,
                total_amount=subtotal + delivery_fee + tax - discount,
                payment_method=PaymentMethod(row.get('payment_method', 'cod')),
                notes=row.get('notes'),
                source="csv_import",
                created_by_user_id=current_user.id
            )
            
            db.add(order)
            db.flush()
            
            results.append(BulkOperationResult(
                id=order.id,
                identifier=order_number,
                success=True
            ))
            success_count += 1
            
        except Exception as e:
            results.append(BulkOperationResult(
                identifier=row.get('customer_name', 'Unknown'),
                success=False,
                error=str(e)
            ))
    
    db.commit()
    
    return BulkOperationResponse(
        success=success_count > 0,
        total_requested=len(results),
        success_count=success_count,
        failure_count=len(results) - success_count,
        results=results,
        message=f"Imported {success_count} of {len(results)} orders from CSV"
    )


@router.post("/agents/import-csv", response_model=BulkOperationResponse)
async def bulk_import_agents_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import agents from CSV file"""
    if not current_user.has_permission("settings.manage"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if not current_user.business_id:
        raise HTTPException(status_code=400, detail="User must be associated with a business")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    content = await file.read()
    decoded = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    
    results = []
    success_count = 0
    
    for row in reader:
        try:
            agent = LogisticAgent(
                business_id=current_user.business_id,
                name=row.get('name', ''),
                phone=row.get('phone'),
                email=row.get('email'),
                employee_id=row.get('employee_id'),
                national_id=row.get('national_id'),
                vehicle_type=VehicleType(row.get('vehicle_type', 'bike')),
                status=AgentStatus(row.get('status', 'available')),
                notes=row.get('notes')
            )
            
            db.add(agent)
            db.flush()
            
            results.append(BulkOperationResult(
                id=agent.id,
                identifier=agent.name,
                success=True
            ))
            success_count += 1
            
        except Exception as e:
            results.append(BulkOperationResult(
                identifier=row.get('name', 'Unknown'),
                success=False,
                error=str(e)
            ))
    
    db.commit()
    
    return BulkOperationResponse(
        success=success_count > 0,
        total_requested=len(results),
        success_count=success_count,
        failure_count=len(results) - success_count,
        results=results,
        message=f"Imported {success_count} of {len(results)} agents from CSV"
    )


# ============== CSV EXPORT ==============

@router.get("/waybills/export")
async def export_waybills(
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export waybills to CSV"""
    query = db.query(Waybill)
    
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(Waybill.business_id == current_user.business_id)
    
    if status:
        query = query.filter(Waybill.status == status)
    if branch_id:
        query = query.filter(Waybill.branch_id == branch_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Waybill.waybill_number.ilike(search_term)) |
            (Waybill.receiver_name.ilike(search_term)) |
            (Waybill.receiver_phone.ilike(search_term))
        )
    
    waybills = query.order_by(Waybill.created_at.desc()).limit(1000).all()
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'waybill_number', 'status', 'shipment_type', 'payment_type',
        'sender_name', 'sender_phone', 'sender_address', 'sender_city',
        'receiver_name', 'receiver_phone', 'receiver_address', 'receiver_city',
        'item_description', 'quantity', 'weight', 'declared_value',
        'delivery_fee', 'cod_amount', 'total_amount', 'created_at'
    ])
    
    # Data
    for w in waybills:
        writer.writerow([
            w.waybill_number, w.status.value, w.shipment_type.value, w.payment_type.value,
            w.sender_name, w.sender_phone, w.sender_address, w.sender_city,
            w.receiver_name, w.receiver_phone, w.receiver_address, w.receiver_city,
            w.item_description, w.quantity, str(w.weight) if w.weight else '',
            str(w.declared_value) if w.declared_value else '',
            str(w.delivery_fee) if w.delivery_fee else '',
            str(w.cod_amount) if w.cod_amount else '',
            str(w.total_amount) if w.total_amount else '',
            str(w.created_at) if w.created_at else ''
        ])
    
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=waybills_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@router.get("/orders/export")
async def export_orders(
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export orders to CSV"""
    query = db.query(Order)
    
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(Order.business_id == current_user.business_id)
    
    if status:
        query = query.filter(Order.status == status)
    if branch_id:
        query = query.filter(Order.branch_id == branch_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Order.order_number.ilike(search_term)) |
            (Order.customer_name.ilike(search_term)) |
            (Order.customer_phone.ilike(search_term))
        )
    
    orders = query.order_by(Order.created_at.desc()).limit(1000).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'order_number', 'status', 'payment_status', 'payment_method',
        'customer_name', 'customer_phone', 'customer_email',
        'delivery_address', 'delivery_city', 'delivery_state',
        'subtotal', 'delivery_fee', 'discount', 'tax', 'total_amount',
        'created_at'
    ])
    
    for o in orders:
        writer.writerow([
            o.order_number, o.status.value, o.payment_status.value, o.payment_method.value,
            o.customer_name, o.customer_phone, o.customer_email,
            o.delivery_address, o.delivery_city, o.delivery_state,
            str(o.subtotal) if o.subtotal else '',
            str(o.delivery_fee) if o.delivery_fee else '',
            str(o.discount) if o.discount else '',
            str(o.tax) if o.tax else '',
            str(o.total_amount) if o.total_amount else '',
            str(o.created_at) if o.created_at else ''
        ])
    
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@router.get("/dispatches/export")
async def export_dispatches(
    status: Optional[str] = None,
    agent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export dispatches to CSV"""
    query = db.query(Dispatch).join(Waybill)
    
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(Waybill.business_id == current_user.business_id)
    
    if status:
        query = query.filter(Dispatch.status == DispatchStatus(status))
    if agent_id:
        query = query.filter(Dispatch.agent_id == agent_id)
    
    dispatches = query.order_by(Dispatch.created_at.desc()).limit(1000).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'dispatch_id', 'waybill_number', 'status', 'agent_name',
        'receiver_name', 'receiver_phone', 'receiver_address', 'receiver_city',
        'dispatched_at', 'attempt_count', 'cod_amount', 'distance_km'
    ])
    
    for d in dispatches:
        waybill = d.waybill
        agent_name = None
        if d.agent_id:
            agent = db.query(LogisticAgent).filter(LogisticAgent.id == d.agent_id).first()
            agent_name = agent.name if agent else None
        
        writer.writerow([
            d.id, waybill.waybill_number if waybill else '', d.status.value, agent_name or '',
            waybill.receiver_name if waybill else '',
            waybill.receiver_phone if waybill else '',
            waybill.receiver_address if waybill else '',
            waybill.receiver_city if waybill else '',
            str(d.dispatched_at) if d.dispatched_at else '',
            d.attempt_count,
            str(waybill.cod_amount) if waybill and waybill.cod_amount else '',
            str(d.distance_km) if d.distance_km else ''
        ])
    
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=dispatches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )
