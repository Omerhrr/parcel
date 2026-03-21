#!/usr/bin/env python3
"""
Seed script to create demo data for ParcelFlow
Run this to create a demo business and admin user
"""
import sys
import os

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models.user import User
from app.models.business import Business
from app.models.branch import Branch
from app.models.role import Role, Permission, role_permissions
from app.services.rbac import initialize_rbac


def seed_database():
    """Seed the database with demo data"""
    # Initialize database tables first
    print("Initializing database...")
    init_db()
    
    db = SessionLocal()
    
    try:
        # Initialize RBAC first
        print("Initializing RBAC...")
        initialize_rbac()
        
        # Check if demo business already exists
        existing = db.query(Business).filter(Business.slug == "demo-logistics").first()
        if existing:
            print("Demo data already exists!")
            print(f"  Business: {existing.name}")
            admin = db.query(User).filter(User.business_id == existing.id).first()
            if admin:
                print(f"  Admin: {admin.email}")
            return
        
        # Create demo business
        print("Creating demo business...")
        business = Business(
            name="Demo Logistics Ltd",
            slug="demo-logistics",
            email="info@demologistics.com",
            phone="+234-801-234-5678",
            address="123 Logistics Way",
            city="Lagos",
            country="Nigeria",
            plan="professional",
            status="active"
        )
        db.add(business)
        db.flush()
        
        # Create main branch
        print("Creating main branch...")
        branch = Branch(
            business_id=business.id,
            name="Lagos Headquarters",
            code="LOS-HQ",
            address="123 Logistics Way, Victoria Island",
            city="Lagos",
            state="Lagos",
            country="Nigeria",
            is_headquarters=1,
            currency="NGN",
            timezone="Africa/Lagos"
        )
        db.add(branch)
        db.flush()
        
        # Get admin role
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        
        # Create admin user
        print("Creating admin user...")
        admin = User(
            business_id=business.id,
            branch_id=branch.id,
            name="Admin User",
            email="admin@demo.com",
            phone="+234-801-234-5679",
            status="active",
            is_verified=True
        )
        admin.set_password("admin123")
        if admin_role:
            admin.roles.append(admin_role)
        db.add(admin)
        
        # Create additional demo users
        print("Creating additional users...")
        
        # Manager
        manager_role = db.query(Role).filter(Role.name == "manager").first()
        manager = User(
            business_id=business.id,
            branch_id=branch.id,
            name="John Manager",
            email="manager@demo.com",
            phone="+234-801-234-5680",
            status="active",
            is_verified=True
        )
        manager.set_password("manager123")
        if manager_role:
            manager.roles.append(manager_role)
        db.add(manager)
        
        # Dispatcher
        dispatcher_role = db.query(Role).filter(Role.name == "dispatcher").first()
        dispatcher = User(
            business_id=business.id,
            branch_id=branch.id,
            name="Jane Dispatcher",
            email="dispatcher@demo.com",
            phone="+234-801-234-5681",
            status="active",
            is_verified=True
        )
        dispatcher.set_password("dispatcher123")
        if dispatcher_role:
            dispatcher.roles.append(dispatcher_role)
        db.add(dispatcher)
        
        db.commit()
        
        print("\n" + "="*50)
        print("✅ Demo data created successfully!")
        print("="*50)
        print("\n📋 Demo Business:")
        print(f"   Name: {business.name}")
        print(f"   Slug: {business.slug}")
        print(f"   Plan: {business.plan}")
        print("\n👤 Demo Users:")
        print("   ┌──────────────────────────────────────────────┐")
        print("   │ Admin User                                   │")
        print("   │   Email: admin@demo.com                      │")
        print("   │   Password: admin123                         │")
        print("   ├──────────────────────────────────────────────┤")
        print("   │ Manager                                      │")
        print("   │   Email: manager@demo.com                    │")
        print("   │   Password: manager123                       │")
        print("   ├──────────────────────────────────────────────┤")
        print("   │ Dispatcher                                   │")
        print("   │   Email: dispatcher@demo.com                 │")
        print("   │   Password: dispatcher123                    │")
        print("   └──────────────────────────────────────────────┘")
        print("\n🚀 You can now login at: http://localhost:5000/auth/login")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
