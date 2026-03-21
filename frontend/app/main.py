"""
ParcelFlow Frontend Application Factory
"""
from flask import Flask, session, g, request, redirect, url_for, flash, abort
from flask_login import LoginManager, current_user
import os
import requests
import secrets

# Initialize extensions
login_manager = LoginManager()


def get_api_url():
    """Get API URL from app config"""
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    """Get authorization headers from session"""
    token = session.get('token_data', {}).get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


def generate_csrf_token():
    """Generate a CSRF token for the session"""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate_csrf_token():
    """Validate CSRF token for POST/PUT/DELETE requests"""
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        token = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
        if not token or token != session.get('_csrf_token'):
            abort(403, description="CSRF token validation failed")


def create_app(config=None):
    """Create and configure the Flask application"""
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    
    # Load configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['API_URL'] = os.environ.get('API_URL', 'http://localhost:8000/api')
    app.config['DEBUG'] = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # Security settings
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Apply any passed config
    if config:
        app.config.update(config)
    
    # Initialize extensions
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # User loader for Flask-Login
    from app.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user from session"""
        user_data = session.get('user_data')
        token_data = session.get('token_data')
        if user_data and str(user_data.get('id')) == str(user_id):
            # Merge roles and permissions from token_data into user_data
            if token_data:
                user_data = dict(user_data)  # Make a copy to avoid modifying session
                user_data['roles'] = token_data.get('roles', [])
                user_data['permissions'] = token_data.get('permissions', [])
            return User(user_data)
        return None
    
    # Register template filters
    register_filters(app)
    
    # CSRF protection before request
    @app.before_request
    def csrf_protect():
        """Validate CSRF token for state-changing requests"""
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Skip CSRF for API routes and login/register
            if request.path.startswith('/api/') or request.path.startswith('/vendors/api/') or request.path in ['/auth/login', '/auth/register']:
                return
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not token or token != session.get('_csrf_token'):
                flash('Security validation failed. Please try again.', 'error')
                return redirect(request.referrer or url_for('dashboard.index'))
    
    # Generate CSRF token for templates
    @app.context_processor
    def csrf_token_processor():
        def get_csrf_token():
            return generate_csrf_token()
        return dict(csrf_token=get_csrf_token)
    
    # Branch context processor - runs before each request
    @app.before_request
    def load_branch_context():
        """Load branch context for authenticated users"""
        if current_user.is_authenticated:
            # Get branches from API
            try:
                response = requests.get(
                    f"{get_api_url()}/branches",
                    headers=get_auth_headers(),
                    timeout=5
                )
                if response.status_code == 200:
                    g.branches = response.json().get('items', [])
                else:
                    g.branches = []
            except:
                g.branches = []
            
            # Get current branch from session or use first branch
            current_branch_id = session.get('current_branch_id')
            if current_branch_id:
                g.current_branch = next(
                    (b for b in g.branches if str(b.get('id')) == str(current_branch_id)),
                    g.branches[0] if g.branches else None
                )
            else:
                g.current_branch = g.branches[0] if g.branches else None
        else:
            g.branches = []
            g.current_branch = None
    
    # Branch switcher route
    @app.route('/switch-branch/<int:branch_id>')
    def switch_branch(branch_id):
        """Switch the current branch context"""
        if current_user.is_authenticated:
            session['current_branch_id'] = branch_id
            flash('Branch switched successfully!', 'success')
        return redirect(request.referrer or url_for('dashboard.index'))
    
    # Register blueprints
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
    from app.routes.vendor_portal import vendor_portal_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(waybills_bp, url_prefix='/waybills')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(vendors_bp, url_prefix='/vendors')
    app.register_blueprint(agents_bp, url_prefix='/agents')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(logistics_bp, url_prefix='/logistics')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(accounting_bp, url_prefix='/accounting')
    app.register_blueprint(leads_bp, url_prefix='/leads')
    app.register_blueprint(bulk_bp, url_prefix='/bulk')
    app.register_blueprint(audit_bp, url_prefix='/audit')
    app.register_blueprint(vendor_portal_bp, url_prefix='/vendor-portal')
    
    # Root route
    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    @app.route('/health')
    def health():
        from flask import jsonify
        return jsonify({'status': 'healthy', 'app': 'ParcelFlow Frontend'})
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
    
    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        """Handle 403 Forbidden errors"""
        from flask import render_template
        return render_template('errors/403.html', description=getattr(e, 'description', 'Access Denied')), 403
    
    @app.errorhandler(404)
    def page_not_found(e):
        """Handle 404 Not Found errors"""
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        """Handle 500 Internal Server errors"""
        from flask import render_template
        return render_template('errors/500.html'), 500
    
    return app


def register_filters(app):
    """Register custom Jinja2 template filters"""
    
    @app.template_filter('currency')
    def currency_filter(value, symbol='₦'):
        """Format number as currency"""
        try:
            return f"{symbol}{float(value):,.2f}"
        except (ValueError, TypeError):
            return f"{symbol}0.00"
    
    @app.template_filter('date')
    def date_filter(value, format='%b %d, %Y'):
        """Format date string"""
        from datetime import datetime
        if not value:
            return ''
        try:
            if 'T' in str(value):
                dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(str(value))
            return dt.strftime(format)
        except (ValueError, TypeError):
            return str(value) if value else ''
    
    @app.template_filter('datetime')
    def datetime_filter(value, format='%b %d, %Y, %I:%M %p'):
        """Format datetime string"""
        from datetime import datetime
        if not value:
            return ''
        try:
            if 'T' in str(value):
                dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(str(value))
            return dt.strftime(format)
        except (ValueError, TypeError):
            return str(value) if value else ''

    @app.template_filter('time_ago')
    def time_ago_filter(value):
        """Format datetime as relative time (e.g., '2 hours ago')"""
        from datetime import datetime, timezone

        if not value:
            return ''

        try:
            # Parse the datetime string
            if 'T' in str(value):
                dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(str(value))

            # Make timezone-aware if needed
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            diff = now - dt

            seconds = int(diff.total_seconds())
            minutes = seconds // 60
            hours = minutes // 60
            days = hours // 24
            weeks = days // 7
            months = days // 30
            years = days // 365

            if seconds < 60:
                return 'Just now'
            elif minutes < 60:
                return f'{minutes} minute{"s" if minutes != 1 else ""} ago'
            elif hours < 24:
                return f'{hours} hour{"s" if hours != 1 else ""} ago'
            elif days < 7:
                return f'{days} day{"s" if days != 1 else ""} ago'
            elif weeks < 4:
                return f'{weeks} week{"s" if weeks != 1 else ""} ago'
            elif months < 12:
                return f'{months} month{"s" if months != 1 else ""} ago'
            else:
                return f'{years} year{"s" if years != 1 else ""} ago'
        except (ValueError, TypeError):
            return str(value) if value else ''

    @app.context_processor
    def inject_user():
        """Inject current_user and branch context into all templates"""
        from flask_login import current_user
        from app.utils.permissions import has_permission, has_role, is_super_admin, get_user_permissions, get_user_roles
        return dict(
            current_user=current_user,
            branches=getattr(g, 'branches', []),
            current_branch=getattr(g, 'current_branch', None),
            has_permission=has_permission,
            has_role=has_role,
            is_super_admin=is_super_admin,
            user_permissions=get_user_permissions(),
            user_roles=get_user_roles()
        )


# Create the app instance
app = create_app()

if __name__ == '__main__':
    import logging
    # Reduce logging verbosity
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)
    app.run(debug=False, host='0.0.0.0', port=5000)
