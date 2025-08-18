#!/usr/bin/env python3
"""Debug the save_data issue"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_registration import registered_apps, save_data, load_data
from datetime import datetime

print("=== Debug save_data ===\n")

# Load current data
load_data()
print(f"Current registered apps: {list(registered_apps.keys())}")

# Get the Flask app
app_id = "app_8173364316bf4910"
if app_id in registered_apps:
    app = registered_apps[app_id]
    print(f"\nBefore update:")
    print(f"  last_discovery_at: {app.get('last_discovery_at')}")
    print(f"  discovery_status: {app.get('discovery_status')}")
    
    # Update discovery fields
    app["last_discovery_at"] = datetime.utcnow().isoformat()
    app["discovery_status"] = "success"
    
    print(f"\nAfter update (in memory):")
    print(f"  last_discovery_at: {app.get('last_discovery_at')}")
    print(f"  discovery_status: {app.get('discovery_status')}")
    
    # Save data
    save_data()
    print("\nCalled save_data()")
    
    # Reload to verify
    load_data()
    app = registered_apps[app_id]
    print(f"\nAfter reload:")
    print(f"  last_discovery_at: {app.get('last_discovery_at')}")
    print(f"  discovery_status: {app.get('discovery_status')}")
else:
    print(f"App {app_id} not found!")