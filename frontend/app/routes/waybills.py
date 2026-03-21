"""
Waybills Routes Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from app.utils.permissions import permission_required
import requests

waybills_bp = Blueprint('waybills', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    token = session.get('token_data', {}).get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


@waybills_bp.route('/')
@login_required
@permission_required('orders.view')
def index():
    """List waybills"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    
    params = {'page': page, 'page_size': 20}
    if status:
        params['status'] = status
    if search:
        params['search'] = search
    
    try:
        response = requests.get(
            f"{get_api_url()}/waybills",
            params=params,
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    except:
        data = {'items': [], 'total': 0}
    
    return render_template('logistics/waybills.html', 
                         waybills=data.get('items', []),
                         pagination=data,
                         filters={'status': status, 'search': search})


@waybills_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('orders.create')
def create():
    """Create waybill"""
    if request.method == 'POST':
        data = {
            'branch_id': request.form.get('branch_id') or None,
            'shipment_type': request.form.get('shipment_type', 'warehouse_delivery'),
            'sender_name': request.form.get('sender_name'),
            'sender_phone': request.form.get('sender_phone'),
            'sender_email': request.form.get('sender_email'),
            'sender_address': request.form.get('sender_address'),
            'sender_city': request.form.get('sender_city'),
            'receiver_name': request.form.get('receiver_name'),
            'receiver_phone': request.form.get('receiver_phone'),
            'receiver_email': request.form.get('receiver_email'),
            'receiver_address': request.form.get('receiver_address'),
            'receiver_city': request.form.get('receiver_city'),
            'receiver_landmark': request.form.get('receiver_landmark'),
            'item_description': request.form.get('item_description'),
            'quantity': int(request.form.get('quantity', 1)),
            'weight': request.form.get('weight'),
            'dimensions': request.form.get('dimensions'),
            'payment_type': request.form.get('payment_type', 'cod'),
            'declared_value': request.form.get('declared_value', 0),
            'delivery_fee': request.form.get('delivery_fee', 0),
            'total_amount': request.form.get('total_amount', 0),
            'cod_amount': request.form.get('cod_amount', 0),
            'notes': request.form.get('notes')
        }
        
        response = requests.post(
            f"{get_api_url()}/waybills",
            json=data,
            headers=get_auth_headers()
        )
        
        if response.status_code == 201:
            flash('Waybill created successfully!', 'success')
            return redirect(url_for('waybills.view', waybill_id=response.json()['id']))
        else:
            flash(response.json().get('detail', 'Failed to create waybill'), 'error')
    
    return render_template('logistics/waybill_form.html', waybill=None)


@waybills_bp.route('/<int:waybill_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('orders.update')
def update(waybill_id):
    """Edit waybill"""
    # Get waybill data
    try:
        response = requests.get(
            f"{get_api_url()}/waybills/{waybill_id}",
            headers=get_auth_headers()
        )
        
        if response.status_code != 200:
            flash('Waybill not found', 'error')
            return redirect(url_for('waybills.index'))
        
        waybill = response.json()
    except:
        flash('Error loading waybill', 'error')
        return redirect(url_for('waybills.index'))
    
    if request.method == 'POST':
        data = {
            'branch_id': request.form.get('branch_id') or None,
            'shipment_type': request.form.get('shipment_type', 'warehouse_delivery'),
            'sender_name': request.form.get('sender_name'),
            'sender_phone': request.form.get('sender_phone'),
            'sender_email': request.form.get('sender_email'),
            'sender_address': request.form.get('sender_address'),
            'sender_city': request.form.get('sender_city'),
            'receiver_name': request.form.get('receiver_name'),
            'receiver_phone': request.form.get('receiver_phone'),
            'receiver_email': request.form.get('receiver_email'),
            'receiver_address': request.form.get('receiver_address'),
            'receiver_city': request.form.get('receiver_city'),
            'receiver_landmark': request.form.get('receiver_landmark'),
            'item_description': request.form.get('item_description'),
            'quantity': int(request.form.get('quantity', 1)),
            'weight': request.form.get('weight'),
            'dimensions': request.form.get('dimensions'),
            'payment_type': request.form.get('payment_type', 'cod'),
            'declared_value': request.form.get('declared_value', 0),
            'delivery_fee': request.form.get('delivery_fee', 0),
            'total_amount': request.form.get('total_amount', 0),
            'cod_amount': request.form.get('cod_amount', 0),
            'notes': request.form.get('notes'),
            'special_instructions': request.form.get('special_instructions')
        }
        
        response = requests.put(
            f"{get_api_url()}/waybills/{waybill_id}",
            json=data,
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            flash('Waybill updated successfully!', 'success')
            return redirect(url_for('waybills.view', waybill_id=waybill_id))
        else:
            flash(response.json().get('detail', 'Failed to update waybill'), 'error')
    
    return render_template('logistics/waybill_form.html', waybill=waybill)


@waybills_bp.route('/<int:waybill_id>')
@login_required
@permission_required('orders.view')
def view(waybill_id):
    """View waybill details"""
    try:
        response = requests.get(
            f"{get_api_url()}/waybills/{waybill_id}",
            headers=get_auth_headers()
        )
        
        if response.status_code != 200:
            flash('Waybill not found', 'error')
            return redirect(url_for('waybills.index'))
        
        waybill = response.json()
    except:
        flash('Error loading waybill', 'error')
        return redirect(url_for('waybills.index'))
    
    return render_template('logistics/waybill_detail.html', waybill=waybill)


@waybills_bp.route('/<int:waybill_id>/update-status', methods=['POST'])
@login_required
@permission_required('orders.update')
def update_status(waybill_id):
    """Update waybill status"""
    status = request.form.get('status')
    location = request.form.get('location')
    notes = request.form.get('notes')
    
    try:
        response = requests.put(
            f"{get_api_url()}/waybills/{waybill_id}/status",
            json={
                'status': status,
                'location': location,
                'notes': notes
            },
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            flash('Status updated successfully!', 'success')
        else:
            flash(response.json().get('detail', 'Failed to update status'), 'error')
    except:
        flash('Error updating status', 'error')
    
    return redirect(url_for('waybills.view', waybill_id=waybill_id))


@waybills_bp.route('/track')
def track():
    """Public tracking page"""
    waybill_number = request.args.get('waybill_number')
    waybill = None
    
    if waybill_number:
        try:
            response = requests.get(f"{get_api_url()}/tracking/{waybill_number}")
            if response.status_code == 200:
                waybill = response.json()
        except:
            pass
    
    return render_template('logistics/tracking.html', waybill=waybill, waybill_number=waybill_number)


@waybills_bp.route('/<int:waybill_id>/cancel', methods=['POST'])
@login_required
@permission_required('orders.update')
def cancel(waybill_id):
    """Cancel a waybill"""
    reason = request.form.get('reason', '')
    
    try:
        response = requests.post(
            f"{get_api_url()}/waybills/{waybill_id}/cancel",
            params={'reason': reason},
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            flash('Waybill cancelled successfully!', 'success')
        else:
            flash(response.json().get('detail', 'Failed to cancel waybill'), 'error')
    except:
        flash('Error cancelling waybill', 'error')
    
    return redirect(url_for('waybills.view', waybill_id=waybill_id))


@waybills_bp.route('/<int:waybill_id>/delete', methods=['POST'])
@login_required
@permission_required('orders.update')
def delete(waybill_id):
    """Delete a waybill"""
    try:
        response = requests.delete(
            f"{get_api_url()}/waybills/{waybill_id}",
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            flash('Waybill deleted successfully!', 'success')
            return redirect(url_for('waybills.index'))
        else:
            flash(response.json().get('detail', 'Failed to delete waybill'), 'error')
    except:
        flash('Error deleting waybill', 'error')
    
    return redirect(url_for('waybills.view', waybill_id=waybill_id))
