"""
Vendors Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.api_client import api_get, api_post, api_put, api_post_raw
from app.utils.permissions import permission_required

vendors_bp = Blueprint('vendors', __name__)


@vendors_bp.route('/')
@login_required
@permission_required('vendors.view')
def index():
    """List vendors"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    params = {'page': page, 'page_size': 20}
    if search:
        params['search'] = search
    
    response = api_get('/vendors', params=params)
    data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    
    return render_template('vendors/index.html', 
                         vendors=data.get('items', []),
                         pagination=data,
                         search=search)


@vendors_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('vendors.create')
def create():
    """Create vendor"""
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'code': request.form.get('code'),
            'contact_person': request.form.get('contact_person'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'business_type': request.form.get('business_type'),
            'bank_name': request.form.get('bank_name'),
            'account_name': request.form.get('account_name'),
            'account_number': request.form.get('account_number'),
            'settlement_cycle': request.form.get('settlement_cycle', 'weekly'),
            'notes': request.form.get('notes')
        }
        
        response = api_post('/vendors', data)
        
        if response.status_code == 201:
            flash('Vendor created successfully!', 'success')
            return redirect(url_for('vendors.view', vendor_id=response.json()['id']))
        else:
            flash(response.json().get('detail', 'Failed to create vendor'), 'error')
    
    return render_template('vendors/form.html', vendor=None)


@vendors_bp.route('/<int:vendor_id>')
@login_required
@permission_required('vendors.view')
def view(vendor_id):
    """View vendor details with tabs for inventory, orders, remittances, and history"""
    response = api_get(f'/vendors/{vendor_id}')
    
    if response.status_code != 200:
        flash('Vendor not found', 'error')
        return redirect(url_for('vendors.index'))
    
    vendor = response.json()
    
    # Get vendor's products
    products_response = api_get('/products', {'vendor_id': vendor_id, 'page_size': 100})
    products = products_response.json().get('items', []) if products_response.status_code == 200 else []
    
    # Get vendor's inventory in warehouses
    inventory_response = api_get('/inventory', {'vendor_id': vendor_id, 'page_size': 100})
    inventory = inventory_response.json().get('items', []) if inventory_response.status_code == 200 else []
    
    # Get vendor's orders
    orders_response = api_get('/orders', {'vendor_id': vendor_id, 'page_size': 50})
    orders = orders_response.json().get('items', []) if orders_response.status_code == 200 else []
    
    # Get vendor's remittances
    remittances_response = api_get(f'/vendors/{vendor_id}/remittances', {'page_size': 50})
    remittances = remittances_response.json().get('items', []) if remittances_response.status_code == 200 else []
    
    # Get stock movements for vendor's products
    stock_movements_response = api_get('/inventory/movements', {'vendor_id': vendor_id, 'page_size': 50})
    stock_movements = stock_movements_response.json().get('items', []) if stock_movements_response.status_code == 200 else []
    
    # Get warehouses for stock request review modal
    warehouses_response = api_get('/warehouses', {'page_size': 100})
    warehouses = warehouses_response.json().get('items', []) if warehouses_response.status_code == 200 else []
    
    # Calculate stats
    stats = {
        'total_products': len(products),
        'total_orders': len(orders),
        'pending_remittance': sum(float(o.get('vendor_amount', 0)) for o in orders if o.get('remittance_status') == 'pending'),
        'total_remitted': sum(float(r.get('amount', 0)) for r in remittances if r.get('status') == 'completed')
    }
    
    return render_template('vendors/detail.html', 
                         vendor=vendor, 
                         products=products,
                         inventory=inventory,
                         orders=orders,
                         remittances=remittances,
                         stock_movements=stock_movements,
                         warehouses=warehouses,
                         stats=stats)


@vendors_bp.route('/<int:vendor_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('vendors.update')
def edit(vendor_id):
    """Edit vendor"""
    response = api_get(f'/vendors/{vendor_id}')
    
    if response.status_code != 200:
        flash('Vendor not found', 'error')
        return redirect(url_for('vendors.index'))
    
    vendor = response.json()
    
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'contact_person': request.form.get('contact_person'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'address': request.form.get('address'),
            'bank_name': request.form.get('bank_name'),
            'account_name': request.form.get('account_name'),
            'account_number': request.form.get('account_number'),
            'is_active': 1 if request.form.get('is_active') else 0,
            'notes': request.form.get('notes')
        }
        
        response = api_put(f'/vendors/{vendor_id}', data)
        
        if response.status_code == 200:
            flash('Vendor updated successfully!', 'success')
            return redirect(url_for('vendors.view', vendor_id=vendor_id))
        else:
            flash(response.json().get('detail', 'Failed to update vendor'), 'error')
    
    return render_template('vendors/form.html', vendor=vendor)


@vendors_bp.route('/<int:vendor_id>/generate-api-key', methods=['POST'])
@login_required
@permission_required('vendors.update')
def generate_api_key(vendor_id):
    """Generate API key for vendor portal access"""
    import requests
    from flask import session
    
    token = session.get('token_data', {}).get('access_token')
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    
    try:
        response = requests.post(
            f"http://localhost:8000/api/vendors/{vendor_id}/generate-api-key",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            flash(f'API Key generated: {data.get("api_key")}', 'success')
        else:
            error = response.json().get('detail', 'Failed to generate API key')
            flash(error, 'error')
    except Exception as e:
        flash('Failed to connect to API server', 'error')
    
    return redirect(url_for('vendors.view', vendor_id=vendor_id))


# ============ API Proxy Routes for Stock Requests ============

@vendors_bp.route('/api/<int:vendor_id>/stock-requests', methods=['GET'])
@login_required
def api_list_stock_requests(vendor_id):
    """API proxy: List stock requests for a vendor"""
    import requests
    from flask import session, jsonify
    
    token = session.get('token_data', {}).get('access_token')
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    
    status = request.args.get('status', '')
    page = request.args.get('page', 1)
    page_size = request.args.get('page_size', 20)
    
    params = {'page': page, 'page_size': page_size}
    if status:
        params['status'] = status
    
    try:
        response = requests.get(
            f"http://localhost:8000/api/vendors/{vendor_id}/stock-requests",
            headers=headers,
            params=params
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'detail': 'Failed to connect to API server'}), 500


@vendors_bp.route('/api/<int:vendor_id>/stock-requests/<int:request_id>/review', methods=['POST'])
@login_required
def api_review_stock_request(vendor_id, request_id):
    """API proxy: Review (approve/reject) a stock request"""
    import requests
    from flask import session, jsonify
    
    token = session.get('token_data', {}).get('access_token')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    } if token else {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(
            f"http://localhost:8000/api/vendors/{vendor_id}/stock-requests/{request_id}/review",
            headers=headers,
            json=request.get_json()
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'detail': 'Failed to connect to API server'}), 500


@vendors_bp.route('/api/<int:vendor_id>/stock-requests/<int:request_id>/receive', methods=['POST'])
@login_required
def api_receive_stock_request(vendor_id, request_id):
    """API proxy: Receive stock and add to inventory"""
    import requests
    from flask import session, jsonify
    
    token = session.get('token_data', {}).get('access_token')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    } if token else {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(
            f"http://localhost:8000/api/vendors/{vendor_id}/stock-requests/{request_id}/receive",
            headers=headers,
            json=request.get_json()
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'detail': 'Failed to connect to API server'}), 500
