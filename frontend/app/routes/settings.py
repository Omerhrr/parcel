"""
Settings Routes Blueprint
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from app.utils.permissions import permission_required, is_super_admin
import requests

settings_bp = Blueprint('settings', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    token = session.get('token_data', {}).get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


@settings_bp.route('/')
@login_required
@permission_required('settings.view')
def index():
    """Settings overview"""
    try:
        response = requests.get(
            f"{get_api_url()}/businesses/current",
            headers=get_auth_headers()
        )
        business = response.json() if response.status_code == 200 else {}
    except:
        business = {}
    
    return render_template('settings/index.html', business=business)


@settings_bp.route('/business', methods=['GET', 'POST'])
@login_required
@permission_required('settings.view')
def business():
    """Business settings"""
    try:
        response = requests.get(
            f"{get_api_url()}/businesses/current",
            headers=get_auth_headers()
        )
        business = response.json() if response.status_code == 200 else {}
    except:
        business = {}
    
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'primary_color': request.form.get('primary_color')
        }
        
        try:
            response = requests.put(
                f"{get_api_url()}/businesses/current",
                json=data,
                headers=get_auth_headers()
            )
            
            if response.status_code == 200:
                flash('Business settings updated!', 'success')
                business = response.json()
            else:
                flash(response.json().get('detail', 'Failed to update settings'), 'error')
        except:
            flash('Error updating settings', 'error')
    
    return render_template('settings/business.html', business=business)


@settings_bp.route('/email', methods=['GET', 'POST'])
@login_required
@permission_required('settings.view')
def email_settings():
    """Email settings"""
    # Get business info
    try:
        response = requests.get(
            f"{get_api_url()}/businesses/current",
            headers=get_auth_headers()
        )
        business = response.json() if response.status_code == 200 else {}
    except:
        business = {}
    
    # Get email settings
    try:
        response = requests.get(
            f"{get_api_url()}/businesses/current/email-settings",
            headers=get_auth_headers()
        )
        email_settings = response.json() if response.status_code == 200 else {}
    except:
        email_settings = {}
    
    if request.method == 'POST':
        data = {
            'smtp_host': request.form.get('smtp_host') or None,
            'smtp_port': int(request.form.get('smtp_port') or 587),
            'smtp_user': request.form.get('smtp_user') or None,
            'smtp_password': request.form.get('smtp_password') or None,
            'smtp_use_tls': request.form.get('smtp_use_tls') == 'on',
            'email_from_name': request.form.get('email_from_name') or business.get('name', 'ParcelFlow'),
            'email_from_address': request.form.get('email_from_address') or None,
            'email_enabled': request.form.get('email_enabled') == 'on',
        }
        
        # Remove None values to keep existing
        data = {k: v for k, v in data.items() if v is not None or k in ['smtp_use_tls', 'email_enabled']}
        
        try:
            response = requests.put(
                f"{get_api_url()}/businesses/current/email-settings",
                json=data,
                headers=get_auth_headers()
            )
            
            if response.status_code == 200:
                flash('Email settings updated!', 'success')
                email_settings = response.json()
            else:
                flash(response.json().get('detail', 'Failed to update email settings'), 'error')
        except Exception as e:
            flash('Error updating email settings', 'error')
    
    return render_template('settings/email.html', business=business, email_settings=email_settings)


@settings_bp.route('/email/test', methods=['POST'])
@login_required
@permission_required('settings.update')
def test_email():
    """Send test email"""
    try:
        response = requests.post(
            f"{get_api_url()}/businesses/current/email-settings/test",
            headers=get_auth_headers()
        )
        return response.json(), response.status_code
    except Exception as e:
        return {'success': False, 'detail': str(e)}, 500


@settings_bp.route('/branches')
@login_required
@permission_required('branches.view')
def branches():
    """Branch management"""
    try:
        response = requests.get(
            f"{get_api_url()}/branches",
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': []}
    except:
        data = {'items': []}
    
    return render_template('settings/branches.html', branches=data.get('items', []))


@settings_bp.route('/branches/create', methods=['GET', 'POST'])
@login_required
@permission_required('branches.create')
def branch_create():
    """Create a new branch"""
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'code': request.form.get('code'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'country': request.form.get('country', 'Nigeria'),
            'postal_code': request.form.get('postal_code'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'is_headquarters': request.form.get('is_headquarters') == 'on',
        }
        
        try:
            response = requests.post(
                f"{get_api_url()}/branches",
                json=data,
                headers=get_auth_headers()
            )
            
            if response.status_code == 201:
                flash('Branch created successfully!', 'success')
                return redirect(url_for('settings.branches'))
            else:
                flash(response.json().get('detail', 'Failed to create branch'), 'error')
        except Exception as e:
            flash('Error creating branch', 'error')
    
    return render_template('settings/branch_form.html', branch=None)


@settings_bp.route('/branches/<int:branch_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('branches.update')
def branch_edit(branch_id):
    """Edit a branch"""
    # Get branch data
    try:
        response = requests.get(
            f"{get_api_url()}/branches/{branch_id}",
            headers=get_auth_headers()
        )
        if response.status_code != 200:
            flash('Branch not found', 'error')
            return redirect(url_for('settings.branches'))
        branch = response.json()
    except:
        flash('Error fetching branch', 'error')
        return redirect(url_for('settings.branches'))
    
    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'code': request.form.get('code'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'country': request.form.get('country'),
            'postal_code': request.form.get('postal_code'),
            'phone': request.form.get('phone'),
            'email': request.form.get('email'),
            'status': request.form.get('status'),
            'is_headquarters': request.form.get('is_headquarters') == 'on',
        }
        
        try:
            response = requests.put(
                f"{get_api_url()}/branches/{branch_id}",
                json=data,
                headers=get_auth_headers()
            )
            
            if response.status_code == 200:
                flash('Branch updated successfully!', 'success')
                return redirect(url_for('settings.branches'))
            else:
                flash(response.json().get('detail', 'Failed to update branch'), 'error')
        except:
            flash('Error updating branch', 'error')
    
    return render_template('settings/branch_form.html', branch=branch)


@settings_bp.route('/branches/<int:branch_id>/delete', methods=['POST'])
@login_required
@permission_required('branches.delete')
def branch_delete(branch_id):
    """Delete a branch"""
    try:
        response = requests.delete(
            f"{get_api_url()}/branches/{branch_id}",
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            flash('Branch deleted successfully!', 'success')
        else:
            flash(response.json().get('detail', 'Failed to delete branch'), 'error')
    except:
        flash('Error deleting branch', 'error')
    
    return redirect(url_for('settings.branches'))


@settings_bp.route('/integrations')
@login_required
def integrations():
    """Integrations settings"""
    return render_template('settings/integrations.html')


@settings_bp.route('/roles')
@login_required
@permission_required('settings.view')
def roles():
    """Roles and permissions"""
    from app.api_client import api_get
    
    # Get all roles
    roles_response = api_get('/roles')
    roles = roles_response.json().get('items', []) if roles_response.status_code == 200 else []
    
    # Get all permissions
    permissions_response = api_get('/roles/permissions/all')
    permissions = permissions_response.json() if permissions_response.status_code == 200 else []
    
    return render_template('settings/roles.html', roles=roles, permissions=permissions)


@settings_bp.route('/roles/<int:role_id>/permissions', methods=['POST'])
@login_required
@permission_required('roles.update')
def update_role_permissions(role_id):
    """Update permissions for a role (super admin only)"""
    from app.api_client import api_put
    
    permission_ids = [int(pid) for pid in request.form.getlist('permission_ids')]
    
    response = api_put(f'/roles/{role_id}/permissions', {'permission_ids': permission_ids})
    
    if response.status_code == 200:
        flash('Permissions updated successfully!', 'success')
    else:
        error_detail = response.json().get('detail', 'Failed to update permissions') if response.json() else 'Failed to update permissions'
        flash(error_detail, 'error')
    
    return redirect(url_for('settings.roles'))
