"""
Reports Routes
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
from flask_login import login_required
from app.utils.permissions import permission_required
import requests
from datetime import datetime, timedelta, date

reports_bp = Blueprint('reports', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    token = session.get('token_data', {}).get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


@reports_bp.route('/')
@login_required
@permission_required('reports.view')
def index():
    """Reports dashboard"""
    # Default to last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    return render_template('reports/index.html',
                         start_date=start_date,
                         end_date=end_date)


@reports_bp.route('/sales')
@login_required
@permission_required('reports.view')
def sales():
    """Sales report"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    branch_id = request.args.get('branch_id', '')
    
    params = {
        'start_date': start_date,
        'end_date': end_date
    }
    if branch_id:
        params['branch_id'] = branch_id
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/sales",
            params=params,
            headers=get_auth_headers()
        )
        report = response.json() if response.status_code == 200 else {}
    except:
        report = {}
    
    # Get branches for filter
    try:
        branches_response = requests.get(
            f"{get_api_url()}/branches",
            params={'page_size': 100},
            headers=get_auth_headers()
        )
        branches = branches_response.json().get('items', []) if branches_response.status_code == 200 else []
    except:
        branches = []
    
    return render_template('reports/sales.html',
                         report=report,
                         branches=branches,
                         start_date=start_date,
                         end_date=end_date,
                         branch_id=branch_id)


@reports_bp.route('/deliveries')
@login_required
@permission_required('reports.view')
def deliveries():
    """Delivery performance report"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    agent_id = request.args.get('agent_id', '')
    
    params = {
        'start_date': start_date,
        'end_date': end_date
    }
    if agent_id:
        params['agent_id'] = agent_id
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/deliveries",
            params=params,
            headers=get_auth_headers()
        )
        report = response.json() if response.status_code == 200 else {}
    except:
        report = {}
    
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
    
    return render_template('reports/deliveries.html',
                         report=report,
                         agents=agents,
                         start_date=start_date,
                         end_date=end_date,
                         agent_id=agent_id)


@reports_bp.route('/agents')
@login_required
@permission_required('reports.view')
def agents():
    """Agent performance report"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/agents",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        report = response.json() if response.status_code == 200 else {}
    except:
        report = {}
    
    return render_template('reports/agents.html',
                         report=report,
                         start_date=start_date,
                         end_date=end_date)


@reports_bp.route('/vendors')
@login_required
@permission_required('reports.view')
def vendors():
    """Vendor settlement report"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/vendors",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        report = response.json() if response.status_code == 200 else {}
    except:
        report = {}
    
    return render_template('reports/vendors.html',
                         report=report,
                         start_date=start_date,
                         end_date=end_date)


@reports_bp.route('/expenses')
@login_required
@permission_required('reports.view')
def expenses():
    """Expense report"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/expenses",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        report = response.json() if response.status_code == 200 else {}
    except:
        report = {}
    
    return render_template('reports/expenses.html',
                         report=report,
                         start_date=start_date,
                         end_date=end_date)


@reports_bp.route('/export/sales')
@login_required
@permission_required('reports.export')
def export_sales():
    """Export sales report as CSV"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    branch_id = request.args.get('branch_id', '')
    
    params = {
        'start_date': start_date,
        'end_date': end_date
    }
    if branch_id:
        params['branch_id'] = branch_id
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/sales",
            params=params,
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            # Return CSV response
            from flask import Response
            return Response(
                response.content,
                mimetype='text/csv',
                headers={'Content-Disposition': response.headers.get('Content-Disposition', f'attachment; filename="sales_report_{start_date}_{end_date}.csv"')}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.sales'))


@reports_bp.route('/export/agents')
@login_required
@permission_required('reports.export')
def export_agents():
    """Export agent report as CSV"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/agents",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='text/csv',
                headers={'Content-Disposition': response.headers.get('Content-Disposition', f'attachment; filename="agent_report_{start_date}_{end_date}.csv"')}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.agents'))


@reports_bp.route('/export/deliveries')
@login_required
@permission_required('reports.export')
def export_deliveries():
    """Export delivery report as CSV"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    agent_id = request.args.get('agent_id', '')
    
    params = {'start_date': start_date, 'end_date': end_date}
    if agent_id:
        params['agent_id'] = agent_id
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/deliveries",
            params=params,
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename="delivery_report_{start_date}_{end_date}.csv"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.deliveries'))


@reports_bp.route('/export/vendors')
@login_required
@permission_required('reports.export')
def export_vendors():
    """Export vendor report as CSV"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/vendors",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename="vendor_report_{start_date}_{end_date}.csv"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.vendors'))


@reports_bp.route('/export/expenses')
@login_required
@permission_required('reports.export')
def export_expenses():
    """Export expense report as CSV"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/expenses",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename="expense_report_{start_date}_{end_date}.csv"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.expenses'))


# ==================== EXCEL EXPORT ROUTES ====================

@reports_bp.route('/export/sales/excel')
@login_required
@permission_required('reports.export')
def export_sales_excel():
    """Export sales report as Excel"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    branch_id = request.args.get('branch_id', '')
    
    params = {'start_date': start_date, 'end_date': end_date}
    if branch_id:
        params['branch_id'] = branch_id
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/sales/excel",
            params=params,
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="sales_report_{start_date}_{end_date}.xlsx"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.sales'))


@reports_bp.route('/export/deliveries/excel')
@login_required
@permission_required('reports.export')
def export_deliveries_excel():
    """Export delivery report as Excel"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    agent_id = request.args.get('agent_id', '')
    
    params = {'start_date': start_date, 'end_date': end_date}
    if agent_id:
        params['agent_id'] = agent_id
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/deliveries/excel",
            params=params,
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="delivery_report_{start_date}_{end_date}.xlsx"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.deliveries'))


@reports_bp.route('/export/agents/excel')
@login_required
@permission_required('reports.export')
def export_agents_excel():
    """Export agent report as Excel"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/agents/excel",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="agent_report_{start_date}_{end_date}.xlsx"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.agents'))


@reports_bp.route('/export/vendors/excel')
@login_required
@permission_required('reports.export')
def export_vendors_excel():
    """Export vendor report as Excel"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/vendors/excel",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="vendor_report_{start_date}_{end_date}.xlsx"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.vendors'))


@reports_bp.route('/export/expenses/excel')
@login_required
@permission_required('reports.export')
def export_expenses_excel():
    """Export expense report as Excel"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/expenses/excel",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': f'attachment; filename="expense_report_{start_date}_{end_date}.xlsx"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.expenses'))


# ==================== PDF EXPORT ROUTES ====================

@reports_bp.route('/export/sales/pdf')
@login_required
@permission_required('reports.export')
def export_sales_pdf():
    """Export sales report as PDF"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    branch_id = request.args.get('branch_id', '')
    
    params = {'start_date': start_date, 'end_date': end_date}
    if branch_id:
        params['branch_id'] = branch_id
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/sales/pdf",
            params=params,
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="sales_report_{start_date}_{end_date}.pdf"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.sales'))


@reports_bp.route('/export/deliveries/pdf')
@login_required
@permission_required('reports.export')
def export_deliveries_pdf():
    """Export delivery report as PDF"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    agent_id = request.args.get('agent_id', '')
    
    params = {'start_date': start_date, 'end_date': end_date}
    if agent_id:
        params['agent_id'] = agent_id
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/deliveries/pdf",
            params=params,
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="delivery_report_{start_date}_{end_date}.pdf"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.deliveries'))


@reports_bp.route('/export/agents/pdf')
@login_required
@permission_required('reports.export')
def export_agents_pdf():
    """Export agent report as PDF"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/agents/pdf",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="agent_report_{start_date}_{end_date}.pdf"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.agents'))


@reports_bp.route('/export/vendors/pdf')
@login_required
@permission_required('reports.export')
def export_vendors_pdf():
    """Export vendor report as PDF"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/vendors/pdf",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="vendor_report_{start_date}_{end_date}.pdf"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.vendors'))


@reports_bp.route('/export/expenses/pdf')
@login_required
@permission_required('reports.export')
def export_expenses_pdf():
    """Export expense report as PDF"""
    start_date = request.args.get('start_date', (date.today() - timedelta(days=30)).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    try:
        response = requests.get(
            f"{get_api_url()}/reports/export/expenses/pdf",
            params={'start_date': start_date, 'end_date': end_date},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="expense_report_{start_date}_{end_date}.pdf"'}
            )
        else:
            flash('Failed to export report', 'error')
    except:
        flash('Error exporting report', 'error')
    
    return redirect(url_for('reports.expenses'))
