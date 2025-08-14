#!/usr/bin/env python3
"""Check registered apps in the app store"""
import requests
import json

# First, let's check the API directly
try:
    # Get admin token from the session (you'll need to be logged in)
    print("Checking registered apps via API...")
    
    # Try to fetch from the API endpoint
    response = requests.get(
        "https://localhost:8000/auth/admin/apps",
        verify=False,
        headers={
            "Authorization": "Bearer YOUR_TOKEN_HERE"  # Would need actual token
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.ok:
        apps = response.json()
        print(f"Found {len(apps)} registered apps:")
        for app in apps:
            print(f"  - {app['name']} (Client ID: {app['client_id']})")
    else:
        print("Failed to fetch apps - need valid admin token")
        
except Exception as e:
    print(f"Error: {e}")

# Let's also check if we can access the app store directly
print("\nChecking app store directly...")
try:
    import sys
    sys.path.append('/home/jnbailey/Desktop/CIDS/azure-auth-app')
    from app_registration import app_store, registered_apps
    
    print(f"Apps in memory: {len(registered_apps)}")
    for client_id, app in registered_apps.items():
        print(f"  - {app['name']} (Client ID: {client_id})")
        print(f"    Active: {app['is_active']}")
        print(f"    Created: {app['created_at']}")
except Exception as e:
    print(f"Error accessing app store: {e}")