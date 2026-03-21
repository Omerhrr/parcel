"""
Vendor Portal Router
ParcelFlow - Multi-tenant Logistics Platform

API endpoints for vendor portal access where vendors can:
- Login with API key
- View their dashboard, inventory, orders, transactions
- Create orders
- Submit stock inbound requests
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.database import get_db
from app.models.vendor import Vendor
from app.models.user import User
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.models.stock_request import StockInboundRequest, StockRequestStatus
from app.models.accounting import Remittance
from app.schemas.order import OrderCreate, OrderResponse, OrderItemCreate, OrderItemResponse
from app.schemas.stock_request import (
    StockRequestCreate, StockRequestResponse, StockRequestListResponse,
    StockRequestUpdate
)
from app.utils.notifications import notify_new_order

router = APIRouter()


async def get_vendor_by_api_key(
    api_key: str = Header(..., alias="X-Vendor-API-Key"),
    db: Session = Depends(get_db)
) -> Vendor:
    """Authenticate vendor by API key"""
    if not api_key or not api_key.startswith("vp_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    vendor = db.query(Vendor).filter(Vendor.api_key == api_key).first()

    if not vendor:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not vendor.is_active:
        raise HTTPException(status_code=403, detail="Vendor account is inactive")

    return vendor


# ============ VENDOR AUTH & PROFILE ============

@router.get("/profile")
async def get_vendor_profile(
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """Get vendor profile information"""
    return {
        "id": vendor.id,
        "name": vendor.name,
        "code": vendor.code,
        "contact_person": vendor.contact_person,
        "phone": vendor.phone,
        "email": vendor.email,
        "address": vendor.address,
        "city": vendor.city,
        "state": vendor.state,
        "business_type": vendor.business_type,
        "bank_name": vendor.bank_name,
        "account_name": vendor.account_name,
        "account_number": vendor.account_number,
        "settlement_cycle": vendor.settlement_cycle,
        "is_active": vendor.is_active,
        "created_at": vendor.created_at,
        "updated_at": vendor.updated_at
    }


@router.get("/dashboard")
async def get_vendor_dashboard(
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """Get vendor dashboard summary"""
    # Get inventory summary
    inventory_items = db.query(Inventory).filter(
        Inventory.vendor_id == vendor.id
    ).all()

    total_inventory = sum(i.quantity for i in inventory_items)
    inventory_value = sum(i.quantity * (i.product.selling_price or 0) for i in inventory_items if i.product)

    # Get orders summary
    orders = db.query(Order).filter(Order.vendor_id == vendor.id).all()
    pending_orders = [o for o in orders if o.status == OrderStatus.PENDING]
    delivered_orders = [o for o in orders if o.status == OrderStatus.DELIVERED]
    total_sales = sum(float(o.total_amount) for o in orders if o.status == OrderStatus.DELIVERED)

    # Get pending remittance
    pending_remittance = sum(float(o.vendor_amount or 0) for o in orders
                           if o.remittance_status == "pending" and o.status == OrderStatus.DELIVERED)

    # Get stock requests
    pending_stock_requests = db.query(StockInboundRequest).filter(
        StockInboundRequest.vendor_id == vendor.id,
        StockInboundRequest.status == StockRequestStatus.PENDING
    ).count()

    # Recent orders
    recent_orders = db.query(Order).filter(
        Order.vendor_id == vendor.id
    ).order_by(Order.created_at.desc()).limit(5).all()

    return {
        "vendor": {
            "id": vendor.id,
            "name": vendor.name
        },
        "summary": {
            "total_inventory": total_inventory,
            "inventory_value": float(inventory_value),
            "total_orders": len(orders),
            "pending_orders": len(pending_orders),
            "delivered_orders": len(delivered_orders),
            "total_sales": float(total_sales),
            "pending_remittance": float(pending_remittance),
            "pending_stock_requests": pending_stock_requests
        },
        "recent_orders": [
            {
                "id": o.id,
                "order_number": o.order_number,
                "customer_name": o.customer_name,
                "total_amount": float(o.total_amount),
                "status": o.status.value if hasattr(o.status, 'value') else o.status,
                "created_at": o.created_at
            }
            for o in recent_orders
        ]
    }


# ============ VENDOR ORDERS ============

@router.get("/orders", response_model=List[OrderResponse])
async def list_vendor_orders(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """List vendor's orders"""
    query = db.query(Order).filter(Order.vendor_id == vendor.id)

    if status:
        query = query.filter(Order.status == status)

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

    return items


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor_order(
    request: OrderCreate,
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """Create a new order from vendor (vendor's sales order)"""
    # Ensure vendor_id is set to the authenticated vendor
    request.vendor_id = vendor.id

    # Generate order number
    order_number = Order.generate_order_number()

    # Calculate prices using dynamic pricing
    subtotal = Decimal("0")
    processed_items = []

    for item_req in request.items:
        if item_req.product_id:
            product = db.query(Product).filter(
                Product.id == item_req.product_id,
                Product.vendor_id == vendor.id
            ).first()

            if product:
                # Use dynamic pricing if available
                if product.pricing_type == "matrix" and product.pricing_matrix:
                    # Calculate total price using pricing matrix
                    item_total = Decimal(str(product.get_total_price_for_quantity(item_req.quantity)))
                    unit_price = item_total / item_req.quantity if item_req.quantity > 0 else Decimal("0")
                else:
                    # Use fixed pricing
                    unit_price = product.selling_price or item_req.unit_price
                    item_total = item_req.quantity * unit_price - item_req.discount
            else:
                unit_price = item_req.unit_price
                item_total = item_req.quantity * unit_price - item_req.discount
        else:
            unit_price = item_req.unit_price
            item_total = item_req.quantity * unit_price - item_req.discount

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

    # Calculate total (delivery fee is deducted, not added)
    total_amount = subtotal - request.delivery_fee + request.tax - request.discount

    # Calculate vendor amount (after delivery fee and logistics fee deductions)
    remittance_fee = request.remittance_fee or Decimal("0")
    vendor_amount = total_amount - remittance_fee

    order = Order(
        business_id=vendor.business_id,
        branch_id=request.branch_id,
        vendor_id=vendor.id,
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
        vendor_amount=max(vendor_amount, Decimal("0")),
        remittance_status="pending",
        payment_method=PaymentMethod(request.payment_method) if request.payment_method else PaymentMethod.COD,
        source="vendor_portal",
        notes=request.notes
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

    # Send notification
    notify_new_order(
        db=db,
        business_id=vendor.business_id,
        order_id=order.id,
        order_number=order_number
    )

    db.commit()
    db.refresh(order)

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


# ============ VENDOR INVENTORY ============

@router.get("/inventory")
async def list_vendor_inventory(
    warehouse_id: Optional[int] = None,
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """List vendor's inventory across warehouses"""
    query = db.query(Inventory).filter(Inventory.vendor_id == vendor.id)

    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)

    items = query.all()

    return [
        {
            "id": i.id,
            "product_id": i.product_id,
            "product_name": i.product.name if i.product else None,
            "product_sku": i.product.sku if i.product else None,
            "warehouse_id": i.warehouse_id,
            "warehouse_name": i.warehouse.name if i.warehouse else None,
            "quantity": i.quantity,
            "reserved_quantity": i.reserved_quantity or 0,
            "available_quantity": i.quantity - (i.reserved_quantity or 0),
            "unit_cost": float(i.product.cost_price) if i.product and i.product.cost_price else 0,
            "selling_price": float(i.product.selling_price) if i.product and i.product.selling_price else 0,
            "updated_at": i.updated_at
        }
        for i in items
    ]


# ============ VENDOR STOCK REQUESTS ============

@router.get("/stock-requests", response_model=List[StockRequestResponse])
async def list_vendor_stock_requests(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """List vendor's stock inbound requests"""
    query = db.query(StockInboundRequest).filter(StockInboundRequest.vendor_id == vendor.id)

    if status:
        query = query.filter(StockInboundRequest.status == status)

    offset = (page - 1) * page_size
    requests = query.order_by(StockInboundRequest.created_at.desc()).offset(offset).limit(page_size).all()

    return [
        StockRequestResponse(
            id=r.id,
            business_id=r.business_id,
            vendor_id=r.vendor_id,
            warehouse_id=r.warehouse_id,
            product_id=r.product_id,
            request_number=r.request_number,
            quantity=r.quantity,
            unit_cost=r.unit_cost,
            product_name=r.product_name,
            product_sku=r.product_sku,
            product_description=r.product_description,
            status=r.status.value if hasattr(r.status, 'value') else r.status,
            expected_delivery_date=r.expected_delivery_date,
            tracking_number=r.tracking_number,
            carrier=r.carrier,
            reviewed_by=r.reviewed_by,
            reviewed_at=r.reviewed_at,
            review_notes=r.review_notes,
            received_by=r.received_by,
            received_at=r.received_at,
            received_quantity=r.received_quantity,
            reception_notes=r.reception_notes,
            notes=r.notes,
            vendor_notes=r.vendor_notes,
            created_at=r.created_at,
            updated_at=r.updated_at,
            vendor_name=vendor.name,
            warehouse_name=r.warehouse.name if r.warehouse else None,
            product_name_resolved=r.product.name if r.product else r.product_name
        )
        for r in requests
    ]


@router.post("/stock-requests", response_model=StockRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor_stock_request(
    request: StockRequestCreate,
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """Create a stock inbound request (vendor wants to send stock to warehouse)"""
    # Warehouse is optional - admin will assign when confirming
    warehouse = None
    if request.warehouse_id:
        # Verify warehouse exists and belongs to same business
        warehouse = db.query(Warehouse).filter(
            Warehouse.id == request.warehouse_id,
            Warehouse.business_id == vendor.business_id
        ).first()
        if not warehouse:
            raise HTTPException(status_code=400, detail="Invalid warehouse")

    # Verify product belongs to vendor
    product = db.query(Product).filter(
        Product.id == request.product_id,
        Product.vendor_id == vendor.id
    ).first()
    if not product:
        raise HTTPException(status_code=400, detail="Invalid product. Please select a product from your catalog.")

    # Generate request number
    request_number = StockInboundRequest.generate_request_number()

    stock_request = StockInboundRequest(
        business_id=vendor.business_id,
        vendor_id=vendor.id,
        warehouse_id=request.warehouse_id,  # Can be None
        product_id=request.product_id,
        request_number=request_number,
        quantity=request.quantity,
        unit_cost=request.unit_cost,
        product_name=product.name,  # Auto-fill from product
        product_sku=product.sku,    # Auto-fill from product
        expected_delivery_date=request.expected_delivery_date,
        vendor_notes=request.notes,
        status=StockRequestStatus.PENDING
    )

    db.add(stock_request)
    db.commit()
    db.refresh(stock_request)

    return StockRequestResponse(
        id=stock_request.id,
        business_id=stock_request.business_id,
        vendor_id=stock_request.vendor_id,
        warehouse_id=stock_request.warehouse_id,
        product_id=stock_request.product_id,
        request_number=stock_request.request_number,
        quantity=stock_request.quantity,
        unit_cost=stock_request.unit_cost,
        product_name=stock_request.product_name,
        product_sku=stock_request.product_sku,
        product_description=stock_request.product_description,
        status=stock_request.status.value,
        expected_delivery_date=stock_request.expected_delivery_date,
        tracking_number=stock_request.tracking_number,
        carrier=stock_request.carrier,
        reviewed_by=stock_request.reviewed_by,
        reviewed_at=stock_request.reviewed_at,
        review_notes=stock_request.review_notes,
        received_by=stock_request.received_by,
        received_at=stock_request.received_at,
        received_quantity=stock_request.received_quantity,
        reception_notes=stock_request.reception_notes,
        notes=stock_request.notes,
        vendor_notes=stock_request.vendor_notes,
        created_at=stock_request.created_at,
        updated_at=stock_request.updated_at,
        vendor_name=vendor.name,
        warehouse_name=warehouse.name if warehouse else None,
        product_name_resolved=product.name
    )


@router.put("/stock-requests/{request_id}", response_model=StockRequestResponse)
async def update_vendor_stock_request(
    request_id: int,
    request: StockRequestUpdate,
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """Update a pending stock request"""
    stock_request = db.query(StockInboundRequest).filter(
        StockInboundRequest.id == request_id,
        StockInboundRequest.vendor_id == vendor.id
    ).first()

    if not stock_request:
        raise HTTPException(status_code=404, detail="Stock request not found")

    if stock_request.status not in [StockRequestStatus.PENDING]:
        raise HTTPException(status_code=400, detail="Can only update pending requests")

    # Update fields
    if request.warehouse_id:
        warehouse = db.query(Warehouse).filter(
            Warehouse.id == request.warehouse_id,
            Warehouse.business_id == vendor.business_id
        ).first()
        if warehouse:
            stock_request.warehouse_id = request.warehouse_id

    if request.quantity:
        stock_request.quantity = request.quantity
    if request.unit_cost:
        stock_request.unit_cost = request.unit_cost
    if request.expected_delivery_date:
        stock_request.expected_delivery_date = request.expected_delivery_date
    if request.tracking_number:
        stock_request.tracking_number = request.tracking_number
    if request.carrier:
        stock_request.carrier = request.carrier
    if request.notes:
        stock_request.vendor_notes = request.notes

    db.commit()
    db.refresh(stock_request)

    return StockRequestResponse(
        id=stock_request.id,
        business_id=stock_request.business_id,
        vendor_id=stock_request.vendor_id,
        warehouse_id=stock_request.warehouse_id,
        product_id=stock_request.product_id,
        request_number=stock_request.request_number,
        quantity=stock_request.quantity,
        unit_cost=stock_request.unit_cost,
        product_name=stock_request.product_name,
        product_sku=stock_request.product_sku,
        product_description=stock_request.product_description,
        status=stock_request.status.value,
        expected_delivery_date=stock_request.expected_delivery_date,
        tracking_number=stock_request.tracking_number,
        carrier=stock_request.carrier,
        reviewed_by=stock_request.reviewed_by,
        reviewed_at=stock_request.reviewed_at,
        review_notes=stock_request.review_notes,
        received_by=stock_request.received_by,
        received_at=stock_request.received_at,
        received_quantity=stock_request.received_quantity,
        reception_notes=stock_request.reception_notes,
        notes=stock_request.notes,
        vendor_notes=stock_request.vendor_notes,
        created_at=stock_request.created_at,
        updated_at=stock_request.updated_at,
        vendor_name=vendor.name,
        warehouse_name=stock_request.warehouse.name if stock_request.warehouse else None,
        product_name_resolved=stock_request.product.name if stock_request.product else stock_request.product_name
    )


@router.post("/stock-requests/{request_id}/cancel")
async def cancel_vendor_stock_request(
    request_id: int,
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """Cancel a pending stock request"""
    stock_request = db.query(StockInboundRequest).filter(
        StockInboundRequest.id == request_id,
        StockInboundRequest.vendor_id == vendor.id
    ).first()

    if not stock_request:
        raise HTTPException(status_code=404, detail="Stock request not found")

    if stock_request.status not in [StockRequestStatus.PENDING, StockRequestStatus.APPROVED]:
        raise HTTPException(status_code=400, detail="Cannot cancel this request")

    stock_request.status = StockRequestStatus.CANCELLED
    db.commit()

    return {"success": True, "message": "Stock request cancelled"}


# ============ VENDOR REMITTANCES ============

@router.get("/remittances")
async def list_vendor_remittances(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """List vendor's remittances"""
    query = db.query(Remittance).filter(Remittance.vendor_id == vendor.id)

    if status:
        query = query.filter(Remittance.status == status)

    offset = (page - 1) * page_size
    remittances = query.order_by(Remittance.created_at.desc()).offset(offset).limit(page_size).all()

    return [
        {
            "id": r.id,
            "remittance_number": r.remittance_number,
            "amount": float(r.amount),
            "status": r.status,
            "payment_reference": r.payment_reference,
            "paid_at": r.paid_at,
            "notes": r.notes,
            "created_at": r.created_at
        }
        for r in remittances
    ]


# ============ VENDOR PRODUCTS ============

@router.get("/products")
async def list_vendor_products(
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """List vendor's products"""
    products = db.query(Product).filter(
        Product.vendor_id == vendor.id,
        Product.is_active == 1
    ).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "description": p.description,
            "selling_price": float(p.selling_price) if p.selling_price else 0,
            "cost_price": float(p.cost_price) if p.cost_price else 0,
            "pricing_type": p.pricing_type or "fixed",
            "pricing_matrix": [
                {
                    "id": t.id,
                    "min_quantity": t.min_quantity,
                    "max_quantity": t.max_quantity,
                    "price": float(t.price) if t.price else 0,
                    "total_price": float(t.total_price) if t.total_price else None,
                    "label": t.label,
                    "is_buy_x_get_y": t.is_buy_x_get_y,
                    "buy_quantity": t.buy_quantity,
                    "get_quantity": t.get_quantity
                }
                for t in p.pricing_matrix
            ] if p.pricing_matrix else [],
            "image_url": p.image_url,
            "is_active": p.is_active,
            "created_at": p.created_at
        }
        for p in products
    ]


# ============ VENDOR WAREHOUSES ============

@router.get("/warehouses")
async def list_vendor_warehouses(
    vendor: Vendor = Depends(get_vendor_by_api_key),
    db: Session = Depends(get_db)
):
    """List available warehouses for vendor"""
    warehouses = db.query(Warehouse).filter(
        Warehouse.business_id == vendor.business_id,
        Warehouse.is_active == 1
    ).all()

    return [
        {
            "id": w.id,
            "name": w.name,
            "code": w.code,
            "address": w.address,
            "city": w.city,
            "is_active": w.is_active
        }
        for w in warehouses
    ]
