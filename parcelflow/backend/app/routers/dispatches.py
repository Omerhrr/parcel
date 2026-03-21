"""
Dispatches Router
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
from app.models.dispatch import Dispatch, DispatchStatus
from app.models.agent import LogisticAgent, Vehicle
from app.models.tracking import TrackingEvent
from app.schemas.logistics import (
    DispatchCreate, DispatchUpdate, DispatchResponse, DispatchListResponse
)
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=DispatchListResponse)
async def list_dispatches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    agent_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List dispatches with filters"""
    query = db.query(Dispatch).join(
        Waybill, Dispatch.waybill_id == Waybill.id
    ).filter(
        Waybill.business_id == current_user.business_id
    )
    
    if status:
        query = query.filter(Dispatch.status == DispatchStatus(status))
    if agent_id:
        query = query.filter(Dispatch.agent_id == agent_id)
    
    total = query.count()
    offset = (page - 1) * page_size
    dispatches = query.order_by(Dispatch.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = []
    for d in dispatches:
        agent_name = None
        if d.agent_id:
            agent = db.query(LogisticAgent).filter(LogisticAgent.id == d.agent_id).first()
            agent_name = agent.name if agent else None
        
        items.append(DispatchResponse(
            id=d.id, waybill_id=d.waybill_id, waybill_number=d.waybill.waybill_number,
            agent_id=d.agent_id, agent_name=agent_name, vehicle_id=d.vehicle_id,
            dispatched_at=d.dispatched_at, estimated_delivery=d.estimated_delivery,
            status=d.status.value, attempt_count=d.attempt_count,
            last_attempt_at=d.last_attempt_at, route_notes=d.route_notes,
            distance_km=d.distance_km, failure_reason=d.failure_reason,
            created_at=d.created_at, updated_at=d.updated_at
        ))
    
    return DispatchListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=DispatchResponse, status_code=status.HTTP_201_CREATED)
async def create_dispatch(
    request: DispatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create/assign a dispatch for a waybill"""
    # Verify waybill belongs to user's business
    waybill = db.query(Waybill).filter(
        Waybill.id == request.waybill_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not waybill:
        raise HTTPException(status_code=404, detail="Waybill not found")
    
    # Check waybill is ready for dispatch
    if waybill.status not in [WaybillStatus.AT_WAREHOUSE, WaybillStatus.PICKED_UP]:
        raise HTTPException(
            status_code=400,
            detail="Waybill must be at warehouse or picked up before dispatch"
        )
    
    # Check for existing active dispatch
    existing = db.query(Dispatch).filter(
        Dispatch.waybill_id == request.waybill_id,
        Dispatch.status.in_([DispatchStatus.ASSIGNED, DispatchStatus.IN_TRANSIT])
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Active dispatch already exists for this waybill")
    
    dispatch = Dispatch(
        waybill_id=request.waybill_id,
        agent_id=request.agent_id,
        vehicle_id=request.vehicle_id,
        estimated_delivery=request.estimated_delivery,
        route_notes=request.route_notes,
        distance_km=request.distance_km,
        dispatched_at=datetime.utcnow().isoformat()
    )
    
    db.add(dispatch)
    
    # Update waybill status
    waybill.status = WaybillStatus.OUT_FOR_DELIVERY
    
    # Get agent name for tracking
    agent_name = None
    if request.agent_id:
        agent = db.query(LogisticAgent).filter(LogisticAgent.id == request.agent_id).first()
        agent_name = agent.name if agent else None
    
    # Create tracking event
    tracking = TrackingEvent(
        waybill_id=waybill.id,
        status="out_for_delivery",
        title="Out for Delivery",
        description=f"Dispatched to {agent_name or 'agent'} for delivery",
        location=waybill.receiver_city,
        actor_name=agent_name,
        actor_role="Agent",
        is_public=1
    )
    db.add(tracking)
    
    db.commit()
    db.refresh(dispatch)
    
    return DispatchResponse(
        id=dispatch.id, waybill_id=dispatch.waybill_id, waybill_number=waybill.waybill_number,
        agent_id=dispatch.agent_id, agent_name=agent_name, vehicle_id=dispatch.vehicle_id,
        dispatched_at=dispatch.dispatched_at, estimated_delivery=dispatch.estimated_delivery,
        status=dispatch.status.value, attempt_count=dispatch.attempt_count,
        last_attempt_at=dispatch.last_attempt_at, route_notes=dispatch.route_notes,
        distance_km=dispatch.distance_km, failure_reason=dispatch.failure_reason,
        created_at=dispatch.created_at, updated_at=dispatch.updated_at
    )


@router.get("/{dispatch_id}")
async def get_dispatch(
    dispatch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dispatch by ID with full details including waybill and agent location"""
    dispatch = db.query(Dispatch).join(
        Waybill, Dispatch.waybill_id == Waybill.id
    ).filter(
        Dispatch.id == dispatch_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    # Build waybill info
    waybill_info = None
    if dispatch.waybill:
        w = dispatch.waybill
        waybill_info = {
            "id": w.id,
            "waybill_number": w.waybill_number,
            "sender_name": w.sender_name,
            "sender_phone": w.sender_phone,
            "sender_address": w.sender_address,
            "sender_city": w.sender_city,
            "pickup_latitude": w.pickup_latitude,
            "pickup_longitude": w.pickup_longitude,
            "receiver_name": w.receiver_name,
            "receiver_phone": w.receiver_phone,
            "receiver_address": w.receiver_address,
            "receiver_city": w.receiver_city,
            "receiver_landmark": w.receiver_landmark,
            "delivery_latitude": w.delivery_latitude,
            "delivery_longitude": w.delivery_longitude,
            "cod_amount": w.cod_amount
        }
    
    # Build agent info
    agent_info = None
    agent_name = None
    if dispatch.agent_id:
        agent = db.query(LogisticAgent).filter(LogisticAgent.id == dispatch.agent_id).first()
        if agent:
            agent_name = agent.name
            agent_info = {
                "id": agent.id,
                "name": agent.name,
                "phone": agent.phone,
                "vehicle_type": agent.vehicle_type.value if agent.vehicle_type else None,
                "current_latitude": agent.current_latitude,
                "current_longitude": agent.current_longitude
            }
    
    return {
        "id": dispatch.id,
        "waybill_id": dispatch.waybill_id,
        "waybill_number": dispatch.waybill.waybill_number if dispatch.waybill else None,
        "waybill": waybill_info,
        "agent_id": dispatch.agent_id,
        "agent_name": agent_name,
        "agent": agent_info,
        "vehicle_id": dispatch.vehicle_id,
        "dispatched_at": dispatch.dispatched_at,
        "estimated_delivery": dispatch.estimated_delivery,
        "status": dispatch.status.value,
        "attempt_count": dispatch.attempt_count,
        "last_attempt_at": dispatch.last_attempt_at,
        "route_notes": dispatch.route_notes,
        "distance_km": dispatch.distance_km,
        "failure_reason": dispatch.failure_reason,
        "cod_amount": dispatch.waybill.cod_amount if dispatch.waybill else None,
        "created_at": dispatch.created_at,
        "updated_at": dispatch.updated_at
    }


@router.put("/{dispatch_id}", response_model=DispatchResponse)
async def update_dispatch(
    dispatch_id: int,
    request: DispatchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update dispatch"""
    dispatch = db.query(Dispatch).join(
        Waybill, Dispatch.waybill_id == Waybill.id
    ).filter(
        Dispatch.id == dispatch_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            value = DispatchStatus(value)
        setattr(dispatch, field, value)
    
    db.commit()
    db.refresh(dispatch)
    
    agent_name = None
    if dispatch.agent_id:
        agent = db.query(LogisticAgent).filter(LogisticAgent.id == dispatch.agent_id).first()
        agent_name = agent.name if agent else None
    
    return DispatchResponse(
        id=dispatch.id, waybill_id=dispatch.waybill_id, waybill_number=dispatch.waybill.waybill_number,
        agent_id=dispatch.agent_id, agent_name=agent_name, vehicle_id=dispatch.vehicle_id,
        dispatched_at=dispatch.dispatched_at, estimated_delivery=dispatch.estimated_delivery,
        status=dispatch.status.value, attempt_count=dispatch.attempt_count,
        last_attempt_at=dispatch.last_attempt_at, route_notes=dispatch.route_notes,
        distance_km=dispatch.distance_km, failure_reason=dispatch.failure_reason,
        created_at=dispatch.created_at, updated_at=dispatch.updated_at
    )


@router.post("/{dispatch_id}/start")
async def start_dispatch(
    dispatch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark dispatch as in transit"""
    dispatch = db.query(Dispatch).join(
        Waybill, Dispatch.waybill_id == Waybill.id
    ).filter(
        Dispatch.id == dispatch_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    dispatch.status = DispatchStatus.IN_TRANSIT
    db.commit()
    
    return {"success": True, "message": "Dispatch started"}


@router.post("/{dispatch_id}/attempt")
async def record_attempt(
    dispatch_id: int,
    notes: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record a delivery attempt"""
    dispatch = db.query(Dispatch).join(
        Waybill, Dispatch.waybill_id == Waybill.id
    ).filter(
        Dispatch.id == dispatch_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    dispatch.attempt_count += 1
    dispatch.last_attempt_at = datetime.utcnow().isoformat()
    if notes:
        dispatch.route_notes = f"{dispatch.route_notes or ''}\nAttempt {dispatch.attempt_count}: {notes}"
    
    db.commit()
    
    return {"success": True, "attempt_count": dispatch.attempt_count}


@router.post("/{dispatch_id}/complete")
async def complete_dispatch(
    dispatch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark dispatch as completed"""
    dispatch = db.query(Dispatch).join(
        Waybill, Dispatch.waybill_id == Waybill.id
    ).filter(
        Dispatch.id == dispatch_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    dispatch.status = DispatchStatus.COMPLETED
    
    # Update waybill status
    waybill = dispatch.waybill
    waybill.status = WaybillStatus.DELIVERED
    
    db.commit()
    
    return {"success": True, "message": "Dispatch completed"}


@router.post("/{dispatch_id}/fail")
async def fail_dispatch(
    dispatch_id: int,
    reason: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark dispatch as failed"""
    dispatch = db.query(Dispatch).join(
        Waybill, Dispatch.waybill_id == Waybill.id
    ).filter(
        Dispatch.id == dispatch_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    
    dispatch.status = DispatchStatus.FAILED
    dispatch.failure_reason = reason
    
    # Update waybill status
    waybill = dispatch.waybill
    waybill.status = WaybillStatus.FAILED
    
    # Create tracking event
    tracking = TrackingEvent(
        waybill_id=waybill.id,
        status="delivery_failed",
        title="Delivery Failed",
        description=f"Delivery failed: {reason}",
        location=waybill.receiver_city,
        is_public=0
    )
    db.add(tracking)
    
    db.commit()
    
    return {"success": True, "message": "Dispatch marked as failed"}
