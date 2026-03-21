"""
Leads Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from app.utils.permissions import permission_required
import requests

leads_bp = Blueprint('leads', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    token = session.get('token_data', {}).get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


@leads_bp.route('/')
@login_required
@permission_required('leads.view')
def index():
    """List leads"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    source = request.args.get('source', '')
    search = request.args.get('search', '')
    
    params = {'page': page, 'page_size': 20}
    if status:
        params['status'] = status
    if source:
        params['source'] = source
    if search:
        params['search'] = search
    
    try:
        response = requests.get(
            f"{get_api_url()}/leads",
            params=params,
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    except:
        data = {'items': [], 'total': 0}
    
    return render_template('leads/index.html',
                         leads=data.get('items', []),
                         pagination=data,
                         filters={'status': status, 'source': source, 'search': search})


@leads_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('leads.create')
def create():
    """Create lead"""
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email') or None,
            'company_name': request.form.get('company_name') or None,
            'company_size': request.form.get('company_size') or None,
            'industry': request.form.get('industry') or None,
            'address': request.form.get('address') or None,
            'city': request.form.get('city') or None,
            'state': request.form.get('state') or None,
            'product_interest': request.form.get('product_interest') or None,
            'service_interest': request.form.get('service_interest') or None,
            'estimated_value': float(request.form.get('estimated_value', 0)) if request.form.get('estimated_value') else None,
            'source': request.form.get('source', 'other'),
            'source_details': request.form.get('source_details') or None,
            'assigned_to_user_id': int(request.form.get('assigned_to_user_id')) if request.form.get('assigned_to_user_id') else None,
            'next_follow_up': request.form.get('next_follow_up') or None,
            'notes': request.form.get('notes') or None
        }
        
        try:
            response = requests.post(
                f"{get_api_url()}/leads",
                json=data,
                headers=get_auth_headers()
            )
            if response.status_code == 201:
                flash('Lead created successfully!', 'success')
                return redirect(url_for('leads.view', lead_id=response.json()['id']))
            else:
                flash(response.json().get('detail', 'Failed to create lead'), 'error')
        except:
            flash('Error creating lead', 'error')
    
    # Get users for assignment
    try:
        users_response = requests.get(
            f"{get_api_url()}/users",
            params={'page_size': 100},
            headers=get_auth_headers()
        )
        users = users_response.json().get('items', []) if users_response.status_code == 200 else []
    except:
        users = []
    
    return render_template('leads/form.html', lead=None, users=users)


@leads_bp.route('/<int:lead_id>')
@login_required
@permission_required('leads.view')
def view(lead_id):
    """View lead details"""
    try:
        response = requests.get(
            f"{get_api_url()}/leads/{lead_id}",
            headers=get_auth_headers()
        )
        if response.status_code != 200:
            flash('Lead not found', 'error')
            return redirect(url_for('leads.index'))
        lead = response.json()
    except:
        flash('Error loading lead', 'error')
        return redirect(url_for('leads.index'))
    
    return render_template('leads/detail.html', lead=lead)


@leads_bp.route('/<int:lead_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('leads.update')
def edit(lead_id):
    """Edit lead"""
    # Get lead
    try:
        response = requests.get(
            f"{get_api_url()}/leads/{lead_id}",
            headers=get_auth_headers()
        )
        if response.status_code != 200:
            flash('Lead not found', 'error')
            return redirect(url_for('leads.index'))
        lead = response.json()
    except:
        flash('Error loading lead', 'error')
        return redirect(url_for('leads.index'))
    
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email') or None,
            'company_name': request.form.get('company_name') or None,
            'company_size': request.form.get('company_size') or None,
            'industry': request.form.get('industry') or None,
            'address': request.form.get('address') or None,
            'city': request.form.get('city') or None,
            'state': request.form.get('state') or None,
            'product_interest': request.form.get('product_interest') or None,
            'service_interest': request.form.get('service_interest') or None,
            'estimated_value': float(request.form.get('estimated_value', 0)) if request.form.get('estimated_value') else None,
            'status': request.form.get('status', 'new'),
            'assigned_to_user_id': int(request.form.get('assigned_to_user_id')) if request.form.get('assigned_to_user_id') else None,
            'next_follow_up': request.form.get('next_follow_up') or None,
            'notes': request.form.get('notes') or None
        }
        
        try:
            response = requests.put(
                f"{get_api_url()}/leads/{lead_id}",
                json=data,
                headers=get_auth_headers()
            )
            if response.status_code == 200:
                flash('Lead updated successfully!', 'success')
                return redirect(url_for('leads.view', lead_id=lead_id))
            else:
                flash(response.json().get('detail', 'Failed to update lead'), 'error')
        except:
            flash('Error updating lead', 'error')
    
    # Get users for assignment
    try:
        users_response = requests.get(
            f"{get_api_url()}/users",
            params={'page_size': 100},
            headers=get_auth_headers()
        )
        users = users_response.json().get('items', []) if users_response.status_code == 200 else []
    except:
        users = []
    
    return render_template('leads/form.html', lead=lead, users=users)


@leads_bp.route('/<int:lead_id>/convert', methods=['POST'])
@login_required
@permission_required('leads.update')
def convert(lead_id):
    """Convert lead to order"""
    try:
        response = requests.post(
            f"{get_api_url()}/leads/{lead_id}/convert",
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Lead converted successfully!', 'success')
        else:
            flash(response.json().get('detail', 'Failed to convert lead'), 'error')
    except:
        flash('Error converting lead', 'error')
    
    return redirect(url_for('leads.view', lead_id=lead_id))


@leads_bp.route('/<int:lead_id>/delete', methods=['POST'])
@login_required
@permission_required('leads.update')
def delete(lead_id):
    """Delete lead"""
    try:
        response = requests.delete(
            f"{get_api_url()}/leads/{lead_id}",
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Lead deleted successfully!', 'success')
            return redirect(url_for('leads.index'))
        else:
            flash(response.json().get('detail', 'Failed to delete lead'), 'error')
    except:
        flash('Error deleting lead', 'error')
    
    return redirect(url_for('leads.view', lead_id=lead_id))
