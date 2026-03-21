"""
Inventory Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.api_client import api_get, api_post, api_put, api_delete
from app.utils.permissions import permission_required

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/')
@login_required
@permission_required('inventory.view')
def index():
    """List inventory"""
    page = request.args.get('page', 1, type=int)
    warehouse_id = request.args.get('warehouse_id', '')
    
    params = {'page': page, 'page_size': 20}
    if warehouse_id:
        params['warehouse_id'] = warehouse_id
    
    response = api_get('/inventory', params=params)
    data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    
    # Get warehouses for filter
    warehouses_response = api_get('/warehouses')
    warehouses = warehouses_response.json().get('items', []) if warehouses_response.status_code == 200 else []
    
    return render_template('warehouse/inventory.html', 
                         inventory=data.get('items', []),
                         pagination=data,
                         warehouses=warehouses,
                         selected_warehouse=warehouse_id)


@inventory_bp.route('/products')
@login_required
@permission_required('inventory.view')
def products():
    """List products"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    params = {'page': page, 'page_size': 20}
    if search:
        params['search'] = search
    if category:
        params['category'] = category
    
    response = api_get('/products', params=params)
    data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    
    return render_template('warehouse/products.html', 
                         products=data.get('items', []),
                         pagination=data,
                         search=search)


@inventory_bp.route('/products/create', methods=['GET', 'POST'])
@login_required
@permission_required('inventory.create')
def create_product():
    """Create product"""
    # Get vendor_id from query param (when coming from vendor detail page)
    preselected_vendor_id = request.args.get('vendor_id', '')
    
    if request.method == 'POST':
        # Get pricing type
        pricing_type = request.form.get('pricing_type', 'fixed')
        
        # Get the correct price fields based on pricing type
        if pricing_type == 'matrix':
            cost_price = request.form.get('cost_price_matrix')
            selling_price = request.form.get('selling_price_matrix')
        else:
            cost_price = request.form.get('cost_price_fixed')
            selling_price = request.form.get('selling_price_fixed')
        
        # Build price tiers for matrix pricing
        price_tiers = []
        if pricing_type == 'matrix':
            # Parse price tiers from form
            tier_indices = set()
            for key in request.form.keys():
                if key.startswith('price_tiers['):
                    # Extract index from key like "price_tiers[0][min_quantity]"
                    parts = key.split('[')
                    if len(parts) >= 2:
                        try:
                            idx = int(parts[1].rstrip(']'))
                            tier_indices.add(idx)
                        except ValueError:
                            pass
            
            for idx in sorted(tier_indices):
                min_qty = request.form.get(f'price_tiers[{idx}][min_quantity]')
                if min_qty:
                    tier = {
                        'min_quantity': int(min_qty),
                        'max_quantity': int(request.form.get(f'price_tiers[{idx}][max_quantity]')) if request.form.get(f'price_tiers[{idx}][max_quantity]') else None,
                        'price': float(request.form.get(f'price_tiers[{idx}][price]') or 0),
                        'total_price': float(request.form.get(f'price_tiers[{idx}][total_price]')) if request.form.get(f'price_tiers[{idx}][total_price]') else None,
                        'label': request.form.get(f'price_tiers[{idx}][label]') or None,
                        'is_buy_x_get_y': request.form.get(f'price_tiers[{idx}][is_buy_x_get_y]') == '1',
                        'buy_quantity': int(request.form.get(f'price_tiers[{idx}][buy_quantity]')) if request.form.get(f'price_tiers[{idx}][buy_quantity]') else None,
                        'get_quantity': int(request.form.get(f'price_tiers[{idx}][get_quantity]')) if request.form.get(f'price_tiers[{idx}][get_quantity]') else None,
                    }
                    price_tiers.append(tier)
        
        data = {
            'name': request.form.get('name'),
            'sku': request.form.get('sku'),
            'barcode': request.form.get('barcode'),
            'description': request.form.get('description'),
            'category': request.form.get('category'),
            'vendor_id': request.form.get('vendor_id') or None,
            'weight': float(request.form.get('weight')) if request.form.get('weight') else None,
            'cost_price': float(cost_price) if cost_price else 0,
            'selling_price': float(selling_price) if selling_price else 0,
            'pricing_type': pricing_type,
            'price_tiers': price_tiers if price_tiers else None
        }
        
        response = api_post('/products', data)
        
        if response.status_code == 201:
            flash('Product created successfully!', 'success')
            # Redirect back to vendor detail if we came from there
            if request.form.get('redirect_to_vendor') and data.get('vendor_id'):
                return redirect(url_for('vendors.view', vendor_id=data['vendor_id']))
            return redirect(url_for('inventory.products'))
        else:
            flash(response.json().get('detail', 'Failed to create product'), 'error')
    
    # Get vendors for selection
    vendors_response = api_get('/vendors', {'page_size': 100})
    vendors = vendors_response.json().get('items', []) if vendors_response.status_code == 200 else []
    
    # Get preselected vendor info
    preselected_vendor = None
    if preselected_vendor_id:
        vendor_response = api_get(f'/vendors/{preselected_vendor_id}')
        if vendor_response.status_code == 200:
            preselected_vendor = vendor_response.json()
    
    return render_template('warehouse/product_form.html', 
                         product=None, 
                         vendors=vendors,
                         preselected_vendor_id=int(preselected_vendor_id) if preselected_vendor_id else None,
                         preselected_vendor=preselected_vendor)


@inventory_bp.route('/products/<int:product_id>')
@login_required
@permission_required('inventory.view')
def view_product(product_id):
    """View product details"""
    response = api_get(f'/products/{product_id}')
    
    if response.status_code != 200:
        flash('Product not found', 'error')
        return redirect(url_for('inventory.products'))
    
    product = response.json()
    
    # Get vendor info if product has a vendor
    vendor = None
    if product.get('vendor_id'):
        vendor_response = api_get(f'/vendors/{product["vendor_id"]}')
        if vendor_response.status_code == 200:
            vendor = vendor_response.json()
    
    return render_template('warehouse/product_detail.html', product=product, vendor=vendor)


@inventory_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('inventory.update')
def edit_product(product_id):
    """Edit product"""
    response = api_get(f'/products/{product_id}')
    
    if response.status_code != 200:
        flash('Product not found', 'error')
        return redirect(url_for('inventory.products'))
    
    product = response.json()
    
    if request.method == 'POST':
        # Get pricing type
        pricing_type = request.form.get('pricing_type', 'fixed')
        
        # Get the correct price fields based on pricing type
        if pricing_type == 'matrix':
            cost_price = request.form.get('cost_price_matrix')
            selling_price = request.form.get('selling_price_matrix')
        else:
            cost_price = request.form.get('cost_price_fixed')
            selling_price = request.form.get('selling_price_fixed')
        
        # Build price tiers for matrix pricing
        price_tiers = []
        if pricing_type == 'matrix':
            # Parse price tiers from form
            tier_indices = set()
            for key in request.form.keys():
                if key.startswith('price_tiers['):
                    # Extract index from key like "price_tiers[0][min_quantity]"
                    parts = key.split('[')
                    if len(parts) >= 2:
                        try:
                            idx = int(parts[1].rstrip(']'))
                            tier_indices.add(idx)
                        except ValueError:
                            pass
            
            for idx in sorted(tier_indices):
                min_qty = request.form.get(f'price_tiers[{idx}][min_quantity]')
                if min_qty:
                    tier = {
                        'min_quantity': int(min_qty),
                        'max_quantity': int(request.form.get(f'price_tiers[{idx}][max_quantity]')) if request.form.get(f'price_tiers[{idx}][max_quantity]') else None,
                        'price': float(request.form.get(f'price_tiers[{idx}][price]') or 0),
                        'total_price': float(request.form.get(f'price_tiers[{idx}][total_price]')) if request.form.get(f'price_tiers[{idx}][total_price]') else None,
                        'label': request.form.get(f'price_tiers[{idx}][label]') or None,
                        'is_buy_x_get_y': request.form.get(f'price_tiers[{idx}][is_buy_x_get_y]') == '1',
                        'buy_quantity': int(request.form.get(f'price_tiers[{idx}][buy_quantity]')) if request.form.get(f'price_tiers[{idx}][buy_quantity]') else None,
                        'get_quantity': int(request.form.get(f'price_tiers[{idx}][get_quantity]')) if request.form.get(f'price_tiers[{idx}][get_quantity]') else None,
                    }
                    price_tiers.append(tier)
        
        data = {
            'name': request.form.get('name'),
            'sku': request.form.get('sku'),
            'barcode': request.form.get('barcode'),
            'description': request.form.get('description'),
            'category': request.form.get('category'),
            'vendor_id': request.form.get('vendor_id') or None,
            'weight': float(request.form.get('weight')) if request.form.get('weight') else None,
            'cost_price': float(cost_price) if cost_price else 0,
            'selling_price': float(selling_price) if selling_price else 0,
            'pricing_type': pricing_type,
            'price_tiers': price_tiers if price_tiers else None,
            'is_active': request.form.get('is_active') == 'on'
        }
        
        update_response = api_put(f'/products/{product_id}', data)
        
        if update_response.status_code == 200:
            flash('Product updated successfully!', 'success')
            return redirect(url_for('inventory.view_product', product_id=product_id))
        else:
            flash(update_response.json().get('detail', 'Failed to update product'), 'error')
    
    # Get vendors for selection
    vendors_response = api_get('/vendors', {'page_size': 100})
    vendors = vendors_response.json().get('items', []) if vendors_response.status_code == 200 else []
    
    return render_template('warehouse/product_form.html',
                         product=product,
                         vendors=vendors,
                         preselected_vendor_id=None,
                         preselected_vendor=None)


@inventory_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
@permission_required('inventory.delete')
def delete_product(product_id):
    """Delete product"""
    response = api_delete(f'/products/{product_id}')
    
    if response.status_code == 204:
        flash('Product deleted successfully!', 'success')
    else:
        flash(response.json().get('detail', 'Failed to delete product'), 'error')
    
    return redirect(url_for('inventory.products'))


@inventory_bp.route('/movements')
@login_required
@permission_required('inventory.view')
def movements():
    """List stock movements"""
    page = request.args.get('page', 1, type=int)
    
    params = {'page': page, 'page_size': 20}
    
    response = api_get('/inventory/movements', params=params)
    data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    
    return render_template('warehouse/movements.html', 
                         movements=data.get('items', []),
                         pagination=data)


@inventory_bp.route('/movements/create', methods=['GET', 'POST'])
@login_required
@permission_required('inventory.create')
def create_movement():
    """Create stock movement"""
    if request.method == 'POST':
        data = {
            'product_id': int(request.form.get('product_id')),
            'warehouse_id': int(request.form.get('warehouse_id')),
            'movement_type': request.form.get('movement_type'),
            'quantity': int(request.form.get('quantity', 0)),
            'to_warehouse_id': int(request.form.get('to_warehouse_id')) if request.form.get('to_warehouse_id') else None,
            'unit_cost': float(request.form.get('unit_cost')) if request.form.get('unit_cost') else None,
            'notes': request.form.get('notes')
        }
        
        response = api_post('/inventory/movements', data)
        
        if response.status_code == 201:
            flash('Stock movement recorded!', 'success')
            return redirect(url_for('inventory.movements'))
        else:
            error_detail = response.json().get('detail', 'Failed to record movement') if response.json() else 'Failed to record movement'
            flash(error_detail, 'error')
    
    # Get products and warehouses
    products_response = api_get('/products', {'page_size': 100})
    products = products_response.json().get('items', []) if products_response.status_code == 200 else []
    
    warehouses_response = api_get('/warehouses')
    warehouses = warehouses_response.json().get('items', []) if warehouses_response.status_code == 200 else []
    
    return render_template('warehouse/movement_form.html', products=products, warehouses=warehouses)


# ==================== WAREHOUSE MANAGEMENT ====================

@inventory_bp.route('/warehouses')
@login_required
@permission_required('warehouses.view')
def warehouses():
    """List warehouses"""
    page = request.args.get('page', 1, type=int)
    
    params = {'page': page, 'page_size': 20}
    
    response = api_get('/warehouses', params=params)
    data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    
    return render_template('warehouse/warehouses.html', 
                         warehouses=data.get('items', []),
                         pagination=data)


@inventory_bp.route('/warehouses/create', methods=['GET', 'POST'])
@login_required
@permission_required('warehouses.create')
def create_warehouse():
    """Create warehouse"""
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'code': request.form.get('code'),
            'branch_id': int(request.form.get('branch_id')) if request.form.get('branch_id') else None,
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'country': request.form.get('country'),
            'manager_name': request.form.get('manager_name'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'capacity_sqm': float(request.form.get('capacity_sqm')) if request.form.get('capacity_sqm') else None,
            'max_items': int(request.form.get('max_items')) if request.form.get('max_items') else None,
            'latitude': float(request.form.get('latitude')) if request.form.get('latitude') else None,
            'longitude': float(request.form.get('longitude')) if request.form.get('longitude') else None
        }
        
        response = api_post('/warehouses', data)
        
        if response.status_code == 201:
            flash('Warehouse created successfully!', 'success')
            return redirect(url_for('inventory.warehouses'))
        else:
            error_detail = response.json().get('detail', 'Failed to create warehouse') if response.json() else 'Failed to create warehouse'
            flash(error_detail, 'error')
    
    # Get branches for selection
    branches_response = api_get('/branches')
    branches = branches_response.json().get('items', []) if branches_response.status_code == 200 else []
    
    return render_template('warehouse/warehouse_form.html', warehouse=None, branches=branches)


@inventory_bp.route('/warehouses/<int:warehouse_id>')
@login_required
@permission_required('warehouses.view')
def view_warehouse(warehouse_id):
    """View warehouse details"""
    response = api_get(f'/warehouses/{warehouse_id}')
    
    if response.status_code != 200:
        flash('Warehouse not found', 'error')
        return redirect(url_for('inventory.warehouses'))
    
    warehouse = response.json()
    
    # Get inventory for this warehouse
    inventory_response = api_get('/inventory', params={'warehouse_id': warehouse_id, 'page_size': 20})
    inventory = inventory_response.json().get('items', []) if inventory_response.status_code == 200 else []
    
    return render_template('warehouse/warehouse_detail.html', warehouse=warehouse, inventory=inventory)


@inventory_bp.route('/warehouses/<int:warehouse_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('warehouses.update')
def edit_warehouse(warehouse_id):
    """Edit warehouse"""
    response = api_get(f'/warehouses/{warehouse_id}')
    
    if response.status_code != 200:
        flash('Warehouse not found', 'error')
        return redirect(url_for('inventory.warehouses'))
    
    warehouse = response.json()
    
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'code': request.form.get('code'),
            'branch_id': int(request.form.get('branch_id')) if request.form.get('branch_id') else None,
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'country': request.form.get('country'),
            'manager_name': request.form.get('manager_name'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'capacity_sqm': float(request.form.get('capacity_sqm')) if request.form.get('capacity_sqm') else None,
            'max_items': int(request.form.get('max_items')) if request.form.get('max_items') else None,
            'latitude': float(request.form.get('latitude')) if request.form.get('latitude') else None,
            'longitude': float(request.form.get('longitude')) if request.form.get('longitude') else None,
            'status': request.form.get('status')
        }
        
        update_response = api_put(f'/warehouses/{warehouse_id}', data)
        
        if update_response.status_code == 200:
            flash('Warehouse updated successfully!', 'success')
            return redirect(url_for('inventory.view_warehouse', warehouse_id=warehouse_id))
        else:
            error_detail = update_response.json().get('detail', 'Failed to update warehouse') if update_response.json() else 'Failed to update warehouse'
            flash(error_detail, 'error')
    
    # Get branches for selection
    branches_response = api_get('/branches')
    branches = branches_response.json().get('items', []) if branches_response.status_code == 200 else []
    
    return render_template('warehouse/warehouse_form.html', warehouse=warehouse, branches=branches)


@inventory_bp.route('/warehouses/<int:warehouse_id>/delete', methods=['POST'])
@login_required
@permission_required('warehouses.delete')
def delete_warehouse(warehouse_id):
    """Delete warehouse"""
    response = api_delete(f'/warehouses/{warehouse_id}')
    
    if response.status_code == 200:
        flash('Warehouse deactivated successfully!', 'success')
    else:
        error_detail = response.json().get('detail', 'Failed to delete warehouse') if response.json() else 'Failed to delete warehouse'
        flash(error_detail, 'error')
    
    return redirect(url_for('inventory.warehouses'))
