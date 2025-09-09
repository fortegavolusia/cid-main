#!/usr/bin/env python3
"""Test script for roles service with database integration"""

import sys
import os
sys.path.insert(0, '/home/dpi/projects/CID/backend')

from services.database import db_service
from services.roles import RolesManager, RolesUpdate, Role

def test_roles_service(test_app_id):
    print("🧪 Testing Roles Service with Database Integration")
    print("=" * 50)
    
    # Initialize roles manager
    roles_manager = RolesManager()
    
    print(f"Using app ID: {test_app_id}")
    
    print("\n1️⃣ Testing role creation/update...")
    try:
        # Create test roles
        update = RolesUpdate(roles=[
            Role(name="Admin", description="Administrator role with full access", permissions=["users.read", "users.write", "users.delete"]),
            Role(name="Viewer", description="Read-only access", permissions=["users.read"]),
            Role(name="Editor", description="Can edit but not delete", permissions=["users.read", "users.write"])
        ])
        
        result = roles_manager.upsert_app_roles(test_app_id, update, "test_user@example.com")
        print(f"✅ Created/Updated {result['roles_count']} roles for app {result['app_client_id']}")
        print(f"   Updated at: {result['updated_at']}")
    except Exception as e:
        print(f"❌ Error creating roles: {e}")
        return False
    
    print("\n2️⃣ Testing role retrieval...")
    try:
        app_roles = roles_manager.get_app_roles(test_app_id)
        if app_roles:
            print(f"✅ Retrieved {len(app_roles['roles'])} roles:")
            for role in app_roles['roles']:
                print(f"   - {role['name']}: {role['description']}")
                print(f"     Permissions: {', '.join(role['permissions']) if role['permissions'] else 'None'}")
        else:
            print("❌ No roles found")
    except Exception as e:
        print(f"❌ Error retrieving roles: {e}")
        return False
    
    print("\n3️⃣ Testing direct database queries...")
    try:
        # Test getting roles directly from database
        db_roles = db_service.get_roles_by_client(test_app_id)
        print(f"✅ Direct DB query returned {len(db_roles)} roles")
        
        if db_roles:
            for role in db_roles:
                print(f"   - Role ID: {role['role_id']}, Name: {role['role_name']}")
                
                # Get permissions for this role
                permissions = db_service.get_permissions_by_role(role['role_id'])
                print(f"     Permissions count: {len(permissions)}")
    except Exception as e:
        print(f"❌ Error with direct DB query: {e}")
        return False
    
    print("\n4️⃣ Testing role permissions retrieval...")
    try:
        admin_perms = roles_manager.get_role_permissions(test_app_id, "Admin")
        print(f"✅ Admin role has {len(admin_perms)} permissions:")
        for perm in admin_perms:
            print(f"   - {perm}")
    except Exception as e:
        print(f"❌ Error getting role permissions: {e}")
        return False
    
    print("\n5️⃣ Testing user role mapping (simulated)...")
    try:
        # Simulate AD groups
        test_ad_groups = ["IT_Admins", "All_Users"]
        
        # First, update a role to have AD groups
        role = db_service.get_role(test_app_id, "Admin")
        if role:
            db_service.update_role(test_app_id, "Admin", {"ad_groups": ["IT_Admins"]})
            print("✅ Updated Admin role with AD group 'IT_Admins'")
        
        # Now test getting user roles
        user_roles = roles_manager.get_user_roles(test_ad_groups)
        print(f"✅ User with groups {test_ad_groups} has roles in {len(user_roles)} apps:")
        for app_id, roles in user_roles.items():
            print(f"   - App {app_id}: {', '.join(roles)}")
    except Exception as e:
        print(f"❌ Error with user role mapping: {e}")
        return False
    
    print("\n✅ All tests completed successfully!")
    return True

if __name__ == "__main__":
    # Test database connection first
    print("📊 Testing database connection...")
    if db_service.connect():
        print("✅ Database connected successfully")
        
        # Check if we have the test app
        apps = db_service.get_all_registered_apps()
        print(f"Found {len(apps)} registered apps")
        
        if apps:
            # Use the first app for testing
            test_app_id = apps[0]['client_id']
            print(f"Using app '{apps[0]['name']}' (ID: {test_app_id}) for testing")
            
            success = test_roles_service(test_app_id)
            sys.exit(0 if success else 1)
        else:
            print("❌ No apps found in database. Please register an app first.")
            sys.exit(1)
    else:
        print("❌ Failed to connect to database")
        sys.exit(1)