#!/usr/bin/env python3
"""
Registration script for FastAPI Test App with CIDS

This script:
1. Registers the FastAPI app with CIDS
2. Saves credentials to .env file
3. Sets up role mappings
"""

import os
import sys
import json
import re
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_registration import AppStore, AppRegistrationRequest

# Initialize app store
store = AppStore()

# Create registration request for FastAPI app
request = AppRegistrationRequest(
    name="FastAPI Test App",
    description="FastAPI application demonstrating CIDS integration with field-level permissions",
    redirect_uris=[
        "http://localhost:5001/auth/callback",
        "http://10.1.5.58:5001/auth/callback"
    ],
    owner_email="admin@company.com",
    discovery_endpoint="http://10.1.5.58:5001/discovery/endpoints",
    allow_discovery=True
)

# Register the app
print("Registering FastAPI Test App with CIDS...")
app_data, client_secret = store.register_app(request)

print("\n✅ FastAPI Test App registered successfully!")
print(f"Client ID: {app_data['client_id']}")
print(f"Client Secret: {client_secret}")

# Update or create .env file
env_file = Path('.env')
env_content = f"""
# FastAPI Test App Credentials
FASTAPI_CLIENT_ID={app_data['client_id']}
FASTAPI_CLIENT_SECRET={client_secret}

# CIDS Configuration
CIDS_URL=http://localhost:8000
APP_URL=http://localhost:5001
"""

if env_file.exists():
    # Read existing content
    with open(env_file, 'r') as f:
        existing_content = f.read()
    
    # Update or append FastAPI credentials
    if 'FASTAPI_CLIENT_ID' in existing_content:
        # Update existing values
        existing_content = re.sub(
            r'FASTAPI_CLIENT_ID=.*', 
            f"FASTAPI_CLIENT_ID={app_data['client_id']}", 
            existing_content
        )
        existing_content = re.sub(
            r'FASTAPI_CLIENT_SECRET=.*', 
            f"FASTAPI_CLIENT_SECRET={client_secret}", 
            existing_content
        )
        with open(env_file, 'w') as f:
            f.write(existing_content)
        print("\n✅ Updated existing .env file with new credentials")
    else:
        # Append to existing file
        with open(env_file, 'a') as f:
            f.write(env_content)
        print("\n✅ Added FastAPI credentials to existing .env file")
else:
    # Create new file
    with open(env_file, 'w') as f:
        f.write(env_content)
    print("\n✅ Created .env file with credentials")

# Set up sample role mappings
print("\n📋 Setting up role mappings...")

# Define role mappings (you should customize these based on your AD groups)
role_mappings = [
    {
        "ad_group": "All Users",
        "app_role": "viewer",
        "description": "Basic read access to non-sensitive fields"
    },
    {
        "ad_group": "Finance Team",
        "app_role": "finance_user",
        "description": "Access to cost and profit margin data"
    },
    {
        "ad_group": "Procurement Team",
        "app_role": "procurement_user",
        "description": "Access to supplier information"
    },
    {
        "ad_group": "Administrators",
        "app_role": "admin",
        "description": "Full access to all fields"
    }
]

# Save role mappings
from app_registration import app_role_mappings, save_data

app_role_mappings[app_data['client_id']] = role_mappings
save_data()

print("✅ Role mappings configured:")
for mapping in role_mappings:
    print(f"   - {mapping['ad_group']} → {mapping['app_role']}")

print("\n" + "="*60)
print("🎉 FastAPI App Registration Complete!")
print("="*60)

print("""
Next steps:

1. Install FastAPI dependencies:
   pip install fastapi uvicorn httpx python-jose[cryptography] python-dotenv jinja2

2. Start the FastAPI app:
   uvicorn fastapi_test_app:app --reload --port 5001

3. Configure permissions in CIDS:
   - Run discovery to detect endpoints and fields
   - Create permission roles (e.g., finance_user gets access to cost fields)
   - Map AD groups to roles

4. Test the authentication flow:
   - Open http://localhost:5001
   - Click "Login with CIDS"
   - Authenticate with Azure AD
   - View filtered product data based on permissions

5. API Testing:
   The app exposes these endpoints:
   - GET  /discovery/endpoints - Field metadata (no auth)
   - GET  /api/products - List products (filtered by permissions)
   - GET  /api/products/{id} - Get product (filtered by permissions)
   - POST /api/products - Create product (requires write permissions)

Note: The app demonstrates field-level filtering where sensitive fields
(cost, supplier, profit_margin) require specific permissions to view.
""")

print(f"\n📁 Credentials saved to: {env_file.absolute()}")
print("⚠️  Keep the client secret secure and never commit it to version control!")