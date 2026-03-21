"""
Accounting Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from app.utils.permissions import permission_required
import requests
from datetime import datetime, date

accounting_bp = Blueprint('accounting', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    token = session.get('token_data', {}).get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


# ==================== DASHBOARD ====================

@accounting_bp.route('/')
@login_required
@permission_required('accounting.view')
def index():
    """Accounting dashboard"""
    # Get accounting summary
    try:
        response = requests.get(
            f"{get_api_url()}/accounting/summary",
            headers=get_auth_headers()
        )
        summary = response.json() if response.status_code == 200 else {}
    except:
        summary = {}
    
    # Get pending remittances
    try:
        remittances_response = requests.get(
            f"{get_api_url()}/accounting/remittances",
            params={'status': 'pending', 'page_size': 10},
            headers=get_auth_headers()
        )
        pending_remittances = remittances_response.json().get('items', []) if remittances_response.status_code == 200 else []
    except:
        pending_remittances = []
    
    # Get pending agent remittances
    try:
        agent_remittances_response = requests.get(
            f"{get_api_url()}/accounting/agent-remittances",
            params={'status': 'pending', 'page_size': 10},
            headers=get_auth_headers()
        )
        pending_agent_remittances = agent_remittances_response.json().get('items', []) if agent_remittances_response.status_code == 200 else []
    except:
        pending_agent_remittances = []
    
    return render_template('accounting/index.html',
                         summary=summary,
                         pending_remittances=pending_remittances,
                         pending_agent_remittances=pending_agent_remittances)


# ==================== EXPENSES ====================

@accounting_bp.route('/expenses')
@login_required
@permission_required('accounting.view')
def list_expenses():
    """List expenses"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    branch_id = request.args.get('branch_id', '')
    
    params = {'page': page, 'page_size': 20}
    if category:
        params['category'] = category
    if branch_id:
        params['branch_id'] = branch_id
    
    try:
        response = requests.get(
            f"{get_api_url()}/accounting/expenses",
            params=params,
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    except:
        data = {'items': [], 'total': 0}
    
    return render_template('accounting/expenses.html',
                         expenses=data.get('items', []),
                         pagination=data,
                         filters={'category': category, 'branch_id': branch_id})


@accounting_bp.route('/expenses/create', methods=['GET', 'POST'])
@login_required
@permission_required('accounting.update')
def create_expense():
    """Create expense"""
    if request.method == 'POST':
        data = {
            'branch_id': request.form.get('branch_id') or None,
            'category': request.form.get('category'),
            'amount': float(request.form.get('amount', 0)),
            'description': request.form.get('description'),
            'expense_date': request.form.get('expense_date'),
            'payment_method': request.form.get('payment_method'),
            'payment_reference': request.form.get('payment_reference') or None,
            'receipt_url': request.form.get('receipt_url') or None,
            'notes': request.form.get('notes') or None
        }
        
        try:
            response = requests.post(
                f"{get_api_url()}/accounting/expenses",
                json=data,
                headers=get_auth_headers()
            )
            if response.status_code == 201:
                flash('Expense recorded successfully!', 'success')
                return redirect(url_for('accounting.list_expenses'))
            else:
                flash(response.json().get('detail', 'Failed to record expense'), 'error')
        except:
            flash('Error recording expense', 'error')
    
    return render_template('accounting/expense_form.html', expense=None)


@accounting_bp.route('/expenses/<int:expense_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('accounting.update')
def edit_expense(expense_id):
    """Edit expense"""
    # Get expense
    try:
        response = requests.get(
            f"{get_api_url()}/accounting/expenses/{expense_id}",
            headers=get_auth_headers()
        )
        if response.status_code != 200:
            flash('Expense not found', 'error')
            return redirect(url_for('accounting.list_expenses'))
        expense = response.json()
    except:
        flash('Error loading expense', 'error')
        return redirect(url_for('accounting.list_expenses'))
    
    if request.method == 'POST':
        data = {
            'branch_id': request.form.get('branch_id') or None,
            'category': request.form.get('category'),
            'amount': float(request.form.get('amount', 0)),
            'description': request.form.get('description'),
            'expense_date': request.form.get('expense_date'),
            'payment_method': request.form.get('payment_method'),
            'payment_reference': request.form.get('payment_reference') or None,
            'receipt_url': request.form.get('receipt_url') or None,
            'notes': request.form.get('notes') or None
        }
        
        try:
            response = requests.put(
                f"{get_api_url()}/accounting/expenses/{expense_id}",
                json=data,
                headers=get_auth_headers()
            )
            if response.status_code == 200:
                flash('Expense updated successfully!', 'success')
                return redirect(url_for('accounting.list_expenses'))
            else:
                flash(response.json().get('detail', 'Failed to update expense'), 'error')
        except:
            flash('Error updating expense', 'error')
    
    return render_template('accounting/expense_form.html', expense=expense)


@accounting_bp.route('/expenses/<int:expense_id>/delete', methods=['POST'])
@login_required
@permission_required('accounting.update')
def delete_expense(expense_id):
    """Delete expense"""
    try:
        response = requests.delete(
            f"{get_api_url()}/accounting/expenses/{expense_id}",
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Expense deleted successfully!', 'success')
        else:
            flash(response.json().get('detail', 'Failed to delete expense'), 'error')
    except:
        flash('Error deleting expense', 'error')
    
    return redirect(url_for('accounting.list_expenses'))


# ==================== VENDOR REMITTANCES ====================

@accounting_bp.route('/remittances')
@login_required
@permission_required('accounting.view')
def list_remittances():
    """List vendor remittances"""
    page = request.args.get('page', 1, type=int)
    vendor_id = request.args.get('vendor_id', '')
    status = request.args.get('status', '')
    
    params = {'page': page, 'page_size': 20}
    if vendor_id:
        params['vendor_id'] = vendor_id
    if status:
        params['status'] = status
    
    try:
        response = requests.get(
            f"{get_api_url()}/accounting/remittances",
            params=params,
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    except:
        data = {'items': [], 'total': 0}
    
    # Get vendors for filter
    try:
        vendors_response = requests.get(
            f"{get_api_url()}/vendors",
            params={'page_size': 100},
            headers=get_auth_headers()
        )
        vendors = vendors_response.json().get('items', []) if vendors_response.status_code == 200 else []
    except:
        vendors = []
    
    return render_template('accounting/remittances.html',
                         remittances=data.get('items', []),
                         pagination=data,
                         vendors=vendors,
                         filters={'vendor_id': vendor_id, 'status': status})


@accounting_bp.route('/remittances/create', methods=['GET', 'POST'])
@login_required
@permission_required('accounting.update')
def create_remittance():
    """Create vendor remittance"""
    if request.method == 'POST':
        data = {
            'vendor_id': int(request.form.get('vendor_id')),
            'amount': float(request.form.get('amount', 0)),
            'period_start': request.form.get('period_start'),
            'period_end': request.form.get('period_end'),
            'payment_method': request.form.get('payment_method'),
            'payment_reference': request.form.get('payment_reference') or None,
            'payment_date': request.form.get('payment_date') or None,
            'notes': request.form.get('notes') or None
        }
        
        try:
            response = requests.post(
                f"{get_api_url()}/accounting/remittances",
                json=data,
                headers=get_auth_headers()
            )
            if response.status_code == 201:
                flash('Remittance created successfully!', 'success')
                return redirect(url_for('accounting.list_remittances'))
            else:
                flash(response.json().get('detail', 'Failed to create remittance'), 'error')
        except:
            flash('Error creating remittance', 'error')
    
    # Get vendors
    try:
        vendors_response = requests.get(
            f"{get_api_url()}/vendors",
            params={'page_size': 100},
            headers=get_auth_headers()
        )
        vendors = vendors_response.json().get('items', []) if vendors_response.status_code == 200 else []
    except:
        vendors = []
    
    return render_template('accounting/remittance_form.html', remittance=None, vendors=vendors)


@accounting_bp.route('/remittances/<int:remittance_id>/approve', methods=['POST'])
@login_required
@permission_required('accounting.update')
def approve_remittance(remittance_id):
    """Approve vendor remittance"""
    try:
        response = requests.post(
            f"{get_api_url()}/accounting/remittances/{remittance_id}/approve",
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Remittance approved successfully!', 'success')
        else:
            flash(response.json().get('detail', 'Failed to approve remittance'), 'error')
    except:
        flash('Error approving remittance', 'error')
    
    return redirect(url_for('accounting.list_remittances'))


# ==================== AGENT REMITTANCES ====================

@accounting_bp.route('/agent-remittances')
@login_required
@permission_required('accounting.view')
def list_agent_remittances():
    """List agent remittances (COD collections)"""
    page = request.args.get('page', 1, type=int)
    agent_id = request.args.get('agent_id', '')
    status = request.args.get('status', '')
    
    params = {'page': page, 'page_size': 20}
    if agent_id:
        params['agent_id'] = agent_id
    if status:
        params['status'] = status
    
    try:
        response = requests.get(
            f"{get_api_url()}/accounting/agent-remittances",
            params=params,
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    except:
        data = {'items': [], 'total': 0}
    
    # Get agents for filter
    try:
        agents_response = requests.get(
            f"{get_api_url()}/agents",
            params={'page_size': 100},
            headers=get_auth_headers()
        )
        agents = agents_response.json().get('items', []) if agents_response.status_code == 200 else []
    except:
        agents = []
    
    return render_template('accounting/agent_remittances.html',
                         remittances=data.get('items', []),
                         pagination=data,
                         agents=agents,
                         filters={'agent_id': agent_id, 'status': status})


@accounting_bp.route('/agent-remittances/<int:remittance_id>/confirm', methods=['POST'])
@login_required
@permission_required('accounting.update')
def confirm_agent_remittance(remittance_id):
    """Confirm agent remittance"""
    payment_method = request.form.get('payment_method', 'cash')
    payment_reference = request.form.get('payment_reference')
    
    params = {'payment_method': payment_method}
    if payment_reference:
        params['payment_reference'] = payment_reference
    
    try:
        response = requests.post(
            f"{get_api_url()}/accounting/agent-remittances/{remittance_id}/confirm",
            params=params,
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Agent remittance confirmed successfully!', 'success')
        else:
            flash(response.json().get('detail', 'Failed to confirm remittance'), 'error')
    except:
        flash('Error confirming remittance', 'error')
    
    return redirect(url_for('accounting.list_agent_remittances'))


# ==================== TRANSACTIONS ====================

@accounting_bp.route('/transactions')
@login_required
@permission_required('accounting.view')
def list_transactions():
    """List transactions"""
    page = request.args.get('page', 1, type=int)
    
    try:
        response = requests.get(
            f"{get_api_url()}/accounting/transactions",
            params={'page': page, 'page_size': 50},
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    except:
        data = {'items': [], 'total': 0}
    
    return render_template('accounting/transactions.html',
                         transactions=data.get('items', []),
                         pagination=data)
