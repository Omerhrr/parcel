"""
Products Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.product import Product, ProductPrice
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    vendor_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List products"""
    query = db.query(Product).filter(Product.business_id == current_user.business_id)
    
    if category:
        query = query.filter(Product.category == category)
    if vendor_id:
        query = query.filter(Product.vendor_id == vendor_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_term)) |
            (Product.sku.ilike(search_term))
        )
    
    total = query.count()
    offset = (page - 1) * page_size
    products = query.offset(offset).limit(page_size).all()
    
    items = [ProductResponse(
        id=p.id, business_id=p.business_id, vendor_id=p.vendor_id,
        name=p.name, sku=p.sku, barcode=p.barcode, description=p.description,
        category=p.category, weight=p.weight, length=p.length, width=p.width,
        height=p.height, cost_price=p.cost_price, selling_price=p.selling_price,
        pricing_type=p.pricing_type or "fixed", is_active=p.is_active, image_url=p.image_url,
        pricing_matrix=[],
        created_at=p.created_at, updated_at=p.updated_at
    ) for p in products]
    
    return ProductListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    request: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create product"""
    if not current_user.has_permission("inventory.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    product = Product(
        business_id=current_user.business_id,
        vendor_id=request.vendor_id,
        name=request.name,
        sku=request.sku,
        barcode=request.barcode,
        description=request.description,
        category=request.category,
        weight=request.weight,
        length=request.length,
        width=request.width,
        height=request.height,
        cost_price=request.cost_price,
        selling_price=request.selling_price,
        pricing_type=request.pricing_type or "fixed",
        image_url=request.image_url
    )
    
    db.add(product)
    db.flush()  # Get the product ID
    
    # Create pricing tiers if provided
    if request.price_tiers:
        for tier_data in request.price_tiers:
            tier = ProductPrice(
                product_id=product.id,
                min_quantity=tier_data.min_quantity,
                max_quantity=tier_data.max_quantity,
                price=tier_data.price,
                total_price=tier_data.total_price,
                is_buy_x_get_y=1 if tier_data.is_buy_x_get_y else 0,
                buy_quantity=tier_data.buy_quantity,
                get_quantity=tier_data.get_quantity,
                label=tier_data.label,
                priority=tier_data.priority
            )
            db.add(tier)
    
    db.commit()
    db.refresh(product)
    
    # Build pricing matrix for response
    pricing_matrix = [
        {
            "id": t.id,
            "product_id": t.product_id,
            "min_quantity": t.min_quantity,
            "max_quantity": t.max_quantity,
            "price": t.price,
            "total_price": t.total_price,
            "is_buy_x_get_y": t.is_buy_x_get_y,
            "buy_quantity": t.buy_quantity,
            "get_quantity": t.get_quantity,
            "label": t.label,
            "priority": t.priority,
            "is_active": t.is_active,
            "created_at": t.created_at,
            "updated_at": t.updated_at
        }
        for t in product.pricing_matrix
    ] if product.pricing_matrix else []
    
    return ProductResponse(
        id=product.id, business_id=product.business_id, vendor_id=product.vendor_id,
        name=product.name, sku=product.sku, barcode=product.barcode,
        description=product.description, category=product.category,
        weight=product.weight, length=product.length, width=product.width,
        height=product.height, cost_price=product.cost_price,
        selling_price=product.selling_price, pricing_type=product.pricing_type or "fixed",
        is_active=product.is_active, image_url=product.image_url,
        pricing_matrix=pricing_matrix,
        created_at=product.created_at, updated_at=product.updated_at
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get product by ID"""
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == current_user.business_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Build pricing matrix for response
    pricing_matrix = [
        {
            "id": t.id,
            "product_id": t.product_id,
            "min_quantity": t.min_quantity,
            "max_quantity": t.max_quantity,
            "price": t.price,
            "total_price": t.total_price,
            "is_buy_x_get_y": t.is_buy_x_get_y,
            "buy_quantity": t.buy_quantity,
            "get_quantity": t.get_quantity,
            "label": t.label,
            "priority": t.priority,
            "is_active": t.is_active,
            "created_at": t.created_at,
            "updated_at": t.updated_at
        }
        for t in product.pricing_matrix
    ] if product.pricing_matrix else []
    
    return ProductResponse(
        id=product.id, business_id=product.business_id, vendor_id=product.vendor_id,
        name=product.name, sku=product.sku, barcode=product.barcode,
        description=product.description, category=product.category,
        weight=product.weight, length=product.length, width=product.width,
        height=product.height, cost_price=product.cost_price,
        selling_price=product.selling_price, pricing_type=product.pricing_type or "fixed",
        is_active=product.is_active, image_url=product.image_url,
        pricing_matrix=pricing_matrix,
        created_at=product.created_at, updated_at=product.updated_at
    )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    request: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update product"""
    if not current_user.has_permission("inventory.update"):
        raise HTTPException(status_code=403, detail="Permission denied")

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == current_user.business_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update basic fields
    if request.vendor_id is not None:
        product.vendor_id = request.vendor_id
    if request.name is not None:
        product.name = request.name
    if request.sku is not None:
        product.sku = request.sku
    if request.barcode is not None:
        product.barcode = request.barcode
    if request.description is not None:
        product.description = request.description
    if request.category is not None:
        product.category = request.category
    if request.weight is not None:
        product.weight = request.weight
    if request.length is not None:
        product.length = request.length
    if request.width is not None:
        product.width = request.width
    if request.height is not None:
        product.height = request.height
    if request.cost_price is not None:
        product.cost_price = request.cost_price
    if request.selling_price is not None:
        product.selling_price = request.selling_price
    if request.pricing_type is not None:
        product.pricing_type = request.pricing_type
    if request.image_url is not None:
        product.image_url = request.image_url
    if request.is_active is not None:
        product.is_active = request.is_active
    
    # Update pricing tiers if provided
    if request.price_tiers is not None:
        # Remove existing tiers
        db.query(ProductPrice).filter(ProductPrice.product_id == product_id).delete()
        
        # Add new tiers
        for tier_data in request.price_tiers:
            tier = ProductPrice(
                product_id=product.id,
                min_quantity=tier_data.min_quantity,
                max_quantity=tier_data.max_quantity,
                price=tier_data.price,
                total_price=tier_data.total_price,
                is_buy_x_get_y=1 if tier_data.is_buy_x_get_y else 0,
                buy_quantity=tier_data.buy_quantity,
                get_quantity=tier_data.get_quantity,
                label=tier_data.label,
                priority=tier_data.priority
            )
            db.add(tier)

    db.commit()
    db.refresh(product)

    # Build pricing matrix for response
    pricing_matrix = [
        {
            "id": t.id,
            "product_id": t.product_id,
            "min_quantity": t.min_quantity,
            "max_quantity": t.max_quantity,
            "price": t.price,
            "total_price": t.total_price,
            "is_buy_x_get_y": t.is_buy_x_get_y,
            "buy_quantity": t.buy_quantity,
            "get_quantity": t.get_quantity,
            "label": t.label,
            "priority": t.priority,
            "is_active": t.is_active,
            "created_at": t.created_at,
            "updated_at": t.updated_at
        }
        for t in product.pricing_matrix
    ] if product.pricing_matrix else []

    return ProductResponse(
        id=product.id, business_id=product.business_id, vendor_id=product.vendor_id,
        name=product.name, sku=product.sku, barcode=product.barcode,
        description=product.description, category=product.category,
        weight=product.weight, length=product.length, width=product.width,
        height=product.height, cost_price=product.cost_price,
        selling_price=product.selling_price, pricing_type=product.pricing_type or "fixed",
        is_active=product.is_active, image_url=product.image_url,
        pricing_matrix=pricing_matrix,
        created_at=product.created_at, updated_at=product.updated_at
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete product"""
    if not current_user.has_permission("inventory.delete"):
        raise HTTPException(status_code=403, detail="Permission denied")

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == current_user.business_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

    return None
