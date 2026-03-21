"""
Warehouses Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.warehouse import Warehouse, WarehouseStatus
from app.schemas.warehouse import (
    WarehouseCreate, WarehouseUpdate, WarehouseResponse, WarehouseListResponse
)
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=WarehouseListResponse)
async def list_warehouses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    branch_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List warehouses for current business"""
    query = db.query(Warehouse).filter(Warehouse.business_id == current_user.business_id)
    
    if branch_id:
        query = query.filter(Warehouse.branch_id == branch_id)
    if status:
        query = query.filter(Warehouse.status == WarehouseStatus(status))
    
    total = query.count()
    offset = (page - 1) * page_size
    warehouses = query.offset(offset).limit(page_size).all()
    
    items = [WarehouseResponse(
        id=w.id, business_id=w.business_id, branch_id=w.branch_id,
        name=w.name, code=w.code, address=w.address, city=w.city,
        state=w.state, country=w.country, manager_name=w.manager_name,
        phone=w.phone, email=w.email, capacity_sqm=w.capacity_sqm,
        max_items=w.max_items, status=w.status.value,
        latitude=w.latitude, longitude=w.longitude,
        created_at=w.created_at, updated_at=w.updated_at
    ) for w in warehouses]
    
    return WarehouseListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    request: WarehouseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new warehouse"""
    if not current_user.has_permission("warehouses.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    warehouse = Warehouse(
        business_id=current_user.business_id,
        branch_id=request.branch_id,
        name=request.name,
        code=request.code,
        address=request.address,
        city=request.city,
        state=request.state,
        country=request.country,
        manager_name=request.manager_name,
        phone=request.phone,
        email=request.email,
        capacity_sqm=request.capacity_sqm,
        max_items=request.max_items,
        latitude=request.latitude,
        longitude=request.longitude
    )
    
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    
    return WarehouseResponse(
        id=warehouse.id, business_id=warehouse.business_id, branch_id=warehouse.branch_id,
        name=warehouse.name, code=warehouse.code, address=warehouse.address, city=warehouse.city,
        state=warehouse.state, country=warehouse.country, manager_name=warehouse.manager_name,
        phone=warehouse.phone, email=warehouse.email, capacity_sqm=warehouse.capacity_sqm,
        max_items=warehouse.max_items, status=warehouse.status.value,
        latitude=warehouse.latitude, longitude=warehouse.longitude,
        created_at=warehouse.created_at, updated_at=warehouse.updated_at
    )


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(
    warehouse_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get warehouse by ID"""
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id,
        Warehouse.business_id == current_user.business_id
    ).first()
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    return WarehouseResponse(
        id=warehouse.id, business_id=warehouse.business_id, branch_id=warehouse.branch_id,
        name=warehouse.name, code=warehouse.code, address=warehouse.address, city=warehouse.city,
        state=warehouse.state, country=warehouse.country, manager_name=warehouse.manager_name,
        phone=warehouse.phone, email=warehouse.email, capacity_sqm=warehouse.capacity_sqm,
        max_items=warehouse.max_items, status=warehouse.status.value,
        latitude=warehouse.latitude, longitude=warehouse.longitude,
        created_at=warehouse.created_at, updated_at=warehouse.updated_at
    )


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: int,
    request: WarehouseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update warehouse"""
    if not current_user.has_permission("warehouses.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id,
        Warehouse.business_id == current_user.business_id
    ).first()
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            value = WarehouseStatus(value)
        setattr(warehouse, field, value)
    
    db.commit()
    db.refresh(warehouse)
    
    return WarehouseResponse(
        id=warehouse.id, business_id=warehouse.business_id, branch_id=warehouse.branch_id,
        name=warehouse.name, code=warehouse.code, address=warehouse.address, city=warehouse.city,
        state=warehouse.state, country=warehouse.country, manager_name=warehouse.manager_name,
        phone=warehouse.phone, email=warehouse.email, capacity_sqm=warehouse.capacity_sqm,
        max_items=warehouse.max_items, status=warehouse.status.value,
        latitude=warehouse.latitude, longitude=warehouse.longitude,
        created_at=warehouse.created_at, updated_at=warehouse.updated_at
    )


@router.delete("/{warehouse_id}")
async def delete_warehouse(
    warehouse_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete warehouse (set status to inactive)"""
    if not current_user.has_permission("warehouses.delete"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id,
        Warehouse.business_id == current_user.business_id
    ).first()
    
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    warehouse.status = WarehouseStatus.INACTIVE
    db.commit()
    
    return {"success": True, "message": "Warehouse deactivated"}
