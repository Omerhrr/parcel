"""
Deliveries Router - Delivery Confirmations
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.models.waybill import Waybill, WaybillStatus
from app.models.delivery import DeliveryConfirmation, DeliveryStatus
from app.models.dispatch import Dispatch, DispatchStatus
from app.models.agent import LogisticAgent
from app.models.tracking import TrackingEvent
from app.schemas.logistics import (
    DeliveryConfirmationCreate, DeliveryConfirmationUpdate, DeliveryConfirmationResponse
)
from app.utils.auth import get_current_user
from app.services.audit import AuditService

router = APIRouter()


@router.get("")
async def list_deliveries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    agent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List delivery confirmations with filters"""
    query = db.query(DeliveryConfirmation).join(
        Waybill, DeliveryConfirmation.waybill_id == Waybill.id
    ).filter(
        Waybill.business_id == current_user.business_id
    )
    
    if status:
        query = query.filter(DeliveryConfirmation.status == DeliveryStatus(status))
    if agent_id:
        query = query.filter(DeliveryConfirmation.agent_id == agent_id)
    
    total = query.count()
    offset = (page - 1) * page_size
    deliveries = query.order_by(DeliveryConfirmation.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = []
    for d in deliveries:
        agent_name = None
        if d.agent_id:
            agent = db.query(User).filter(User.id == d.agent_id).first()
            agent_name = agent.name if agent else None
        
        items.append(DeliveryConfirmationResponse(
            id=d.id, waybill_id=d.waybill_id, waybill_number=d.waybill.waybill_number,
            agent_id=d.agent_id, agent_name=agent_name, delivered_at=d.delivered_at,
            status=d.status.value, receiver_name=d.receiver_name,
            receiver_relationship=d.receiver_relationship, receiver_id_type=d.receiver_id_type,
            receiver_id_number=d.receiver_id_number, receiver_signature=d.receiver_signature,
            receiver_signature_svg=d.receiver_signature_svg, proof_photo_url=d.proof_photo_url,
            delivery_latitude=d.delivery_latitude, delivery_longitude=d.delivery_longitude,
            cod_collected=d.cod_collected, cod_amount=d.cod_amount, payment_method=d.payment_method,
            delivery_notes=d.delivery_notes, failure_reason=d.failure_reason,
            created_at=d.created_at, updated_at=d.updated_at
        ))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("", response_model=DeliveryConfirmationResponse, status_code=status.HTTP_201_CREATED)
async def confirm_delivery(
    request: DeliveryConfirmationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm delivery for a waybill"""
    # Verify waybill belongs to user's business
    waybill = db.query(Waybill).filter(
        Waybill.id == request.waybill_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not waybill:
        raise HTTPException(status_code=404, detail="Waybill not found")
    
    # Check if delivery already confirmed
    existing = db.query(DeliveryConfirmation).filter(
        DeliveryConfirmation.waybill_id == request.waybill_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Delivery already confirmed for this waybill")
    
    # Create delivery confirmation
    delivery = DeliveryConfirmation(
        waybill_id=request.waybill_id,
        agent_id=request.agent_id or current_user.id,
        delivered_at=request.delivered_at or datetime.utcnow().isoformat(),
        status=DeliveryStatus(request.status),
        receiver_name=request.receiver_name,
        receiver_relationship=request.receiver_relationship,
        receiver_id_type=request.receiver_id_type,
        receiver_id_number=request.receiver_id_number,
        receiver_signature=request.receiver_signature,
        receiver_signature_svg=request.receiver_signature_svg,
        delivery_latitude=request.delivery_latitude,
        delivery_longitude=request.delivery_longitude,
        cod_collected=1 if request.cod_collected else 0,
        cod_amount=request.cod_amount,
        payment_method=request.payment_method,
        delivery_notes=request.delivery_notes
    )
    
    db.add(delivery)
    
    # Update waybill status
    if request.status == "delivered":
        waybill.status = WaybillStatus.DELIVERED
        event_title = "Delivered"
        event_description = f"Successfully delivered to {request.receiver_name or 'receiver'}"
    elif request.status == "partial":
        waybill.status = WaybillStatus.DELIVERED
        event_title = "Partial Delivery"
        event_description = f"Partially delivered to {request.receiver_name or 'receiver'}"
    elif request.status == "returned":
        waybill.status = WaybillStatus.RETURNED
        event_title = "Returned"
        event_description = "Item returned"
    else:
        waybill.status = WaybillStatus.FAILED
        event_title = "Delivery Failed"
        event_description = request.delivery_notes or "Delivery failed"
    
    # Update dispatch status if exists
    dispatch = db.query(Dispatch).filter(
        Dispatch.waybill_id == request.waybill_id
    ).order_by(Dispatch.id.desc()).first()
    if dispatch:
        if request.status == "delivered":
            dispatch.status = DispatchStatus.COMPLETED
        elif request.status == "returned":
            dispatch.status = DispatchStatus.RETURNED
        elif request.status == "failed":
            dispatch.status = DispatchStatus.FAILED
    
    # Create tracking event
    tracking = TrackingEvent(
        waybill_id=waybill.id,
        status=request.status,
        title=event_title,
        description=event_description,
        location=waybill.receiver_city,
        actor_name=current_user.name,
        actor_role="Agent",
        is_public=1
    )
    db.add(tracking)
    
    # Create audit log
    audit = AuditService(db)
    audit.log_create(
        entity=delivery,
        user_id=current_user.id,
        business_id=waybill.business_id,
        description=f"Delivery confirmation created for waybill {waybill.waybill_number} - {event_title}"
    )
    
    db.commit()
    db.refresh(delivery)
    
    agent_name = None
    if delivery.agent_id:
        agent = db.query(User).filter(User.id == delivery.agent_id).first()
        agent_name = agent.name if agent else None
    
    return DeliveryConfirmationResponse(
        id=delivery.id, waybill_id=delivery.waybill_id, waybill_number=waybill.waybill_number,
        agent_id=delivery.agent_id, agent_name=agent_name, delivered_at=delivery.delivered_at,
        status=delivery.status.value, receiver_name=delivery.receiver_name,
        receiver_relationship=delivery.receiver_relationship, receiver_id_type=delivery.receiver_id_type,
        receiver_id_number=delivery.receiver_id_number, receiver_signature=delivery.receiver_signature,
        receiver_signature_svg=delivery.receiver_signature_svg, proof_photo_url=delivery.proof_photo_url,
        delivery_latitude=delivery.delivery_latitude, delivery_longitude=delivery.delivery_longitude,
        cod_collected=delivery.cod_collected, cod_amount=delivery.cod_amount,
        payment_method=delivery.payment_method, delivery_notes=delivery.delivery_notes,
        failure_reason=delivery.failure_reason, created_at=delivery.created_at, updated_at=delivery.updated_at
    )


@router.get("/{delivery_id}", response_model=DeliveryConfirmationResponse)
async def get_delivery(
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get delivery confirmation by ID"""
    delivery = db.query(DeliveryConfirmation).join(
        Waybill, DeliveryConfirmation.waybill_id == Waybill.id
    ).filter(
        DeliveryConfirmation.id == delivery_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery confirmation not found")
    
    agent_name = None
    if delivery.agent_id:
        agent = db.query(User).filter(User.id == delivery.agent_id).first()
        agent_name = agent.name if agent else None
    
    return DeliveryConfirmationResponse(
        id=delivery.id, waybill_id=delivery.waybill_id, waybill_number=delivery.waybill.waybill_number,
        agent_id=delivery.agent_id, agent_name=agent_name, delivered_at=delivery.delivered_at,
        status=delivery.status.value, receiver_name=delivery.receiver_name,
        receiver_relationship=delivery.receiver_relationship, receiver_id_type=delivery.receiver_id_type,
        receiver_id_number=delivery.receiver_id_number, receiver_signature=delivery.receiver_signature,
        receiver_signature_svg=delivery.receiver_signature_svg, proof_photo_url=delivery.proof_photo_url,
        delivery_latitude=delivery.delivery_latitude, delivery_longitude=delivery.delivery_longitude,
        cod_collected=delivery.cod_collected, cod_amount=delivery.cod_amount,
        payment_method=delivery.payment_method, delivery_notes=delivery.delivery_notes,
        failure_reason=delivery.failure_reason, created_at=delivery.created_at, updated_at=delivery.updated_at
    )


@router.put("/{delivery_id}", response_model=DeliveryConfirmationResponse)
async def update_delivery(
    delivery_id: int,
    request: DeliveryConfirmationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update delivery confirmation"""
    delivery = db.query(DeliveryConfirmation).join(
        Waybill, DeliveryConfirmation.waybill_id == Waybill.id
    ).filter(
        DeliveryConfirmation.id == delivery_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery confirmation not found")
    
    update_data = request.model_dump(exclude_unset=True)
    old_values = {}
    for field, value in update_data.items():
        if field == "status" and value:
            old_values[field] = delivery.status.value if delivery.status else None
            value = DeliveryStatus(value)
        else:
            old_values[field] = getattr(delivery, field, None)
        setattr(delivery, field, value)
    
    # Create audit log
    audit = AuditService(db)
    audit.log_update(
        entity=delivery,
        old_values=old_values,
        user_id=current_user.id,
        business_id=delivery.waybill.business_id,
        updated_fields=list(update_data.keys()),
        description=f"Delivery confirmation updated for waybill {delivery.waybill.waybill_number}"
    )
    
    db.commit()
    db.refresh(delivery)
    
    agent_name = None
    if delivery.agent_id:
        agent = db.query(User).filter(User.id == delivery.agent_id).first()
        agent_name = agent.name if agent else None
    
    return DeliveryConfirmationResponse(
        id=delivery.id, waybill_id=delivery.waybill_id, waybill_number=delivery.waybill.waybill_number,
        agent_id=delivery.agent_id, agent_name=agent_name, delivered_at=delivery.delivered_at,
        status=delivery.status.value, receiver_name=delivery.receiver_name,
        receiver_relationship=delivery.receiver_relationship, receiver_id_type=delivery.receiver_id_type,
        receiver_id_number=delivery.receiver_id_number, receiver_signature=delivery.receiver_signature,
        receiver_signature_svg=delivery.receiver_signature_svg, proof_photo_url=delivery.proof_photo_url,
        delivery_latitude=delivery.delivery_latitude, delivery_longitude=delivery.delivery_longitude,
        cod_collected=delivery.cod_collected, cod_amount=delivery.cod_amount,
        payment_method=delivery.payment_method, delivery_notes=delivery.delivery_notes,
        failure_reason=delivery.failure_reason, created_at=delivery.created_at, updated_at=delivery.updated_at
    )
