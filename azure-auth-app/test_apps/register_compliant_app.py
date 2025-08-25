#!/usr/bin/env python3
"""
Registration helper for CIDS Compliant Test App
This script helps register the compliant app with CIDS and get an API key
"""

import httpx
import asyncio
import json
import sys
from typing import Optional

# Configuration
CIDS_BASE_URL = "http://localhost:8000"
APP_BASE_URL = "http://localhost:8001"

async def check_cids_connection():
    """Check if CIDS is running"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CIDS_BASE_URL}/")
        return response.status_code == 200
    except:
        return False

async def get_admin_token():
    """Get admin token (you need to be logged in as admin)"""
    print("\n📝 To register the app, you need admin access to CIDS")
    print("Please provide an admin access token from CIDS")
    print("(You can get this by logging into CIDS and checking localStorage)")
    token = input("\nEnter admin access token: ").strip()
    
    if not token:
        print("❌ No token provided")
        return None
    
    # Validate token
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CIDS_BASE_URL}/auth/validate",
                headers={"Authorization": f"Bearer {token}"}
            )
        if response.status_code == 200:
            print("✅ Token validated successfully")
            return token
        else:
            print("❌ Invalid token")
            return None
    except Exception as e:
        print(f"❌ Error validating token: {e}")
        return None

async def register_app(token: str):
    """Register the compliant app with CIDS"""
    app_data = {
        "name": "CIDS Compliant Test App",
        "description": "A fully CIDS-compliant test application demonstrating all features including discovery, field-level permissions, and RLS",
        "owner_email": "admin@example.com",
        "redirect_uris": [f"{APP_BASE_URL}/auth/callback"],
        "allow_discovery": True,
        "discovery_endpoint": f"{APP_BASE_URL}/discovery/endpoints"
    }
    
    print("\n📦 Registering app with CIDS...")
    print(f"   Name: {app_data['name']}")
    print(f"   Discovery: {app_data['discovery_endpoint']}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CIDS_BASE_URL}/auth/admin/apps",
                json=app_data,
                headers={"Authorization": f"Bearer {token}"}
            )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ App registered successfully!")
            print(f"   Client ID: {result['app']['client_id']}")
            print(f"   Client Secret: {result['client_secret']}")
            print("\n⚠️  SAVE THE CLIENT SECRET! It won't be shown again.")
            return result['app']['client_id'], result['client_secret']
        else:
            print(f"❌ Failed to register app: {response.text}")
            return None, None
    except Exception as e:
        print(f"❌ Error registering app: {e}")
        return None, None

async def create_api_key(token: str, client_id: str):
    """Create an API key for the app"""
    print("\n🔑 Creating API key for the app...")
    
    key_data = {
        "name": "Test Environment Key",
        "permissions": [
            "admin",  # Full admin access for testing
            "compliant_app.users.read",
            "compliant_app.users.read.*",
            "compliant_app.users.write",
            "compliant_app.users.delete",
            "compliant_app.orders.read",
            "compliant_app.orders.read.*",
            "compliant_app.reports.read",
            "compliant_app.reports.read.*"
        ],
        "ttl_days": 90
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CIDS_BASE_URL}/auth/admin/apps/{client_id}/api-keys",
                json=key_data,
                headers={"Authorization": f"Bearer {token}"}
            )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ API key created successfully!")
            print(f"\n🔑 API Key: {result['api_key']}")
            print("\n⚠️  SAVE THIS API KEY! It won't be shown again.")
            return result['api_key']
        else:
            print(f"❌ Failed to create API key: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating API key: {e}")
        return None

async def test_discovery(client_id: str):
    """Test the discovery endpoint"""
    print("\n🔍 Testing discovery endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Call CIDS to trigger discovery
            response = await client.post(
                f"{CIDS_BASE_URL}/discovery/endpoints/{client_id}",
                timeout=30.0
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Discovery successful!")
            print(f"   Status: {result.get('status')}")
            print(f"   Endpoints discovered: {result.get('endpoints_discovered', 0)}")
            print(f"   Endpoints stored: {result.get('endpoints_stored', 0)}")
            return True
        else:
            print(f"❌ Discovery failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error running discovery: {e}")
        return False

async def test_api_key(api_key: str):
    """Test the API key by making a request"""
    print("\n🧪 Testing API key...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test with CIDS validation
            response = await client.get(
                f"{CIDS_BASE_URL}/auth/validate",
                headers={"Authorization": f"Bearer {api_key}"}
            )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API key is valid!")
            print(f"   App: {result.get('app_client_id')}")
            print(f"   Auth type: {result.get('auth_type')}")
            print(f"   Permissions: {len(result.get('permissions', []))} permissions granted")
            
            # Now test with the actual app
            response = await client.get(
                f"{APP_BASE_URL}/api/users",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if response.status_code == 200:
                print("✅ Successfully accessed protected endpoint!")
                users = response.json().get('users', [])
                print(f"   Retrieved {len(users)} users")
            else:
                print(f"⚠️  Could not access app endpoint: {response.status_code}")
            
            return True
        else:
            print(f"❌ API key validation failed")
            return False
    except Exception as e:
        print(f"❌ Error testing API key: {e}")
        return False

async def save_configuration(client_id: str, client_secret: str, api_key: str):
    """Save configuration to .env file"""
    env_content = f"""# CIDS Compliant Test App Configuration
# Generated by register_compliant_app.py

# CIDS Configuration
CIDS_BASE_URL=http://localhost:8000
CIDS_CLIENT_ID={client_id}
CIDS_CLIENT_SECRET={client_secret}
CIDS_API_KEY={api_key}

# App Configuration
APP_PORT=8001
APP_BASE_URL=http://localhost:8001
"""
    
    env_file = "/home/jnbailey/Desktop/CIDS/azure-auth-app/test_apps/.env"
    
    try:
        with open(env_file, "w") as f:
            f.write(env_content)
        print(f"\n✅ Configuration saved to {env_file}")
        return True
    except Exception as e:
        print(f"⚠️  Could not save .env file: {e}")
        print("\n📋 Configuration to save manually:")
        print(env_content)
        return False

async def main():
    """Main registration flow"""
    print("=" * 60)
    print("CIDS COMPLIANT APP REGISTRATION")
    print("=" * 60)
    
    # Check CIDS connection
    print("\n🔌 Checking CIDS connection...")
    if not await check_cids_connection():
        print("❌ CIDS is not running at http://localhost:8000")
        print("   Please start CIDS first")
        return
    print("✅ CIDS is running")
    
    # Check if app is running
    print("\n🔌 Checking if compliant app is running...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{APP_BASE_URL}/")
        if response.status_code == 200:
            print("✅ Compliant app is running")
        else:
            print("⚠️  Compliant app may not be running properly")
    except:
        print("⚠️  Compliant app is not running at http://localhost:8001")
        print("   Start it with: python test_apps/compliant_app.py")
    
    # Get admin token
    token = await get_admin_token()
    if not token:
        print("\n❌ Cannot proceed without admin token")
        print("\nTo get an admin token:")
        print("1. Open CIDS in browser: http://localhost:5173")
        print("2. Log in as admin")
        print("3. Open browser console (F12)")
        print("4. Run: localStorage.getItem('access_token')")
        print("5. Copy the token and run this script again")
        return
    
    # Register app
    client_id, client_secret = await register_app(token)
    if not client_id:
        print("\n❌ App registration failed")
        return
    
    # Create API key
    api_key = await create_api_key(token, client_id)
    if not api_key:
        print("\n⚠️  API key creation failed, but app is registered")
        print(f"   You can create an API key manually in the admin portal")
        return
    
    # Save configuration
    await save_configuration(client_id, client_secret, api_key)
    
    # Test discovery
    print("\n" + "=" * 60)
    print("TESTING INTEGRATION")
    print("=" * 60)
    
    await test_discovery(client_id)
    await test_api_key(api_key)
    
    # Summary
    print("\n" + "=" * 60)
    print("REGISTRATION COMPLETE!")
    print("=" * 60)
    print("\n📋 Summary:")
    print(f"   Client ID: {client_id}")
    print(f"   API Key: {api_key}")
    print()
    print("🚀 Next steps:")
    print("1. The .env file has been created with your credentials")
    print("2. Restart the compliant app to use the API key:")
    print("   python test_apps/compliant_app.py")
    print("3. Test the endpoints:")
    print(f"   curl -H 'Authorization: Bearer {api_key}' {APP_BASE_URL}/api/users")
    print()
    print("📊 Admin Portal:")
    print("   http://localhost:5173/admin")
    print("   - View registered app")
    print("   - Manage API keys")
    print("   - Configure permissions")
    print("   - Run discovery")

if __name__ == "__main__":
    asyncio.run(main())