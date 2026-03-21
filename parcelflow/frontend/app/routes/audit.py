"""
Audit Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from app.utils.permissions import permission_required
import requests

audit_bp = Blueprint('audit', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    token = session.get('token_data', {}).get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


@audit_bp.route('/')
@login_required
@permission_required('audit.view')
def index():
    """List audit logs"""
    page = request.args.get('page', 1, type=int)
    entity_type = request.args.get('entity_type', '')
    action = request.args.get('action', '')
    user_id = request.args.get('user_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    params = {'page': page, 'page_size': 20}
    if entity_type:
        params['entity_type'] = entity_type
    if action:
        params['action'] = action
    if user_id:
        params['user_id'] = user_id
    if date_from:
        params['date_from'] = date_from
    if date_to:
        params['date_to'] = date_to
    
    try:
        response = requests.get(
            f"{get_api_url()}/audit-logs",
            params=params,
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    except:
        data = {'items': [], 'total': 0}
    
    # Get users for filter
    users = []
    try:
        users_response = requests.get(
            f"{get_api_url()}/users",
            params={'page_size': 100},
            headers=get_auth_headers()
        )
        users = users_response.json().get('items', []) if users_response.status_code == 200 else []
    except:
        pass
    
    return render_template('audit/index.html',
                         logs=data.get('items', []),
                         pagination=data,
                         users=users,
                         filters={
                             'entity_type': entity_type,
                             'action': action,
                             'user_id': user_id,
                             'date_from': date_from,
                             'date_to': date_to
                         })


@audit_bp.route('/<int:log_id>')
@login_required
@permission_required('audit.view')
def view(log_id):
    """View audit log details"""
    try:
        response = requests.get(
            f"{get_api_url()}/audit-logs/{log_id}",
            headers=get_auth_headers()
        )
        if response.status_code != 200:
            flash('Audit log not found', 'error')
            return redirect(url_for('audit.index'))
        log = response.json()
    except:
        flash('Error loading audit log', 'error')
        return redirect(url_for('audit.index'))
    
    return render_template('audit/detail.html', log=log)
