"""
Role and Permission Models for RBAC
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from typing import List

from app.database import Base
from app.models.base import TimestampMixin


# Many-to-Many relationship table for Role-Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True),
)


# Many-to-Many relationship table for User-Role (for users with multiple roles)
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True),
)


class Role(Base, TimestampMixin):
    """
    Role entity - defines a set of permissions.
    Roles are either system-defined (global) or business-specific.
    """
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # System roles cannot be modified/deleted by business admins
    is_system = Column(Integer, default=0)  # 0 = Business role, 1 = System role
    
    # Relationships
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin"
    )
    users = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles"
    )
    
    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if role has a specific permission"""
        return any(p.name == permission_name for p in self.permissions)
    
    def get_permission_names(self) -> List[str]:
        """Get list of permission names"""
        return [p.name for p in self.permissions]


class Permission(Base, TimestampMixin):
    """
    Permission entity - defines a specific action/ability in the system.
    Permissions follow a naming convention: resource.action
    """
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    
    # Grouping for UI organization
    module = Column(String(50), nullable=True)  # e.g., "users", "orders", "inventory"
    
    # Relationships
    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions"
    )
    
    def __repr__(self):
        return f"<Permission(id={self.id}, name='{self.name}')>"


class RolePermission(Base):
    """Explicit model for the role_permissions junction table"""
    __tablename__ = "role_permissions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)


# Default roles configuration
DEFAULT_ROLES = [
    {
        "name": "super_admin",
        "display_name": "Super Administrator",
        "description": "Full system access across all businesses",
        "is_system": 1,
        "permissions": ["*"]  # All permissions
    },
    {
        "name": "admin",
        "display_name": "Business Administrator",
        "description": "Full access within their business",
        "is_system": 1,
        "permissions": [
            "users.create", "users.update", "users.delete", "users.view",
            "branches.create", "branches.update", "branches.view",
            "orders.*", "inventory.*", "warehouses.*", "vendors.*", "agents.*",
            "deliveries.*", "accounting.*", "settings.*"
        ]
    },
    {
        "name": "manager",
        "display_name": "Branch Manager",
        "description": "Manage operations within assigned branch",
        "is_system": 1,
        "permissions": [
            "users.view", "users.update",
            "orders.view", "orders.update", "orders.assign",
            "inventory.view", "inventory.update",
            "deliveries.view", "deliveries.assign",
            "agents.view", "accounting.view"
        ]
    },
    {
        "name": "sales_agent",
        "display_name": "Sales Agent",
        "description": "Create and manage orders and leads",
        "is_system": 1,
        "permissions": [
            "orders.create", "orders.view", "orders.update",
            "leads.*", "customers.view"
        ]
    },
    {
        "name": "dispatcher",
        "display_name": "Dispatcher",
        "description": "Assign and manage deliveries",
        "is_system": 1,
        "permissions": [
            "orders.view", "orders.assign",
            "deliveries.*", "agents.view"
        ]
    },
    {
        "name": "warehouse_staff",
        "display_name": "Warehouse Staff",
        "description": "Manage inventory and warehouse operations",
        "is_system": 1,
        "permissions": [
            "inventory.*", "warehouse.*",
            "orders.view", "deliveries.view"
        ]
    },
    {
        "name": "viewer",
        "display_name": "Viewer",
        "description": "Read-only access to most modules",
        "is_system": 1,
        "permissions": [
            "orders.view", "inventory.view", "deliveries.view",
            "vendors.view", "agents.view", "accounting.view"
        ]
    },
    {
        "name": "vendor_user",
        "display_name": "Vendor User",
        "description": "Limited access for vendor partners",
        "is_system": 1,
        "permissions": [
            "vendors.view_own", "inventory.view_own",
            "orders.view_own", "deliveries.view_own",
            "remittances.view_own"
        ]
    }
]


# All permissions in the system
ALL_PERMISSIONS = [
    # Wildcard permission for super admins
    {"name": "*", "display_name": "All Permissions", "module": "system"},

    # Users
    {"name": "users.create", "display_name": "Create Users", "module": "users"},
    {"name": "users.view", "display_name": "View Users", "module": "users"},
    {"name": "users.update", "display_name": "Update Users", "module": "users"},
    {"name": "users.delete", "display_name": "Delete Users", "module": "users"},
    
    # Branches
    {"name": "branches.create", "display_name": "Create Branches", "module": "branches"},
    {"name": "branches.view", "display_name": "View Branches", "module": "branches"},
    {"name": "branches.update", "display_name": "Update Branches", "module": "branches"},
    {"name": "branches.delete", "display_name": "Delete Branches", "module": "branches"},
    
    # Warehouses
    {"name": "warehouses.create", "display_name": "Create Warehouses", "module": "warehouses"},
    {"name": "warehouses.view", "display_name": "View Warehouses", "module": "warehouses"},
    {"name": "warehouses.update", "display_name": "Update Warehouses", "module": "warehouses"},
    {"name": "warehouses.delete", "display_name": "Delete Warehouses", "module": "warehouses"},
    
    # Orders
    {"name": "orders.create", "display_name": "Create Orders", "module": "orders"},
    {"name": "orders.view", "display_name": "View Orders", "module": "orders"},
    {"name": "orders.update", "display_name": "Update Orders", "module": "orders"},
    {"name": "orders.delete", "display_name": "Delete Orders", "module": "orders"},
    {"name": "orders.assign", "display_name": "Assign Orders", "module": "orders"},
    {"name": "orders.view_own", "display_name": "View Own Orders", "module": "orders"},
    
    # Inventory
    {"name": "inventory.create", "display_name": "Create Inventory", "module": "inventory"},
    {"name": "inventory.view", "display_name": "View Inventory", "module": "inventory"},
    {"name": "inventory.update", "display_name": "Update Inventory", "module": "inventory"},
    {"name": "inventory.delete", "display_name": "Delete Inventory", "module": "inventory"},
    {"name": "inventory.view_own", "display_name": "View Own Inventory", "module": "inventory"},
    
    # Vendors
    {"name": "vendors.create", "display_name": "Create Vendors", "module": "vendors"},
    {"name": "vendors.view", "display_name": "View Vendors", "module": "vendors"},
    {"name": "vendors.update", "display_name": "Update Vendors", "module": "vendors"},
    {"name": "vendors.delete", "display_name": "Delete Vendors", "module": "vendors"},
    {"name": "vendors.manage", "display_name": "Manage Vendors", "module": "vendors"},
    {"name": "vendors.view_own", "display_name": "View Own Vendor Profile", "module": "vendors"},
    
    # Agents
    {"name": "agents.create", "display_name": "Create Agents", "module": "agents"},
    {"name": "agents.view", "display_name": "View Agents", "module": "agents"},
    {"name": "agents.update", "display_name": "Update Agents", "module": "agents"},
    {"name": "agents.delete", "display_name": "Delete Agents", "module": "agents"},
    {"name": "agents.manage", "display_name": "Manage Agents", "module": "agents"},
    
    # Deliveries
    {"name": "deliveries.create", "display_name": "Create Deliveries", "module": "deliveries"},
    {"name": "deliveries.view", "display_name": "View Deliveries", "module": "deliveries"},
    {"name": "deliveries.update", "display_name": "Update Deliveries", "module": "deliveries"},
    {"name": "deliveries.assign", "display_name": "Assign Deliveries", "module": "deliveries"},
    {"name": "deliveries.view_own", "display_name": "View Own Deliveries", "module": "deliveries"},
    
    # Warehouse operations
    {"name": "warehouse.view", "display_name": "View Warehouse", "module": "warehouse"},
    {"name": "warehouse.update", "display_name": "Update Warehouse", "module": "warehouse"},
    
    # Accounting
    {"name": "accounting.view", "display_name": "View Accounting", "module": "accounting"},
    {"name": "accounting.update", "display_name": "Update Accounting", "module": "accounting"},
    {"name": "remittances.view_own", "display_name": "View Own Remittances", "module": "accounting"},
    
    # Settings
    {"name": "settings.view", "display_name": "View Settings", "module": "settings"},
    {"name": "settings.update", "display_name": "Update Settings", "module": "settings"},
    
    # Leads
    {"name": "leads.create", "display_name": "Create Leads", "module": "leads"},
    {"name": "leads.view", "display_name": "View Leads", "module": "leads"},
    {"name": "leads.update", "display_name": "Update Leads", "module": "leads"},
    {"name": "leads.delete", "display_name": "Delete Leads", "module": "leads"},
    
    # Customers
    {"name": "customers.view", "display_name": "View Customers", "module": "customers"},
    {"name": "customers.create", "display_name": "Create Customers", "module": "customers"},
    {"name": "customers.update", "display_name": "Update Customers", "module": "customers"},
]
