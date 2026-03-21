"""
RBAC Service - Initialize roles and permissions
ParcelFlow - Multi-tenant Logistics Platform
"""
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.role import Role, Permission, DEFAULT_ROLES, ALL_PERMISSIONS


def initialize_rbac():
    """
    Initialize default roles and permissions.
    Should be called on application startup.
    """
    db: Session = SessionLocal()

    try:
        # Create permissions if they don't exist
        for perm_data in ALL_PERMISSIONS:
            existing = db.query(Permission).filter(
                Permission.name == perm_data["name"]
            ).first()

            if not existing:
                permission = Permission(
                    name=perm_data["name"],
                    display_name=perm_data["display_name"],
                    module=perm_data.get("module")
                )
                db.add(permission)

        db.commit()

        # Create or update roles
        for role_data in DEFAULT_ROLES:
            existing = db.query(Role).filter(
                Role.name == role_data["name"]
            ).first()

            if not existing:
                role = Role(
                    name=role_data["name"],
                    display_name=role_data["display_name"],
                    description=role_data.get("description"),
                    is_system=role_data.get("is_system", 0)
                )
                db.add(role)
                db.flush()

                # Assign permissions
                if role_data.get("permissions") == ["*"]:
                    # Assign the wildcard permission to super_admin
                    wildcard_perm = db.query(Permission).filter(
                        Permission.name == "*"
                    ).first()
                    if wildcard_perm:
                        role.permissions = [wildcard_perm]
                    else:
                        # Fallback: assign all permissions if * doesn't exist
                        all_perms = db.query(Permission).all()
                        role.permissions = all_perms
                else:
                    # Specific permissions
                    for perm_name in role_data.get("permissions", []):
                        # Handle wildcard permissions like "orders.*"
                        if perm_name.endswith(".*"):
                            module = perm_name.replace(".*", "")
                            perms = db.query(Permission).filter(
                                Permission.name.like(f"{module}.%")
                            ).all()
                            role.permissions.extend(perms)
                        else:
                            perm = db.query(Permission).filter(
                                Permission.name == perm_name
                            ).first()
                            if perm:
                                role.permissions.append(perm)
            else:
                # Update existing role permissions
                # Clear existing permissions and re-assign based on config
                if role_data.get("permissions") == ["*"]:
                    # Assign the wildcard permission to super_admin
                    wildcard_perm = db.query(Permission).filter(
                        Permission.name == "*"
                    ).first()
                    if wildcard_perm:
                        existing.permissions = [wildcard_perm]
                    else:
                        # Fallback: assign all permissions if * doesn't exist
                        all_perms = db.query(Permission).all()
                        existing.permissions = all_perms
                else:
                    # Clear and re-assign specific permissions
                    existing.permissions = []
                    for perm_name in role_data.get("permissions", []):
                        # Handle wildcard permissions like "orders.*"
                        if perm_name.endswith(".*"):
                            module = perm_name.replace(".*", "")
                            perms = db.query(Permission).filter(
                                Permission.name.like(f"{module}.%")
                            ).all()
                            existing.permissions.extend(perms)
                        else:
                            perm = db.query(Permission).filter(
                                Permission.name == perm_name
                            ).first()
                            if perm:
                                existing.permissions.append(perm)

        db.commit()
        # RBAC initialization complete - roles and permissions ready

    except Exception as e:
        print(f"Error initializing RBAC: {e}")
        db.rollback()
    finally:
        db.close()
