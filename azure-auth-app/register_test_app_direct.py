#!/usr/bin/env python3
"""Register the Flask test app directly in the app store"""
import sys
sys.path.append('/home/jnbailey/Desktop/CIDS/azure-auth-app')

from app_registration import AppRegistrationStore, RegisterAppRequest
import json

# Create the app registration store
store = AppRegistrationStore()

# Register the Flask test app
request = RegisterAppRequest(
    name="Flask Test App",
    description="Simple Flask app for testing auth integration",
    redirect_uris=["http://localhost:5000/auth/callback"],
    owner_email="test@company.com"
)

app_data, client_secret = store.register_app(request)

print("Flask Test App registered successfully!")
print(f"Client ID: {app_data['client_id']}")
print(f"Client Secret: {client_secret}")

# Update the .env file
try:
    with open('.env', 'r') as f:
        content = f.read()
    
    # Replace existing values
    import re
    content = re.sub(r'TEST_APP_CLIENT_ID=.*', f"TEST_APP_CLIENT_ID={app_data['client_id']}", content)
    content = re.sub(r'TEST_APP_CLIENT_SECRET=.*', f"TEST_APP_CLIENT_SECRET={client_secret}", content)
    
    with open('.env', 'w') as f:
        f.write(content)
    
    print("\n.env file updated with new credentials")
except Exception as e:
    print(f"\nError updating .env file: {e}")
    print("\nPlease update .env manually with:")
    print(f"TEST_APP_CLIENT_ID={app_data['client_id']}")
    print(f"TEST_APP_CLIENT_SECRET={client_secret}")

# Also set role mappings
print("\nSetting role mappings...")
mappings = {
    "Domain Users": "viewer",
    "Engineering": "editor", 
    "IT Section Manager": "admin"
}

if store.set_role_mappings(app_data['client_id'], mappings, "admin"):
    print("Role mappings configured:")
    for group, role in mappings.items():
        print(f"  - {group} → {role}")
else:
    print("Failed to set role mappings")

print("\nApp registration complete! Check the admin UI to see the registered app.")