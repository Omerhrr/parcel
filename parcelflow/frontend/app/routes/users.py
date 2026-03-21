"""
Users Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.api_client import api_get, api_post, api_put, api_delete
from app.utils.permissions import permission_required

users_bp = Blueprint('users', __name__)


@users_bp.route('/')
@login_required
@permission_required('users.view')
def index():
    """List users"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    params = {'page': page, 'page_size': 20}
    if search:
        params['search'] = search
    if status:
        params['status'] = status
    
    response = api_get('/users', params=params)
    data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    
    return render_template('settings/users.html', 
                         users=data.get('items', []),
                         pagination=data,
                         search=search,
                         status_filter=status)


@users_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('users.create')
def create():
    """Create user"""
    if request.method == 'POST':
        # Convert role_ids to integers
        role_ids = [int(rid) for rid in request.form.getlist('role_ids') if rid]
        
        data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'password': request.form.get('password'),
            'branch_id': int(request.form.get('branch_id')) if request.form.get('branch_id') else None,
            'status': request.form.get('status', 'pending'),
            'role_ids': role_ids
        }
        
        response = api_post('/users', data)
        
        if response.status_code == 201:
            flash('User created successfully!', 'success')
            return redirect(url_for('users.index'))
        else:
            flash(response.json().get('detail', 'Failed to create user'), 'error')
    
    # Get roles and branches
    roles_response = api_get('/roles/brief')
    roles = roles_response.json() if roles_response.status_code == 200 else []
    
    branches_response = api_get('/branches')
    branches = branches_response.json().get('items', []) if branches_response.status_code == 200 else []
    
    return render_template('settings/user_form.html', user=None, roles=roles, branches=branches, user_role_ids=[])


@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('users.update')
def edit(user_id):
    """Edit user"""
    response = api_get(f'/users/{user_id}')
    
    if response.status_code != 200:
        flash('User not found', 'error')
        return redirect(url_for('users.index'))
    
    user = response.json()
    
    if request.method == 'POST':
        # Convert role_ids to integers
        role_ids = [int(rid) for rid in request.form.getlist('role_ids') if rid]
        
        data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'branch_id': int(request.form.get('branch_id')) if request.form.get('branch_id') else None,
            'status': request.form.get('status'),
            'role_ids': role_ids
        }
        
        response = api_put(f'/users/{user_id}', data)
        
        if response.status_code == 200:
            flash('User updated successfully!', 'success')
            return redirect(url_for('users.index'))
        else:
            flash(response.json().get('detail', 'Failed to update user'), 'error')
    
    # Get roles and branches
    roles_response = api_get('/roles/brief')
    roles = roles_response.json() if roles_response.status_code == 200 else []
    
    branches_response = api_get('/branches')
    branches = branches_response.json().get('items', []) if branches_response.status_code == 200 else []
    
    # Get user's current role IDs
    user_role_ids = [r.get('id') for r in user.get('roles', [])]
    
    return render_template('settings/user_form.html', user=user, roles=roles, branches=branches, user_role_ids=user_role_ids)


@users_bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
@permission_required('users.delete')
def delete(user_id):
    """Delete user"""
    response = api_delete(f'/users/{user_id}')
    
    if response.status_code == 200:
        flash('User deactivated successfully!', 'success')
    else:
        flash(response.json().get('detail', 'Failed to deactivate user'), 'error')
    
    return redirect(url_for('users.index'))


@users_bp.route('/profile')
@login_required
def profile():
    """User profile"""
    response = api_get('/auth/me')
    user = response.json() if response.status_code == 200 else {}
    
    return render_template('settings/profile.html', user=user)


@users_bp.route('/profile/password', methods=['POST'])
@login_required
def change_password():
    """Change password"""
    data = {
        'current_password': request.form.get('current_password'),
        'new_password': request.form.get('new_password'),
        'confirm_password': request.form.get('confirm_password')
    }
    
    response = api_post('/auth/change-password', data)
    
    if response.status_code == 200:
        flash('Password changed successfully!', 'success')
    else:
        flash(response.json().get('detail', 'Failed to change password'), 'error')
    
    return redirect(url_for('users.profile'))
