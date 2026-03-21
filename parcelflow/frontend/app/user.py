"""
User Model for Flask-Login
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask_login import UserMixin


class User(UserMixin):
    """User class for Flask-Login"""

    def __init__(self, user_data=None):
        if user_data:
            self.id = user_data.get('id')
            self.name = user_data.get('name')
            self.email = user_data.get('email')
            self.phone = user_data.get('phone')
            self.business_id = user_data.get('business_id')
            self.branch_id = user_data.get('branch_id')
            self.roles = user_data.get('roles', [])
            self.permissions = user_data.get('permissions', [])
            self._is_active = user_data.get('is_active', True)
        else:
            self.id = None
            self.name = None
            self.email = None
            self.phone = None
            self.business_id = None
            self.branch_id = None
            self.roles = []
            self.permissions = []
            self._is_active = False

    def get_id(self):
        return str(self.id)

    def has_permission(self, permission):
        """Check if user has a specific permission"""
        # Super admin and admin have all permissions
        if 'super_admin' in self.roles or 'admin' in self.roles:
            return True
        return permission in self.permissions or '*' in self.permissions

    def has_role(self, role_name):
        """Check if user has a specific role"""
        return role_name in self.roles

    @property
    def is_active(self):
        """Override UserMixin's is_active property"""
        return self._is_active

    @property
    def is_authenticated(self):
        return self.id is not None

    @property
    def is_anonymous(self):
        return self.id is None
