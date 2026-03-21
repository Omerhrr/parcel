"""
Frontend Routes Package
ParcelFlow - Multi-tenant Logistics Platform
"""
from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.waybills import waybills_bp
from app.routes.orders import orders_bp
from app.routes.vendors import vendors_bp
from app.routes.agents import agents_bp
from app.routes.inventory import inventory_bp
from app.routes.users import users_bp
from app.routes.settings import settings_bp
from app.routes.logistics import logistics_bp
from app.routes.notifications import notifications_bp
from app.routes.reports import reports_bp
from app.routes.accounting import accounting_bp
from app.routes.leads import leads_bp
from app.routes.bulk import bulk_bp
from app.routes.audit import audit_bp

__all__ = [
    'auth_bp', 'dashboard_bp', 'waybills_bp', 'orders_bp',
    'vendors_bp', 'agents_bp', 'inventory_bp', 'users_bp', 'settings_bp',
    'logistics_bp', 'notifications_bp', 'reports_bp', 'accounting_bp',
    'leads_bp', 'bulk_bp', 'audit_bp'
]
