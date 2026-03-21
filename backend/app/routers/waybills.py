"""
Waybills Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.waybill import Waybill, WaybillStatus, ShipmentType
from app.models.tracking import TrackingEvent
from app.schemas.waybill import (
    WaybillCreate, WaybillUpdate, WaybillResponse, 
    WaybillListResponse, WaybillStatusUpdate
)
from app.utils.auth import get_current_user
from app.utils.notifications import (
    notify_waybill_created, notify_waybill_dispatched,
    notify_waybill_delivered, notify_waybill_failed
)
from app.services.audit import AuditService

router = APIRouter()


@router.get("", response_model=WaybillListResponse)
async def list_waybills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    shipment_type: Optional[str] = None,
    branch_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List waybills with filters"""
    query = db.query(Waybill)
    
    # Super admins can see all waybills, others are filtered by business
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(Waybill.business_id == current_user.business_id)
        else:
            # User without business - return empty
            return WaybillListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)
    
    if status:
        query = query.filter(Waybill.status == status)
    if shipment_type:
        query = query.filter(Waybill.shipment_type == shipment_type)
    if branch_id:
        query = query.filter(Waybill.branch_id == branch_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Waybill.waybill_number.ilike(search_term)) |
            (Waybill.receiver_name.ilike(search_term)) |
            (Waybill.receiver_phone.ilike(search_term))
        )
    
    total = query.count()
    offset = (page - 1) * page_size
    waybills = query.order_by(Waybill.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = [WaybillResponse(
        id=w.id, waybill_number=w.waybill_number, business_id=w.business_id,
        branch_id=w.branch_id, shipment_type=w.shipment_type.value,
        payment_type=w.payment_type.value,
        sender_name=w.sender_name, sender_phone=w.sender_phone,
        sender_email=w.sender_email, sender_address=w.sender_address,
        sender_city=w.sender_city,
        receiver_name=w.receiver_name, receiver_phone=w.receiver_phone,
        receiver_email=w.receiver_email, receiver_address=w.receiver_address,
        receiver_city=w.receiver_city, receiver_landmark=w.receiver_landmark,
        item_description=w.item_description, quantity=w.quantity,
        weight=w.weight, dimensions=w.dimensions,
        declared_value=w.declared_value, delivery_fee=w.delivery_fee,
        insurance_fee=w.insurance_fee, total_amount=w.total_amount,
        cod_amount=w.cod_amount, status=w.status.value,
        vendor_id=w.vendor_id, order_id=w.order_id,
        notes=w.notes, special_instructions=w.special_instructions,
        estimated_delivery_date=w.estimated_delivery_date,
        created_at=w.created_at, updated_at=w.updated_at
    ) for w in waybills]
    
    return WaybillListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=WaybillResponse, status_code=status.HTTP_201_CREATED)
async def create_waybill(
    request: WaybillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new waybill"""
    if not current_user.has_permission("orders.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Determine business_id
    business_id = current_user.business_id
    if not business_id:
        raise HTTPException(status_code=400, detail="User must be associated with a business")
    
    # Generate waybill number
    branch_code = None
    if request.branch_id:
        from app.models.branch import Branch
        branch = db.query(Branch).filter(Branch.id == request.branch_id).first()
        branch_code = branch.code if branch else None
    
    waybill_number = Waybill.generate_waybill_number(branch_code)
    
    waybill = Waybill(
        business_id=business_id,
        branch_id=request.branch_id,
        waybill_number=waybill_number,
        shipment_type=request.shipment_type,
        sender_name=request.sender_name,
        sender_phone=request.sender_phone,
        sender_email=request.sender_email,
        sender_address=request.sender_address,
        sender_city=request.sender_city,
        receiver_name=request.receiver_name,
        receiver_phone=request.receiver_phone,
        receiver_email=request.receiver_email,
        receiver_address=request.receiver_address,
        receiver_city=request.receiver_city,
        receiver_landmark=request.receiver_landmark,
        item_description=request.item_description,
        quantity=request.quantity,
        weight=request.weight,
        dimensions=request.dimensions,
        declared_value=request.declared_value,
        delivery_fee=request.delivery_fee,
        insurance_fee=request.insurance_fee,
        total_amount=request.total_amount,
        payment_type=request.payment_type,
        cod_amount=request.cod_amount,
        vendor_id=request.vendor_id,
        order_id=request.order_id,
        notes=request.notes,
        special_instructions=request.special_instructions,
        estimated_delivery_date=request.estimated_delivery_date
    )
    
    db.add(waybill)
    db.flush()
    
    # Create tracking event
    tracking = TrackingEvent(
        waybill_id=waybill.id,
        status="created",
        title="Waybill Created",
        description=f"Waybill {waybill_number} has been created",
        is_public=1
    )
    db.add(tracking)
    
    # Send notification for new waybill
    notify_waybill_created(
        db=db,
        business_id=business_id,
        waybill_id=waybill.id,
        waybill_number=waybill_number
    )
    
    # Create audit log
    audit = AuditService(db)
    audit.log_create(
        entity=waybill,
        user_id=current_user.id,
        business_id=business_id,
        description=f"Created waybill {waybill_number}"
    )
    
    db.commit()
    db.refresh(waybill)
    
    return WaybillResponse(
        id=waybill.id, waybill_number=waybill.waybill_number,
        business_id=waybill.business_id, branch_id=waybill.branch_id,
        shipment_type=waybill.shipment_type.value, payment_type=waybill.payment_type.value,
        sender_name=waybill.sender_name, sender_phone=waybill.sender_phone,
        sender_email=waybill.sender_email, sender_address=waybill.sender_address,
        sender_city=waybill.sender_city,
        receiver_name=waybill.receiver_name, receiver_phone=waybill.receiver_phone,
        receiver_email=waybill.receiver_email, receiver_address=waybill.receiver_address,
        receiver_city=waybill.receiver_city, receiver_landmark=waybill.receiver_landmark,
        item_description=waybill.item_description, quantity=waybill.quantity,
        weight=waybill.weight, dimensions=waybill.dimensions,
        declared_value=waybill.declared_value, delivery_fee=waybill.delivery_fee,
        insurance_fee=waybill.insurance_fee, total_amount=waybill.total_amount,
        cod_amount=waybill.cod_amount, status=waybill.status.value,
        vendor_id=waybill.vendor_id, order_id=waybill.order_id,
        notes=waybill.notes, special_instructions=waybill.special_instructions,
        estimated_delivery_date=waybill.estimated_delivery_date,
        created_at=waybill.created_at, updated_at=waybill.updated_at
    )


@router.get("/{waybill_id}", response_model=WaybillResponse)
async def get_waybill(
    waybill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get waybill by ID"""
    query = db.query(Waybill).filter(Waybill.id == waybill_id)
    
    # Super admins can access any waybill
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(Waybill.business_id == current_user.business_id)
        else:
            raise HTTPException(status_code=404, detail="Waybill not found")
    
    waybill = query.first()
    
    if not waybill:
        raise HTTPException(status_code=404, detail="Waybill not found")
    
    # Get tracking events
    events = db.query(TrackingEvent).filter(
        TrackingEvent.waybill_id == waybill.id
    ).order_by(TrackingEvent.created_at.desc()).all()
    
    from app.schemas.waybill import TrackingEventResponse
    tracking_events = [TrackingEventResponse(
        id=e.id, status=e.status, title=e.title, description=e.description,
        location=e.location, is_public=e.is_public, created_at=e.created_at
    ) for e in events]
    
    return WaybillResponse(
        id=waybill.id, waybill_number=waybill.waybill_number,
        business_id=waybill.business_id, branch_id=waybill.branch_id,
        shipment_type=waybill.shipment_type.value, payment_type=waybill.payment_type.value,
        sender_name=waybill.sender_name, sender_phone=waybill.sender_phone,
        sender_email=waybill.sender_email, sender_address=waybill.sender_address,
        sender_city=waybill.sender_city,
        receiver_name=waybill.receiver_name, receiver_phone=waybill.receiver_phone,
        receiver_email=waybill.receiver_email, receiver_address=waybill.receiver_address,
        receiver_city=waybill.receiver_city, receiver_landmark=waybill.receiver_landmark,
        item_description=waybill.item_description, quantity=waybill.quantity,
        weight=waybill.weight, dimensions=waybill.dimensions,
        declared_value=waybill.declared_value, delivery_fee=waybill.delivery_fee,
        insurance_fee=waybill.insurance_fee, total_amount=waybill.total_amount,
        cod_amount=waybill.cod_amount, status=waybill.status.value,
        vendor_id=waybill.vendor_id, order_id=waybill.order_id,
        notes=waybill.notes, special_instructions=waybill.special_instructions,
        estimated_delivery_date=waybill.estimated_delivery_date,
        created_at=waybill.created_at, updated_at=waybill.updated_at,
        tracking_events=tracking_events
    )


@router.put("/{waybill_id}", response_model=WaybillResponse)
async def update_waybill(
    waybill_id: int,
    request: WaybillUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update waybill details"""
    if not current_user.has_permission("orders.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    query = db.query(Waybill).filter(Waybill.id == waybill_id)
    
    # Super admins can access any waybill
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(Waybill.business_id == current_user.business_id)
        else:
            raise HTTPException(status_code=404, detail="Waybill not found")
    
    waybill = query.first()
    
    if not waybill:
        raise HTTPException(status_code=404, detail="Waybill not found")
    
    # Update fields
    if request.shipment_type:
        waybill.shipment_type = ShipmentType(request.shipment_type)
    if request.sender_name is not None:
        waybill.sender_name = request.sender_name
    if request.sender_phone is not None:
        waybill.sender_phone = request.sender_phone
    if request.sender_email is not None:
        waybill.sender_email = request.sender_email
    if request.sender_address is not None:
        waybill.sender_address = request.sender_address
    if request.sender_city is not None:
        waybill.sender_city = request.sender_city
    if request.receiver_name is not None:
        waybill.receiver_name = request.receiver_name
    if request.receiver_phone is not None:
        waybill.receiver_phone = request.receiver_phone
    if request.receiver_email is not None:
        waybill.receiver_email = request.receiver_email
    if request.receiver_address is not None:
        waybill.receiver_address = request.receiver_address
    if request.receiver_city is not None:
        waybill.receiver_city = request.receiver_city
    if request.receiver_landmark is not None:
        waybill.receiver_landmark = request.receiver_landmark
    if request.item_description is not None:
        waybill.item_description = request.item_description
    if request.quantity is not None:
        waybill.quantity = request.quantity
    if request.weight is not None:
        waybill.weight = request.weight
    if request.dimensions is not None:
        waybill.dimensions = request.dimensions
    if request.declared_value is not None:
        waybill.declared_value = request.declared_value
    if request.delivery_fee is not None:
        waybill.delivery_fee = request.delivery_fee
    if request.total_amount is not None:
        waybill.total_amount = request.total_amount
    if request.cod_amount is not None:
        waybill.cod_amount = request.cod_amount
    if request.payment_type:
        from app.models.waybill import PaymentType
        waybill.payment_type = PaymentType(request.payment_type)
    if request.notes is not None:
        waybill.notes = request.notes
    if request.special_instructions is not None:
        waybill.special_instructions = request.special_instructions
    
    waybill.updated_at = datetime.utcnow()
    
    # Create audit log
    audit = AuditService(db)
    audit.log_update(
        entity=waybill,
        user_id=current_user.id,
        business_id=waybill.business_id,
        description=f"Updated waybill {waybill.waybill_number}"
    )
    
    db.commit()
    db.refresh(waybill)
    
    return WaybillResponse(
        id=waybill.id, waybill_number=waybill.waybill_number,
        business_id=waybill.business_id, branch_id=waybill.branch_id,
        shipment_type=waybill.shipment_type.value, payment_type=waybill.payment_type.value,
        sender_name=waybill.sender_name, sender_phone=waybill.sender_phone,
        sender_email=waybill.sender_email, sender_address=waybill.sender_address,
        sender_city=waybill.sender_city,
        receiver_name=waybill.receiver_name, receiver_phone=waybill.receiver_phone,
        receiver_email=waybill.receiver_email, receiver_address=waybill.receiver_address,
        receiver_city=waybill.receiver_city, receiver_landmark=waybill.receiver_landmark,
        item_description=waybill.item_description, quantity=waybill.quantity,
        weight=waybill.weight, dimensions=waybill.dimensions,
        declared_value=waybill.declared_value, delivery_fee=waybill.delivery_fee,
        insurance_fee=waybill.insurance_fee, total_amount=waybill.total_amount,
        cod_amount=waybill.cod_amount, status=waybill.status.value,
        vendor_id=waybill.vendor_id, order_id=waybill.order_id,
        notes=waybill.notes, special_instructions=waybill.special_instructions,
        estimated_delivery_date=waybill.estimated_delivery_date,
        created_at=waybill.created_at, updated_at=waybill.updated_at
    )


@router.put("/{waybill_id}/status")
async def update_waybill_status(
    waybill_id: int,
    request: WaybillStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update waybill status"""
    if not current_user.has_permission("orders.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    query = db.query(Waybill).filter(Waybill.id == waybill_id)
    
    # Super admins can access any waybill
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(Waybill.business_id == current_user.business_id)
        else:
            raise HTTPException(status_code=404, detail="Waybill not found")
    
    waybill = query.first()
    
    if not waybill:
        raise HTTPException(status_code=404, detail="Waybill not found")
    
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
        "returned": "Returned"
    }
    
    tracking = TrackingEvent(
        waybill_id=waybill.id,
        status=request.status,
        title=status_titles.get(request.status, request.status.replace("_", " ").title()),
        description=request.notes or f"Status updated from {old_status} to {request.status}",
        location=request.location,
        is_public=1
    )
    db.add(tracking)
    
    # Send notifications based on status
    if request.status == "out_for_delivery":
        notify_waybill_dispatched(
            db=db,
            business_id=waybill.business_id,
            waybill_id=waybill.id,
            waybill_number=waybill.waybill_number
        )
    elif request.status == "delivered":
        notify_waybill_delivered(
            db=db,
            business_id=waybill.business_id,
            waybill_id=waybill.id,
            waybill_number=waybill.waybill_number
        )
    elif request.status == "failed":
        notify_waybill_failed(
            db=db,
            business_id=waybill.business_id,
            waybill_id=waybill.id,
            waybill_number=waybill.waybill_number,
            reason=request.notes
        )
    
    # Create audit log for status change
    audit = AuditService(db)
    audit.log_status_change(
        entity=waybill,
        old_status=old_status,
        new_status=request.status,
        user_id=current_user.id,
        business_id=waybill.business_id,
        description=f"Status changed from {old_status} to {request.status} for waybill {waybill.waybill_number}"
    )
    
    db.commit()
    
    return {"success": True, "message": "Status updated"}


@router.post("/{waybill_id}/cancel")
async def cancel_waybill(
    waybill_id: int,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a waybill"""
    if not current_user.has_permission("orders.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    query = db.query(Waybill).filter(Waybill.id == waybill_id)
    
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(Waybill.business_id == current_user.business_id)
        else:
            raise HTTPException(status_code=404, detail="Waybill not found")
    
    waybill = query.first()
    
    if not waybill:
        raise HTTPException(status_code=404, detail="Waybill not found")
    
    # Check if waybill can be cancelled
    non_cancellable_statuses = [
        WaybillStatus.DELIVERED, 
        WaybillStatus.CANCELLED,
        WaybillStatus.RETURNED
    ]
    
    if waybill.status in non_cancellable_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel waybill with status '{waybill.status.value}'"
        )
    
    # Update status
    old_status = waybill.status.value
    waybill.status = WaybillStatus.CANCELLED
    
    # Create tracking event
    tracking = TrackingEvent(
        waybill_id=waybill.id,
        status="cancelled",
        title="Waybill Cancelled",
        description=reason or f"Waybill cancelled from {old_status} status",
        is_public=1
    )
    db.add(tracking)
    
    # Create audit log
    audit = AuditService(db)
    audit.log_status_change(
        entity=waybill,
        old_status=old_status,
        new_status="cancelled",
        user_id=current_user.id,
        business_id=waybill.business_id,
        description=reason or f"Waybill {waybill.waybill_number} cancelled from {old_status} status"
    )
    
    db.commit()
    
    return {"success": True, "message": "Waybill cancelled successfully"}


@router.delete("/{waybill_id}")
async def delete_waybill(
    waybill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a waybill (soft delete by setting status to cancelled)"""
    if not current_user.has_permission("orders.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    query = db.query(Waybill).filter(Waybill.id == waybill_id)
    
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(Waybill.business_id == current_user.business_id)
        else:
            raise HTTPException(status_code=404, detail="Waybill not found")
    
    waybill = query.first()
    
    if not waybill:
        raise HTTPException(status_code=404, detail="Waybill not found")
    
    # Check if waybill can be deleted
    non_deletable_statuses = [
        WaybillStatus.DELIVERED, 
        WaybillStatus.OUT_FOR_DELIVERY,
        WaybillStatus.PICKED_UP
    ]
    
    if waybill.status in non_deletable_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete waybill with status '{waybill.status.value}'. Cancel it first."
        )
    
    # Soft delete - set status to cancelled
    old_status = waybill.status.value
    waybill.status = WaybillStatus.CANCELLED
    
    # Create tracking event
    tracking = TrackingEvent(
        waybill_id=waybill.id,
        status="deleted",
        title="Waybill Deleted",
        description=f"Waybill deleted from {old_status} status",
        is_public=0
    )
    db.add(tracking)
    
    # Create audit log
    audit = AuditService(db)
    audit.log_delete(
        entity=waybill,
        user_id=current_user.id,
        business_id=waybill.business_id,
        description=f"Waybill {waybill.waybill_number} deleted from {old_status} status"
    )
    
    db.commit()
    
    return {"success": True, "message": "Waybill deleted successfully"}
