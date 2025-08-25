from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import secrets
import hashlib
import uuid
from pydantic import BaseModel
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class RegisterAppRequest(BaseModel):
    name: str
    description: str
    redirect_uris: List[str]
    owner_email: str
    discovery_endpoint: Optional[str] = None  # URL where app exposes its endpoints
    allow_discovery: bool = False  # Whether to allow endpoint discovery
    create_api_key: bool = False  # Whether to create an initial API key
    api_key_name: Optional[str] = None  # Name for the initial API key
    api_key_permissions: Optional[List[str]] = None  # Permissions for the initial API key
    
class UpdateAppRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    redirect_uris: Optional[List[str]] = None
    is_active: Optional[bool] = None
    discovery_endpoint: Optional[str] = None
    allow_discovery: Optional[bool] = None

class AppResponse(BaseModel):
    client_id: str
    name: str
    description: str
    redirect_uris: List[str]
    owner_email: str
    is_active: bool
    created_at: str
    updated_at: str
    discovery_endpoint: Optional[str] = None
    allow_discovery: bool = False
    last_discovery_at: Optional[str] = None
    discovery_status: Optional[str] = None

class AppRegistrationResponse(BaseModel):
    app: AppResponse
    client_secret: str  # Only returned on initial registration
    api_key: Optional[str] = None  # API key if requested during registration
    api_key_metadata: Optional[Dict] = None  # Metadata for the created API key

class AppRoleMapping(BaseModel):
    ad_group: str
    app_role: str
    created_by: str
    created_at: str

class SetRoleMappingRequest(BaseModel):
    mappings: Dict[str, Union[str, List[str]]]  # AD group -> app role(s)

# Storage file paths
DATA_DIR = Path("app_data")
DATA_DIR.mkdir(exist_ok=True)
APPS_FILE = DATA_DIR / "registered_apps.json"
SECRETS_FILE = DATA_DIR / "app_secrets.json"
ROLE_MAPPINGS_FILE = DATA_DIR / "app_role_mappings.json"

# Load data from files or initialize empty
def load_data():
    global registered_apps, app_secrets, app_role_mappings
    
    try:
        if APPS_FILE.exists():
            with open(APPS_FILE, 'r') as f:
                registered_apps = json.load(f)
                
            # Migrate existing apps to add new fields
            needs_save = False
            for client_id, app in registered_apps.items():
                if 'discovery_endpoint' not in app:
                    app['discovery_endpoint'] = None
                    needs_save = True
                if 'allow_discovery' not in app:
                    app['allow_discovery'] = False
                    needs_save = True
                if 'last_discovery_at' not in app:
                    app['last_discovery_at'] = None
                    needs_save = True
                if 'discovery_status' not in app:
                    app['discovery_status'] = None
                    needs_save = True
            
            # Save if we migrated any apps
            if needs_save:
                save_data()
                logger.info("Migrated existing apps with discovery fields")
        else:
            registered_apps = {}
    except Exception as e:
        logger.error(f"Error loading registered apps: {e}")
        registered_apps = {}
    
    try:
        if SECRETS_FILE.exists():
            with open(SECRETS_FILE, 'r') as f:
                app_secrets = json.load(f)
        else:
            app_secrets = {}
    except Exception as e:
        logger.error(f"Error loading app secrets: {e}")
        app_secrets = {}
    
    try:
        if ROLE_MAPPINGS_FILE.exists():
            with open(ROLE_MAPPINGS_FILE, 'r') as f:
                app_role_mappings = json.load(f)
        else:
            app_role_mappings = {}
    except Exception as e:
        logger.error(f"Error loading role mappings: {e}")
        app_role_mappings = {}

# Save data to files
def save_data():
    try:
        # Log what we're about to save
        logger.debug(f"Saving {len(registered_apps)} registered apps")
        
        # Debug: Check specific app before saving
        if 'app_8f777f620aac48d1' in registered_apps:
            logger.debug(f"App app_8f777f620aac48d1 discovery_status before save: {registered_apps['app_8f777f620aac48d1'].get('discovery_status')}")
            logger.debug(f"App app_8f777f620aac48d1 last_discovery_at before save: {registered_apps['app_8f777f620aac48d1'].get('last_discovery_at')}")
        
        # Ensure directory exists
        DATA_DIR.mkdir(exist_ok=True)
        
        # Write to temporary files first
        temp_apps = APPS_FILE.with_suffix('.tmp')
        temp_secrets = SECRETS_FILE.with_suffix('.tmp')
        temp_mappings = ROLE_MAPPINGS_FILE.with_suffix('.tmp')
        
        with open(temp_apps, 'w') as f:
            json.dump(registered_apps, f, indent=2)
            f.write('\n')  # Add trailing newline
        
        with open(temp_secrets, 'w') as f:
            json.dump(app_secrets, f, indent=2)
            f.write('\n')
            
        with open(temp_mappings, 'w') as f:
            json.dump(app_role_mappings, f, indent=2)
            f.write('\n')
        
        # Atomically replace the files
        temp_apps.replace(APPS_FILE)
        temp_secrets.replace(SECRETS_FILE)
        temp_mappings.replace(ROLE_MAPPINGS_FILE)
        
        logger.debug("Data saved successfully")
    except Exception as e:
        logger.error(f"Error saving data: {e}", exc_info=True)
        raise  # Re-raise to make errors visible

# Initialize data
registered_apps: Dict[str, dict] = {}
app_secrets: Dict[str, str] = {}  # client_id -> hashed secret
app_role_mappings: Dict[str, List[dict]] = {}  # client_id -> list of mappings
load_data()

class AppRegistrationStore:
    """Manages app registrations and credentials"""
    
    @staticmethod
    def generate_client_credentials() -> Tuple[str, str]:
        """Generate client_id and client_secret"""
        client_id = f"app_{uuid.uuid4().hex[:16]}"
        client_secret = secrets.token_urlsafe(32)
        return client_id, client_secret
    
    @staticmethod
    def hash_secret(secret: str) -> str:
        """Hash client secret for storage"""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    @staticmethod
    def verify_secret(secret: str, hashed: str) -> bool:
        """Verify client secret against hash"""
        return hashlib.sha256(secret.encode()).hexdigest() == hashed
    
    def register_app(self, request: RegisterAppRequest) -> Tuple[dict, str]:
        """Register a new application"""
        client_id, client_secret = self.generate_client_credentials()
        
        app_data = {
            "client_id": client_id,
            "name": request.name,
            "description": request.description,
            "redirect_uris": request.redirect_uris,
            "owner_email": request.owner_email,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "discovery_endpoint": request.discovery_endpoint,
            "allow_discovery": request.allow_discovery,
            "last_discovery_at": None,
            "discovery_status": None
        }
        
        # Store app data and hashed secret
        registered_apps[client_id] = app_data
        app_secrets[client_id] = self.hash_secret(client_secret)
        
        # Save to persistent storage
        save_data()
        
        logger.info(f"Registered new app: {client_id} ({request.name})")
        
        return app_data, client_secret
    
    def get_app(self, client_id: str) -> Optional[dict]:
        """Get app by client_id"""
        return registered_apps.get(client_id)
    
    def list_apps(self) -> List[dict]:
        """List all active registered apps"""
        # Filter out any legacy soft-deleted apps (is_active = False)
        return [app for app in registered_apps.values() if app.get("is_active", True)]
    
    def update_app(self, client_id: str, request: UpdateAppRequest) -> Optional[dict]:
        """Update app details"""
        app = registered_apps.get(client_id)
        if not app:
            return None
        
        if request.name is not None:
            app["name"] = request.name
        if request.description is not None:
            app["description"] = request.description
        if request.redirect_uris is not None:
            app["redirect_uris"] = request.redirect_uris
        if request.is_active is not None:
            app["is_active"] = request.is_active
        if request.discovery_endpoint is not None:
            app["discovery_endpoint"] = request.discovery_endpoint
        if request.allow_discovery is not None:
            app["allow_discovery"] = request.allow_discovery
        
        app["updated_at"] = datetime.utcnow().isoformat()
        
        # Save to persistent storage
        save_data()
        
        logger.info(f"Updated app: {client_id}")
        return app
    
    def validate_client_credentials(self, client_id: str, client_secret: str) -> bool:
        """Validate client credentials"""
        if client_id not in app_secrets:
            return False
        
        app = registered_apps.get(client_id)
        if not app or not app.get("is_active", False):
            return False
        
        return self.verify_secret(client_secret, app_secrets[client_id])
    
    def validate_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        """Validate that redirect URI is registered for the app"""
        app = registered_apps.get(client_id)
        if not app:
            return False
        
        # Exact match required for security
        return redirect_uri in app.get("redirect_uris", [])
    
    def rotate_client_secret(self, client_id: str) -> Optional[str]:
        """Generate new client secret for an app"""
        if client_id not in registered_apps:
            return None
        
        _, new_secret = self.generate_client_credentials()
        app_secrets[client_id] = self.hash_secret(new_secret)
        
        app = registered_apps[client_id]
        app["updated_at"] = datetime.utcnow().isoformat()
        
        # Save to persistent storage
        save_data()
        
        logger.info(f"Rotated client secret for app: {client_id}")
        return new_secret
    
    def delete_app(self, client_id: str) -> bool:
        """Delete an app permanently"""
        if client_id not in registered_apps:
            return False
        
        # Store app name for logging
        app_name = registered_apps[client_id].get("name", "Unknown")
        
        # Remove from registered apps
        del registered_apps[client_id]
        
        # Remove associated secrets
        if client_id in app_secrets:
            del app_secrets[client_id]
        
        # Remove associated role mappings
        if client_id in app_role_mappings:
            del app_role_mappings[client_id]
        
        
        # Save to persistent storage
        save_data()
        
        logger.info(f"Permanently deleted app: {client_id} ({app_name})")
        return True
    
    # Role mapping methods
    def set_role_mappings(self, client_id: str, mappings: Dict[str, Union[str, List[str]]], created_by: str) -> bool:
        """Set AD group to app role mappings"""
        if client_id not in registered_apps:
            return False
        
        # Clear existing mappings and set new ones
        app_role_mappings[client_id] = []
        
        for ad_group, app_roles in mappings.items():
            # Handle both single role (string) and multiple roles (list)
            if isinstance(app_roles, str):
                app_roles = [app_roles]
            
            # Create a mapping for each role
            for app_role in app_roles:
                mapping = {
                    "ad_group": ad_group,
                    "app_role": app_role,
                    "created_by": created_by,
                    "created_at": datetime.utcnow().isoformat()
                }
                app_role_mappings[client_id].append(mapping)
        
        # Save to persistent storage
        save_data()
        
        total_mappings = sum(len(roles) if isinstance(roles, list) else 1 for roles in mappings.values())
        logger.info(f"Set {total_mappings} role mappings for app: {client_id}")
        return True
    
    def get_role_mappings(self, client_id: str) -> List[dict]:
        """Get role mappings for an app"""
        return app_role_mappings.get(client_id, [])
    
    def get_user_roles_for_app(self, client_id: str, user_groups: List[str]) -> List[str]:
        """Get user's roles for an app based on their AD groups"""
        mappings = app_role_mappings.get(client_id, [])
        user_roles = []
        
        for mapping in mappings:
            if mapping["ad_group"] in user_groups:
                role = mapping["app_role"]
                if role not in user_roles:
                    user_roles.append(role)
        
        return user_roles

# Global instance
app_store = AppRegistrationStore()