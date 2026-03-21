"""
Audit Service - Handles audit logging throughout the application
ParcelFlow - Multi-tenant Logistics Platform

This service provides:
- Direct logging functions for audit events
- Decorator for automatic logging
- Helper functions for capturing entity changes
"""
from functools import wraps
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
import json
import inspect

from sqlalchemy.orm import Session
from fastapi import Request

from app.models.audit import AuditLog


class AuditService:
    """
    Audit Service class for logging system changes.
    
    Usage:
        # Direct logging
        audit = AuditService(db)
        audit.log_create(waybill, user_id=1, ip_address="127.0.0.1")
        
        # Status change
        audit.log_status_change(
            entity=waybill,
            old_status="pending",
            new_status="delivered",
            user_id=1
        )
        
        # Using decorator
        @audit_decorator(action="update", entity_type="waybill")
        def update_waybill(waybill_id: int, data: dict):
            ...
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: int,
        user_id: Optional[int] = None,
        business_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.
        
        Args:
            action: The action performed (create, update, delete, status_change, etc.)
            entity_type: Type of entity (waybill, order, agent, etc.)
            entity_id: ID of the entity
            user_id: ID of the user who performed the action
            business_id: ID of the business (for multi-tenant)
            old_values: Dictionary of values before the change
            new_values: Dictionary of values after the change
            ip_address: IP address of the request
            user_agent: User agent string
            description: Human-readable description of the change
            metadata: Additional metadata
        
        Returns:
            The created AuditLog instance
        """
        audit_log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            business_id=business_id,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            timestamp=datetime.utcnow(),
        )
        
        if old_values:
            audit_log.set_old_values(old_values)
        if new_values:
            audit_log.set_new_values(new_values)
        if metadata:
            audit_log.set_metadata(metadata)
        
        self.db.add(audit_log)
        # Note: We don't commit here - let the caller handle the transaction
        # This allows the audit log to be part of the same transaction
        self.db.flush()  # Flush to get the ID
        
        return audit_log
    
    def log_create(
        self,
        entity: Any,
        user_id: Optional[int] = None,
        business_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AuditLog:
        """
        Log the creation of an entity.
        
        Args:
            entity: The created entity
            user_id: ID of the user who created the entity
            business_id: ID of the business
            ip_address: IP address of the request
            user_agent: User agent string
            description: Optional description
        
        Returns:
            The created AuditLog instance
        """
        entity_type = entity.__class__.__name__.lower()
        entity_id = entity.id
        new_values = self._entity_to_dict(entity)
        
        if not description:
            description = f"Created {entity_type} #{entity_id}"
        
        return self.log(
            action="create",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            business_id=business_id or getattr(entity, 'business_id', None),
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )
    
    def log_update(
        self,
        entity: Any,
        old_values: Dict[str, Any],
        user_id: Optional[int] = None,
        business_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        description: Optional[str] = None,
        updated_fields: Optional[List[str]] = None,
    ) -> AuditLog:
        """
        Log an update to an entity.
        
        Args:
            entity: The updated entity
            old_values: Dictionary of values before the update
            user_id: ID of the user who updated the entity
            business_id: ID of the business
            ip_address: IP address of the request
            user_agent: User agent string
            description: Optional description
            updated_fields: List of fields that were updated
        
        Returns:
            The created AuditLog instance
        """
        entity_type = entity.__class__.__name__.lower()
        entity_id = entity.id
        new_values = self._entity_to_dict(entity, fields=updated_fields)
        
        # Filter old_values to only include updated fields
        if updated_fields:
            old_values = {k: v for k, v in old_values.items() if k in updated_fields}
            new_values = {k: v for k, v in new_values.items() if k in updated_fields}
        
        if not description:
            if updated_fields:
                description = f"Updated {entity_type} #{entity_id}: {', '.join(updated_fields)}"
            else:
                description = f"Updated {entity_type} #{entity_id}"
        
        return self.log(
            action="update",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            business_id=business_id or getattr(entity, 'business_id', None),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )
    
    def log_delete(
        self,
        entity: Any,
        user_id: Optional[int] = None,
        business_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AuditLog:
        """
        Log the deletion of an entity.
        
        Args:
            entity: The deleted entity
            user_id: ID of the user who deleted the entity
            business_id: ID of the business
            ip_address: IP address of the request
            user_agent: User agent string
            description: Optional description
        
        Returns:
            The created AuditLog instance
        """
        entity_type = entity.__class__.__name__.lower()
        entity_id = entity.id
        old_values = self._entity_to_dict(entity)
        
        if not description:
            description = f"Deleted {entity_type} #{entity_id}"
        
        return self.log(
            action="delete",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            business_id=business_id or getattr(entity, 'business_id', None),
            old_values=old_values,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )
    
    def log_status_change(
        self,
        entity: Any,
        old_status: str,
        new_status: str,
        user_id: Optional[int] = None,
        business_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        description: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Log a status change for an entity.
        
        Args:
            entity: The entity whose status changed
            old_status: The previous status
            new_status: The new status
            user_id: ID of the user who changed the status
            business_id: ID of the business
            ip_address: IP address of the request
            user_agent: User agent string
            description: Optional description
            additional_data: Additional data to include in new_values
        
        Returns:
            The created AuditLog instance
        """
        entity_type = entity.__class__.__name__.lower()
        entity_id = entity.id
        
        old_values = {"status": old_status}
        new_values = {"status": new_status}
        
        if additional_data:
            new_values.update(additional_data)
        
        if not description:
            description = f"Status changed from '{old_status}' to '{new_status}' for {entity_type} #{entity_id}"
        
        return self.log(
            action="status_change",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            business_id=business_id or getattr(entity, 'business_id', None),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )
    
    def log_assignment(
        self,
        entity: Any,
        assigned_to_id: int,
        assigned_to_name: str,
        user_id: Optional[int] = None,
        business_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        description: Optional[str] = None,
        old_assignee: Optional[str] = None,
    ) -> AuditLog:
        """
        Log an assignment change.
        
        Args:
            entity: The entity being assigned
            assigned_to_id: ID of the user/agent being assigned to
            assigned_to_name: Name of the user/agent being assigned to
            user_id: ID of the user who made the assignment
            business_id: ID of the business
            ip_address: IP address of the request
            user_agent: User agent string
            description: Optional description
            old_assignee: Name of the previous assignee (if any)
        
        Returns:
            The created AuditLog instance
        """
        entity_type = entity.__class__.__name__.lower()
        entity_id = entity.id
        
        old_values = {}
        new_values = {"assigned_to_id": assigned_to_id, "assigned_to_name": assigned_to_name}
        
        if old_assignee:
            old_values["assigned_to"] = old_assignee
        
        if not description:
            if old_assignee:
                description = f"Reassigned {entity_type} #{entity_id} from {old_assignee} to {assigned_to_name}"
            else:
                description = f"Assigned {entity_type} #{entity_id} to {assigned_to_name}"
        
        return self.log(
            action="assign",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            business_id=business_id or getattr(entity, 'business_id', None),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )
    
    def log_role_change(
        self,
        user_id_target: int,
        user_name: str,
        old_roles: List[str],
        new_roles: List[str],
        user_id: Optional[int] = None,
        business_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AuditLog:
        """
        Log a role change for a user.
        
        Args:
            user_id_target: ID of the user whose roles changed
            user_name: Name of the user whose roles changed
            old_roles: List of previous roles
            new_roles: List of new roles
            user_id: ID of the user who made the change
            business_id: ID of the business
            ip_address: IP address of the request
            user_agent: User agent string
            description: Optional description
        
        Returns:
            The created AuditLog instance
        """
        old_values = {"roles": old_roles}
        new_values = {"roles": new_roles}
        
        if not description:
            added = set(new_roles) - set(old_roles)
            removed = set(old_roles) - set(new_roles)
            changes = []
            if added:
                changes.append(f"added {', '.join(added)}")
            if removed:
                changes.append(f"removed {', '.join(removed)}")
            description = f"Roles for {user_name}: {'; '.join(changes)}"
        
        return self.log(
            action="role_change",
            entity_type="user",
            entity_id=user_id_target,
            user_id=user_id,
            business_id=business_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )
    
    def log_login(
        self,
        user_id: int,
        business_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        description: Optional[str] = None,
    ) -> AuditLog:
        """
        Log a user login attempt.
        
        Args:
            user_id: ID of the user who logged in
            business_id: ID of the business
            ip_address: IP address of the request
            user_agent: User agent string
            success: Whether the login was successful
            description: Optional description
        
        Returns:
            The created AuditLog instance
        """
        action = "login" if success else "login_failed"
        
        if not description:
            description = "Login successful" if success else "Login failed"
        
        return self.log(
            action=action,
            entity_type="user",
            entity_id=user_id,
            user_id=user_id,
            business_id=business_id,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
        )
    
    def log_logout(
        self,
        user_id: int,
        business_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Log a user logout.
        
        Args:
            user_id: ID of the user who logged out
            business_id: ID of the business
            ip_address: IP address of the request
            user_agent: User agent string
        
        Returns:
            The created AuditLog instance
        """
        return self.log(
            action="logout",
            entity_type="user",
            entity_id=user_id,
            user_id=user_id,
            business_id=business_id,
            ip_address=ip_address,
            user_agent=user_agent,
            description="User logged out",
        )
    
    def log_export(
        self,
        entity_type: str,
        export_format: str,
        record_count: int,
        user_id: Optional[int] = None,
        business_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Log a data export.
        
        Args:
            entity_type: Type of data exported
            export_format: Format of export (csv, pdf, excel, etc.)
            record_count: Number of records exported
            user_id: ID of the user who performed the export
            business_id: ID of the business
            ip_address: IP address of the request
            user_agent: User agent string
            filters: Filters applied to the export
        
        Returns:
            The created AuditLog instance
        """
        metadata = {
            "export_format": export_format,
            "record_count": record_count,
            "filters": filters,
        }
        
        return self.log(
            action="export",
            entity_type=entity_type,
            entity_id=0,  # No specific entity
            user_id=user_id,
            business_id=business_id,
            ip_address=ip_address,
            user_agent=user_agent,
            description=f"Exported {record_count} {entity_type} records as {export_format}",
            metadata=metadata,
        )
    
    @staticmethod
    def _entity_to_dict(entity: Any, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Convert an entity to a dictionary.
        
        Args:
            entity: The entity to convert
            fields: Optional list of fields to include
        
        Returns:
            Dictionary representation of the entity
        """
        result = {}
        
        # Get all columns from the entity
        if hasattr(entity, '__table__'):
            for column in entity.__table__.columns:
                field_name = column.name
                if fields and field_name not in fields:
                    continue
                
                value = getattr(entity, field_name, None)
                
                # Skip sensitive fields
                if field_name in ['password_hash', 'password_reset_token', 'email_verification_token']:
                    continue
                
                # Handle special types
                if hasattr(value, 'value'):  # Enum
                    result[field_name] = value.value
                elif hasattr(value, 'isoformat'):  # datetime
                    result[field_name] = value.isoformat()
                else:
                    result[field_name] = value
        
        return result


def get_request_context(request: Optional[Request]) -> Dict[str, str]:
    """
    Extract IP address and user agent from a FastAPI request.
    
    Args:
        request: The FastAPI request object
    
    Returns:
        Dictionary with ip_address and user_agent
    """
    if not request:
        return {"ip_address": None, "user_agent": None}
    
    # Get IP address (handle proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        real_ip = request.headers.get("X-Real-IP")
        ip_address = real_ip or (request.client.host if request.client else None)
    
    # Get user agent
    user_agent = request.headers.get("User-Agent", "")[:500]
    
    return {
        "ip_address": ip_address,
        "user_agent": user_agent,
    }


# Convenience function for direct use
def log_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int,
    user_id: Optional[int] = None,
    business_id: Optional[int] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Convenience function for creating audit logs.
    
    Usage:
        log_audit(
            db=db,
            action="update",
            entity_type="waybill",
            entity_id=waybill.id,
            user_id=current_user.id,
            old_values={"status": "pending"},
            new_values={"status": "delivered"},
            description="Waybill delivered"
        )
    """
    service = AuditService(db)
    return service.log(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        business_id=business_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
        description=description,
        metadata=metadata,
    )
