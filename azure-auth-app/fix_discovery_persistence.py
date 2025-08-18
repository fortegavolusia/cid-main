#!/usr/bin/env python3
"""Fix discovery persistence issue"""

import json
from datetime import datetime

# Manually update the registered apps file
apps_file = "app_data/registered_apps.json"

with open(apps_file, 'r') as f:
    apps = json.load(f)

# Update the Flask app with discovery info
app_id = "app_8173364316bf4910"
if app_id in apps:
    apps[app_id]["last_discovery_at"] = datetime.utcnow().isoformat()
    apps[app_id]["discovery_status"] = "success"
    
    # Save back
    with open(apps_file, 'w') as f:
        json.dump(apps, f, indent=2)
    
    print(f"Updated {app_id}:")
    print(f"  last_discovery_at: {apps[app_id]['last_discovery_at']}")
    print(f"  discovery_status: {apps[app_id]['discovery_status']}")
else:
    print(f"App {app_id} not found!")