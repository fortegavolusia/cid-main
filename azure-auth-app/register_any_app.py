#!/usr/bin/env python3
"""
Generic CIDS App Registration Script

This script can register ANY application with CIDS interactively.
It prompts for all necessary information and saves credentials.
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import List, Optional
import getpass

def get_admin_token() -> str:
    """Get admin token for registration"""
    print("\n🔐 Authentication Required")
    print("-" * 40)
    print("You need an admin token to register apps.")
    print("\nOptions:")
    print("1. Login to CIDS web UI and copy token from browser DevTools")
    print("2. Use existing token from environment variable")
    print("3. Skip (will show curl command instead)")
    
    choice = input("\nChoice (1/2/3): ").strip()
    
    if choice == "2":
        token = os.getenv("CIDS_ADMIN_TOKEN", "")
        if token:
            return token
        print("❌ No CIDS_ADMIN_TOKEN environment variable found")
        return ""
    elif choice == "1":
        print("\nTo get your token:")
        print("1. Open CIDS in browser and login")
        print("2. Open DevTools (F12)")
        print("3. Go to Application/Storage > Local Storage")
        print("4. Copy the 'access_token' value")
        token = input("\nPaste token here: ").strip()
        return token
    else:
        return ""

def register_app_interactive():
    """Interactive app registration"""
    print("\n🚀 CIDS App Registration")
    print("=" * 50)
    
    # Get CIDS URL
    cids_url = input("CIDS URL [http://localhost:8000]: ").strip()
    if not cids_url:
        cids_url = "http://localhost:8000"
    
    # Get app details
    print("\n📝 App Information")
    print("-" * 40)
    
    app_name = input("App Name: ").strip()
    while not app_name:
        print("❌ App name is required")
        app_name = input("App Name: ").strip()
    
    app_description = input("App Description: ").strip()
    
    owner_email = input("Owner Email: ").strip()
    while not owner_email or "@" not in owner_email:
        print("❌ Valid email required")
        owner_email = input("Owner Email: ").strip()
    
    # Get redirect URIs
    print("\n🔗 Redirect URIs (one per line, empty line to finish)")
    redirect_uris = []
    while True:
        uri = input(f"Redirect URI {len(redirect_uris) + 1}: ").strip()
        if not uri:
            if not redirect_uris:
                print("❌ At least one redirect URI required")
                continue
            break
        redirect_uris.append(uri)
    
    # Discovery configuration
    print("\n🔍 Discovery Configuration")
    enable_discovery = input("Enable discovery? (y/n) [y]: ").strip().lower()
    enable_discovery = enable_discovery != 'n'
    
    discovery_endpoint = ""
    if enable_discovery:
        discovery_endpoint = input("Discovery Endpoint URL: ").strip()
        if not discovery_endpoint:
            # Try to guess from redirect URI
            if redirect_uris:
                base_url = redirect_uris[0].split('/auth')[0]
                suggested = f"{base_url}/discovery/endpoints"
                use_suggested = input(f"Use {suggested}? (y/n) [y]: ").strip().lower()
                if use_suggested != 'n':
                    discovery_endpoint = suggested
    
    # Build registration request
    registration_data = {
        "name": app_name,
        "description": app_description,
        "redirect_uris": redirect_uris,
        "owner_email": owner_email,
        "allow_discovery": enable_discovery
    }
    
    if discovery_endpoint:
        registration_data["discovery_endpoint"] = discovery_endpoint
    
    print("\n📋 Registration Summary")
    print("-" * 40)
    print(json.dumps(registration_data, indent=2))
    
    confirm = input("\nProceed with registration? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Registration cancelled")
        return
    
    # Get admin token
    token = get_admin_token()
    
    if not token:
        # Show curl command instead
        print("\n📌 Manual Registration Command:")
        print("-" * 40)
        print(f"""
curl -X POST {cids_url}/auth/admin/apps \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \\
  -d '{json.dumps(registration_data, indent=2)}'
        """)
        return
    
    # Register the app
    print("\n⏳ Registering app with CIDS...")
    
    try:
        response = requests.post(
            f"{cids_url}/auth/admin/apps",
            json=registration_data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ App registered successfully!")
            print("=" * 50)
            print(f"\n🔑 Client ID: {result['client_id']}")
            print(f"🔐 Client Secret: {result['client_secret']}")
            print("\n⚠️  SAVE THESE CREDENTIALS - The secret won't be shown again!")
            
            # Offer to save to env file
            save_env = input("\nSave to .env file? (y/n): ").strip().lower()
            if save_env == 'y':
                env_path = input("Path to .env file [./.env]: ").strip()
                if not env_path:
                    env_path = ".env"
                
                env_prefix = input("Environment variable prefix [APP]: ").strip().upper()
                if not env_prefix:
                    env_prefix = "APP"
                
                env_content = f"""
# {app_name} CIDS Credentials
{env_prefix}_CLIENT_ID={result['client_id']}
{env_prefix}_CLIENT_SECRET={result['client_secret']}
{env_prefix}_CIDS_URL={cids_url}
"""
                
                # Append to existing or create new
                mode = 'a' if Path(env_path).exists() else 'w'
                with open(env_path, mode) as f:
                    f.write(env_content)
                
                print(f"\n✅ Credentials saved to {env_path}")
                print(f"   Variables: {env_prefix}_CLIENT_ID, {env_prefix}_CLIENT_SECRET")
            
            print("\n📝 Next Steps:")
            print("-" * 40)
            print("1. Save the client credentials securely")
            print("2. Configure your app with the client_id and client_secret")
            print("3. Implement OAuth flow using the redirect URIs")
            if enable_discovery:
                print("4. Implement discovery endpoint at:", discovery_endpoint)
                print("5. Run discovery in CIDS admin panel")
                print("6. Configure role mappings and permissions")
            
        elif response.status_code == 401:
            print("❌ Authentication failed - invalid or expired token")
            print("Please get a fresh token from the CIDS web UI")
        elif response.status_code == 403:
            print("❌ Access denied - you need admin privileges")
        else:
            print(f"❌ Registration failed: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to CIDS at {cids_url}")
        print("Make sure CIDS is running and accessible")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main entry point"""
    print("""
╔════════════════════════════════════════╗
║     CIDS App Registration Tool         ║
║     Register ANY app with CIDS         ║
╚════════════════════════════════════════╝
    """)
    
    register_app_interactive()

if __name__ == "__main__":
    main()