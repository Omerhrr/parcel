"""
Decorators for route protection
ParcelFlow - Multi-tenant Logistics Platform
"""
from functools import wraps
from fastapi import HTTPException, status
from typing import Callable, Optional


def tenant_required(func: Callable) -> Callable:
    """
    Decorator to ensure tenant context is present.
    Adds business_id to function kwargs.
    """
    @wraps(func)
    async def wrapper(*args, current_user=None, **kwargs):
        if not current_user or not current_user.business_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant context required"
            )
        kwargs['business_id'] = current_user.business_id
        kwargs['current_user'] = current_user
        return await func(*args, **kwargs)
    return wrapper


def permission_required(permission: str) -> Callable:
    """
    Decorator factory to require specific permission.
    Usage: @permission_required("orders.view")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user=None, **kwargs):
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            if not current_user.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required"
                )
            kwargs['current_user'] = current_user
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def role_required(role: str) -> Callable:
    """
    Decorator factory to require specific role.
    Usage: @role_required("admin")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, current_user=None, **kwargs):
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            if not current_user.has_role(role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role}' required"
                )
            kwargs['current_user'] = current_user
            return await func(*args, **kwargs)
        return wrapper
    return decorator
