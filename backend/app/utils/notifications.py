"""
Notification Helper Utilities
ParcelFlow - Multi-tenant Logistics Platform

Helper functions for creating notifications from various parts of the system.
Includes email notification support.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.notification import (
    Notification, NotificationType, NotificationPriority, NotificationPreference
)
from app.models.user import User
from app.models.agent import LogisticAgent
from app.config import settings


logger = logging.getLogger(__name__)


def _run_async(coro):
    """
    Run an async coroutine synchronously.
    Used for running async email sends from sync code.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, create a task
            asyncio.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create one
        asyncio.run(coro)


async def _send_notification_email(
    user: User,
    title: str,
    message: str,
    action_url: Optional[str] = None,
    action_text: str = "View Details"
):
    """
    Send a notification email to a user.
    
    Args:
        user: User to send email to
        title: Email subject/title
        message: Email message
        action_url: URL for action button
        action_text: Text for action button
    """
    from app.services.email import send_notification as send_email_notification
    
    if not user or not user.email:
        return False
    
    # Build full URL if relative
    if action_url and not action_url.startswith('http'):
        action_url = f"{settings.FRONTEND_URL}{action_url}"
    
    try:
        result = await send_email_notification(
            to=user.email,
            title=title,
            message=message,
            action_url=action_url,
            action_text=action_text
        )
        return result
    except Exception as e:
        logger.error(f"Failed to send notification email to {user.email}: {str(e)}")
        return False


def get_user_email_preference(
    db: Session,
    user_id: int,
    notification_type: NotificationType
) -> bool:
    """
    Check if user has email notifications enabled for a specific type.
    
    Args:
        db: Database session
        user_id: User ID
        notification_type: Type of notification
        
    Returns:
        True if email is enabled for this notification type
    """
    # Map notification types to preference fields
    type_to_preference = {
        NotificationType.WAYBILL_CREATED: "notify_waybill_updates",
        NotificationType.WAYBILL_DISPATCHED: "notify_waybill_updates",
        NotificationType.WAYBILL_DELIVERED: "notify_waybill_updates",
        NotificationType.WAYBILL_FAILED: "notify_waybill_updates",
        NotificationType.PICKUP_ASSIGNED: "notify_pickup_assignments",
        NotificationType.PICKUP_COMPLETED: "notify_pickup_assignments",
        NotificationType.DELIVERY_ASSIGNED: "notify_delivery_assignments",
        NotificationType.DELIVERY_COMPLETED: "notify_delivery_assignments",
        NotificationType.ORDER_NEW: "notify_order_updates",
        NotificationType.ORDER_CONFIRMED: "notify_order_updates",
        NotificationType.ORDER_CANCELLED: "notify_order_updates",
        NotificationType.LOW_STOCK: "notify_stock_alerts",
        NotificationType.PAYMENT_RECEIVED: "notify_payment_updates",
        NotificationType.SYSTEM: "notify_system",
        NotificationType.REMINDER: "notify_system",
        NotificationType.CUSTOM: "notify_system",
    }
    
    preference_field = type_to_preference.get(notification_type, "notify_system")
    
    # Get user preference
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id
    ).first()
    
    if not pref:
        return True  # Default to sending emails
    
    return getattr(pref, preference_field, True) and pref.email_enabled


def create_notification(
    db: Session,
    business_id: int,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.SYSTEM,
    user_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
    action_url: Optional[str] = None,
    expires_in_hours: Optional[int] = 72,
    send_email: bool = False
) -> Notification:
    """
    Create a notification.
    
    Args:
        db: Database session
        business_id: Business ID
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        user_id: User ID (None for broadcast)
        agent_id: Agent ID (for agent notifications)
        priority: Priority level
        related_entity_type: Type of related entity (e.g., 'waybill', 'order')
        related_entity_id: ID of related entity
        action_url: URL to navigate when notification is clicked
        expires_in_hours: Hours until notification expires (None for no expiry)
        send_email: Whether to also send an email notification
        
    Returns:
        Created notification
    """
    expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours) if expires_in_hours else None
    
    notification = Notification(
        business_id=business_id,
        user_id=user_id,
        agent_id=agent_id,
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        action_url=action_url,
        expires_at=expires_at
    )
    
    db.add(notification)
    db.flush()  # Get ID without committing
    
    # Send email if requested and user has email enabled
    if send_email and user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user and get_user_email_preference(db, user_id, notification_type):
            # Run email sending asynchronously
            _run_async(_send_notification_email(
                user=user,
                title=title,
                message=message,
                action_url=action_url
            ))
            notification.sent_email = True
    
    return notification


def create_notification_with_email(
    db: Session,
    business_id: int,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.SYSTEM,
    user_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
    action_url: Optional[str] = None,
    expires_in_hours: Optional[int] = 72
) -> Notification:
    """
    Create a notification and send an email if user has it enabled.
    Convenience wrapper around create_notification with send_email=True.
    """
    return create_notification(
        db=db,
        business_id=business_id,
        title=title,
        message=message,
        notification_type=notification_type,
        user_id=user_id,
        agent_id=agent_id,
        priority=priority,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        action_url=action_url,
        expires_in_hours=expires_in_hours,
        send_email=True
    )


async def send_delivery_update_email(
    to_email: str,
    waybill_number: str,
    status: str,
    status_message: str,
    tracking_url: str,
    recipient_name: Optional[str] = None
):
    """
    Send a delivery status update email.
    
    Args:
        to_email: Recipient email
        waybill_number: Waybill/tracking number
        status: Delivery status
        status_message: Status message
        tracking_url: URL to track delivery
        recipient_name: Recipient name (optional)
    """
    from app.services.email import send_delivery_update
    
    # Build full URL if relative
    if tracking_url and not tracking_url.startswith('http'):
        tracking_url = f"{settings.FRONTEND_URL}{tracking_url}"
    
    await send_delivery_update(
        to=to_email,
        waybill_number=waybill_number,
        status=status,
        status_message=status_message,
        tracking_url=tracking_url,
        recipient_name=recipient_name
    )


async def send_waybill_created_email(
    to_email: str,
    waybill_number: str,
    sender_name: str,
    receiver_name: str,
    origin: str,
    destination: str,
    tracking_url: str
):
    """
    Send a waybill creation notification email.
    
    Args:
        to_email: Recipient email
        waybill_number: Waybill number
        sender_name: Sender name
        receiver_name: Receiver name
        origin: Origin location
        destination: Destination location
        tracking_url: URL to track waybill
    """
    from app.services.email import send_waybill_created
    
    # Build full URL if relative
    if tracking_url and not tracking_url.startswith('http'):
        tracking_url = f"{settings.FRONTEND_URL}{tracking_url}"
    
    await send_waybill_created(
        to=to_email,
        waybill_number=waybill_number,
        sender_name=sender_name,
        receiver_name=receiver_name,
        origin=origin,
        destination=destination,
        tracking_url=tracking_url
    )


def notify_waybill_created(
    db: Session,
    business_id: int,
    waybill_id: int,
    waybill_number: str,
    user_ids: List[int] = None,
    send_email: bool = False
):
    """Notify about new waybill creation"""
    notifications = []
    
    # Create notification for each user
    if user_ids:
        for user_id in user_ids:
            notification = create_notification(
                db=db,
                business_id=business_id,
                user_id=user_id,
                title="New Waybill Created",
                message=f"Waybill {waybill_number} has been created successfully.",
                notification_type=NotificationType.WAYBILL_CREATED,
                related_entity_type="waybill",
                related_entity_id=waybill_id,
                action_url=f"/waybills/{waybill_id}",
                send_email=send_email
            )
            notifications.append(notification)
    else:
        notification = create_notification(
            db=db,
            business_id=business_id,
            title="New Waybill Created",
            message=f"Waybill {waybill_number} has been created successfully.",
            notification_type=NotificationType.WAYBILL_CREATED,
            related_entity_type="waybill",
            related_entity_id=waybill_id,
            action_url=f"/waybills/{waybill_id}",
            send_email=send_email
        )
        notifications.append(notification)
    
    return notifications[0] if notifications else None


def notify_waybill_dispatched(
    db: Session,
    business_id: int,
    waybill_id: int,
    waybill_number: str,
    agent_id: int = None,
    user_ids: List[int] = None,
    send_email: bool = False
):
    """Notify about waybill dispatch"""
    # Notify agent if assigned
    if agent_id:
        create_notification(
            db=db,
            business_id=business_id,
            agent_id=agent_id,
            title="New Delivery Assignment",
            message=f"You have been assigned to deliver waybill {waybill_number}.",
            notification_type=NotificationType.DELIVERY_ASSIGNED,
            priority=NotificationPriority.HIGH,
            related_entity_type="waybill",
            related_entity_id=waybill_id,
            action_url=f"/waybills/{waybill_id}",
            send_email=send_email
        )
    
    # Notify relevant users
    notification = create_notification(
        db=db,
        business_id=business_id,
        title="Waybill Dispatched",
        message=f"Waybill {waybill_number} has been dispatched for delivery.",
        notification_type=NotificationType.WAYBILL_DISPATCHED,
        related_entity_type="waybill",
        related_entity_id=waybill_id,
        action_url=f"/waybills/{waybill_id}",
        send_email=send_email
    )
    return notification


def notify_waybill_delivered(
    db: Session,
    business_id: int,
    waybill_id: int,
    waybill_number: str,
    receiver_name: str = None,
    user_ids: List[int] = None,
    send_email: bool = False
):
    """Notify about successful delivery"""
    message = f"Waybill {waybill_number} has been successfully delivered"
    if receiver_name:
        message += f" to {receiver_name}"
    message += "."
    
    notification = create_notification(
        db=db,
        business_id=business_id,
        title="Waybill Delivered",
        message=message,
        notification_type=NotificationType.WAYBILL_DELIVERED,
        related_entity_type="waybill",
        related_entity_id=waybill_id,
        action_url=f"/waybills/{waybill_id}",
        send_email=send_email
    )
    return notification


def notify_waybill_failed(
    db: Session,
    business_id: int,
    waybill_id: int,
    waybill_number: str,
    reason: str = None,
    send_email: bool = False
):
    """Notify about failed delivery"""
    message = f"Delivery failed for waybill {waybill_number}"
    if reason:
        message += f": {reason}"
    
    notification = create_notification(
        db=db,
        business_id=business_id,
        title="Delivery Failed",
        message=message,
        notification_type=NotificationType.WAYBILL_FAILED,
        priority=NotificationPriority.HIGH,
        related_entity_type="waybill",
        related_entity_id=waybill_id,
        action_url=f"/waybills/{waybill_id}",
        send_email=send_email
    )
    return notification


def notify_pickup_assigned(
    db: Session,
    business_id: int,
    pickup_id: int,
    waybill_number: str,
    agent_id: int,
    send_email: bool = False
):
    """Notify agent about pickup assignment"""
    notification = create_notification(
        db=db,
        business_id=business_id,
        agent_id=agent_id,
        title="New Pickup Assignment",
        message=f"You have been assigned to pick up waybill {waybill_number}.",
        notification_type=NotificationType.PICKUP_ASSIGNED,
        priority=NotificationPriority.HIGH,
        related_entity_type="pickup",
        related_entity_id=pickup_id,
        action_url=f"/pickups/{pickup_id}",
        send_email=send_email
    )
    return notification


def notify_new_order(
    db: Session,
    business_id: int,
    order_id: int,
    order_number: str,
    user_ids: List[int] = None,
    send_email: bool = False
):
    """Notify about new order"""
    notification = create_notification(
        db=db,
        business_id=business_id,
        title="New Order Received",
        message=f"New order {order_number} has been received.",
        notification_type=NotificationType.ORDER_NEW,
        priority=NotificationPriority.HIGH,
        related_entity_type="order",
        related_entity_id=order_id,
        action_url=f"/orders/{order_id}",
        send_email=send_email
    )
    return notification


def notify_low_stock(
    db: Session,
    business_id: int,
    product_id: int,
    product_name: str,
    current_stock: int,
    threshold: int = 10,
    send_email: bool = True  # Default True for low stock alerts
):
    """Notify about low stock"""
    notification = create_notification(
        db=db,
        business_id=business_id,
        title="Low Stock Alert",
        message=f"Product '{product_name}' is running low on stock. Current: {current_stock}, Threshold: {threshold}",
        notification_type=NotificationType.LOW_STOCK,
        priority=NotificationPriority.HIGH,
        related_entity_type="product",
        related_entity_id=product_id,
        action_url=f"/inventory?product_id={product_id}",
        expires_in_hours=24,
        send_email=send_email
    )
    return notification


def notify_payment_received(
    db: Session,
    business_id: int,
    order_id: int,
    order_number: str,
    amount: float,
    send_email: bool = False
):
    """Notify about payment received"""
    notification = create_notification(
        db=db,
        business_id=business_id,
        title="Payment Received",
        message=f"Payment of ${amount:.2f} received for order {order_number}.",
        notification_type=NotificationType.PAYMENT_RECEIVED,
        related_entity_type="order",
        related_entity_id=order_id,
        action_url=f"/orders/{order_id}",
        send_email=send_email
    )
    return notification


def get_users_to_notify(db: Session, business_id: int, notification_type: NotificationType) -> List[int]:
    """
    Get list of user IDs who should receive a specific notification type
    based on their preferences.
    """
    # Map notification types to preference fields
    type_to_preference = {
        NotificationType.WAYBILL_CREATED: "notify_waybill_updates",
        NotificationType.WAYBILL_DISPATCHED: "notify_waybill_updates",
        NotificationType.WAYBILL_DELIVERED: "notify_waybill_updates",
        NotificationType.WAYBILL_FAILED: "notify_waybill_updates",
        NotificationType.PICKUP_ASSIGNED: "notify_pickup_assignments",
        NotificationType.PICKUP_COMPLETED: "notify_pickup_assignments",
        NotificationType.DELIVERY_ASSIGNED: "notify_delivery_assignments",
        NotificationType.DELIVERY_COMPLETED: "notify_delivery_assignments",
        NotificationType.ORDER_NEW: "notify_order_updates",
        NotificationType.ORDER_CONFIRMED: "notify_order_updates",
        NotificationType.ORDER_CANCELLED: "notify_order_updates",
        NotificationType.LOW_STOCK: "notify_stock_alerts",
        NotificationType.PAYMENT_RECEIVED: "notify_payment_updates",
        NotificationType.SYSTEM: "notify_system",
        NotificationType.REMINDER: "notify_system",
        NotificationType.CUSTOM: "notify_system",
    }
    
    preference_field = type_to_preference.get(notification_type, "notify_system")
    
    # Get users with this notification type enabled
    prefs = db.query(NotificationPreference).join(User).filter(
        NotificationPreference.business_id == business_id,
        getattr(NotificationPreference, preference_field) == True,
        User.status == 'active'
    ).all()
    
    return [p.user_id for p in prefs]


def cleanup_expired_notifications(db: Session, business_id: int = None):
    """Delete expired notifications"""
    query = db.query(Notification).filter(
        Notification.expires_at < datetime.utcnow()
    )
    
    if business_id:
        query = query.filter(Notification.business_id == business_id)
    
    deleted = query.delete()
    db.commit()
    
    return deleted
