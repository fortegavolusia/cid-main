#!/usr/bin/env python3
"""Register app via API with admin token"""
import requests
import json
import sys
from dotenv import load_dotenv
import os

load_dotenv()

# Disable SSL warnings for local dev
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_admin_token():
    """Get an admin token by creating a test token"""
    # This would normally require actual login, but for testing we can use the test endpoint
    print("Note: You need to manually get an admin token from your browser session")
    print("1. Login to https://localhost:8000")
    print("2. Open browser dev tools (F12)")
    print("3. Go to Application/Storage → Cookies")
    print("4. Find 'internal_token' cookie value")
    print("5. Or go to https://localhost:8000/auth/my-token and copy the token")
    return None

def register_app_via_api(token):
    """Register the Flask test app via API"""
    
    url = "https://localhost:8000/auth/admin/apps"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": "Flask Test App",
        "description": "Simple Flask app for testing auth integration",
        "redirect_uris": ["http://localhost:5000/auth/callback"],
        "owner_email": "test@company.com"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, verify=False)
        
        if response.ok:
            result = response.json()
            print("App registered successfully!")
            print(f"Client ID: {result['app']['client_id']}")
            print(f"Client Secret: {result['client_secret']}")
            
            # Update .env file
            with open('.env', 'r') as f:
                content = f.read()
            
            # Replace existing values
            import re
            content = re.sub(r'TEST_APP_CLIENT_ID=.*', f"TEST_APP_CLIENT_ID={result['app']['client_id']}", content)
            content = re.sub(r'TEST_APP_CLIENT_SECRET=.*', f"TEST_APP_CLIENT_SECRET={result['client_secret']}", content)
            
            with open('.env', 'w') as f:
                f.write(content)
            
            print("\n.env file updated with new credentials")
            
            # Now set role mappings
            set_role_mappings(token, result['app']['client_id'])
            
        else:
            print(f"Failed to register app: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

def set_role_mappings(token, client_id):
    """Set role mappings for the app"""
    url = f"https://localhost:8000/auth/admin/apps/{client_id}/role-mappings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "mappings": {
            "Domain Users": "viewer",
            "Engineering": "editor",
            "IT Section Manager": "admin"  # You're in this group
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, verify=False)
        if response.ok:
            print("\nRole mappings configured:")
            for group, role in data['mappings'].items():
                print(f"  - {group} → {role}")
        else:
            print(f"Failed to set role mappings: {response.status_code}")
    except Exception as e:
        print(f"Error setting role mappings: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        token = sys.argv[1]
        register_app_via_api(token)
    else:
        print("Usage: python register_app_api.py YOUR_ADMIN_TOKEN")
        print("\nTo get your admin token:")
        print("1. Login to https://localhost:8000")  
        print("2. Go to https://localhost:8000/auth/my-token")
        print("3. Copy the 'access_token' value")
        print("4. Run: python register_app_api.py YOUR_TOKEN")