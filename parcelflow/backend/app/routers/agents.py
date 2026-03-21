"""
Agents Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.agent import LogisticAgent, Vehicle, AgentStatus
from app.schemas.agent import (
    AgentCreate, AgentUpdate, AgentResponse, AgentListResponse,
    VehicleCreate, VehicleResponse
)
from app.utils.auth import get_current_user
from app.services.audit import AuditService

router = APIRouter()


@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List agents"""
    query = db.query(LogisticAgent).filter(
        LogisticAgent.business_id == current_user.business_id
    )
    
    if status:
        query = query.filter(LogisticAgent.status == status)
    if branch_id:
        query = query.filter(LogisticAgent.branch_id == branch_id)
    
    total = query.count()
    offset = (page - 1) * page_size
    agents = query.offset(offset).limit(page_size).all()
    
    items = [AgentResponse(
        id=a.id, business_id=a.business_id, branch_id=a.branch_id,
        user_id=a.user_id, name=a.name, phone=a.phone, email=a.email,
        employee_id=a.employee_id, national_id=a.national_id,
        vehicle_type=a.vehicle_type.value, vehicle_id=a.vehicle_id,
        status=a.status.value, total_deliveries=a.total_deliveries,
        successful_deliveries=a.successful_deliveries, failed_deliveries=a.failed_deliveries,
        rating=a.rating, base_salary=a.base_salary, commission_rate=a.commission_rate,
        current_latitude=a.current_latitude, current_longitude=a.current_longitude,
        last_location_update=a.last_location_update, notes=a.notes,
        created_at=a.created_at, updated_at=a.updated_at
    ) for a in agents]
    
    return AgentListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create agent"""
    if not current_user.has_permission("agents.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Convert string values to enum values
    from app.models.agent import VehicleType
    
    try:
        vehicle_type_enum = VehicleType(request.vehicle_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid vehicle_type: {request.vehicle_type}")
    
    try:
        status_enum = AgentStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    
    agent = LogisticAgent(
        business_id=current_user.business_id,
        branch_id=request.branch_id,
        user_id=request.user_id,
        name=request.name,
        phone=request.phone,
        email=request.email,
        employee_id=request.employee_id,
        national_id=request.national_id,
        vehicle_type=vehicle_type_enum,
        vehicle_id=request.vehicle_id,
        status=status_enum,
        base_salary=request.base_salary,
        commission_rate=request.commission_rate,
        notes=request.notes
    )
    
    db.add(agent)
    db.flush()  # Flush to get the agent ID before creating audit log
    
    # Create audit log
    audit = AuditService(db)
    audit.log_create(
        entity=agent,
        user_id=current_user.id,
        business_id=current_user.business_id,
        description=f"Created agent {agent.name}"
    )
    
    db.commit()
    db.refresh(agent)
    
    return AgentResponse(
        id=agent.id, business_id=agent.business_id, branch_id=agent.branch_id,
        user_id=agent.user_id, name=agent.name, phone=agent.phone, email=agent.email,
        employee_id=agent.employee_id, national_id=agent.national_id,
        vehicle_type=agent.vehicle_type.value, vehicle_id=agent.vehicle_id,
        status=agent.status.value, total_deliveries=agent.total_deliveries,
        successful_deliveries=agent.successful_deliveries, failed_deliveries=agent.failed_deliveries,
        rating=agent.rating, base_salary=agent.base_salary, commission_rate=agent.commission_rate,
        current_latitude=agent.current_latitude, current_longitude=agent.current_longitude,
        last_location_update=agent.last_location_update, notes=agent.notes,
        created_at=agent.created_at, updated_at=agent.updated_at
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get agent by ID"""
    agent = db.query(LogisticAgent).filter(
        LogisticAgent.id == agent_id,
        LogisticAgent.business_id == current_user.business_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse(
        id=agent.id, business_id=agent.business_id, branch_id=agent.branch_id,
        user_id=agent.user_id, name=agent.name, phone=agent.phone, email=agent.email,
        employee_id=agent.employee_id, national_id=agent.national_id,
        vehicle_type=agent.vehicle_type.value, vehicle_id=agent.vehicle_id,
        status=agent.status.value, total_deliveries=agent.total_deliveries,
        successful_deliveries=agent.successful_deliveries, failed_deliveries=agent.failed_deliveries,
        rating=agent.rating, base_salary=agent.base_salary, commission_rate=agent.commission_rate,
        current_latitude=agent.current_latitude, current_longitude=agent.current_longitude,
        last_location_update=agent.last_location_update, notes=agent.notes,
        created_at=agent.created_at, updated_at=agent.updated_at
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    request: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update agent"""
    from app.models.agent import VehicleType
    
    agent = db.query(LogisticAgent).filter(
        LogisticAgent.id == agent_id,
        LogisticAgent.business_id == current_user.business_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    update_data = request.model_dump(exclude_unset=True)
    old_values = {}
    for field, value in update_data.items():
        old_values[field] = getattr(agent, field, None)
        # Convert string values to enum for vehicle_type and status
        if field == 'vehicle_type' and isinstance(value, str):
            try:
                value = VehicleType(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid vehicle_type: {value}")
        elif field == 'status' and isinstance(value, str):
            try:
                value = AgentStatus(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {value}")
        setattr(agent, field, value)
    
    # Create audit log
    audit = AuditService(db)
    audit.log_update(
        entity=agent,
        old_values=old_values,
        user_id=current_user.id,
        business_id=agent.business_id,
        updated_fields=list(update_data.keys()),
        description=f"Updated agent {agent.name}"
    )
    
    db.commit()
    db.refresh(agent)
    
    return AgentResponse(
        id=agent.id, business_id=agent.business_id, branch_id=agent.branch_id,
        user_id=agent.user_id, name=agent.name, phone=agent.phone, email=agent.email,
        employee_id=agent.employee_id, national_id=agent.national_id,
        vehicle_type=agent.vehicle_type.value, vehicle_id=agent.vehicle_id,
        status=agent.status.value, total_deliveries=agent.total_deliveries,
        successful_deliveries=agent.successful_deliveries, failed_deliveries=agent.failed_deliveries,
        rating=agent.rating, base_salary=agent.base_salary, commission_rate=agent.commission_rate,
        current_latitude=agent.current_latitude, current_longitude=agent.current_longitude,
        last_location_update=agent.last_location_update, notes=agent.notes,
        created_at=agent.created_at, updated_at=agent.updated_at
    )


@router.get("/{agent_id}/stats")
async def get_agent_stats(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get agent performance statistics"""
    agent = db.query(LogisticAgent).filter(
        LogisticAgent.id == agent_id,
        LogisticAgent.business_id == current_user.business_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "total_deliveries": agent.total_deliveries,
        "successful_deliveries": agent.successful_deliveries,
        "failed_deliveries": agent.failed_deliveries,
        "success_rate": agent.success_rate,
        "rating": float(agent.rating)
    }


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete agent (soft delete by setting status to inactive)"""
    if not current_user.has_permission("agents.delete"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    agent = db.query(LogisticAgent).filter(
        LogisticAgent.id == agent_id,
        LogisticAgent.business_id == current_user.business_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check if agent has active dispatches
    from app.models.dispatch import Dispatch, DispatchStatus
    active_dispatches = db.query(Dispatch).filter(
        Dispatch.agent_id == agent_id,
        Dispatch.status.in_([DispatchStatus.assigned, DispatchStatus.in_transit])
    ).count()
    
    if active_dispatches > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete agent with {active_dispatches} active dispatches. Reassign or complete them first."
        )
    
    # Soft delete - set status to inactive
    old_status = agent.status.value
    agent.status = AgentStatus.INACTIVE
    
    # Create audit log
    audit = AuditService(db)
    audit.log_status_change(
        entity=agent,
        old_status=old_status,
        new_status="inactive",
        user_id=current_user.id,
        business_id=agent.business_id,
        description=f"Agent {agent.name} deactivated"
    )
    
    db.commit()
    
    return {"success": True, "message": "Agent deactivated successfully"}


@router.put("/{agent_id}/location")
async def update_agent_location(
    agent_id: int,
    latitude: float,
    longitude: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update agent's current location"""
    from datetime import datetime
    
    agent = db.query(LogisticAgent).filter(
        LogisticAgent.id == agent_id,
        LogisticAgent.business_id == current_user.business_id
    ).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.current_latitude = latitude
    agent.current_longitude = longitude
    agent.last_location_update = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Location updated",
        "latitude": latitude,
        "longitude": longitude,
        "updated_at": agent.last_location_update.isoformat()
    }


@router.get("/locations")
async def get_agent_locations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all agents with their current locations.
    Returns agent data including lat/lng and current dispatch info if assigned.
    """
    from app.models.dispatch import Dispatch, DispatchStatus
    
    # Query all agents for the current business
    agents = db.query(LogisticAgent).filter(
        LogisticAgent.business_id == current_user.business_id
    ).all()
    
    result = []
    for agent in agents:
        # Get current active dispatch if any
        current_dispatch = None
        active_dispatch = db.query(Dispatch).filter(
            Dispatch.agent_id == agent.id,
            Dispatch.status.in_([DispatchStatus.assigned, DispatchStatus.in_transit])
        ).first()
        
        if active_dispatch and active_dispatch.waybill:
            current_dispatch = {
                "id": active_dispatch.id,
                "waybill_number": active_dispatch.waybill.waybill_number,
                "receiver_name": active_dispatch.waybill.receiver_name,
                "receiver_address": active_dispatch.waybill.receiver_address,
                "status": active_dispatch.status.value
            }
        
        # Only include agents that have location data
        if agent.current_latitude and agent.current_longitude:
            result.append({
                "id": agent.id,
                "name": agent.name,
                "phone": agent.phone,
                "email": agent.email,
                "status": agent.status.value,
                "vehicle_type": agent.vehicle_type.value if agent.vehicle_type else None,
                "total_deliveries": agent.total_deliveries,
                "successful_deliveries": agent.successful_deliveries,
                "failed_deliveries": agent.failed_deliveries,
                "rating": float(agent.rating) if agent.rating else 0,
                "current_latitude": agent.current_latitude,
                "current_longitude": agent.current_longitude,
                "last_location_update": agent.last_location_update.isoformat() if agent.last_location_update else None,
                "current_dispatch": current_dispatch
            })
    
    return result
