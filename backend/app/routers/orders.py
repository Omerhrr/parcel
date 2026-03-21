"""
Orders Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus, PaymentMethod
from app.models.product import Product, ProductPrice
from app.models.vendor import Vendor
from app.schemas.order import (
    OrderCreate, OrderUpdate, OrderResponse, OrderListResponse,
    OrderItemCreate, OrderItemResponse, OrderAssignmentCreate,
    PriceCalculationRequest, PriceCalculationResponse
)
from app.utils.auth import get_current_user
from app.utils.notifications import notify_new_order, notify_payment_received
from app.services.audit import AuditService

router = APIRouter()


def calculate_product_price(db: Session, product_id: int, quantity: int) -> dict:
    """
    Calculate price for a product based on pricing matrix.
    Returns dict with unit_price, total_price, tier_label, etc.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None
    
    result = {
        'product_id': product.id,
        'product_name': product.name,
        'vendor_id': product.vendor_id,
        'quantity': quantity,
        'unit_price': float(product.selling_price or 0),
        'total_price': float(product.selling_price or 0) * quantity,
        'applied_tier_label': None,
        'is_buy_x_get_y': False,
        'free_quantity': 0
    }
    
    # If fixed pricing or no pricing matrix, return base price
    if product.pricing_type == 'fixed' or not product.pricing_matrix:
        return result
    
    # Find applicable price tier (sorted by priority desc, then min_quantity desc)
    applicable_tier = None
    for tier in sorted(product.pricing_matrix, key=lambda t: (-t.priority, -t.min_quantity)):
        if quantity >= tier.min_quantity:
            if tier.max_quantity is None or quantity <= tier.max_quantity:
                applicable_tier = tier
                break
    
    if not applicable_tier:
        return result
    
    # Apply the tier pricing
    result['applied_tier_label'] = applicable_tier.label
    
    # Handle Buy X Get Y deals
    if applicable_tier.is_buy_x_get_y and applicable_tier.buy_quantity and applicable_tier.get_quantity:
        result['is_buy_x_get_y'] = True
        # Calculate how many free items
        sets = quantity // applicable_tier.buy_quantity
        free_items = sets * applicable_tier.get_quantity
        result['free_quantity'] = free_items
        result['total_price'] = float(applicable_tier.price or product.selling_price or 0) * quantity
        result['unit_price'] = result['total_price'] / quantity if quantity > 0 else 0
    elif applicable_tier.total_price:
        # Fixed total price for the quantity (e.g., 2 for ₦30,000)
        result['total_price'] = float(applicable_tier.total_price)
        result['unit_price'] = result['total_price'] / quantity if quantity > 0 else 0
    else:
        # Unit price for this tier
        result['unit_price'] = float(applicable_tier.price or product.selling_price or 0)
        result['total_price'] = result['unit_price'] * quantity
    
    return result


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    vendor_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List orders with filters"""
    query = db.query(Order).filter(Order.business_id == current_user.business_id)
    
    if status:
        query = query.filter(Order.status == status)
    if vendor_id:
        query = query.filter(Order.vendor_id == vendor_id)
    if branch_id:
        query = query.filter(Order.branch_id == branch_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Order.order_number.ilike(search_term)) |
            (Order.customer_name.ilike(search_term)) |
            (Order.customer_phone.ilike(search_term))
        )
    
    total = query.count()
    offset = (page - 1) * page_size
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = []
    for o in orders:
        order_items = [OrderItemResponse(
            id=i.id, order_id=i.order_id, product_id=i.product_id,
            product_name=i.product_name, product_sku=i.product_sku,
            quantity=i.quantity, unit_price=i.unit_price, discount=i.discount,
            total=i.total, notes=i.notes
        ) for i in o.items] if o.items else []
        
        items.append(OrderResponse(
            id=o.id, order_number=o.order_number, business_id=o.business_id,
            branch_id=o.branch_id, vendor_id=o.vendor_id,
            customer_name=o.customer_name, customer_phone=o.customer_phone, 
            customer_email=o.customer_email,
            delivery_address=o.delivery_address, delivery_city=o.delivery_city,
            delivery_state=o.delivery_state, delivery_landmark=o.delivery_landmark,
            subtotal=o.subtotal, delivery_fee=o.delivery_fee, discount=o.discount,
            tax=o.tax, total_amount=o.total_amount,
            remittance_fee=o.remittance_fee or Decimal("0"),
            vendor_amount=o.vendor_amount or Decimal("0"),
            remittance_status=o.remittance_status or "pending",
            payment_method=o.payment_method.value if isinstance(o.payment_method, PaymentMethod) else o.payment_method,
            payment_status=o.payment_status.value if hasattr(o.payment_status, 'value') else o.payment_status,
            payment_reference=o.payment_reference, paid_at=o.paid_at, 
            status=o.status.value if hasattr(o.status, 'value') else o.status,
            source=o.source, landing_page_id=o.landing_page_id,
            confirmed_at=o.confirmed_at, shipped_at=o.shipped_at, 
            delivered_at=o.delivered_at, remitted_at=o.remitted_at,
            notes=o.notes, cancellation_reason=o.cancellation_reason,
            created_at=o.created_at, updated_at=o.updated_at,
            items=order_items
        ))
    
    return OrderListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.post("/calculate-price", response_model=PriceCalculationResponse)
async def calculate_price(
    request: PriceCalculationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate price for a product based on pricing matrix"""
    result = calculate_product_price(db, request.product_id, request.quantity)
    
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get vendor name if applicable
    vendor_name = None
    if result['vendor_id']:
        vendor = db.query(Vendor).filter(Vendor.id == result['vendor_id']).first()
        if vendor:
            vendor_name = vendor.name
    
    return PriceCalculationResponse(
        product_id=result['product_id'],
        product_name=result['product_name'],
        vendor_id=result['vendor_id'],
        vendor_name=vendor_name,
        quantity=result['quantity'],
        unit_price=Decimal(str(result['unit_price'])),
        total_price=Decimal(str(result['total_price'])),
        applied_tier_label=result['applied_tier_label'],
        is_buy_x_get_y=result['is_buy_x_get_y'],
        free_quantity=result['free_quantity']
    )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new order with pricing matrix support and remittance calculation"""
    # Generate order number
    order_number = Order.generate_order_number()
    
    # Determine primary vendor and calculate prices using pricing matrix
    primary_vendor_id = request.vendor_id
    subtotal = Decimal("0")
    processed_items = []
    vendor_totals = {}  # Track totals per vendor
    
    for item_req in request.items:
        if item_req.product_id:
            # Get product and calculate price using pricing matrix
            price_info = calculate_product_price(db, item_req.product_id, item_req.quantity)
            
            if price_info:
                unit_price = Decimal(str(price_info['total_price'])) / item_req.quantity
                item_total = Decimal(str(price_info['total_price'])) - item_req.discount
                
                # Track vendor totals
                item_vendor_id = price_info['vendor_id']
                if item_vendor_id:
                    if item_vendor_id not in vendor_totals:
                        vendor_totals[item_vendor_id] = Decimal("0")
                    vendor_totals[item_vendor_id] += item_total
                    
                    # Use first vendor as primary if not specified
                    if not primary_vendor_id:
                        primary_vendor_id = item_vendor_id
            else:
                # Product not found, use provided price
                unit_price = item_req.unit_price
                item_total = item_req.quantity * item_req.unit_price - item_req.discount
        else:
            # Manual entry, use provided price
            unit_price = item_req.unit_price
            item_total = item_req.quantity * item_req.unit_price - item_req.discount
        
        subtotal += item_total
        processed_items.append({
            'product_id': item_req.product_id,
            'product_name': item_req.product_name,
            'product_sku': item_req.product_sku,
            'quantity': item_req.quantity,
            'unit_price': unit_price,
            'discount': item_req.discount,
            'total': item_total,
            'notes': item_req.notes
        })
    
    # Calculate total
    total_amount = subtotal + request.delivery_fee + request.tax - request.discount
    
    # Calculate remittance (logistics fee deducted from vendor payment)
    # Remittance fee is per order (single fee for same customer)
    remittance_fee = request.remittance_fee
    
    # Calculate vendor amount (what vendor receives after logistics fee)
    vendor_amount = Decimal("0")
    if primary_vendor_id and primary_vendor_id in vendor_totals:
        vendor_amount = vendor_totals[primary_vendor_id] - remittance_fee
        # If there are multiple vendors, we need to handle differently
        # For now, remittance fee is deducted from primary vendor's total
        if len(vendor_totals) > 1:
            # Multiple vendors - remittance fee comes from subtotal proportionally
            total_vendor_amount = sum(vendor_totals.values())
            vendor_amount = total_vendor_amount - remittance_fee
    
    order = Order(
        business_id=current_user.business_id,
        branch_id=request.branch_id,
        vendor_id=primary_vendor_id,
        order_number=order_number,
        customer_name=request.customer_name,
        customer_phone=request.customer_phone,
        customer_email=request.customer_email,
        delivery_address=request.delivery_address,
        delivery_city=request.delivery_city,
        delivery_state=request.delivery_state,
        delivery_landmark=request.delivery_landmark,
        subtotal=subtotal,
        delivery_fee=request.delivery_fee,
        discount=request.discount,
        tax=request.tax,
        total_amount=total_amount,
        remittance_fee=remittance_fee,
        vendor_amount=max(vendor_amount, Decimal("0")),  # Ensure non-negative
        remittance_status="pending",
        payment_method=PaymentMethod(request.payment_method) if request.payment_method else PaymentMethod.COD,
        source=request.source,
        landing_page_id=request.landing_page_id,
        notes=request.notes,
        created_by_user_id=current_user.id
    )
    
    db.add(order)
    db.flush()
    
    # Create order items
    for item_data in processed_items:
        item = OrderItem(
            order_id=order.id,
            product_id=item_data['product_id'],
            product_name=item_data['product_name'],
            product_sku=item_data['product_sku'],
            quantity=item_data['quantity'],
            unit_price=item_data['unit_price'],
            discount=item_data['discount'],
            total=item_data['total'],
            notes=item_data['notes']
        )
        db.add(item)
    
    # Send notification for new order
    notify_new_order(
        db=db,
        business_id=current_user.business_id,
        order_id=order.id,
        order_number=order_number
    )
    
    # Create audit log
    audit = AuditService(db)
    audit.log_create(
        entity=order,
        user_id=current_user.id,
        business_id=current_user.business_id,
        description=f"Created order {order_number} for {request.customer_name}"
    )
    
    db.commit()
    db.refresh(order)
    
    # Build response with items
    order_items = [OrderItemResponse(
        id=i.id, order_id=i.order_id, product_id=i.product_id,
        product_name=i.product_name, product_sku=i.product_sku,
        quantity=i.quantity, unit_price=i.unit_price, discount=i.discount,
        total=i.total, notes=i.notes
    ) for i in order.items] if order.items else []
    
    return OrderResponse(
        id=order.id, order_number=order.order_number, business_id=order.business_id,
        branch_id=order.branch_id, vendor_id=order.vendor_id,
        customer_name=order.customer_name, customer_phone=order.customer_phone,
        customer_email=order.customer_email,
        delivery_address=order.delivery_address, delivery_city=order.delivery_city,
        delivery_state=order.delivery_state, delivery_landmark=order.delivery_landmark,
        subtotal=order.subtotal, delivery_fee=order.delivery_fee, discount=order.discount,
        tax=order.tax, total_amount=order.total_amount,
        remittance_fee=order.remittance_fee or Decimal("0"),
        vendor_amount=order.vendor_amount or Decimal("0"),
        remittance_status=order.remittance_status or "pending",
        payment_method=order.payment_method.value if isinstance(order.payment_method, PaymentMethod) else order.payment_method,
        payment_status=order.payment_status.value if hasattr(order.payment_status, 'value') else order.payment_status,
        payment_reference=order.payment_reference, paid_at=order.paid_at,
        status=order.status.value if hasattr(order.status, 'value') else order.status,
        source=order.source, landing_page_id=order.landing_page_id,
        confirmed_at=order.confirmed_at, shipped_at=order.shipped_at,
        delivered_at=order.delivered_at, remitted_at=order.remitted_at,
        notes=order.notes, cancellation_reason=order.cancellation_reason,
        created_at=order.created_at, updated_at=order.updated_at,
        items=order_items
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order by ID"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.business_id == current_user.business_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    items = [OrderItemResponse(
        id=i.id, order_id=i.order_id, product_id=i.product_id,
        product_name=i.product_name, product_sku=i.product_sku,
        quantity=i.quantity, unit_price=i.unit_price, discount=i.discount,
        total=i.total, notes=i.notes
    ) for i in order.items]
    
    return OrderResponse(
        id=order.id, order_number=order.order_number, business_id=order.business_id,
        branch_id=order.branch_id, vendor_id=order.vendor_id,
        customer_name=order.customer_name, customer_phone=order.customer_phone,
        customer_email=order.customer_email,
        delivery_address=order.delivery_address, delivery_city=order.delivery_city,
        delivery_state=order.delivery_state, delivery_landmark=order.delivery_landmark,
        subtotal=order.subtotal, delivery_fee=order.delivery_fee, discount=order.discount,
        tax=order.tax, total_amount=order.total_amount,
        remittance_fee=order.remittance_fee or Decimal("0"),
        vendor_amount=order.vendor_amount or Decimal("0"),
        remittance_status=order.remittance_status or "pending",
        payment_method=order.payment_method.value if isinstance(order.payment_method, PaymentMethod) else order.payment_method,
        payment_status=order.payment_status.value if hasattr(order.payment_status, 'value') else order.payment_status,
        payment_reference=order.payment_reference, paid_at=order.paid_at,
        status=order.status.value if hasattr(order.status, 'value') else order.status,
        source=order.source, landing_page_id=order.landing_page_id,
        confirmed_at=order.confirmed_at, shipped_at=order.shipped_at,
        delivered_at=order.delivered_at, remitted_at=order.remitted_at,
        notes=order.notes, cancellation_reason=order.cancellation_reason,
        created_at=order.created_at, updated_at=order.updated_at,
        items=items
    )


@router.put("/{order_id}/status")
async def update_order_status(
    order_id: int,
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update order status"""
    if not current_user.has_permission("orders.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.business_id == current_user.business_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_status = order.status.value if hasattr(order.status, 'value') else order.status
    order.status = OrderStatus(status)
    
    # Update related timestamps
    if status == "confirmed":
        order.confirmed_at = datetime.utcnow().isoformat()
    elif status == "shipped":
        order.shipped_at = datetime.utcnow().isoformat()
    elif status == "delivered":
        order.delivered_at = datetime.utcnow().isoformat()
    
    # Create audit log
    audit = AuditService(db)
    audit.log_status_change(
        entity=order,
        old_status=old_status,
        new_status=status,
        user_id=current_user.id,
        business_id=order.business_id,
        description=f"Status changed from {old_status} to {status} for order {order.order_number}"
    )
    
    db.commit()
    
    return {"success": True, "message": "Order status updated"}


@router.post("/{order_id}/assign")
async def assign_order(
    order_id: int,
    request: OrderAssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign order to user"""
    if not current_user.has_permission("orders.assign"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Verify order belongs to user's business
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.business_id == current_user.business_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify assigned user belongs to same business
    from app.models.user import User
    assigned_user = db.query(User).filter(User.id == request.assigned_to_user_id).first()
    if not assigned_user:
        raise HTTPException(status_code=400, detail="Assigned user not found")
    
    if assigned_user.business_id != current_user.business_id:
        raise HTTPException(status_code=403, detail="Cannot assign order to user from different business")
    
    from app.models.order import OrderAssignment
    
    assignment = OrderAssignment(
        order_id=order_id,
        assigned_to_user_id=request.assigned_to_user_id,
        assigned_by_user_id=current_user.id,
        assigned_at=datetime.utcnow().isoformat(),
        assignment_type=request.assignment_type,
        notes=request.notes
    )
    
    db.add(assignment)
    
    # Create audit log
    audit = AuditService(db)
    audit.log_assignment(
        entity=order,
        assigned_to_id=request.assigned_to_user_id,
        assigned_to_name=assigned_user.name,
        user_id=current_user.id,
        business_id=order.business_id,
        description=f"Order {order.order_number} assigned to {assigned_user.name}"
    )
    
    db.commit()
    
    return {"success": True, "message": "Order assigned"}


@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel an order"""
    if not current_user.has_permission("orders.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.business_id == current_user.business_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order can be cancelled
    non_cancellable_statuses = [
        OrderStatus.DELIVERED, 
        OrderStatus.CANCELLED,
        OrderStatus.RETURNED
    ]
    
    if order.status in non_cancellable_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order with status '{order.status.value if hasattr(order.status, 'value') else order.status}'"
        )
    
    # Update status
    old_status = order.status.value if hasattr(order.status, 'value') else order.status
    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = reason
    
    # Create audit log
    audit = AuditService(db)
    audit.log_status_change(
        entity=order,
        old_status=old_status,
        new_status="cancelled",
        user_id=current_user.id,
        business_id=order.business_id,
        description=reason or f"Order {order.order_number} cancelled from {old_status} status"
    )
    
    db.commit()
    
    return {"success": True, "message": "Order cancelled successfully"}


@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an order (soft delete by setting status to cancelled)"""
    if not current_user.has_permission("orders.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.business_id == current_user.business_id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order can be deleted
    non_deletable_statuses = [
        OrderStatus.DELIVERED,
        OrderStatus.SHIPPED
    ]
    
    if order.status in non_deletable_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete order with status '{order.status.value if hasattr(order.status, 'value') else order.status}'. Cancel it first."
        )
    
    # Soft delete - set status to cancelled
    old_status = order.status.value if hasattr(order.status, 'value') else order.status
    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = "Deleted by user"
    
    # Create audit log
    audit = AuditService(db)
    audit.log_delete(
        entity=order,
        user_id=current_user.id,
        business_id=order.business_id,
        description=f"Order {order.order_number} deleted from {old_status} status"
    )
    
    db.commit()
    
    return {"success": True, "message": "Order deleted successfully"}
