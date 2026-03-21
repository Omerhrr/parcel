"""
Notifications Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from app.utils.permissions import permission_required
from app.api_client import api_get, api_post, api_put, api_delete
import requests

notifications_bp = Blueprint('notifications', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    token = session.get('token_data', {}).get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


@notifications_bp.route('/')
@login_required
def index():
    """List notifications"""
    page = request.args.get('page', 1, type=int)
    unread_only = request.args.get('unread', 'false').lower() == 'true'
    notification_type = request.args.get('type', '')
    
    params = {'page': page, 'page_size': 20}
    if unread_only:
        params['unread_only'] = True
    if notification_type:
        params['notification_type'] = notification_type
    
    try:
        response = requests.get(
            f"{get_api_url()}/notifications",
            params=params,
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0, 'unread_count': 0}
    except:
        data = {'items': [], 'total': 0, 'unread_count': 0}
    
    return render_template('notifications/index.html',
                         notifications=data.get('items', []),
                         pagination=data,
                         unread_count=data.get('unread_count', 0),
                         filters={'unread': unread_only, 'type': notification_type})


@notifications_bp.route('/unread-count')
@login_required
def unread_count():
    """Get unread notification count (for AJAX)"""
    try:
        response = requests.get(
            f"{get_api_url()}/notifications/unread-count",
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {'unread_count': 0}


@notifications_bp.route('/recent')
@login_required
def recent():
    """Get recent notifications for dropdown (HTMX partial)"""
    try:
        response = requests.get(
            f"{get_api_url()}/notifications",
            params={'page_size': 5},
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'unread_count': 0}
        notifications = data.get('items', [])
        unread_count = data.get('unread_count', 0)
    except:
        notifications = []
        unread_count = 0

    # Return partial HTML for HTMX
    return render_template('notifications/_recent_dropdown.html',
                         notifications=notifications,
                         unread_count=unread_count)


@notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark notification as read"""
    try:
        response = requests.post(
            f"{get_api_url()}/notifications/{notification_id}/read",
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Notification marked as read', 'success')
        else:
            flash('Failed to mark notification as read', 'error')
    except:
        flash('Error marking notification as read', 'error')
    
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read"""
    try:
        response = requests.post(
            f"{get_api_url()}/notifications/mark-all-read",
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('All notifications marked as read', 'success')
        else:
            flash('Failed to mark notifications as read', 'error')
    except:
        flash('Error marking notifications as read', 'error')
    
    return redirect(url_for('notifications.index'))


@notifications_bp.route('/<int:notification_id>/delete', methods=['POST'])
@login_required
def delete(notification_id):
    """Delete a notification"""
    try:
        response = requests.delete(
            f"{get_api_url()}/notifications/{notification_id}",
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Notification deleted', 'success')
        else:
            flash('Failed to delete notification', 'error')
    except:
        flash('Error deleting notification', 'error')
    
    return redirect(url_for('notifications.index'))


# ==================== PREFERENCES ====================

@notifications_bp.route('/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    """Manage notification preferences"""
    if request.method == 'POST':
        data = {
            'email_enabled': request.form.get('email_enabled') == 'on',
            'sms_enabled': request.form.get('sms_enabled') == 'on',
            'push_enabled': request.form.get('push_enabled') == 'on',
            'in_app_enabled': request.form.get('in_app_enabled') == 'on',
            'notify_waybill_updates': request.form.get('notify_waybill_updates') == 'on',
            'notify_pickup_assignments': request.form.get('notify_pickup_assignments') == 'on',
            'notify_delivery_assignments': request.form.get('notify_delivery_assignments') == 'on',
            'notify_order_updates': request.form.get('notify_order_updates') == 'on',
            'notify_stock_alerts': request.form.get('notify_stock_alerts') == 'on',
            'notify_payment_updates': request.form.get('notify_payment_updates') == 'on',
            'notify_system': request.form.get('notify_system') == 'on',
        }
        
        try:
            response = requests.put(
                f"{get_api_url()}/notifications/preferences",
                json=data,
                headers=get_auth_headers()
            )
            if response.status_code == 200:
                flash('Preferences updated successfully!', 'success')
            else:
                flash('Failed to update preferences', 'error')
        except:
            flash('Error updating preferences', 'error')
        
        return redirect(url_for('notifications.preferences'))
    
    # GET - fetch current preferences
    try:
        response = requests.get(
            f"{get_api_url()}/notifications/preferences",
            headers=get_auth_headers()
        )
        prefs = response.json() if response.status_code == 200 else {}
    except:
        prefs = {}
    
    return render_template('notifications/preferences.html', prefs=prefs)


# ==================== ADMIN ====================

@notifications_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('notifications.create')
def create():
    """Create notification (admin)"""
    if request.method == 'POST':
        data = {
            'title': request.form.get('title'),
            'message': request.form.get('message'),
            'notification_type': request.form.get('notification_type', 'system'),
            'priority': request.form.get('priority', 'normal'),
            'user_id': request.form.get('user_id') or None,
            'action_url': request.form.get('action_url') or None,
            'related_entity_type': request.form.get('related_entity_type') or None,
            'related_entity_id': request.form.get('related_entity_id') or None,
        }
        
        try:
            response = requests.post(
                f"{get_api_url()}/notifications/create",
                json=data,
                headers=get_auth_headers()
            )
            if response.status_code == 201:
                flash('Notification created successfully!', 'success')
                return redirect(url_for('notifications.index'))
            else:
                flash(response.json().get('detail', 'Failed to create notification'), 'error')
        except:
            flash('Error creating notification', 'error')
    
    # Get users for the user dropdown
    try:
        users_response = requests.get(
            f"{get_api_url()}/users",
            params={'page_size': 100},
            headers=get_auth_headers()
        )
        users = users_response.json().get('items', []) if users_response.status_code == 200 else []
    except:
        users = []
    
    return render_template('notifications/form.html', notification=None, users=users)


@notifications_bp.route('/broadcast', methods=['GET', 'POST'])
@login_required
@permission_required('notifications.create')
def broadcast():
    """Broadcast notification to all users"""
    if request.method == 'POST':
        data = {
            'title': request.form.get('title'),
            'message': request.form.get('message'),
            'notification_type': request.form.get('notification_type', 'system'),
            'priority': request.form.get('priority', 'normal'),
            'action_url': request.form.get('action_url') or None,
            'expires_in_hours': int(request.form.get('expires_in_hours', 72)) or None,
        }
        
        try:
            response = requests.post(
                f"{get_api_url()}/notifications/broadcast",
                params=data,
                headers=get_auth_headers()
            )
            if response.status_code == 200:
                flash('Broadcast notification sent successfully!', 'success')
                return redirect(url_for('notifications.index'))
            else:
                flash(response.json().get('detail', 'Failed to send broadcast'), 'error')
        except:
            flash('Error sending broadcast', 'error')
    
    return render_template('notifications/broadcast.html')
