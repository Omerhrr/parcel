"""
Bulk Operations Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required
from app.utils.permissions import permission_required
from werkzeug.utils import secure_filename
import requests
import io
import csv
import json

bulk_bp = Blueprint('bulk', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    token_data = session.get('token_data', {})
    token = token_data.get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


# ============== BULK STATUS UPDATES ==============

@bulk_bp.route('/waybills/status', methods=['POST'])
@login_required
@permission_required('orders.update')
def update_waybills_status():
    """Update status for multiple waybills"""
    ids = request.form.getlist('ids[]') or request.form.getlist('ids')
    status_value = request.form.get('status')
    notes = request.form.get('notes', '')
    
    if not ids:
        flash('No waybills selected', 'error')
        return redirect(request.referrer or url_for('waybills.index'))
    
    if not status_value:
        flash('No status selected', 'error')
        return redirect(request.referrer or url_for('waybills.index'))
    
    data = {
        'ids': [int(id) for id in ids],
        'status': status_value,
        'notes': notes
    }
    
    try:
        response = requests.post(
            f"{get_api_url()}/bulk/waybills/status",
            json=data,
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            flash(result.get('message', 'Status updated successfully'), 'success')
        else:
            error_data = response.json()
            flash(error_data.get('detail', 'Failed to update status'), 'error')
    except Exception as e:
        flash('Error updating status', 'error')
    
    return redirect(request.referrer or url_for('waybills.index'))


@bulk_bp.route('/orders/status', methods=['POST'])
@login_required
@permission_required('orders.update')
def update_orders_status():
    """Update status for multiple orders"""
    ids = request.form.getlist('ids[]') or request.form.getlist('ids')
    status_value = request.form.get('status')
    notes = request.form.get('notes', '')
    
    if not ids:
        flash('No orders selected', 'error')
        return redirect(request.referrer or url_for('orders.index'))
    
    if not status_value:
        flash('No status selected', 'error')
        return redirect(request.referrer or url_for('orders.index'))
    
    data = {
        'ids': [int(id) for id in ids],
        'status': status_value,
        'notes': notes
    }
    
    try:
        response = requests.post(
            f"{get_api_url()}/bulk/orders/status",
            json=data,
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            flash(result.get('message', 'Status updated successfully'), 'success')
        else:
            error_data = response.json()
            flash(error_data.get('detail', 'Failed to update status'), 'error')
    except Exception as e:
        flash('Error updating status', 'error')
    
    return redirect(request.referrer or url_for('orders.index'))


@bulk_bp.route('/dispatches/assign', methods=['POST'])
@login_required
@permission_required('deliveries.update')
def assign_dispatches():
    """Assign multiple dispatches to an agent"""
    dispatch_ids = request.form.getlist('dispatch_ids[]') or request.form.getlist('dispatch_ids')
    agent_id = request.form.get('agent_id')
    
    if not dispatch_ids:
        flash('No dispatches selected', 'error')
        return redirect(request.referrer or url_for('logistics.list_dispatches'))
    
    if not agent_id:
        flash('No agent selected', 'error')
        return redirect(request.referrer or url_for('logistics.list_dispatches'))
    
    data = {
        'dispatch_ids': [int(id) for id in dispatch_ids],
        'agent_id': int(agent_id)
    }
    
    try:
        response = requests.post(
            f"{get_api_url()}/bulk/dispatches/assign",
            json=data,
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            result = response.json()
            flash(result.get('message', 'Dispatches assigned successfully'), 'success')
        else:
            error_data = response.json()
            flash(error_data.get('detail', 'Failed to assign dispatches'), 'error')
    except Exception as e:
        flash('Error assigning dispatches', 'error')
    
    return redirect(request.referrer or url_for('logistics.list_dispatches'))


# ============== BULK IMPORT PAGES ==============

@bulk_bp.route('/import')
@login_required
@permission_required('orders.view')
def import_page():
    """Generic import page"""
    return render_template('bulk/import.html')


@bulk_bp.route('/import/waybills', methods=['GET', 'POST'])
@login_required
@permission_required('orders.create')
def import_waybills():
    """Import waybills from CSV/JSON"""
    if request.method == 'POST':
        branch_id = request.form.get('branch_id')
        
        # Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file.filename.endswith('.csv'):
            # Upload CSV to API
            files = {'file': (secure_filename(file.filename), file.read(), 'text/csv')}
            params = {'branch_id': branch_id} if branch_id else {}
            
            # Reset file pointer
            file.seek(0)
            files = {'file': (secure_filename(file.filename), file.read(), 'text/csv')}
            
            try:
                response = requests.post(
                    f"{get_api_url()}/bulk/waybills/import-csv",
                    files=files,
                    params=params,
                    headers=get_auth_headers()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    flash(result.get('message', 'Import completed'), 'success')
                    if result.get('failure_count', 0) > 0:
                        errors = [r for r in result.get('results', []) if not r.get('success')]
                        for error in errors[:5]:  # Show first 5 errors
                            flash(f"{error.get('identifier', 'Unknown')}: {error.get('error', 'Unknown error')}", 'warning')
                else:
                    error_data = response.json()
                    flash(error_data.get('detail', 'Import failed'), 'error')
            except Exception as e:
                flash('Error importing waybills', 'error')
            
            return redirect(request.url)
        
        elif file.filename.endswith('.json'):
            try:
                data = json.load(file)
                waybills = data if isinstance(data, list) else data.get('waybills', [])
                
                payload = {
                    'waybills': waybills,
                    'branch_id': int(branch_id) if branch_id else None
                }
                
                response = requests.post(
                    f"{get_api_url()}/bulk/waybills/import",
                    json=payload,
                    headers=get_auth_headers()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    flash(result.get('message', 'Import completed'), 'success')
                else:
                    error_data = response.json()
                    flash(error_data.get('detail', 'Import failed'), 'error')
            except Exception as e:
                flash('Error parsing JSON file', 'error')
            
            return redirect(request.url)
        else:
            flash('Invalid file format. Please upload CSV or JSON.', 'error')
            return redirect(request.url)
    
    # GET request - show import form
    branches = []
    try:
        response = requests.get(
            f"{get_api_url()}/branches",
            params={'page_size': 100},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            branches = response.json().get('items', [])
    except:
        pass
    
    return render_template('bulk/waybills_import.html', branches=branches)


@bulk_bp.route('/import/orders', methods=['GET', 'POST'])
@login_required
@permission_required('orders.create')
def import_orders():
    """Import orders from CSV/JSON"""
    if request.method == 'POST':
        branch_id = request.form.get('branch_id')
        
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file.filename.endswith('.csv'):
            files = {'file': (secure_filename(file.filename), file.read(), 'text/csv')}
            params = {'branch_id': branch_id} if branch_id else {}
            
            try:
                response = requests.post(
                    f"{get_api_url()}/bulk/orders/import-csv",
                    files=files,
                    params=params,
                    headers=get_auth_headers()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    flash(result.get('message', 'Import completed'), 'success')
                else:
                    error_data = response.json()
                    flash(error_data.get('detail', 'Import failed'), 'error')
            except Exception as e:
                flash('Error importing orders', 'error')
            
            return redirect(request.url)
        
        elif file.filename.endswith('.json'):
            try:
                data = json.load(file)
                orders = data if isinstance(data, list) else data.get('orders', [])
                
                payload = {
                    'orders': orders,
                    'branch_id': int(branch_id) if branch_id else None
                }
                
                response = requests.post(
                    f"{get_api_url()}/bulk/orders/import",
                    json=payload,
                    headers=get_auth_headers()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    flash(result.get('message', 'Import completed'), 'success')
                else:
                    error_data = response.json()
                    flash(error_data.get('detail', 'Import failed'), 'error')
            except Exception as e:
                flash('Error parsing JSON file', 'error')
            
            return redirect(request.url)
        else:
            flash('Invalid file format. Please upload CSV or JSON.', 'error')
            return redirect(request.url)
    
    # GET request - show import form
    branches = []
    try:
        response = requests.get(
            f"{get_api_url()}/branches",
            params={'page_size': 100},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            branches = response.json().get('items', [])
    except:
        pass
    
    return render_template('bulk/orders_import.html', branches=branches)


@bulk_bp.route('/import/agents', methods=['GET', 'POST'])
@login_required
@permission_required('settings.manage')
def import_agents():
    """Import agents from CSV/JSON"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file.filename.endswith('.csv'):
            files = {'file': (secure_filename(file.filename), file.read(), 'text/csv')}
            
            try:
                response = requests.post(
                    f"{get_api_url()}/bulk/agents/import-csv",
                    files=files,
                    headers=get_auth_headers()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    flash(result.get('message', 'Import completed'), 'success')
                else:
                    error_data = response.json()
                    flash(error_data.get('detail', 'Import failed'), 'error')
            except Exception as e:
                flash('Error importing agents', 'error')
            
            return redirect(request.url)
        
        elif file.filename.endswith('.json'):
            try:
                data = json.load(file)
                agents = data if isinstance(data, list) else data.get('agents', [])
                
                response = requests.post(
                    f"{get_api_url()}/bulk/agents/import",
                    json={'agents': agents},
                    headers=get_auth_headers()
                )
                
                if response.status_code == 200:
                    result = response.json()
                    flash(result.get('message', 'Import completed'), 'success')
                else:
                    error_data = response.json()
                    flash(error_data.get('detail', 'Import failed'), 'error')
            except Exception as e:
                flash('Error parsing JSON file', 'error')
            
            return redirect(request.url)
        else:
            flash('Invalid file format. Please upload CSV or JSON.', 'error')
            return redirect(request.url)
    
    return render_template('bulk/agents_import.html')


# ============== CSV EXPORT ==============

@bulk_bp.route('/export/waybills')
@login_required
@permission_required('orders.view')
def export_waybills():
    """Export waybills to CSV"""
    # Get filter parameters from query string
    params = {}
    for key in ['status', 'branch_id', 'search', 'date_from', 'date_to']:
        value = request.args.get(key)
        if value:
            params[key] = value
    
    try:
        response = requests.get(
            f"{get_api_url()}/bulk/waybills/export",
            params=params,
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            from flask import Response
            return Response(
                response.content,
                mimetype='text/csv',
                headers=dict(response.headers)
            )
        else:
            flash('Failed to export waybills', 'error')
            return redirect(request.referrer or url_for('waybills.index'))
    except Exception as e:
        flash('Error exporting waybills', 'error')
        return redirect(request.referrer or url_for('waybills.index'))


@bulk_bp.route('/export/orders')
@login_required
@permission_required('orders.view')
def export_orders():
    """Export orders to CSV"""
    params = {}
    for key in ['status', 'branch_id', 'search', 'date_from', 'date_to']:
        value = request.args.get(key)
        if value:
            params[key] = value
    
    try:
        response = requests.get(
            f"{get_api_url()}/bulk/orders/export",
            params=params,
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            from flask import Response
            return Response(
                response.content,
                mimetype='text/csv',
                headers=dict(response.headers)
            )
        else:
            flash('Failed to export orders', 'error')
            return redirect(request.referrer or url_for('orders.index'))
    except Exception as e:
        flash('Error exporting orders', 'error')
        return redirect(request.referrer or url_for('orders.index'))


@bulk_bp.route('/export/dispatches')
@login_required
@permission_required('deliveries.view')
def export_dispatches():
    """Export dispatches to CSV"""
    params = {}
    for key in ['status', 'agent_id']:
        value = request.args.get(key)
        if value:
            params[key] = value
    
    try:
        response = requests.get(
            f"{get_api_url()}/bulk/dispatches/export",
            params=params,
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            from flask import Response
            return Response(
                response.content,
                mimetype='text/csv',
                headers=dict(response.headers)
            )
        else:
            flash('Failed to export dispatches', 'error')
            return redirect(request.referrer or url_for('logistics.list_dispatches'))
    except Exception as e:
        flash('Error exporting dispatches', 'error')
        return redirect(request.referrer or url_for('logistics.list_dispatches'))


# ============== HTMX PARTIALS ==============

@bulk_bp.route('/progress/<operation_id>')
@login_required
def import_progress(operation_id):
    """Get progress for an ongoing import operation (for HTMX polling)"""
    # This would typically check a background job status
    # For now, return a placeholder
    return render_template('bulk/partials/progress.html', 
                          operation_id=operation_id,
                          progress=100,
                          status='completed')
