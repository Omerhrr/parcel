"""
Vendor Portal Routes Blueprint
External vendor access to manage orders, inventory, and stock requests
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import requests

vendor_portal_bp = Blueprint('vendor_portal', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_vendor_headers():
    """Get headers with vendor API key"""
    api_key = session.get('vendor_api_key')
    if api_key:
        return {
            'X-Vendor-API-Key': api_key,
            'Content-Type': 'application/json'
        }
    return {'Content-Type': 'application/json'}


def is_vendor_logged_in():
    """Check if vendor is logged in"""
    return session.get('vendor_api_key') is not None


@vendor_portal_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Vendor portal login with API key"""
    if is_vendor_logged_in():
        return redirect(url_for('vendor_portal.dashboard'))
    
    if request.method == 'POST':
        api_key = request.form.get('api_key', '').strip()
        
        if not api_key:
            flash('Please enter your API key', 'error')
            return render_template('vendor_portal/login.html')
        
        # Validate API key with backend
        try:
            response = requests.get(
                f"{get_api_url()}/vendor-portal/profile",
                headers={'X-Vendor-API-Key': api_key}
            )
            
            if response.status_code == 200:
                vendor_data = response.json()
                session['vendor_api_key'] = api_key
                session['vendor_id'] = vendor_data['id']
                session['vendor_name'] = vendor_data['name']
                flash(f'Welcome, {vendor_data["name"]}!', 'success')
                return redirect(url_for('vendor_portal.dashboard'))
            else:
                flash('Invalid API key. Please check and try again.', 'error')
        except Exception as e:
            flash('Unable to connect to server. Please try again later.', 'error')
    
    return render_template('vendor_portal/login.html')


@vendor_portal_bp.route('/logout')
def logout():
    """Vendor logout"""
    session.pop('vendor_api_key', None)
    session.pop('vendor_id', None)
    session.pop('vendor_name', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('vendor_portal.login'))


@vendor_portal_bp.route('/')
def dashboard():
    """Vendor portal dashboard"""
    if not is_vendor_logged_in():
        return redirect(url_for('vendor_portal.login'))
    
    try:
        response = requests.get(
            f"{get_api_url()}/vendor-portal/dashboard",
            headers=get_vendor_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
        else:
            data = {'vendor': {'name': session.get('vendor_name')}, 'summary': {}, 'recent_orders': []}
            flash('Unable to load dashboard data', 'error')
    except Exception:
        data = {'vendor': {'name': session.get('vendor_name')}, 'summary': {}, 'recent_orders': []}
        flash('Unable to connect to server', 'error')
    
    return render_template('vendor_portal/dashboard.html', data=data)


@vendor_portal_bp.route('/orders')
def orders():
    """List vendor's orders"""
    if not is_vendor_logged_in():
        return redirect(url_for('vendor_portal.login'))
    
    status_filter = request.args.get('status', '')
    
    params = {'page': 1, 'page_size': 50}
    if status_filter:
        params['status'] = status_filter
    
    try:
        response = requests.get(
            f"{get_api_url()}/vendor-portal/orders",
            params=params,
            headers=get_vendor_headers()
        )
        
        if response.status_code == 200:
            orders_list = response.json()
        else:
            orders_list = []
            flash('Unable to load orders', 'error')
    except Exception:
        orders_list = []
        flash('Unable to connect to server', 'error')
    
    return render_template('vendor_portal/orders.html', orders=orders_list, status_filter=status_filter)


@vendor_portal_bp.route('/orders/create', methods=['GET', 'POST'])
def create_order():
    """Create a new order"""
    if not is_vendor_logged_in():
        return redirect(url_for('vendor_portal.login'))
    
    # Get products and warehouses for the form
    try:
        products_response = requests.get(
            f"{get_api_url()}/vendor-portal/products",
            headers=get_vendor_headers()
        )
        products = products_response.json() if products_response.status_code == 200 else []
        
        warehouses_response = requests.get(
            f"{get_api_url()}/vendor-portal/warehouses",
            headers=get_vendor_headers()
        )
        warehouses = warehouses_response.json() if warehouses_response.status_code == 200 else []
    except Exception:
        products = []
        warehouses = []
    
    if request.method == 'POST':
        # Build order data
        items = []
        for i in range(int(request.form.get('item_count', 1))):
            product_id = request.form.get(f'product_id_{i}')
            product_name = request.form.get(f'product_name_{i}')
            quantity = int(request.form.get(f'quantity_{i}', 1))
            unit_price = float(request.form.get(f'unit_price_{i}', 0))
            
            if product_name and quantity > 0:
                items.append({
                    'product_id': int(product_id) if product_id else None,
                    'product_name': product_name,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'discount': 0
                })
        
        order_data = {
            'customer_name': request.form.get('customer_name'),
            'customer_phone': request.form.get('customer_phone'),
            'customer_email': request.form.get('customer_email'),
            'delivery_address': request.form.get('delivery_address'),
            'delivery_city': request.form.get('delivery_city'),
            'delivery_state': request.form.get('delivery_state'),
            'delivery_landmark': request.form.get('delivery_landmark'),
            'items': items,
            'delivery_fee': float(request.form.get('delivery_fee', 0)),
            'payment_method': request.form.get('payment_method', 'cod'),
            'notes': request.form.get('notes')
        }
        
        try:
            response = requests.post(
                f"{get_api_url()}/vendor-portal/orders",
                json=order_data,
                headers=get_vendor_headers()
            )
            
            if response.status_code == 201:
                order = response.json()
                flash(f'Order {order["order_number"]} created successfully!', 'success')
                return redirect(url_for('vendor_portal.orders'))
            else:
                error = response.json().get('detail', 'Failed to create order')
                flash(error, 'error')
        except Exception as e:
            flash('Unable to connect to server', 'error')
    
    return render_template('vendor_portal/order_form.html', products=products, warehouses=warehouses)


@vendor_portal_bp.route('/inventory')
def inventory():
    """List vendor's inventory"""
    if not is_vendor_logged_in():
        return redirect(url_for('vendor_portal.login'))
    
    try:
        response = requests.get(
            f"{get_api_url()}/vendor-portal/inventory",
            headers=get_vendor_headers()
        )
        
        if response.status_code == 200:
            inventory_list = response.json()
        else:
            inventory_list = []
            flash('Unable to load inventory', 'error')
    except Exception:
        inventory_list = []
        flash('Unable to connect to server', 'error')
    
    return render_template('vendor_portal/inventory.html', inventory=inventory_list)


@vendor_portal_bp.route('/stock-requests')
def stock_requests():
    """List vendor's stock inbound requests"""
    if not is_vendor_logged_in():
        return redirect(url_for('vendor_portal.login'))
    
    status_filter = request.args.get('status', '')
    
    params = {'page': 1, 'page_size': 50}
    if status_filter:
        params['status'] = status_filter
    
    try:
        response = requests.get(
            f"{get_api_url()}/vendor-portal/stock-requests",
            params=params,
            headers=get_vendor_headers()
        )
        
        if response.status_code == 200:
            requests_list = response.json()
        else:
            requests_list = []
            flash('Unable to load stock requests', 'error')
    except Exception:
        requests_list = []
        flash('Unable to connect to server', 'error')
    
    return render_template('vendor_portal/stock_requests.html', stock_requests=requests_list, status_filter=status_filter)


@vendor_portal_bp.route('/stock-requests/create', methods=['GET', 'POST'])
def create_stock_request():
    """Create a stock inbound request"""
    if not is_vendor_logged_in():
        return redirect(url_for('vendor_portal.login'))
    
    # Get products and warehouses for the form
    try:
        products_response = requests.get(
            f"{get_api_url()}/vendor-portal/products",
            headers=get_vendor_headers()
        )
        products = products_response.json() if products_response.status_code == 200 else []
        
        warehouses_response = requests.get(
            f"{get_api_url()}/vendor-portal/warehouses",
            headers=get_vendor_headers()
        )
        warehouses = warehouses_response.json() if warehouses_response.status_code == 200 else []
    except Exception:
        products = []
        warehouses = []
    
    if request.method == 'POST':
        warehouse_id = request.form.get('warehouse_id')
        request_data = {
            'product_id': int(request.form.get('product_id')),
            'quantity': int(request.form.get('quantity', 1)),
            'unit_cost': float(request.form.get('unit_cost', 0)),
            'expected_delivery_date': request.form.get('expected_delivery_date'),
            'notes': request.form.get('notes')
        }
        # Only include warehouse_id if provided (admin will assign later)
        if warehouse_id:
            request_data['warehouse_id'] = int(warehouse_id)
        
        try:
            response = requests.post(
                f"{get_api_url()}/vendor-portal/stock-requests",
                json=request_data,
                headers=get_vendor_headers()
            )
            
            if response.status_code == 201:
                stock_request = response.json()
                flash(f'Stock request {stock_request["request_number"]} submitted successfully!', 'success')
                return redirect(url_for('vendor_portal.stock_requests'))
            else:
                error = response.json().get('detail', 'Failed to create request')
                flash(error, 'error')
        except Exception:
            flash('Unable to connect to server', 'error')
    
    return render_template('vendor_portal/stock_request_form.html', products=products, warehouses=warehouses)


@vendor_portal_bp.route('/remittances')
def remittances():
    """List vendor's remittances"""
    if not is_vendor_logged_in():
        return redirect(url_for('vendor_portal.login'))
    
    try:
        response = requests.get(
            f"{get_api_url()}/vendor-portal/remittances",
            headers=get_vendor_headers()
        )
        
        if response.status_code == 200:
            remittances_list = response.json()
        else:
            remittances_list = []
            flash('Unable to load remittances', 'error')
    except Exception:
        remittances_list = []
        flash('Unable to connect to server', 'error')
    
    return render_template('vendor_portal/remittances.html', remittances=remittances_list)
