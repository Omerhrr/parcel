"""
Authentication Utilities
ParcelFlow - Multi-tenant Logistics Platform
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenData

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def get_token_data(token: str) -> Optional[TokenData]:
    """Extract token data from JWT"""
    payload = decode_token(token)
    if not payload:
        return None
    
    return TokenData(
        user_id=payload.get("sub") and int(payload.get("sub")),
        business_id=payload.get("business_id"),
        branch_id=payload.get("branch_id"),
        roles=payload.get("roles", []),
        permissions=payload.get("permissions", []),
        exp=payload.get("exp")
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    Raises HTTPException if not authenticated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token = credentials.credentials
    token_data = get_token_data(token)
    
    if token_data is None or token_data.user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to get the current user (optional).
    Returns None if not authenticated.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    token_data = get_token_data(token)
    
    if token_data is None or token_data.user_id is None:
        return None
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    return user


def require_permission(permission: str):
    """
    Dependency factory to require a specific permission.
    Usage: @router.get("/", dependencies=[Depends(require_permission("orders.view"))])
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ):
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    return permission_checker


def require_role(role_name: str):
    """
    Dependency factory to require a specific role.
    Usage: @router.get("/", dependencies=[Depends(require_role("admin"))])
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ):
        if not current_user.has_role(role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_name}' required"
            )
        return current_user
    return role_checker


def require_business_access(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user has business context.
    Super admins can bypass business checks.
    """
    if not current_user.business_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with a business"
        )
    return current_user


def check_tenant_access(
    user: User,
    resource_business_id: int,
    resource_branch_id: Optional[int] = None
) -> bool:
    """
    Check if user has access to a tenant-scoped resource.
    Super admins have access to all resources.
    """
    # Super admins have access to everything
    if user.has_role("super_admin"):
        return True
    
    # Check business access
    if user.business_id != resource_business_id:
        return False
    
    # Check branch access (if user is branch-scoped and resource is branch-scoped)
    if user.branch_id and resource_branch_id:
        if user.branch_id != resource_branch_id:
            # Managers can access their branch resources
            if not user.has_permission("branches.view"):
                return False
    
    return True


def generate_tokens(user: User) -> dict:
    """Generate access and refresh tokens for a user"""
    roles = [r.name for r in user.roles]
    permissions = user.get_all_permissions()
    
    token_data = {
        "sub": str(user.id),
        "business_id": user.business_id,
        "branch_id": user.branch_id,
        "roles": roles,
        "permissions": permissions
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "business_id": user.business_id,
        "branch_id": user.branch_id,
        "roles": roles,
        "permissions": permissions
    }
