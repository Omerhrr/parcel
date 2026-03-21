"""
Audit Log Model - Tracks all system changes
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import json

from app.database import Base


class AuditLog(Base):
    """
    AuditLog entity - records all changes in the system.
    Tracks CRUD operations with before/after values.
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Multi-tenant
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Who made the change
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # What action was performed
    action = Column(String(50), nullable=False, index=True)  # create, update, delete, status_change, etc.
    
    # What entity was affected
    entity_type = Column(String(100), nullable=False, index=True)  # waybill, order, delivery, agent, user, etc.
    entity_id = Column(Integer, nullable=False, index=True)
    
    # Before and after values (JSON)
    old_values = Column(Text, nullable=True)  # JSON string of values before change
    new_values = Column(Text, nullable=True)  # JSON string of values after change
    
    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    
    # Additional metadata
    description = Column(Text, nullable=True)  # Human-readable description of the change
    extra_data = Column(Text, nullable=True)  # Additional JSON metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", backref="audit_logs")
    business = relationship("Business", backref="audit_logs")
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_audit_logs_entity_type_id', 'entity_type', 'entity_id'),
        Index('ix_audit_logs_business_timestamp', 'business_id', 'timestamp'),
        Index('ix_audit_logs_user_timestamp', 'user_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', entity='{self.entity_type}:{self.entity_id}')>"
    
    @property
    def old_values_dict(self) -> dict:
        """Get old values as dictionary"""
        if not self.old_values:
            return {}
        try:
            return json.loads(self.old_values)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @property
    def new_values_dict(self) -> dict:
        """Get new values as dictionary"""
        if not self.new_values:
            return {}
        try:
            return json.loads(self.new_values)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @property
    def extra_data_dict(self) -> dict:
        """Get extra_data as dictionary"""
        if not self.extra_data:
            return {}
        try:
            return json.loads(self.extra_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_old_values(self, values: dict):
        """Set old values from dictionary"""
        if values:
            # Convert non-serializable values
            serializable = self._make_serializable(values)
            self.old_values = json.dumps(serializable, default=str)
    
    def set_new_values(self, values: dict):
        """Set new values from dictionary"""
        if values:
            serializable = self._make_serializable(values)
            self.new_values = json.dumps(serializable, default=str)
    
    def set_extra_data(self, values: dict):
        """Set extra_data from dictionary"""
        if values:
            serializable = self._make_serializable(values)
            self.extra_data = json.dumps(serializable, default=str)
    
    @staticmethod
    def _make_serializable(values: dict) -> dict:
        """Convert non-serializable values to serializable format"""
        result = {}
        for key, value in values.items():
            if hasattr(value, 'value'):  # Enum
                result[key] = value.value
            elif hasattr(value, 'isoformat'):  # datetime
                result[key] = value.isoformat()
            elif isinstance(value, (int, float, str, bool, type(None))):
                result[key] = value
            elif isinstance(value, dict):
                result[key] = AuditLog._make_serializable(value)
            elif isinstance(value, (list, tuple)):
                result[key] = [AuditLog._make_serializable({'item': v})['item'] if isinstance(v, dict) else str(v) for v in value]
            else:
                result[key] = str(value)
        return result
    
    def get_diff(self) -> dict:
        """
        Get the differences between old and new values.
        Returns a dict with 'added', 'removed', and 'changed' keys.
        """
        old = self.old_values_dict
        new = self.new_values_dict
        
        diff = {
            'added': {},
            'removed': {},
            'changed': {}
        }
        
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            if key not in old:
                diff['added'][key] = new[key]
            elif key not in new:
                diff['removed'][key] = old[key]
            elif old[key] != new[key]:
                diff['changed'][key] = {
                    'old': old[key],
                    'new': new[key]
                }
        
        return diff
    
    def get_action_display(self) -> str:
        """Get human-readable action name"""
        action_map = {
            'create': 'Created',
            'update': 'Updated',
            'delete': 'Deleted',
            'status_change': 'Status Changed',
            'assign': 'Assigned',
            'unassign': 'Unassigned',
            'login': 'Logged In',
            'logout': 'Logged Out',
            'password_change': 'Password Changed',
            'role_change': 'Role Changed',
            'export': 'Exported',
            'import': 'Imported',
        }
        return action_map.get(self.action, self.action.replace('_', ' ').title())
    
    def get_entity_display(self) -> str:
        """Get human-readable entity name"""
        entity_map = {
            'waybill': 'Waybill',
            'order': 'Order',
            'delivery': 'Delivery',
            'agent': 'Agent',
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
        return entity_map.get(self.entity_type, self.entity_type.replace('_', ' ').title())
