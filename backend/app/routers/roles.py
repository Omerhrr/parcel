"""
Roles Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models.user import User
from app.models.role import Role, Permission
from app.schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    PermissionResponse, RoleBrief
)
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=RoleListResponse)
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all available roles"""
    query = db.query(Role).order_by(Role.name)
    
    total = query.count()
    offset = (page - 1) * page_size
    roles = query.offset(offset).limit(page_size).all()
    
    items = []
    for r in roles:
        permissions = [
            PermissionResponse(
                id=p.id, name=p.name, display_name=p.display_name,
                description=p.description, module=p.module
            ) for p in r.permissions
        ]
        items.append(RoleResponse(
            id=r.id, name=r.name, display_name=r.display_name,
            description=r.description, is_system=r.is_system,
            permissions=permissions,
            created_at=r.created_at, updated_at=r.updated_at
        ))
    
    return RoleListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/brief", response_model=List[RoleBrief])
async def list_roles_brief(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List roles briefly for dropdowns"""
    roles = db.query(Role).order_by(Role.display_name).all()
    
    return [
        RoleBrief(id=r.id, name=r.name, display_name=r.display_name)
        for r in roles
    ]


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get role by ID"""
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    permissions = [
        PermissionResponse(
            id=p.id, name=p.name, display_name=p.display_name,
            description=p.description, module=p.module
        ) for p in role.permissions
    ]
    
    return RoleResponse(
        id=role.id, name=role.name, display_name=role.display_name,
        description=role.description, is_system=role.is_system,
        permissions=permissions,
        created_at=role.created_at, updated_at=role.updated_at
    )


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new role"""
    if not current_user.has_permission("settings.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Check if role name exists
    existing = db.query(Role).filter(Role.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role name already exists")
    
    role = Role(
        name=request.name,
        display_name=request.display_name,
        description=request.description
    )
    
    # Assign permissions
    if request.permission_ids:
        permissions = db.query(Permission).filter(
            Permission.id.in_(request.permission_ids)
        ).all()
        role.permissions = permissions
    
    db.add(role)
    db.commit()
    db.refresh(role)
    
    permissions = [
        PermissionResponse(
            id=p.id, name=p.name, display_name=p.display_name,
            description=p.description, module=p.module
        ) for p in role.permissions
    ]
    
    return RoleResponse(
        id=role.id, name=role.name, display_name=role.display_name,
        description=role.description, is_system=role.is_system,
        permissions=permissions,
        created_at=role.created_at, updated_at=role.updated_at
    )


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    request: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update role"""
    if not current_user.has_permission("settings.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system roles")
    
    update_data = request.model_dump(exclude_unset=True, exclude={'permission_ids'})
    for field, value in update_data.items():
        setattr(role, field, value)
    
    # Update permissions
    if request.permission_ids is not None:
        permissions = db.query(Permission).filter(
            Permission.id.in_(request.permission_ids)
        ).all()
        role.permissions = permissions
    
    db.commit()
    db.refresh(role)
    
    permissions = [
        PermissionResponse(
            id=p.id, name=p.name, display_name=p.display_name,
            description=p.description, module=p.module
        ) for p in role.permissions
    ]
    
    return RoleResponse(
        id=role.id, name=role.name, display_name=role.display_name,
        description=role.description, is_system=role.is_system,
        permissions=permissions,
        created_at=role.created_at, updated_at=role.updated_at
    )


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete role"""
    if not current_user.has_permission("settings.update"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
    
    db.delete(role)
    db.commit()
    
    return {"success": True, "message": "Role deleted"}


@router.get("/permissions/all", response_model=List[PermissionResponse])
async def list_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all available permissions"""
    permissions = db.query(Permission).order_by(Permission.module, Permission.name).all()
    
    return [
        PermissionResponse(
            id=p.id, name=p.name, display_name=p.display_name,
            description=p.description, module=p.module
        ) for p in permissions
    ]


@router.put("/{role_id}/permissions")
async def update_role_permissions(
    role_id: int,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update permissions for a role (super admin only)"""
    # Check if user is super admin
    if not current_user.has_role("super_admin"):
        raise HTTPException(status_code=403, detail="Only super admins can modify role permissions")
    
    role = db.query(Role).filter(Role.id == role_id).first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    permission_ids = request.get('permission_ids', [])
    
    # Get permissions
    if permission_ids:
        permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
    else:
        permissions = []
    
    role.permissions = permissions
    db.commit()
    db.refresh(role)
    
    return {
        "success": True,
        "message": "Permissions updated successfully",
        "role_id": role.id,
        "permissions": [p.name for p in role.permissions]
    }
