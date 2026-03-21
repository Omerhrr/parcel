"""
Inventory Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.inventory import Inventory, StockMovement, MovementType
from app.schemas.inventory import (
    InventoryResponse, InventoryUpdate, InventoryListResponse,
    StockMovementCreate, StockMovementResponse, StockMovementListResponse
)
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=InventoryListResponse)
async def list_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    low_stock: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List inventory"""
    from app.schemas.inventory import InventoryResponse, ProductBrief, WarehouseBrief
    
    if not current_user.has_permission("inventory.view"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    query = db.query(Inventory).join(
        Inventory.product
    ).filter(
        Inventory.product.has(business_id=current_user.business_id)
    )
    
    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)
    
    if vendor_id:
        query = query.filter(Inventory.vendor_id == vendor_id)
    
    if low_stock:
        query = query.filter(Inventory.quantity <= Inventory.reorder_level)
    
    total = query.count()
    offset = (page - 1) * page_size
    inventory = query.offset(offset).limit(page_size).all()
    
    items = []
    for i in inventory:
        # Build product brief
        product_brief = None
        if i.product:
            product_brief = ProductBrief(
                id=i.product.id,
                name=i.product.name,
                sku=i.product.sku
            )
        
        # Build warehouse brief
        warehouse_brief = None
        if i.warehouse:
            warehouse_brief = WarehouseBrief(
                id=i.warehouse.id,
                name=i.warehouse.name,
                code=i.warehouse.code
            )
        
        items.append(InventoryResponse(
            id=i.id, product_id=i.product_id, warehouse_id=i.warehouse_id,
            quantity=i.quantity, reserved_quantity=i.reserved_quantity,
            available_quantity=i.available_quantity, reorder_level=i.reorder_level,
            max_level=i.max_level, bin_location=i.bin_location,
            created_at=i.created_at, updated_at=i.updated_at,
            product=product_brief, warehouse=warehouse_brief
        ))
    
    return InventoryListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/movements", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_movement(
    request: StockMovementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create stock movement (in/out/transfer)"""
    if not current_user.has_permission("inventory.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Verify product belongs to user's business
    from app.models.product import Product
    product = db.query(Product).filter(
        Product.id == request.product_id,
        Product.business_id == current_user.business_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=400, detail="Product not found or access denied")
    
    # Verify warehouse belongs to user's business
    from app.models.warehouse import Warehouse
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == request.warehouse_id,
        Warehouse.business_id == current_user.business_id
    ).first()
    
    if not warehouse:
        raise HTTPException(status_code=400, detail="Warehouse not found or access denied")
    
    # For transfers, verify destination warehouse too
    if request.movement_type == "transfer" and request.to_warehouse_id:
        dest_warehouse = db.query(Warehouse).filter(
            Warehouse.id == request.to_warehouse_id,
            Warehouse.business_id == current_user.business_id
        ).first()
        
        if not dest_warehouse:
            raise HTTPException(status_code=400, detail="Destination warehouse not found or access denied")
    
    # Get current inventory
    inventory = db.query(Inventory).filter(
        Inventory.product_id == request.product_id,
        Inventory.warehouse_id == request.warehouse_id
    ).first()
    
    if not inventory:
        # Create inventory record if not exists
        inventory = Inventory(
            product_id=request.product_id,
            warehouse_id=request.warehouse_id,
            quantity=0
        )
        db.add(inventory)
        db.flush()
    
    # Update quantity based on movement type
    if request.movement_type == "in":
        inventory.quantity += request.quantity
    elif request.movement_type == "out":
        if inventory.quantity < request.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        inventory.quantity -= request.quantity
    elif request.movement_type == "transfer" and request.to_warehouse_id:
        # Transfer out from current warehouse
        if inventory.quantity < request.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        inventory.quantity -= request.quantity
        
        # Transfer in to destination warehouse
        dest_inventory = db.query(Inventory).filter(
            Inventory.product_id == request.product_id,
            Inventory.warehouse_id == request.to_warehouse_id
        ).first()
        
        if not dest_inventory:
            dest_inventory = Inventory(
                product_id=request.product_id,
                warehouse_id=request.to_warehouse_id,
                quantity=0
            )
            db.add(dest_inventory)
            db.flush()
        
        dest_inventory.quantity += request.quantity
    
    inventory.update_available()
    
    # Create movement record
    movement = StockMovement(
        product_id=request.product_id,
        warehouse_id=request.warehouse_id,
        movement_type=MovementType(request.movement_type),
        quantity=request.quantity,
        reference_type=request.reference_type,
        reference_id=request.reference_id,
        from_warehouse_id=request.from_warehouse_id,
        to_warehouse_id=request.to_warehouse_id,
        unit_cost=request.unit_cost,
        balance_after=inventory.quantity,
        performed_by=current_user.id,
        notes=request.notes
    )
    
    db.add(movement)
    db.commit()
    db.refresh(movement)
    
    # Build nested objects for response
    from app.schemas.inventory import ProductBrief, WarehouseBrief
    product_brief = ProductBrief(
        id=product.id,
        name=product.name,
        sku=product.sku
    ) if product else None
    
    warehouse_brief = WarehouseBrief(
        id=warehouse.id,
        name=warehouse.name,
        code=warehouse.code
    ) if warehouse else None
    
    return StockMovementResponse(
        id=movement.id, product_id=movement.product_id,
        warehouse_id=movement.warehouse_id,
        movement_type=movement.movement_type.value,
        quantity=movement.quantity, reference_type=movement.reference_type,
        reference_id=movement.reference_id, from_warehouse_id=movement.from_warehouse_id,
        to_warehouse_id=movement.to_warehouse_id, balance_after=movement.balance_after,
        unit_cost=movement.unit_cost, total_cost=movement.total_cost,
        performed_by=movement.performed_by, notes=movement.notes,
        created_at=movement.created_at, updated_at=movement.updated_at,
        product=product_brief, warehouse=warehouse_brief
    )


@router.get("/movements", response_model=StockMovementListResponse)
async def list_stock_movements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    product_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List stock movements"""
    from app.schemas.inventory import ProductBrief, WarehouseBrief
    
    query = db.query(StockMovement).join(
        StockMovement.product
    ).filter(
        StockMovement.product.has(business_id=current_user.business_id)
    )
    
    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    
    if vendor_id:
        # Filter by vendor_id through the product relationship
        query = query.filter(StockMovement.product.has(vendor_id=vendor_id))
    
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)
    
    total = query.count()
    offset = (page - 1) * page_size
    movements = query.order_by(StockMovement.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = []
    for m in movements:
        # Build product brief
        product_brief = None
        if m.product:
            product_brief = ProductBrief(
                id=m.product.id,
                name=m.product.name,
                sku=m.product.sku
            )
        
        # Build warehouse brief
        warehouse_brief = None
        if m.warehouse:
            warehouse_brief = WarehouseBrief(
                id=m.warehouse.id,
                name=m.warehouse.name,
                code=m.warehouse.code
            )
        
        items.append(StockMovementResponse(
            id=m.id, product_id=m.product_id, warehouse_id=m.warehouse_id,
            movement_type=m.movement_type.value, quantity=m.quantity,
            reference_type=m.reference_type, reference_id=m.reference_id,
            from_warehouse_id=m.from_warehouse_id, to_warehouse_id=m.to_warehouse_id,
            balance_after=m.balance_after, unit_cost=m.unit_cost, total_cost=m.total_cost,
            performed_by=m.performed_by, notes=m.notes,
            created_at=m.created_at, updated_at=m.updated_at,
            product=product_brief, warehouse=warehouse_brief
        ))
    
    return StockMovementListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )
