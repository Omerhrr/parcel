"""
Orders Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.api_client import api_get, api_post, api_put, api_delete
from app.utils.permissions import permission_required

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/')
@login_required
@permission_required('orders.view')
def index():
    """List orders"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    
    params = {'page': page, 'page_size': 20}
    if status:
        params['status'] = status
    if search:
        params['search'] = search
    
    response = api_get('/orders', params=params)
    data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    
    return render_template('orders/index.html', 
                         orders=data.get('items', []),
                         pagination=data,
                         filters={'status': status, 'search': search})


@orders_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('orders.create')
def create():
    """Create order"""
    if request.method == 'POST':
        # Build order data from dynamic items
        items = []
        item_count = int(request.form.get('item_count', 0))
        
        for i in range(item_count):
            product_id = request.form.get(f'product_id_{i}')
            product_name = request.form.get(f'product_name_{i}')
            quantity = int(request.form.get(f'quantity_{i}', 1))
            unit_price = float(request.form.get(f'unit_price_{i}', 0))
            
            if product_name and quantity > 0:  # Only add valid items
                items.append({
                    'product_id': int(product_id) if product_id else None,
                    'product_name': product_name,
                    'product_sku': request.form.get(f'product_sku_{i}'),
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'discount': float(request.form.get(f'discount_{i}', 0))
                })
        
        if not items:
            flash('Please add at least one item to the order', 'error')
            return redirect(url_for('orders.create'))
        
        data = {
            'vendor_id': int(request.form.get('vendor_id')) if request.form.get('vendor_id') else None,
            'customer_name': request.form.get('customer_name'),
            'customer_phone': request.form.get('customer_phone'),
            'customer_email': request.form.get('customer_email'),
            'delivery_address': request.form.get('delivery_address'),
            'delivery_city': request.form.get('delivery_city'),
            'delivery_state': request.form.get('delivery_state'),
            'delivery_landmark': request.form.get('delivery_landmark'),
            'delivery_fee': float(request.form.get('delivery_fee', 0)),
            'discount': float(request.form.get('discount', 0)),
            'remittance_fee': float(request.form.get('remittance_fee', 0)),
            'payment_method': request.form.get('payment_method', 'cod'),
            'notes': request.form.get('notes'),
            'items': items
        }
        
        response = api_post('/orders', data)
        
        if response.status_code == 201:
            flash('Order created successfully!', 'success')
            return redirect(url_for('orders.view', order_id=response.json()['id']))
        else:
            flash(response.json().get('detail', 'Failed to create order'), 'error')
    
    # Get products for selection
    products_response = api_get('/products', {'page_size': 200})
    products = products_response.json().get('items', []) if products_response.status_code == 200 else []
    
    # Get vendors for selection
    vendors_response = api_get('/vendors', {'page_size': 100})
    vendors = vendors_response.json().get('items', []) if vendors_response.status_code == 200 else []
    
    return render_template('orders/form.html', order=None, products=products, vendors=vendors)


@orders_bp.route('/<int:order_id>')
@login_required
@permission_required('orders.view')
def view(order_id):
    """View order details"""
    response = api_get(f'/orders/{order_id}')
    
    if response.status_code != 200:
        flash('Order not found', 'error')
        return redirect(url_for('orders.index'))
    
    order = response.json()
    return render_template('orders/detail.html', order=order)


@orders_bp.route('/<int:order_id>/update-status', methods=['POST'])
@login_required
@permission_required('orders.update')
def update_status(order_id):
    """Update order status"""
    status = request.form.get('status')
    
    response = api_put(f'/orders/{order_id}/status?status={status}')
    
    if response.status_code == 200:
        flash('Order status updated!', 'success')
    else:
        flash(response.json().get('detail', 'Failed to update status'), 'error')
    
    return redirect(url_for('orders.view', order_id=order_id))


@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
@permission_required('orders.update')
def cancel(order_id):
    """Cancel an order"""
    reason = request.form.get('reason', '')
    
    response = api_post(f'/orders/{order_id}/cancel', {'reason': reason} if reason else None)
    
    if response.status_code == 200:
        flash('Order cancelled successfully!', 'success')
    else:
        flash(response.json().get('detail', 'Failed to cancel order'), 'error')
    
    return redirect(url_for('orders.view', order_id=order_id))


@orders_bp.route('/<int:order_id>/delete', methods=['POST'])
@login_required
@permission_required('orders.update')
def delete(order_id):
    """Delete an order"""
    response = api_delete(f'/orders/{order_id}')
    
    if response.status_code == 200:
        flash('Order deleted successfully!', 'success')
        return redirect(url_for('orders.index'))
    else:
        flash(response.json().get('detail', 'Failed to delete order'), 'error')
    
    return redirect(url_for('orders.view', order_id=order_id))
