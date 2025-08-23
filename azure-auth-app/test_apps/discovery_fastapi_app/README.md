# Discovery FastAPI Test App

A minimal FastAPI application to generate and expose CID-discoverable endpoints and fields.

- Simple UI to add endpoints and fields
- Persists configuration to a local JSON file (no external DB required)
- Exposes /discovery/endpoints in CID v2.0 format
- No changes to CID code; this is a standalone test app

## Folder structure

- app/
  - main.py (FastAPI app and routes)
  - models.py (Pydantic models)
  - storage.py (JSON file storage)
- static/
  - index.html (simple UI)
- requirements.txt

## Configure

Environment variables (optional):
- DISCOVERY_APP_ID: Application ID shown as app_id in discovery (required by CID)
- DISCOVERY_APP_NAME: Human-readable app name (default: Discovery Test App)
- DISCOVERY_APP_DESCRIPTION: Description (default provided)
- DISCOVERY_PORT: Port to run on (default: 5001)
- DISCOVERY_DATA_FILE: Path to JSON storage (default: ./data/metadata.json)

## Run

1) Install dependencies
   pip install -r requirements.txt

2) Start the app
   python -m app.main

3) Open the UI
   http://localhost:5002/

4) Preview discovery output
   http://localhost:5002/discovery/endpoints

## Notes
- Ensure DISCOVERY_APP_ID is set to a valid client/app identifier for CID to accept discovery output.
- You can reset by deleting the data/metadata.json file; the app will recreate with defaults.
- This app does not require authentication and is intended for local testing.

