#!/usr/bin/env python3
"""Update Flask app redirect URI"""
import sys
sys.path.append('/home/jnbailey/Desktop/CIDS/azure-auth-app')

from app_registration import app_store, UpdateAppRequest

# Update the Flask test app to include both redirect URIs
client_id = "app_8173364316bf4910"

update_request = UpdateAppRequest(
    redirect_uris=[
        "http://localhost:5000/auth/callback",
        "http://10.1.5.58:5000/auth/callback"
    ]
)

app = app_store.update_app(client_id, update_request)
if app:
    print("Updated Flask Test App redirect URIs:")
    for uri in app['redirect_uris']:
        print(f"  - {uri}")
else:
    print("Failed to update app")