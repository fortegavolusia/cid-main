#!/usr/bin/env python3
"""Quick check to see if discovery fields are in the app data"""

import json
from pathlib import Path

# Load app data
apps_file = Path("app_data/registered_apps.json")
if apps_file.exists():
    with open(apps_file, 'r') as f:
        apps = json.load(f)
    
    print("Current apps with discovery fields:")
    for client_id, app in apps.items():
        print(f"\nApp: {app['name']}")
        print(f"  Client ID: {client_id}")
        print(f"  Discovery Endpoint: {app.get('discovery_endpoint', 'NOT SET')}")
        print(f"  Allow Discovery: {app.get('allow_discovery', False)}")
        print(f"  Last Discovery: {app.get('last_discovery_at', 'Never')}")
        print(f"  Discovery Status: {app.get('discovery_status', 'Never run')}")
else:
    print("No registered apps found")