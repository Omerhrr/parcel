"""
Permission Utilities for Flask Frontend
ParcelFlow - Multi-tenant Logistics Platform
"""
from functools import wraps
from flask import abort, session, has_request_context
from flask_login import current_user


def has_permission(permission: str) -> bool:
    """
    Check if current user has a specific permission.
    Returns True if user has the permission or has wildcard (*) permission.
    Returns False if user is not authenticated or any error occurs.
    Super admins and admins have all permissions.
    """
    try:
        # Check if we have a request context
        if not has_request_context():
            return False

        if not current_user.is_authenticated:
            return False

        # Get user roles - check both current_user and session
        user_roles = []
        if hasattr(current_user, 'roles'):
            user_roles = current_user.roles or []
        
        # Also check session as fallback
        token_data = session.get('token_data', {})
        session_roles = token_data.get('roles', [])
        
        # Combine roles from both sources
        all_roles = set(user_roles) | set(session_roles)
        
        # Super admin and admin have all permissions
        if 'super_admin' in all_roles or 'admin' in all_roles:
            return True

        # Check if user object has the permission method
        if hasattr(current_user, 'has_permission') and callable(current_user.has_permission):
            result = current_user.has_permission(permission)
            if result:
                return result

        # Check if user object has permissions attribute
        if hasattr(current_user, 'permissions'):
            user_perms = current_user.permissions or []
            if permission in user_perms or '*' in user_perms:
                return True

        # Fallback: check session data
        permissions = token_data.get('permissions', [])
        return permission in permissions or '*' in permissions
    except Exception as e:
        # Return False on any error to prevent template rendering issues
        import logging
        logging.getLogger('permissions').error(f"Permission check error: {e}")
        return False


def has_role(role_name: str) -> bool:
    """
    Check if current user has a specific role.
    """
    try:
        if not has_request_context():
            return False
            
        if not current_user.is_authenticated:
            return False
        
        # Check if user object has the role method
        if hasattr(current_user, 'has_role') and callable(current_user.has_role):
            return current_user.has_role(role_name)
        
        # Check if user object has roles attribute
        if hasattr(current_user, 'roles'):
            user_roles = current_user.roles or []
            if isinstance(user_roles, list):
                # Roles might be strings or dicts
                for r in user_roles:
                    if isinstance(r, str) and r == role_name:
                        return True
                    elif isinstance(r, dict) and r.get('name') == role_name:
                        return True
            return False
        
        # Fallback: check session data
        token_data = session.get('token_data', {})
        roles = token_data.get('roles', [])
        return role_name in roles
    except Exception:
        return False


def is_super_admin() -> bool:
    """
    Check if current user is a super admin.
    """
    return has_role('super_admin')


def permission_required(permission: str):
    """
    Decorator to require a specific permission for a route.
    Usage: @permission_required('users.view')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not has_permission(permission):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def role_required(role_name: str):
    """
    Decorator to require a specific role for a route.
    Usage: @role_required('admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not has_role(role_name):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def any_permission_required(permissions: list):
    """
    Decorator to require any of the specified permissions.
    Usage: @any_permission_required(['users.view', 'users.update'])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not any(has_permission(p) for p in permissions):
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_user_permissions():
    """
    Get all permissions for the current user.
    """
    try:
        if not has_request_context():
            return []
        return session.get('token_data', {}).get('permissions', [])
    except Exception:
        return []


def get_user_roles():
    """
    Get all roles for the current user.
    """
    try:
        if not has_request_context():
            return []
        return session.get('token_data', {}).get('roles', [])
    except Exception:
        return []
