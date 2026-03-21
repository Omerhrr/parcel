"""
Agents Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.api_client import api_get, api_post, api_put
from app.utils.permissions import permission_required

agents_bp = Blueprint('agents', __name__)


@agents_bp.route('/')
@login_required
@permission_required('agents.view')
def index():
    """List agents"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    params = {'page': page, 'page_size': 20}
    if status:
        params['status'] = status
    
    response = api_get('/agents', params=params)
    data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    
    return render_template('agents/index.html', 
                         agents=data.get('items', []),
                         pagination=data,
                         status_filter=status)


@agents_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('agents.create')
def create():
    """Create agent"""
    if request.method == 'POST':
        # Get branch_id and convert to int or None
        branch_id = request.form.get('branch_id')
        if branch_id:
            try:
                branch_id = int(branch_id)
            except ValueError:
                branch_id = None
        else:
            branch_id = None
        
        # Get numeric values
        base_salary = request.form.get('base_salary') or 0
        commission_rate = request.form.get('commission_rate') or 0
        
        data = {
            'name': request.form.get('name'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email') or None,
            'employee_id': request.form.get('employee_id') or None,
            'vehicle_type': request.form.get('vehicle_type', 'bike'),
            'branch_id': branch_id,
            'base_salary': float(base_salary) if base_salary else 0,
            'commission_rate': float(commission_rate) if commission_rate else 0,
            'notes': request.form.get('notes') or None
        }
        
        response = api_post('/agents', data)
        
        if response.status_code == 201:
            flash('Agent created successfully!', 'success')
            return redirect(url_for('agents.view', agent_id=response.json()['id']))
        else:
            error_detail = response.json().get('detail', 'Failed to create agent')
            flash(error_detail, 'error')
    
    # Get branches for selection
    branches_response = api_get('/branches')
    branches = branches_response.json().get('items', []) if branches_response.status_code == 200 else []
    
    return render_template('agents/form.html', agent=None, branches=branches)


@agents_bp.route('/<int:agent_id>')
@login_required
@permission_required('agents.view')
def view(agent_id):
    """View agent details"""
    response = api_get(f'/agents/{agent_id}')
    
    if response.status_code != 200:
        flash('Agent not found', 'error')
        return redirect(url_for('agents.index'))
    
    agent = response.json()
    
    # Get agent stats
    stats_response = api_get(f'/agents/{agent_id}/stats')
    stats = stats_response.json() if stats_response.status_code == 200 else {}
    
    return render_template('agents/detail.html', agent=agent, stats=stats)


@agents_bp.route('/<int:agent_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('agents.update')
def edit(agent_id):
    """Edit agent"""
    response = api_get(f'/agents/{agent_id}')
    
    if response.status_code != 200:
        flash('Agent not found', 'error')
        return redirect(url_for('agents.index'))
    
    agent = response.json()
    
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'vehicle_type': request.form.get('vehicle_type'),
            'status': request.form.get('status'),
            'base_salary': request.form.get('base_salary'),
            'commission_rate': request.form.get('commission_rate'),
            'notes': request.form.get('notes')
        }
        
        response = api_put(f'/agents/{agent_id}', data)
        
        if response.status_code == 200:
            flash('Agent updated successfully!', 'success')
            return redirect(url_for('agents.view', agent_id=agent_id))
        else:
            flash(response.json().get('detail', 'Failed to update agent'), 'error')
    
    branches_response = api_get('/branches')
    branches = branches_response.json().get('items', []) if branches_response.status_code == 200 else []
    
    return render_template('agents/form.html', agent=agent, branches=branches)
