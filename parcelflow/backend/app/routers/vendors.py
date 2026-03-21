"""
Vendors Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.vendor import Vendor
from app.models.stock_request import StockInboundRequest, StockRequestStatus
from app.models.inventory import Inventory
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorResponse, VendorListResponse
from app.schemas.stock_request import StockRequestReview, StockRequestReception
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=VendorListResponse)
async def list_vendors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List vendors"""
    query = db.query(Vendor).filter(Vendor.business_id == current_user.business_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(Vendor.name.ilike(search_term))
    
    total = query.count()
    offset = (page - 1) * page_size
    vendors = query.offset(offset).limit(page_size).all()
    
    items = [VendorResponse(
        id=v.id, business_id=v.business_id, name=v.name, code=v.code,
        contact_person=v.contact_person, phone=v.phone, email=v.email,
        address=v.address, city=v.city, state=v.state, country=v.country,
        business_type=v.business_type, tax_id=v.tax_id, bank_name=v.bank_name,
        account_name=v.account_name, account_number=v.account_number,
        remittance_fee=v.remittance_fee or Decimal("0"),
        settlement_cycle=v.settlement_cycle, settlement_day=v.settlement_day,
        is_active=v.is_active, api_key=v.api_key, notes=v.notes,
        created_at=v.created_at, updated_at=v.updated_at
    ) for v in vendors]
    
    return VendorListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    request: VendorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create vendor"""
    if not current_user.has_permission("vendors.manage"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    vendor = Vendor(
        business_id=current_user.business_id,
        name=request.name,
        code=request.code,
        contact_person=request.contact_person,
        phone=request.phone,
        email=request.email,
        address=request.address,
        city=request.city,
        state=request.state,
        country=request.country,
        business_type=request.business_type,
        tax_id=request.tax_id,
        bank_name=request.bank_name,
        account_name=request.account_name,
        account_number=request.account_number,
        settlement_cycle=request.settlement_cycle,
        settlement_day=request.settlement_day,
        notes=request.notes
    )
    
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return VendorResponse(
        id=vendor.id, business_id=vendor.business_id, name=vendor.name, code=vendor.code,
        contact_person=vendor.contact_person, phone=vendor.phone, email=vendor.email,
        address=vendor.address, city=vendor.city, state=vendor.state, country=vendor.country,
        business_type=vendor.business_type, tax_id=vendor.tax_id, bank_name=vendor.bank_name,
        account_name=vendor.account_name, account_number=vendor.account_number,
        remittance_fee=vendor.remittance_fee or Decimal("0"),
        settlement_cycle=vendor.settlement_cycle, settlement_day=vendor.settlement_day,
        is_active=vendor.is_active, api_key=vendor.api_key, notes=vendor.notes,
        created_at=vendor.created_at, updated_at=vendor.updated_at
    )


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get vendor by ID"""
    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.business_id == current_user.business_id
    ).first()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return VendorResponse(
        id=vendor.id, business_id=vendor.business_id, name=vendor.name, code=vendor.code,
        contact_person=vendor.contact_person, phone=vendor.phone, email=vendor.email,
        address=vendor.address, city=vendor.city, state=vendor.state, country=vendor.country,
        business_type=vendor.business_type, tax_id=vendor.tax_id, bank_name=vendor.bank_name,
        account_name=vendor.account_name, account_number=vendor.account_number,
        remittance_fee=vendor.remittance_fee or Decimal("0"),
        settlement_cycle=vendor.settlement_cycle, settlement_day=vendor.settlement_day,
        is_active=vendor.is_active, api_key=vendor.api_key, notes=vendor.notes,
        created_at=vendor.created_at, updated_at=vendor.updated_at
    )


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: int,
    request: VendorUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update vendor"""
    if not current_user.has_permission("vendors.manage"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.business_id == current_user.business_id
    ).first()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)
    
    db.commit()
    db.refresh(vendor)
    
    return VendorResponse(
        id=vendor.id, business_id=vendor.business_id, name=vendor.name, code=vendor.code,
        contact_person=vendor.contact_person, phone=vendor.phone, email=vendor.email,
        address=vendor.address, city=vendor.city, state=vendor.state, country=vendor.country,
        business_type=vendor.business_type, tax_id=vendor.tax_id, bank_name=vendor.bank_name,
        account_name=vendor.account_name, account_number=vendor.account_number,
        remittance_fee=vendor.remittance_fee or Decimal("0"),
        settlement_cycle=vendor.settlement_cycle, settlement_day=vendor.settlement_day,
        is_active=vendor.is_active, api_key=vendor.api_key, notes=vendor.notes,
        created_at=vendor.created_at, updated_at=vendor.updated_at
    )


@router.post("/{vendor_id}/generate-api-key")
async def generate_vendor_api_key(
    vendor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate or regenerate API key for vendor portal access"""
    if not current_user.has_permission("vendors.manage"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.business_id == current_user.business_id
    ).first()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Generate new API key
    vendor.api_key = Vendor.generate_api_key()
    db.commit()
    
    return {
        "success": True,
        "api_key": vendor.api_key,
        "message": "API key generated. Share this with the vendor for portal access."
    }


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete vendor (soft delete by deactivating)"""
    if not current_user.has_permission("vendors.manage"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.business_id == current_user.business_id
    ).first()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Soft delete - deactivate instead of hard delete
    vendor.is_active = False
    db.commit()
    
    return None


# ============ STOCK REQUEST MANAGEMENT (ADMIN) ============

@router.get("/{vendor_id}/stock-requests")
async def list_vendor_stock_requests_admin(
    vendor_id: int,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List stock requests for a vendor (admin view)"""
    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.business_id == current_user.business_id
    ).first()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    query = db.query(StockInboundRequest).filter(StockInboundRequest.vendor_id == vendor_id)
    
    if status:
        query = query.filter(StockInboundRequest.status == status)
    
    total = query.count()
    offset = (page - 1) * page_size
    requests = query.order_by(StockInboundRequest.created_at.desc()).offset(offset).limit(page_size).all()
    
    return {
        "items": [
            {
                "id": r.id,
                "request_number": r.request_number,
                "product_id": r.product_id,
                "product_name": r.product.name if r.product else r.product_name,
                "product_sku": r.product.sku if r.product else r.product_sku,
                "warehouse_id": r.warehouse_id,
                "warehouse_name": r.warehouse.name if r.warehouse else None,
                "quantity": r.quantity,
                "unit_cost": float(r.unit_cost) if r.unit_cost else 0,
                "status": r.status.value if hasattr(r.status, 'value') else r.status,
                "expected_delivery_date": r.expected_delivery_date,
                "tracking_number": r.tracking_number,
                "carrier": r.carrier,
                "review_notes": r.review_notes,
                "reception_notes": r.reception_notes,
                "received_quantity": r.received_quantity,
                "vendor_notes": r.vendor_notes,
                "notes": r.notes,
                "reviewed_at": r.reviewed_at,
                "received_at": r.received_at,
                "created_at": r.created_at,
                "updated_at": r.updated_at
            }
            for r in requests
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/{vendor_id}/stock-requests/{request_id}/review")
async def review_stock_request(
    vendor_id: int,
    request_id: int,
    review: StockRequestReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin review of stock request (approve/reject)"""
    if not (current_user.has_permission("inventory.manage") or 
            current_user.has_permission("inventory.update") or
            current_user.has_permission("vendors.manage")):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.business_id == current_user.business_id
    ).first()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    stock_request = db.query(StockInboundRequest).filter(
        StockInboundRequest.id == request_id,
        StockInboundRequest.vendor_id == vendor_id
    ).first()
    
    if not stock_request:
        raise HTTPException(status_code=404, detail="Stock request not found")
    
    if stock_request.status != StockRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only review pending requests")
    
    # Update status
    if review.status == "approved":
        stock_request.status = StockRequestStatus.APPROVED
    elif review.status == "rejected":
        stock_request.status = StockRequestStatus.REJECTED
    else:
        raise HTTPException(status_code=400, detail="Invalid status. Use 'approved' or 'rejected'")
    
    stock_request.reviewed_by = current_user.id
    stock_request.reviewed_at = datetime.utcnow().isoformat()
    stock_request.review_notes = review.review_notes
    
    # Optionally change warehouse
    if review.warehouse_id:
        from app.models.warehouse import Warehouse
        warehouse = db.query(Warehouse).filter(
            Warehouse.id == review.warehouse_id,
            Warehouse.business_id == current_user.business_id
        ).first()
        if warehouse:
            stock_request.warehouse_id = review.warehouse_id
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Stock request {review.status}",
        "status": stock_request.status.value
    }


@router.post("/{vendor_id}/stock-requests/{request_id}/receive")
async def receive_stock_request(
    vendor_id: int,
    request_id: int,
    reception: StockRequestReception,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Confirm stock reception and add to inventory"""
    if not (current_user.has_permission("inventory.manage") or 
            current_user.has_permission("inventory.update") or
            current_user.has_permission("vendors.manage")):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.business_id == current_user.business_id
    ).first()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    stock_request = db.query(StockInboundRequest).filter(
        StockInboundRequest.id == request_id,
        StockInboundRequest.vendor_id == vendor_id
    ).first()
    
    if not stock_request:
        raise HTTPException(status_code=404, detail="Stock request not found")
    
    if stock_request.status != StockRequestStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Can only receive approved requests")
    
    # Update stock request
    stock_request.status = StockRequestStatus.RECEIVED
    stock_request.received_by = current_user.id
    stock_request.received_at = datetime.utcnow().isoformat()
    stock_request.received_quantity = reception.received_quantity
    stock_request.reception_notes = reception.reception_notes
    
    # Add to inventory
    if stock_request.product_id and stock_request.warehouse_id:
        # Check if inventory record exists
        inventory = db.query(Inventory).filter(
            Inventory.product_id == stock_request.product_id,
            Inventory.warehouse_id == stock_request.warehouse_id,
            Inventory.vendor_id == vendor_id
        ).first()
        
        if inventory:
            # Update existing inventory
            inventory.quantity += reception.received_quantity
            inventory.updated_at = datetime.utcnow().isoformat()
        else:
            # Create new inventory record
            inventory = Inventory(
                business_id=current_user.business_id,
                product_id=stock_request.product_id,
                warehouse_id=stock_request.warehouse_id,
                vendor_id=vendor_id,
                quantity=reception.received_quantity,
                unit_cost=stock_request.unit_cost,
                reserved_quantity=0
            )
            db.add(inventory)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Stock received and added to inventory",
        "received_quantity": reception.received_quantity
    }
