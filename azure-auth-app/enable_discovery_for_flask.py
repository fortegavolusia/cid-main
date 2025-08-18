#!/usr/bin/env python3
"""Enable discovery for the existing Flask Test App"""

import json
from pathlib import Path

# Load app data
apps_file = Path("app_data/registered_apps.json")
if apps_file.exists():
    with open(apps_file, 'r') as f:
        apps = json.load(f)
    
    # Find and update Flask Test App
    for client_id, app in apps.items():
        if app['name'] == 'Flask Test App':
            print(f"Updating {app['name']} ({client_id})...")
            app['discovery_endpoint'] = 'http://10.1.5.58:5000/discovery/endpoints'
            app['allow_discovery'] = True
            
            # Save back
            with open(apps_file, 'w') as f:
                json.dump(apps, f, indent=2)
            
            print("✅ Discovery enabled!")
            print(f"   Discovery Endpoint: {app['discovery_endpoint']}")
            print(f"   Allow Discovery: {app['allow_discovery']}")
            break
else:
    print("No registered apps found")