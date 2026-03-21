"""
Branches Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.branch import Branch, BranchStatus
from app.schemas.branch import BranchCreate, BranchUpdate, BranchResponse, BranchListResponse
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=BranchListResponse)
async def list_branches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List branches for current business"""
    query = db.query(Branch).filter(Branch.business_id == current_user.business_id)
    
    if status:
        query = query.filter(Branch.status == status)
    
    total = query.count()
    offset = (page - 1) * page_size
    branches = query.offset(offset).limit(page_size).all()
    
    items = [BranchResponse(
        id=b.id, business_id=b.business_id, name=b.name, code=b.code,
        address=b.address, city=b.city, state=b.state, country=b.country,
        postal_code=b.postal_code, phone=b.phone, email=b.email,
        currency=b.currency, timezone=b.timezone, status=b.status.value,
        is_headquarters=b.is_headquarters, latitude=b.latitude, longitude=b.longitude,
        created_at=b.created_at, updated_at=b.updated_at
    ) for b in branches]
    
    return BranchListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    request: BranchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new branch"""
    if not current_user.has_permission("branches.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    branch = Branch(
        business_id=current_user.business_id,
        name=request.name,
        code=request.code,
        address=request.address,
        city=request.city,
        state=request.state,
        country=request.country,
        postal_code=request.postal_code,
        phone=request.phone,
        email=request.email,
        currency=request.currency,
        timezone=request.timezone,
        is_headquarters=1 if request.is_headquarters else 0,
        latitude=request.latitude,
        longitude=request.longitude
    )
    
    db.add(branch)
    db.commit()
    db.refresh(branch)
    
    return BranchResponse(
        id=branch.id, business_id=branch.business_id, name=branch.name, code=branch.code,
        address=branch.address, city=branch.city, state=branch.state, country=branch.country,
        postal_code=branch.postal_code, phone=branch.phone, email=branch.email,
        currency=branch.currency, timezone=branch.timezone, status=branch.status.value,
        is_headquarters=branch.is_headquarters, latitude=branch.latitude, longitude=branch.longitude,
        created_at=branch.created_at, updated_at=branch.updated_at
    )


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get branch by ID"""
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.business_id == current_user.business_id
    ).first()
    
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    return BranchResponse(
        id=branch.id, business_id=branch.business_id, name=branch.name, code=branch.code,
        address=branch.address, city=branch.city, state=branch.state, country=branch.country,
        postal_code=branch.postal_code, phone=branch.phone, email=branch.email,
        currency=branch.currency, timezone=branch.timezone, status=branch.status.value,
        is_headquarters=branch.is_headquarters, latitude=branch.latitude, longitude=branch.longitude,
        created_at=branch.created_at, updated_at=branch.updated_at
    )


@router.put("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: int,
    request: BranchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update branch"""
    if not current_user.has_permission("branches.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.business_id == current_user.business_id
    ).first()
    
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "is_headquarters":
            value = 1 if value else 0
        setattr(branch, field, value)
    
    db.commit()
    db.refresh(branch)
    
    return BranchResponse(
        id=branch.id, business_id=branch.business_id, name=branch.name, code=branch.code,
        address=branch.address, city=branch.city, state=branch.state, country=branch.country,
        postal_code=branch.postal_code, phone=branch.phone, email=branch.email,
        currency=branch.currency, timezone=branch.timezone, status=branch.status.value,
        is_headquarters=branch.is_headquarters, latitude=branch.latitude, longitude=branch.longitude,
        created_at=branch.created_at, updated_at=branch.updated_at
    )


@router.delete("/{branch_id}")
async def delete_branch(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete branch (soft delete by setting status to inactive)"""
    if not current_user.has_permission("branches.delete"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.business_id == current_user.business_id
    ).first()
    
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Check if this is the only branch or headquarters
    total_branches = db.query(Branch).filter(
        Branch.business_id == current_user.business_id,
        Branch.status == BranchStatus.active
    ).count()
    
    if total_branches <= 1:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete the only active branch. Businesses must have at least one branch."
        )
    
    if branch.is_headquarters:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete headquarters branch. Transfer headquarters status first."
        )
    
    # Soft delete - set status to inactive
    branch.status = BranchStatus.inactive
    db.commit()
    
    return {"success": True, "message": "Branch deactivated successfully"}
