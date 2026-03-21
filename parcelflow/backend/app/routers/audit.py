"""
Audit Logs Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.audit import (
    AuditLogResponse, AuditLogListResponse, AuditLogDiffResponse,
    AuditStatsResponse
)
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List audit logs with filters.
    
    Query params:
    - page: Page number (default 1)
    - page_size: Items per page (default 20, max 100)
    - entity_type: Filter by entity type
    - entity_id: Filter by entity ID
    - user_id: Filter by user who made the change
    - action: Filter by action type
    - start_date: Filter by start date (ISO format)
    - end_date: Filter by end date (ISO format)
    - search: Search in description
    """
    query = db.query(AuditLog)
    
    # Super admins can see all logs, others are filtered by business
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(AuditLog.business_id == current_user.business_id)
        else:
            return AuditLogListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)
    
    # Apply filters
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.timestamp >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.timestamp <= end_dt)
        except ValueError:
            pass
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(AuditLog.description.ilike(search_term))
    
    # Get total count
    total = query.count()
    
    # Order by timestamp descending
    offset = (page - 1) * page_size
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size).all()
    
    # Build response with user info
    items = []
    for log in logs:
        user_name = None
        user_email = None
        if log.user:
            user_name = log.user.name
            user_email = log.user.email
        
        items.append(AuditLogResponse(
            id=log.id,
            business_id=log.business_id,
            user_id=log.user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            old_values=log.old_values_dict,
            new_values=log.new_values_dict,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            description=log.description,
            metadata=log.metadata_dict,
            timestamp=log.timestamp,
            action_display=log.get_action_display(),
            entity_display=log.get_entity_display(),
            user_name=user_name,
            user_email=user_email,
        ))
    
    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get audit log statistics"""
    query = db.query(AuditLog)
    
    # Filter by business for non-super admins
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(AuditLog.business_id == current_user.business_id)
        else:
            return AuditStatsResponse(
                total_logs=0, logs_today=0, logs_this_week=0, logs_this_month=0,
                top_actions=[], top_entity_types=[], top_users=[]
            )
    
    # Total logs
    total_logs = query.count()
    
    # Logs today
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    logs_today = query.filter(AuditLog.timestamp >= today).count()
    
    # Logs this week
    week_start = today - timedelta(days=today.weekday())
    logs_this_week = query.filter(AuditLog.timestamp >= week_start).count()
    
    # Logs this month
    month_start = today.replace(day=1)
    logs_this_month = query.filter(AuditLog.timestamp >= month_start).count()
    
    # Top actions
    from sqlalchemy import func
    top_actions_query = db.query(
        AuditLog.action,
        func.count(AuditLog.id).label('count')
    )
    if not current_user.has_role("super_admin") and current_user.business_id:
        top_actions_query = top_actions_query.filter(AuditLog.business_id == current_user.business_id)
    top_actions = [
        {"action": row.action, "count": row.count}
        for row in top_actions_query.group_by(AuditLog.action).order_by(func.count(AuditLog.id).desc()).limit(5).all()
    ]
    
    # Top entity types
    top_entities_query = db.query(
        AuditLog.entity_type,
        func.count(AuditLog.id).label('count')
    )
    if not current_user.has_role("super_admin") and current_user.business_id:
        top_entities_query = top_entities_query.filter(AuditLog.business_id == current_user.business_id)
    top_entity_types = [
        {"entity_type": row.entity_type, "count": row.count}
        for row in top_entities_query.group_by(AuditLog.entity_type).order_by(func.count(AuditLog.id).desc()).limit(5).all()
    ]
    
    # Top users
    top_users_query = db.query(
        AuditLog.user_id,
        User.name,
        func.count(AuditLog.id).label('count')
    ).outerjoin(User, AuditLog.user_id == User.id)
    if not current_user.has_role("super_admin") and current_user.business_id:
        top_users_query = top_users_query.filter(AuditLog.business_id == current_user.business_id)
    top_users = [
        {"user_id": row.user_id, "user_name": row.name or "System", "count": row.count}
        for row in top_users_query.group_by(AuditLog.user_id, User.name).order_by(func.count(AuditLog.id).desc()).limit(5).all()
    ]
    
    return AuditStatsResponse(
        total_logs=total_logs,
        logs_today=logs_today,
        logs_this_week=logs_this_week,
        logs_this_month=logs_this_month,
        top_actions=top_actions,
        top_entity_types=top_entity_types,
        top_users=top_users,
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=AuditLogListResponse)
async def get_entity_audit_logs(
    entity_type: str,
    entity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all audit logs for a specific entity.
    This is useful for viewing the complete history of a waybill, order, etc.
    """
    query = db.query(AuditLog).filter(
        AuditLog.entity_type == entity_type,
        AuditLog.entity_id == entity_id
    )
    
    # Filter by business for non-super admins
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(AuditLog.business_id == current_user.business_id)
        else:
            return AuditLogListResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)
    
    total = query.count()
    offset = (page - 1) * page_size
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size).all()
    
    items = []
    for log in logs:
        user_name = None
        user_email = None
        if log.user:
            user_name = log.user.name
            user_email = log.user.email
        
        items.append(AuditLogResponse(
            id=log.id,
            business_id=log.business_id,
            user_id=log.user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            old_values=log.old_values_dict,
            new_values=log.new_values_dict,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            description=log.description,
            metadata=log.metadata_dict,
            timestamp=log.timestamp,
            action_display=log.get_action_display(),
            entity_display=log.get_entity_display(),
            user_name=user_name,
            user_email=user_email,
        ))
    
    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get("/{log_id}", response_model=AuditLogDiffResponse)
async def get_audit_log_detail(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed audit log with diff of changes.
    Shows added, removed, and changed fields between old and new values.
    """
    query = db.query(AuditLog).filter(AuditLog.id == log_id)
    
    # Filter by business for non-super admins
    if not current_user.has_role("super_admin"):
        if current_user.business_id:
            query = query.filter(AuditLog.business_id == current_user.business_id)
        else:
            raise HTTPException(status_code=404, detail="Audit log not found")
    
    log = query.first()
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    # Get diff
    diff = log.get_diff()
    
    # Get user info
    user_name = None
    if log.user:
        user_name = log.user.name
    
    return AuditLogDiffResponse(
        id=log.id,
        action=log.action,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        timestamp=log.timestamp,
        description=log.description,
        added=diff['added'],
        removed=diff['removed'],
        changed=diff['changed'],
        user_name=user_name,
    )


@router.get("/actions/list")
async def list_audit_actions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of available audit actions for filtering"""
    from sqlalchemy import func
    
    query = db.query(AuditLog.action).distinct()
    
    if not current_user.has_role("super_admin") and current_user.business_id:
        query = query.filter(AuditLog.business_id == current_user.business_id)
    
    actions = [row.action for row in query.all()]
    
    # Define action display names
    action_map = {
        'create': 'Created',
        'update': 'Updated',
        'delete': 'Deleted',
        'status_change': 'Status Changed',
        'assign': 'Assigned',
        'unassign': 'Unassigned',
        'login': 'Logged In',
        'logout': 'Logged Out',
        'login_failed': 'Login Failed',
        'password_change': 'Password Changed',
        'role_change': 'Role Changed',
        'export': 'Exported',
        'import': 'Imported',
    }
    
    return [
        {"value": action, "label": action_map.get(action, action.replace('_', ' ').title())}
        for action in sorted(actions)
    ]


@router.get("/entity-types/list")
async def list_entity_types(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of available entity types for filtering"""
    query = db.query(AuditLog.entity_type).distinct()
    
    if not current_user.has_role("super_admin") and current_user.business_id:
        query = query.filter(AuditLog.business_id == current_user.business_id)
    
    entity_types = [row.entity_type for row in query.all()]
    
    # Define entity display names
    entity_map = {
        'waybill': 'Waybill',
        'order': 'Order',
        'deliveryconfirmation': 'Delivery',
        'logisticagent': 'Agent',
        'user': 'User',
        'vendor': 'Vendor',
        'branch': 'Branch',
        'product': 'Product',
        'warehouse': 'Warehouse',
        'vehicle': 'Vehicle',
        'pickup': 'Pickup',
        'dispatch': 'Dispatch',
        'expense': 'Expense',
        'transaction': 'Transaction',
        'lead': 'Lead',
    }
    
    return [
        {"value": entity, "label": entity_map.get(entity.lower(), entity.replace('_', ' ').title())}
        for entity in sorted(entity_types)
    ]
