"""
Users Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User, UserStatus
from app.models.role import Role
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    UserPasswordUpdate
)
from app.schemas.base import PaginatedResponse
from app.utils.auth import get_current_user, hash_password, require_permission

router = APIRouter()


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    branch_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List users with pagination and filters.
    Requires 'users.view' permission.
    """
    # Check permission
    if not current_user.has_permission("users.view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # Build query
    query = db.query(User).filter(User.business_id == current_user.business_id)
    
    # Apply filters
    if status:
        query = query.filter(User.status == status)
    
    if branch_id:
        query = query.filter(User.branch_id == branch_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_term)) |
            (User.email.ilike(search_term)) |
            (User.phone.ilike(search_term))
        )
    
    # Get total count
    total = query.count()
    
    # Paginate
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
    
    # Build response
    from app.schemas.user import RoleBrief
    from app.schemas.auth import BranchBrief
    
    items = []
    for u in users:
        roles = [RoleBrief(id=r.id, name=r.name, display_name=r.display_name) for r in u.roles]
        branch = None
        if u.branch:
            branch = BranchBrief(
                id=u.branch.id,
                name=u.branch.name,
                code=u.branch.code,
                city=u.branch.city,
                currency=u.branch.currency
            )
        
        items.append(UserResponse(
            id=u.id,
            business_id=u.business_id,
            branch_id=u.branch_id,
            name=u.name,
            email=u.email,
            phone=u.phone,
            status=u.status.value,
            is_verified=u.is_verified,
            avatar_url=u.avatar_url,
            timezone=u.timezone,
            language=u.language,
            last_login=u.last_login,
            created_at=u.created_at,
            updated_at=u.updated_at,
            roles=roles,
            branch=branch
        ))
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    return UserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user by ID.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.business_id == current_user.business_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    from app.schemas.user import RoleBrief
    from app.schemas.auth import BranchBrief
    
    roles = [RoleBrief(id=r.id, name=r.name, display_name=r.display_name) for r in user.roles]
    branch = None
    if user.branch:
        branch = BranchBrief(
            id=user.branch.id,
            name=user.branch.name,
            code=user.branch.code,
            city=user.branch.city,
            currency=user.branch.currency
        )
    
    return UserResponse(
        id=user.id,
        business_id=user.business_id,
        branch_id=user.branch_id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        status=user.status.value,
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
        timezone=user.timezone,
        language=user.language,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=roles,
        branch=branch
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user.
    Requires 'users.create' permission.
    """
    if not current_user.has_permission("users.create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # Check if email exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate branch belongs to user's business if provided
    if request.branch_id:
        from app.models.branch import Branch
        branch = db.query(Branch).filter(
            Branch.id == request.branch_id,
            Branch.business_id == current_user.business_id
        ).first()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid branch specified"
            )
    
    # Validate roles - ensure only valid role IDs and prevent super_admin assignment
    if request.role_ids:
        roles = db.query(Role).filter(Role.id.in_(request.role_ids)).all()
        # Check if trying to assign super_admin role
        if any(r.name == "super_admin" for r in roles):
            if not current_user.has_role("super_admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only super admins can assign the super_admin role"
                )
    else:
        roles = []
    
    # Create user
    user = User(
        business_id=current_user.business_id,
        branch_id=request.branch_id,
        name=request.name,
        email=request.email,
        phone=request.phone,
        status=request.status,
        timezone=request.timezone,
        language=request.language
    )
    user.set_password(request.password)
    
    # Assign roles
    if roles:
        user.roles = roles
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    from app.schemas.user import RoleBrief
    roles = [RoleBrief(id=r.id, name=r.name, display_name=r.display_name) for r in user.roles]
    
    return UserResponse(
        id=user.id,
        business_id=user.business_id,
        branch_id=user.branch_id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        status=user.status.value,
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
        timezone=user.timezone,
        language=user.language,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=roles
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user.
    Requires 'users.update' permission.
    """
    if not current_user.has_permission("users.update"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.business_id == current_user.business_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate branch belongs to user's business if provided
    if request.branch_id:
        from app.models.branch import Branch
        branch = db.query(Branch).filter(
            Branch.id == request.branch_id,
            Branch.business_id == current_user.business_id
        ).first()
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid branch specified"
            )
    
    # Update fields
    update_data = request.model_dump(exclude_unset=True, exclude={'role_ids'})
    for field, value in update_data.items():
        setattr(user, field, value)
    
    # Update roles
    if request.role_ids is not None:
        roles = db.query(Role).filter(Role.id.in_(request.role_ids)).all()
        
        # Check if trying to assign super_admin role
        if any(r.name == "super_admin" for r in roles):
            if not current_user.has_role("super_admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only super admins can assign the super_admin role"
                )
        
        # Check if trying to remove super_admin role from another super_admin
        if current_user.has_role("super_admin") and user.has_role("super_admin"):
            if not any(r.name == "super_admin" for r in roles):
                # Prevent removing the last super_admin
                super_admin_count = db.query(User).join(
                    user_roles, User.id == user_roles.c.user_id
                ).join(
                    Role, user_roles.c.role_id == Role.id
                ).filter(
                    Role.name == "super_admin",
                    User.business_id == current_user.business_id
                ).count()
                
                if super_admin_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot remove super_admin role from the last super admin"
                    )
        
        user.roles = roles
    
    db.commit()
    db.refresh(user)
    
    from app.schemas.user import RoleBrief
    roles = [RoleBrief(id=r.id, name=r.name, display_name=r.display_name) for r in user.roles]
    
    return UserResponse(
        id=user.id,
        business_id=user.business_id,
        branch_id=user.branch_id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        status=user.status.value,
        is_verified=user.is_verified,
        avatar_url=user.avatar_url,
        timezone=user.timezone,
        language=user.language,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=roles
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete (deactivate) user.
    Requires 'users.delete' permission.
    """
    if not current_user.has_permission("users.delete"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.business_id == current_user.business_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Soft delete - just deactivate
    user.status = UserStatus.INACTIVE
    db.commit()
    
    return {
        "success": True,
        "message": "User deactivated successfully"
    }
