#!/usr/bin/env python3
"""
Test Azure AD Connectivity
Tests the connection to Azure AD using the provided credentials
"""

import os
import sys
from dotenv import load_dotenv
import requests
from urllib.parse import urlencode

# Load environment variables
load_dotenv()

# Azure AD Configuration
TENANT_ID = os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
OBJECT_ID = os.getenv('AZURE_OBJECT_ID')

def test_azure_config():
    """Test if Azure AD configuration is complete"""
    print("=" * 50)
    print("AZURE AD CONFIGURATION TEST")
    print("=" * 50)
    print()
    
    config_ok = True
    
    print("🔍 Checking environment variables...")
    print()
    
    if TENANT_ID:
        print(f"✅ AZURE_TENANT_ID: {TENANT_ID}")
    else:
        print("❌ AZURE_TENANT_ID: Not set")
        config_ok = False
    
    if CLIENT_ID:
        print(f"✅ AZURE_CLIENT_ID: {CLIENT_ID}")
    else:
        print("❌ AZURE_CLIENT_ID: Not set")
        config_ok = False
    
    if OBJECT_ID:
        print(f"✅ AZURE_OBJECT_ID: {OBJECT_ID}")
    else:
        print("❌ AZURE_OBJECT_ID: Not set")
        config_ok = False
    
    if CLIENT_SECRET:
        print(f"✅ AZURE_CLIENT_SECRET: {'*' * 10} (hidden)")
    else:
        print("⚠️  AZURE_CLIENT_SECRET: Not set (required for app authentication)")
        print("   You need to get this from Azure Portal or your admin")
    
    print()
    return config_ok

def test_azure_endpoints():
    """Test Azure AD endpoints accessibility"""
    print("🌐 Testing Azure AD endpoints...")
    print()
    
    # OpenID Configuration endpoint
    openid_config_url = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration"
    
    try:
        print(f"Testing OpenID Configuration endpoint...")
        response = requests.get(openid_config_url, timeout=10)
        if response.status_code == 200:
            print("✅ OpenID Configuration endpoint is accessible")
            config = response.json()
            print(f"   Authorization endpoint: {config.get('authorization_endpoint', 'N/A')}")
            print(f"   Token endpoint: {config.get('token_endpoint', 'N/A')}")
            print(f"   JWKS URI: {config.get('jwks_uri', 'N/A')}")
            return True
        else:
            print(f"❌ Failed to access OpenID Configuration: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {str(e)}")
        return False

def test_client_credentials():
    """Test client credentials flow (requires CLIENT_SECRET)"""
    print()
    print("🔐 Testing Client Credentials Flow...")
    print()
    
    if not CLIENT_SECRET:
        print("⚠️  Skipping: CLIENT_SECRET is required for this test")
        print("   This test verifies app-to-app authentication")
        return False
    
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default',
        'grant_type': 'client_credentials'
    }
    
    try:
        print("Requesting access token...")
        response = requests.post(token_url, data=data, timeout=10)
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Successfully obtained access token")
            print(f"   Token type: {token_data.get('token_type', 'N/A')}")
            print(f"   Expires in: {token_data.get('expires_in', 'N/A')} seconds")
            print(f"   Scope: {token_data.get('scope', 'N/A')}")
            return True
        else:
            print(f"❌ Failed to obtain token: HTTP {response.status_code}")
            error_data = response.json()
            print(f"   Error: {error_data.get('error', 'Unknown')}")
            print(f"   Description: {error_data.get('error_description', 'No description')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {str(e)}")
        return False

def generate_auth_url():
    """Generate the authorization URL for user login"""
    print()
    print("🔗 Authorization URL for User Login")
    print("=" * 50)
    
    base_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
    
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': 'http://localhost:3000/auth/callback',
        'response_mode': 'query',
        'scope': 'openid profile email User.Read',
        'state': 'test_state_12345'
    }
    
    auth_url = f"{base_url}?{urlencode(params)}"
    
    print("Use this URL to test user authentication:")
    print()
    print(auth_url)
    print()
    print("📝 Notes:")
    print("   • This URL will redirect users to Microsoft login")
    print("   • After login, it redirects to: http://localhost:3000/auth/callback")
    print("   • The redirect will include an authorization code")
    print("   • That code can be exchanged for tokens")

def main():
    """Run all connectivity tests"""
    
    # Test configuration
    config_ok = test_azure_config()
    
    if not config_ok:
        print()
        print("⚠️  Configuration incomplete. Please set all required environment variables.")
        sys.exit(1)
    
    print()
    
    # Test endpoints
    endpoints_ok = test_azure_endpoints()
    
    # Test client credentials (if SECRET is available)
    test_client_credentials()
    
    # Generate auth URL
    generate_auth_url()
    
    print()
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    if endpoints_ok:
        print("✅ Azure AD endpoints are accessible")
    else:
        print("❌ Cannot reach Azure AD endpoints")
    
    if CLIENT_SECRET:
        print("✅ Client credentials configured")
    else:
        print("⚠️  CLIENT_SECRET missing - needed for full authentication")
    
    print()
    print("Next steps:")
    if not CLIENT_SECRET:
        print("1. Get CLIENT_SECRET from Azure Portal or admin")
        print("2. Add it to .env file")
        print("3. Run this test again")
    else:
        print("1. Set up the CID backend with Docker")
        print("2. Configure the frontend for Azure AD")
        print("3. Test the full authentication flow")

if __name__ == "__main__":
    main()