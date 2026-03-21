"""
Leads Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.lead import Lead, LeadStatus
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse, LeadListResponse
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    source: Optional[str] = None,
    assigned_to: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List leads"""
    query = db.query(Lead).filter(Lead.business_id == current_user.business_id)
    
    if status:
        query = query.filter(Lead.status == status)
    if source:
        query = query.filter(Lead.source == source)
    if assigned_to:
        query = query.filter(Lead.assigned_to_user_id == assigned_to)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Lead.name.ilike(search_term)) |
            (Lead.phone.ilike(search_term)) |
            (Lead.email.ilike(search_term))
        )
    
    total = query.count()
    offset = (page - 1) * page_size
    leads = query.order_by(Lead.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = [LeadResponse(
        id=l.id, business_id=l.business_id, name=l.name, phone=l.phone,
        email=l.email, company_name=l.company_name, company_size=l.company_size,
        industry=l.industry, address=l.address, city=l.city, state=l.state,
        product_interest=l.product_interest, service_interest=l.service_interest,
        estimated_value=l.estimated_value, source=l.source.value,
        source_details=l.source_details, status=l.status.value,
        assigned_to_user_id=l.assigned_to_user_id, created_by_user_id=l.created_by_user_id,
        next_follow_up=l.next_follow_up, last_contact=l.last_contact,
        converted_at=l.converted_at, converted_to_order_id=l.converted_to_order_id,
        notes=l.notes, rejection_reason=l.rejection_reason,
        created_at=l.created_at, updated_at=l.updated_at
    ) for l in leads]
    
    return LeadListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    request: LeadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create lead"""
    if not current_user.has_permission("leads.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    lead = Lead(
        business_id=current_user.business_id,
        name=request.name,
        phone=request.phone,
        email=request.email,
        company_name=request.company_name,
        company_size=request.company_size,
        industry=request.industry,
        address=request.address,
        city=request.city,
        state=request.state,
        product_interest=request.product_interest,
        service_interest=request.service_interest,
        estimated_value=request.estimated_value,
        source=request.source,
        source_details=request.source_details,
        assigned_to_user_id=request.assigned_to_user_id,
        created_by_user_id=current_user.id,
        next_follow_up=request.next_follow_up,
        notes=request.notes
    )
    
    db.add(lead)
    db.commit()
    db.refresh(lead)
    
    return LeadResponse(
        id=lead.id, business_id=lead.business_id, name=lead.name, phone=lead.phone,
        email=lead.email, company_name=lead.company_name, company_size=lead.company_size,
        industry=lead.industry, address=lead.address, city=lead.city, state=lead.state,
        product_interest=lead.product_interest, service_interest=lead.service_interest,
        estimated_value=lead.estimated_value, source=lead.source.value,
        source_details=lead.source_details, status=lead.status.value,
        assigned_to_user_id=lead.assigned_to_user_id, created_by_user_id=lead.created_by_user_id,
        next_follow_up=lead.next_follow_up, last_contact=lead.last_contact,
        converted_at=lead.converted_at, converted_to_order_id=lead.converted_to_order_id,
        notes=lead.notes, rejection_reason=lead.rejection_reason,
        created_at=lead.created_at, updated_at=lead.updated_at
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get lead by ID"""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.business_id == current_user.business_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return LeadResponse(
        id=lead.id, business_id=lead.business_id, name=lead.name, phone=lead.phone,
        email=lead.email, company_name=lead.company_name, company_size=lead.company_size,
        industry=lead.industry, address=lead.address, city=lead.city, state=lead.state,
        product_interest=lead.product_interest, service_interest=lead.service_interest,
        estimated_value=lead.estimated_value, source=lead.source.value,
        source_details=lead.source_details, status=lead.status.value,
        assigned_to_user_id=lead.assigned_to_user_id, created_by_user_id=lead.created_by_user_id,
        next_follow_up=lead.next_follow_up, last_contact=lead.last_contact,
        converted_at=lead.converted_at, converted_to_order_id=lead.converted_to_order_id,
        notes=lead.notes, rejection_reason=lead.rejection_reason,
        created_at=lead.created_at, updated_at=lead.updated_at
    )


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    request: LeadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update lead"""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.business_id == current_user.business_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            value = LeadStatus(value)
        setattr(lead, field, value)
    
    db.commit()
    db.refresh(lead)
    
    return LeadResponse(
        id=lead.id, business_id=lead.business_id, name=lead.name, phone=lead.phone,
        email=lead.email, company_name=lead.company_name, company_size=lead.company_size,
        industry=lead.industry, address=lead.address, city=lead.city, state=lead.state,
        product_interest=lead.product_interest, service_interest=lead.service_interest,
        estimated_value=lead.estimated_value, source=lead.source.value,
        source_details=lead.source_details, status=lead.status.value,
        assigned_to_user_id=lead.assigned_to_user_id, created_by_user_id=lead.created_by_user_id,
        next_follow_up=lead.next_follow_up, last_contact=lead.last_contact,
        converted_at=lead.converted_at, converted_to_order_id=lead.converted_to_order_id,
        notes=lead.notes, rejection_reason=lead.rejection_reason,
        created_at=lead.created_at, updated_at=lead.updated_at
    )


@router.post("/{lead_id}/convert")
async def convert_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Convert lead to order"""
    from datetime import datetime
    
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.business_id == current_user.business_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.status = LeadStatus.CONVERTED
    lead.converted_at = datetime.utcnow().isoformat()
    db.commit()
    
    return {"success": True, "message": "Lead converted successfully"}


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete lead"""
    if not current_user.has_permission("leads.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.business_id == current_user.business_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Prevent deleting converted leads
    if lead.status == LeadStatus.CONVERTED:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete converted leads"
        )
    
    db.delete(lead)
    db.commit()
    
    return {"success": True, "message": "Lead deleted successfully"}
