"""
Dashboard Routes Blueprint
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
import requests
from datetime import datetime, timedelta
import random

dashboard_bp = Blueprint('dashboard', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    from flask import session
    token = session.get('token_data', {}).get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


def generate_mock_delivery_trend():
    """Generate mock delivery trend data for last 7 days"""
    days = []
    successful = []
    failed = []
    returned = []
    
    for i in range(6, -1, -1):
        date = datetime.now() - timedelta(days=i)
        days.append(date.strftime('%a'))
        successful.append(random.randint(35, 75))
        failed.append(random.randint(2, 6))
        returned.append(random.randint(1, 4))
    
    return {
        'dates': days,
        'successful': successful,
        'failed': failed,
        'returned': returned
    }


def generate_mock_status_distribution():
    """Generate mock status distribution data"""
    return [
        {'name': 'Delivered', 'value': random.randint(140, 170), 'color': '#10B981'},
        {'name': 'In Transit', 'value': random.randint(35, 50), 'color': '#3B82F6'},
        {'name': 'Pending Pickup', 'value': random.randint(20, 35), 'color': '#F59E0B'},
        {'name': 'Failed', 'value': random.randint(5, 12), 'color': '#EF4444'},
        {'name': 'Returned', 'value': random.randint(3, 8), 'color': '#8B5CF6'}
    ]


def generate_mock_agent_performance_chart():
    """Generate mock agent performance data for chart"""
    names = ['John Smith', 'Sarah Johnson', 'Mike Wilson', 'Emily Davis', 'Chris Brown']
    return {
        'names': names,
        'completed': [random.randint(30, 55) for _ in names],
        'inTransit': [random.randint(2, 8) for _ in names],
        'failed': [random.randint(1, 4) for _ in names]
    }


def generate_mock_revenue_trend():
    """Generate mock revenue trend data for last 30 days"""
    dates = []
    revenue = []
    
    for i in range(29, -1, -1):
        date = datetime.now() - timedelta(days=i)
        dates.append(str(30 - i))
        revenue.append(random.randint(11000, 22000))
    
    return {
        'dates': dates,
        'revenue': revenue
    }


def generate_mock_revenue_breakdown():
    """Generate mock revenue breakdown by payment type"""
    return [
        {'name': 'Cash on Delivery', 'value': random.randint(100000, 150000), 'color': '#10B981'},
        {'name': 'Prepaid', 'value': random.randint(70000, 100000), 'color': '#3B82F6'},
        {'name': 'Bank Transfer', 'value': random.randint(35000, 55000), 'color': '#8B5CF6'}
    ]


def generate_mock_weekly_comparison():
    """Generate mock weekly comparison data"""
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    return {
        'days': days,
        'thisWeek': [random.randint(15000, 30000) for _ in days],
        'lastWeek': [random.randint(12000, 25000) for _ in days]
    }


def generate_mock_expense_categories():
    """Generate mock expense categories data"""
    categories = [
        ('Agent Commissions', 40000, 50000),
        ('Fuel & Transport', 22000, 35000),
        ('Warehouse Rent', 18000, 26000),
        ('Staff Salaries', 30000, 40000),
        ('Packaging Materials', 8000, 15000),
        ('Utilities', 6000, 10000),
        ('Insurance', 5000, 8000),
        ('Maintenance', 3000, 6000)
    ]
    
    return [
        {'category': cat, 'amount': random.randint(min_val, max_val)}
        for cat, min_val, max_val in categories
    ]


@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard"""
    # Get dashboard stats
    try:
        response = requests.get(
            f"{get_api_url()}/dashboard/overview",
            headers=get_auth_headers()
        )
        stats = response.json() if response.status_code == 200 else {}
    except:
        stats = {}
    
    # Get logistics dashboard
    try:
        logistics_response = requests.get(
            f"{get_api_url()}/dashboard/logistics",
            headers=get_auth_headers()
        )
        logistics = logistics_response.json() if logistics_response.status_code == 200 else {}
    except:
        logistics = {}
    
    return render_template('dashboard/index.html', stats=stats, logistics=logistics)


@dashboard_bp.route('/logistics')
@login_required
def logistics():
    """Logistics dashboard"""
    try:
        response = requests.get(
            f"{get_api_url()}/dashboard/logistics",
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {}
    except:
        data = {}
    
    # Add chart data
    data['delivery_trend'] = generate_mock_delivery_trend()
    data['status_distribution'] = generate_mock_status_distribution()
    data['agent_performance_chart'] = generate_mock_agent_performance_chart()
    
    # Add additional metrics
    data['avg_delivery_time'] = round(random.uniform(2.0, 3.5), 1)
    data['on_time_rate'] = round(random.uniform(92.0, 97.0), 1)
    data['total_agents'] = data.get('total_agents', 15)
    data['busy_agents'] = random.randint(1, 3)
    
    return render_template('dashboard/logistics.html', data=data)


@dashboard_bp.route('/logistics/active-dispatches')
@login_required
def active_dispatches_partial():
    """Partial for HTMX polling - returns just the active dispatches list"""
    try:
        response = requests.get(
            f"{get_api_url()}/dashboard/logistics",
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {}
    except:
        data = {}
    
    return render_template('dashboard/partials/active_dispatches.html', data=data)


@dashboard_bp.route('/financial')
@login_required
def financial():
    """Financial dashboard"""
    date_range = request.args.get('date_range', '30days')
    
    try:
        response = requests.get(
            f"{get_api_url()}/dashboard/financial",
            headers=get_auth_headers(),
            params={'date_range': date_range}
        )
        data = response.json() if response.status_code == 200 else {}
    except:
        data = {}
    
    # Add chart data
    data['revenue_trend'] = generate_mock_revenue_trend()
    data['revenue_breakdown'] = generate_mock_revenue_breakdown()
    data['weekly_comparison'] = generate_mock_weekly_comparison()
    data['expense_categories'] = generate_mock_expense_categories()
    
    # Calculate additional metrics
    total_revenue = data.get('total_revenue', random.randint(200000, 300000))
    total_expenses = data.get('total_expenses', random.randint(80000, 120000))
    
    data['net_profit'] = data.get('net_profit', total_revenue - total_expenses)
    data['profit_margin'] = data.get('profit_margin', round((data['net_profit'] / total_revenue) * 100, 1) if total_revenue > 0 else 0)
    data['avg_order_value'] = data.get('avg_order_value', round(random.uniform(150, 250), 2))
    data['total_orders'] = data.get('total_orders', random.randint(800, 1500))
    
    cod_total = data.get('cod_revenue', random.randint(80000, 120000))
    cod_collected = data.get('cod_collected', int(cod_total * random.uniform(0.8, 0.95)))
    data['cod_total'] = cod_total
    data['cod_collected'] = cod_collected
    data['collection_rate'] = data.get('collection_rate', round((cod_collected / cod_total) * 100, 1) if cod_total > 0 else 0)
    
    return render_template('dashboard/financial.html', data=data)


@dashboard_bp.route('/financial/data')
@login_required
def financial_data():
    """HTMX endpoint for financial data filtering"""
    date_range = request.args.get('date_range', '30days')
    
    try:
        response = requests.get(
            f"{get_api_url()}/dashboard/financial",
            headers=get_auth_headers(),
            params={'date_range': date_range}
        )
        data = response.json() if response.status_code == 200 else {}
    except:
        data = {}
    
    # Add chart data based on date range
    data['revenue_trend'] = generate_mock_revenue_trend()
    data['revenue_breakdown'] = generate_mock_revenue_breakdown()
    data['weekly_comparison'] = generate_mock_weekly_comparison()
    data['expense_categories'] = generate_mock_expense_categories()
    
    # Calculate additional metrics
    total_revenue = data.get('total_revenue', random.randint(200000, 300000))
    total_expenses = data.get('total_expenses', random.randint(80000, 120000))
    
    data['net_profit'] = data.get('net_profit', total_revenue - total_expenses)
    data['profit_margin'] = data.get('profit_margin', round((data['net_profit'] / total_revenue) * 100, 1) if total_revenue > 0 else 0)
    data['avg_order_value'] = data.get('avg_order_value', round(random.uniform(150, 250), 2))
    data['total_orders'] = data.get('total_orders', random.randint(800, 1500))
    
    cod_total = data.get('cod_revenue', random.randint(80000, 120000))
    cod_collected = data.get('cod_collected', int(cod_total * random.uniform(0.8, 0.95)))
    data['cod_total'] = cod_total
    data['cod_collected'] = cod_collected
    data['collection_rate'] = data.get('collection_rate', round((cod_collected / cod_total) * 100, 1) if cod_total > 0 else 0)
    
    return render_template('dashboard/financial.html', data=data)


@dashboard_bp.route('/api/charts/delivery-trend')
@login_required
def delivery_trend_api():
    """API endpoint for delivery trend chart data"""
    return jsonify(generate_mock_delivery_trend())


@dashboard_bp.route('/api/charts/status-distribution')
@login_required
def status_distribution_api():
    """API endpoint for status distribution chart data"""
    return jsonify(generate_mock_status_distribution())


@dashboard_bp.route('/api/charts/agent-performance')
@login_required
def agent_performance_api():
    """API endpoint for agent performance chart data"""
    return jsonify(generate_mock_agent_performance_chart())


@dashboard_bp.route('/api/charts/revenue-trend')
@login_required
def revenue_trend_api():
    """API endpoint for revenue trend chart data"""
    return jsonify(generate_mock_revenue_trend())


@dashboard_bp.route('/api/charts/revenue-breakdown')
@login_required
def revenue_breakdown_api():
    """API endpoint for revenue breakdown chart data"""
    return jsonify(generate_mock_revenue_breakdown())


@dashboard_bp.route('/api/charts/weekly-comparison')
@login_required
def weekly_comparison_api():
    """API endpoint for weekly comparison chart data"""
    return jsonify(generate_mock_weekly_comparison())


@dashboard_bp.route('/api/charts/expense-categories')
@login_required
def expense_categories_api():
    """API endpoint for expense categories chart data"""
    return jsonify(generate_mock_expense_categories())
