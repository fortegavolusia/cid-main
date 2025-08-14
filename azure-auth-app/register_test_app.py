#!/usr/bin/env python3
"""
Quick script to register the test app directly for testing purposes
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_registration import app_store, RegisterAppRequest

# Register the Flask test app
request = RegisterAppRequest(
    name="Flask Test App",
    description="Simple Flask app for testing auth integration",
    redirect_uris=["http://localhost:5000/auth/callback"],
    owner_email="test@company.com"
)

app_data, client_secret = app_store.register_app(request)

print("Test app registered successfully!")
print(f"Client ID: {app_data['client_id']}")
print(f"Client Secret: {client_secret}")
print()
print("Add these to your .env file:")
print(f"TEST_APP_CLIENT_ID={app_data['client_id']}")
print(f"TEST_APP_CLIENT_SECRET={client_secret}")

# Write to .env file if it doesn't exist or append if it does
env_file = ".env"
env_content = f"\n# Test App Credentials\nTEST_APP_CLIENT_ID={app_data['client_id']}\nTEST_APP_CLIENT_SECRET={client_secret}\n"

if os.path.exists(env_file):
    with open(env_file, 'a') as f:
        f.write(env_content)
    print(f"\nCredentials appended to {env_file}")
else:
    with open(env_file, 'w') as f:
        f.write(env_content)
    print(f"\nCredentials written to new {env_file}")

# Also set up some test role mappings
app_store.set_role_mappings(
    app_data['client_id'],
    {
        "Domain Users": "viewer",
        "Engineering": "editor"
    },
    "test_script"
)

print("\nRole mappings configured:")
print("- Domain Users → viewer")
print("- Engineering → editor")