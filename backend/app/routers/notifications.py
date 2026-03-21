"""
Notifications Router
ParcelFlow - Multi-tenant Logistics Platform
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.notification import (
    Notification, NotificationType, NotificationPriority,
    NotificationCreate, NotificationResponse, NotificationListResponse,
    NotificationPreference, NotificationPreferenceResponse, NotificationPreferenceUpdate
)
from app.utils.auth import get_current_user
from app.schemas.base import BaseSchema

router = APIRouter()


class MarkReadRequest(BaseSchema):
    notification_ids: List[int]


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    notification_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List notifications for current user"""
    query = db.query(Notification).filter(
        Notification.business_id == current_user.business_id,
        or_(
            Notification.user_id == current_user.id,
            Notification.user_id.is_(None)  # Broadcast notifications
        ),
        or_(
            Notification.expires_at.is_(None),
            Notification.expires_at > datetime.utcnow()
        )
    )
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    if notification_type:
        try:
            query = query.filter(Notification.notification_type == NotificationType(notification_type))
        except ValueError:
            pass
    
    # Get unread count
    unread_count = db.query(Notification).filter(
        Notification.business_id == current_user.business_id,
        Notification.is_read == False,
        or_(
            Notification.user_id == current_user.id,
            Notification.user_id.is_(None)
        )
    ).count()
    
    total = query.count()
    offset = (page - 1) * page_size
    notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(page_size).all()
    
    return NotificationListResponse(
        items=[NotificationResponse(
            id=n.id,
            business_id=n.business_id,
            user_id=n.user_id,
            agent_id=n.agent_id,
            notification_type=n.notification_type,
            title=n.title,
            message=n.message,
            priority=n.priority,
            related_entity_type=n.related_entity_type,
            related_entity_id=n.related_entity_id,
            action_url=n.action_url,
            is_read=n.is_read,
            read_at=n.read_at,
            created_at=n.created_at,
            expires_at=n.expires_at
        ) for n in notifications],
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get unread notification count"""
    count = db.query(Notification).filter(
        Notification.business_id == current_user.business_id,
        Notification.is_read == False,
        or_(
            Notification.user_id == current_user.id,
            Notification.user_id.is_(None)
        ),
        or_(
            Notification.expires_at.is_(None),
            Notification.expires_at > datetime.utcnow()
        )
    ).count()
    
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.business_id == current_user.business_id,
        or_(
            Notification.user_id == current_user.id,
            Notification.user_id.is_(None)
        )
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()
    
    return {"success": True, "message": "Notification marked as read"}


@router.post("/mark-all-read")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    db.query(Notification).filter(
        Notification.business_id == current_user.business_id,
        Notification.is_read == False,
        or_(
            Notification.user_id == current_user.id,
            Notification.user_id.is_(None)
        )
    ).update({
        "is_read": True,
        "read_at": datetime.utcnow()
    })
    db.commit()
    
    return {"success": True, "message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a notification"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.business_id == current_user.business_id,
        or_(
            Notification.user_id == current_user.id,
            Notification.user_id.is_(None)
        )
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"success": True, "message": "Notification deleted"}


# ==================== PREFERENCES ====================

@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's notification preferences"""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.business_id == current_user.business_id,
        NotificationPreference.user_id == current_user.id
    ).first()
    
    if not prefs:
        # Create default preferences
        prefs = NotificationPreference(
            business_id=current_user.business_id,
            user_id=current_user.id
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    
    return NotificationPreferenceResponse(
        email_enabled=prefs.email_enabled,
        sms_enabled=prefs.sms_enabled,
        push_enabled=prefs.push_enabled,
        in_app_enabled=prefs.in_app_enabled,
        notify_waybill_updates=prefs.notify_waybill_updates,
        notify_pickup_assignments=prefs.notify_pickup_assignments,
        notify_delivery_assignments=prefs.notify_delivery_assignments,
        notify_order_updates=prefs.notify_order_updates,
        notify_stock_alerts=prefs.notify_stock_alerts,
        notify_payment_updates=prefs.notify_payment_updates,
        notify_system=prefs.notify_system,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end
    )


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preferences(
    request: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's notification preferences"""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.business_id == current_user.business_id,
        NotificationPreference.user_id == current_user.id
    ).first()
    
    if not prefs:
        prefs = NotificationPreference(
            business_id=current_user.business_id,
            user_id=current_user.id
        )
        db.add(prefs)
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prefs, field, value)
    
    prefs.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prefs)
    
    return NotificationPreferenceResponse(
        email_enabled=prefs.email_enabled,
        sms_enabled=prefs.sms_enabled,
        push_enabled=prefs.push_enabled,
        in_app_enabled=prefs.in_app_enabled,
        notify_waybill_updates=prefs.notify_waybill_updates,
        notify_pickup_assignments=prefs.notify_pickup_assignments,
        notify_delivery_assignments=prefs.notify_delivery_assignments,
        notify_order_updates=prefs.notify_order_updates,
        notify_stock_alerts=prefs.notify_stock_alerts,
        notify_payment_updates=prefs.notify_payment_updates,
        notify_system=prefs.notify_system,
        quiet_hours_start=prefs.quiet_hours_start,
        quiet_hours_end=prefs.quiet_hours_end
    )


# ==================== ADMIN ENDPOINTS ====================

@router.post("/create", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    request: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new notification (admin/system use)"""
    if not current_user.has_permission("notifications.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    notification = Notification(
        business_id=current_user.business_id,
        user_id=request.user_id,
        agent_id=request.agent_id,
        notification_type=request.notification_type,
        title=request.title,
        message=request.message,
        priority=request.priority,
        related_entity_type=request.related_entity_type,
        related_entity_id=request.related_entity_id,
        action_url=request.action_url,
        expires_at=request.expires_at
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return NotificationResponse(
        id=notification.id,
        business_id=notification.business_id,
        user_id=notification.user_id,
        agent_id=notification.agent_id,
        notification_type=notification.notification_type,
        title=notification.title,
        message=notification.message,
        priority=notification.priority,
        related_entity_type=notification.related_entity_type,
        related_entity_id=notification.related_entity_id,
        action_url=notification.action_url,
        is_read=notification.is_read,
        read_at=notification.read_at,
        created_at=notification.created_at,
        expires_at=notification.expires_at
    )


@router.post("/broadcast")
async def broadcast_notification(
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.SYSTEM,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    action_url: Optional[str] = None,
    expires_in_hours: Optional[int] = 72,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Broadcast notification to all users in business"""
    if not current_user.has_permission("notifications.create"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Create broadcast notification (user_id = None)
    expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours) if expires_in_hours else None
    
    notification = Notification(
        business_id=current_user.business_id,
        user_id=None,  # Broadcast
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        action_url=action_url,
        expires_at=expires_at
    )
    
    db.add(notification)
    db.commit()
    
    return {"success": True, "message": "Notification broadcast created"}
