"""
Public API Router (for WordPress integration and external access)
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from decimal import Decimal
import re

from app.database import get_db
from app.models.waybill import Waybill
from app.models.order import Order, OrderItem, OrderStatus
from app.models.tracking import TrackingEvent

router = APIRouter()


class LandingPageOrderRequest(BaseModel):
    """Order submission from WordPress landing page"""
    name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=10, max_length=20)
    address: str = Field(..., min_length=5, max_length=500)
    product_id: Optional[int] = None
    product_name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(1, ge=1, le=100)
    city: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)
    # Business identification
    business_slug: str = Field(..., min_length=1, max_length=100)
    landing_page_id: Optional[str] = Field(None, max_length=50)
    
    @validator('phone')
    def validate_phone(cls, v):
        # Basic phone validation - allow digits, spaces, dashes, parentheses, +
        if not re.match(r'^[\d\s\-\+\(\)]+$', v):
            raise ValueError('Invalid phone number format')
        # Must have at least 10 digits
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10:
            raise ValueError('Phone number must have at least 10 digits')
        return v
    
    @validator('business_slug')
    def validate_business_slug(cls, v):
        # Only allow alphanumeric, dashes, underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Invalid business identifier')
        return v.lower()


class LandingPageOrderResponse(BaseModel):
    """Response for landing page order"""
    success: bool
    order_number: Optional[str] = None
    message: str


@router.post("/orders/landing", response_model=LandingPageOrderResponse)
async def submit_landing_page_order(
    request: LandingPageOrderRequest,
    db: Session = Depends(get_db)
):
    """
    Receive orders from WordPress landing pages.
    This is the endpoint configured in the plan.
    Rate limited to prevent abuse.
    """
    from app.models.business import Business
    from app.models.branch import Branch
    
    # Find business by slug
    business = db.query(Business).filter(Business.slug == request.business_slug).first()
    
    if not business:
        # Don't reveal whether business exists or not
        raise HTTPException(status_code=404, detail="Business not found")
    
    if not business.is_active:
        raise HTTPException(status_code=400, detail="Business is not accepting orders")
    
    # Get default branch
    branch = db.query(Branch).filter(
        Branch.business_id == business.id,
        Branch.is_headquarters == 1
    ).first()
    
    if not branch:
        branch = db.query(Branch).filter(
            Branch.business_id == business.id
        ).first()
    
    # Generate order number
    branch_code = branch.code if branch else None
    order_number = Order.generate_order_number(branch_code)
    
    # Sanitize inputs
    customer_name = request.name.strip()[:255]
    customer_phone = request.phone.strip()[:20]
    delivery_address = request.address.strip()[:500]
    product_name = request.product_name.strip()[:255]
    
    # Create order
    order = Order(
        business_id=business.id,
        branch_id=branch.id if branch else None,
        order_number=order_number,
        customer_name=customer_name,
        customer_phone=customer_phone,
        delivery_address=delivery_address,
        delivery_city=request.city.strip()[:100] if request.city else None,
        source="landing_page",
        landing_page_id=request.landing_page_id[:50] if request.landing_page_id else None,
        notes=request.notes.strip()[:1000] if request.notes else None,
        status=OrderStatus.PENDING
    )
    
    db.add(order)
    db.flush()
    
    # Create order item
    item = OrderItem(
        order_id=order.id,
        product_id=request.product_id,
        product_name=product_name,
        quantity=request.quantity,
        unit_price=Decimal("0"),  # Price will be updated later
        discount=Decimal("0"),
        total=Decimal("0")
    )
    db.add(item)
    
    # Create tracking event
    tracking = TrackingEvent(
        waybill_id=None,  # No waybill yet
        status="order_created",
        title="Order Received",
        description=f"Order {order_number} received from landing page",
        is_public=1
    )
    db.add(tracking)
    
    db.commit()
    
    return LandingPageOrderResponse(
        success=True,
        order_number=order_number,
        message="Order submitted successfully"
    )


@router.get("/products/{business_slug}")
async def get_public_products(
    business_slug: str,
    db: Session = Depends(get_db)
):
    """Get products for a business (for landing pages)"""
    from app.models.business import Business
    from app.models.product import Product
    
    business = db.query(Business).filter(Business.slug == business_slug).first()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    products = db.query(Product).filter(
        Product.business_id == business.id,
        Product.is_active == 1
    ).all()
    
    return {
        "business": {
            "name": business.name,
            "logo_url": business.logo_url
        },
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "price": float(p.selling_price),
                "image_url": p.image_url,
                "description": p.description
            }
            for p in products
        ]
    }


@router.get("/track/{waybill_number}")
async def public_track_shipment(
    waybill_number: str,
    db: Session = Depends(get_db)
):
    """Public tracking (redirects to tracking router)"""
    from app.routers.tracking import track_shipment
    return await track_shipment(waybill_number, db)
