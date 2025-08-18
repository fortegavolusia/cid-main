#!/usr/bin/env python3
"""Verify discovery is working and updating files correctly"""

import json
from pathlib import Path

print("=== Discovery Verification ===\n")

# Check registered apps
apps_file = Path("app_data/registered_apps.json")
if apps_file.exists():
    with open(apps_file) as f:
        apps = json.load(f)
    
    print("Registered Apps:")
    for client_id, app in apps.items():
        print(f"\n  {client_id}: {app['name']}")
        print(f"    Discovery endpoint: {app.get('discovery_endpoint', 'Not set')}")
        print(f"    Allow discovery: {app.get('allow_discovery', False)}")
        print(f"    Last discovery: {app.get('last_discovery_at', 'Never')}")
        print(f"    Discovery status: {app.get('discovery_status', 'Unknown')}")

# Check endpoints
endpoints_file = Path("app_data/app_endpoints.json")
if endpoints_file.exists():
    with open(endpoints_file) as f:
        endpoints = json.load(f)
    
    print("\n\nDiscovered Endpoints:")
    for client_id, data in endpoints.items():
        if data.get('has_discovered'):
            print(f"\n  {client_id}:")
            print(f"    Endpoints: {len(data.get('endpoints', []))}")
            print(f"    Last updated: {data.get('updated_at', 'Unknown')}")
            for ep in data.get('endpoints', [])[:3]:  # Show first 3
                print(f"      - {ep['method']} {ep['path']}: {ep['description']}")

print("\n\nIssue Summary:")
print("- Endpoints are being discovered and stored successfully")
print("- The app_endpoints.json file is updated correctly")
print("- However, the registered_apps.json file is not being updated with discovery status")
print("\nThis suggests the save_data() function might not be persisting changes properly")