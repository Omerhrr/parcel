"""
Pickups Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.waybill import Waybill, WaybillStatus, ShipmentType
from app.models.pickup import Pickup, PickupStatus
from app.models.agent import LogisticAgent
from app.models.tracking import TrackingEvent
from app.schemas.logistics import (
    PickupCreate, PickupUpdate, PickupResponse, PickupListResponse
)
from app.utils.auth import get_current_user
from app.utils.notifications import notify_pickup_assigned

router = APIRouter()


@router.get("", response_model=PickupListResponse)
async def list_pickups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    agent_id: Optional[int] = None,
    scheduled_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List pickups with filters"""
    query = db.query(Pickup).join(
        Waybill, Pickup.waybill_id == Waybill.id
    ).filter(
        Waybill.business_id == current_user.business_id
    )
    
    if status:
        query = query.filter(Pickup.status == PickupStatus(status))
    if agent_id:
        query = query.filter(Pickup.agent_id == agent_id)
    if scheduled_date:
        query = query.filter(Pickup.scheduled_date == scheduled_date)
    
    total = query.count()
    offset = (page - 1) * page_size
    pickups = query.order_by(Pickup.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = []
    for p in pickups:
        agent_name = None
        if p.agent_id:
            agent = db.query(LogisticAgent).filter(LogisticAgent.id == p.agent_id).first()
            agent_name = agent.name if agent else None
        
        items.append(PickupResponse(
            id=p.id, waybill_id=p.waybill_id, waybill_number=p.waybill.waybill_number,
            pickup_address=p.pickup_address, pickup_city=p.pickup_city,
            pickup_landmark=p.pickup_landmark, pickup_contact_name=p.pickup_contact_name,
            pickup_contact_phone=p.pickup_contact_phone, scheduled_date=p.scheduled_date,
            scheduled_time_from=p.scheduled_time_from, scheduled_time_to=p.scheduled_time_to,
            agent_id=p.agent_id, agent_name=agent_name, status=p.status.value,
            actual_pickup_time=p.actual_pickup_time, notes=p.notes,
            failure_reason=p.failure_reason,
            created_at=p.created_at, updated_at=p.updated_at
        ))
    
    return PickupListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=PickupResponse, status_code=status.HTTP_201_CREATED)
async def create_pickup(
    request: PickupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule a pickup for a waybill"""
    # Verify waybill belongs to user's business
    waybill = db.query(Waybill).filter(
        Waybill.id == request.waybill_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not waybill:
        raise HTTPException(status_code=404, detail="Waybill not found")
    
    # Check if waybill is pickup type
    if waybill.shipment_type != ShipmentType.PICKUP_DELIVERY:
        raise HTTPException(status_code=400, detail="Waybill is not a pickup delivery type")
    
    # Check if pickup already exists
    existing = db.query(Pickup).filter(Pickup.waybill_id == request.waybill_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Pickup already scheduled for this waybill")
    
    pickup = Pickup(
        waybill_id=request.waybill_id,
        pickup_address=request.pickup_address,
        pickup_city=request.pickup_city,
        pickup_landmark=request.pickup_landmark,
        pickup_contact_name=request.pickup_contact_name,
        pickup_contact_phone=request.pickup_contact_phone,
        scheduled_date=request.scheduled_date,
        scheduled_time_from=request.scheduled_time_from,
        scheduled_time_to=request.scheduled_time_to,
        agent_id=request.agent_id,
        notes=request.notes
    )
    
    if request.agent_id:
        pickup.status = PickupStatus.AGENT_ASSIGNED
        # Send notification to agent
        notify_pickup_assigned(
            db=db,
            business_id=current_user.business_id,
            pickup_id=pickup.id,
            waybill_number=waybill.waybill_number,
            agent_id=request.agent_id
        )
    
    # Update waybill status
    waybill.status = WaybillStatus.PICKUP_SCHEDULED
    
    # Create tracking event
    tracking = TrackingEvent(
        waybill_id=waybill.id,
        status="pickup_scheduled",
        title="Pickup Scheduled",
        description=f"Pickup scheduled for {request.scheduled_date or 'pending'}",
        location=request.pickup_city,
        is_public=1
    )
    db.add(tracking)
    
    db.commit()
    db.refresh(pickup)
    
    agent_name = None
    if pickup.agent_id:
        agent = db.query(LogisticAgent).filter(LogisticAgent.id == pickup.agent_id).first()
        agent_name = agent.name if agent else None
    
    return PickupResponse(
        id=pickup.id, waybill_id=pickup.waybill_id, waybill_number=waybill.waybill_number,
        pickup_address=pickup.pickup_address, pickup_city=pickup.pickup_city,
        pickup_landmark=pickup.pickup_landmark, pickup_contact_name=pickup.pickup_contact_name,
        pickup_contact_phone=pickup.pickup_contact_phone, scheduled_date=pickup.scheduled_date,
        scheduled_time_from=pickup.scheduled_time_from, scheduled_time_to=pickup.scheduled_time_to,
        agent_id=pickup.agent_id, agent_name=agent_name, status=pickup.status.value,
        actual_pickup_time=pickup.actual_pickup_time, notes=pickup.notes,
        failure_reason=pickup.failure_reason,
        created_at=pickup.created_at, updated_at=pickup.updated_at
    )


@router.get("/{pickup_id}", response_model=PickupResponse)
async def get_pickup(
    pickup_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pickup by ID"""
    pickup = db.query(Pickup).join(
        Waybill, Pickup.waybill_id == Waybill.id
    ).filter(
        Pickup.id == pickup_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup not found")
    
    agent_name = None
    if pickup.agent_id:
        agent = db.query(LogisticAgent).filter(LogisticAgent.id == pickup.agent_id).first()
        agent_name = agent.name if agent else None
    
    return PickupResponse(
        id=pickup.id, waybill_id=pickup.waybill_id, waybill_number=pickup.waybill.waybill_number,
        pickup_address=pickup.pickup_address, pickup_city=pickup.pickup_city,
        pickup_landmark=pickup.pickup_landmark, pickup_contact_name=pickup.pickup_contact_name,
        pickup_contact_phone=pickup.pickup_contact_phone, scheduled_date=pickup.scheduled_date,
        scheduled_time_from=pickup.scheduled_time_from, scheduled_time_to=pickup.scheduled_time_to,
        agent_id=pickup.agent_id, agent_name=agent_name, status=pickup.status.value,
        actual_pickup_time=pickup.actual_pickup_time, notes=pickup.notes,
        failure_reason=pickup.failure_reason,
        created_at=pickup.created_at, updated_at=pickup.updated_at
    )


@router.put("/{pickup_id}", response_model=PickupResponse)
async def update_pickup(
    pickup_id: int,
    request: PickupUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update pickup"""
    pickup = db.query(Pickup).join(
        Waybill, Pickup.waybill_id == Waybill.id
    ).filter(
        Pickup.id == pickup_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            value = PickupStatus(value)
        setattr(pickup, field, value)
    
    db.commit()
    db.refresh(pickup)
    
    agent_name = None
    if pickup.agent_id:
        agent = db.query(LogisticAgent).filter(LogisticAgent.id == pickup.agent_id).first()
        agent_name = agent.name if agent else None
    
    return PickupResponse(
        id=pickup.id, waybill_id=pickup.waybill_id, waybill_number=pickup.waybill.waybill_number,
        pickup_address=pickup.pickup_address, pickup_city=pickup.pickup_city,
        pickup_landmark=pickup.pickup_landmark, pickup_contact_name=pickup.pickup_contact_name,
        pickup_contact_phone=pickup.pickup_contact_phone, scheduled_date=pickup.scheduled_date,
        scheduled_time_from=pickup.scheduled_time_from, scheduled_time_to=pickup.scheduled_time_to,
        agent_id=pickup.agent_id, agent_name=agent_name, status=pickup.status.value,
        actual_pickup_time=pickup.actual_pickup_time, notes=pickup.notes,
        failure_reason=pickup.failure_reason,
        created_at=pickup.created_at, updated_at=pickup.updated_at
    )


@router.post("/{pickup_id}/complete")
async def complete_pickup(
    pickup_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark pickup as completed"""
    pickup = db.query(Pickup).join(
        Waybill, Pickup.waybill_id == Waybill.id
    ).filter(
        Pickup.id == pickup_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup not found")
    
    pickup.status = PickupStatus.PICKED_UP
    pickup.actual_pickup_time = datetime.utcnow().isoformat()
    
    # Update waybill status
    waybill = pickup.waybill
    waybill.status = WaybillStatus.PICKED_UP
    
    # Create tracking event
    tracking = TrackingEvent(
        waybill_id=waybill.id,
        status="picked_up",
        title="Picked Up",
        description="Item has been picked up from sender",
        location=pickup.pickup_city,
        is_public=1
    )
    db.add(tracking)
    
    db.commit()
    
    return {"success": True, "message": "Pickup completed"}


@router.post("/{pickup_id}/fail")
async def fail_pickup(
    pickup_id: int,
    reason: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark pickup as failed"""
    pickup = db.query(Pickup).join(
        Waybill, Pickup.waybill_id == Waybill.id
    ).filter(
        Pickup.id == pickup_id,
        Waybill.business_id == current_user.business_id
    ).first()
    
    if not pickup:
        raise HTTPException(status_code=404, detail="Pickup not found")
    
    pickup.status = PickupStatus.FAILED
    pickup.failure_reason = reason
    
    # Create tracking event
    tracking = TrackingEvent(
        waybill_id=pickup.waybill_id,
        status="pickup_failed",
        title="Pickup Failed",
        description=f"Pickup failed: {reason}",
        location=pickup.pickup_city,
        is_public=0
    )
    db.add(tracking)
    
    db.commit()
    
    return {"success": True, "message": "Pickup marked as failed"}
