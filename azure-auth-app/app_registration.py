from typing import Dict, List, Optional, Tuple
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
    
class UpdateAppRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    redirect_uris: Optional[List[str]] = None
    is_active: Optional[bool] = None

class AppResponse(BaseModel):
    client_id: str
    name: str
    description: str
    redirect_uris: List[str]
    owner_email: str
    is_active: bool
    created_at: str
    updated_at: str

class AppRegistrationResponse(BaseModel):
    app: AppResponse
    client_secret: str  # Only returned on initial registration

class AppRoleMapping(BaseModel):
    ad_group: str
    app_role: str
    created_by: str
    created_at: str

class SetRoleMappingRequest(BaseModel):
    mappings: Dict[str, str]  # AD group -> app role

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
        with open(APPS_FILE, 'w') as f:
            json.dump(registered_apps, f, indent=2)
        with open(SECRETS_FILE, 'w') as f:
            json.dump(app_secrets, f, indent=2)
        with open(ROLE_MAPPINGS_FILE, 'w') as f:
            json.dump(app_role_mappings, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

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
            "updated_at": datetime.utcnow().isoformat()
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
        """List all registered apps"""
        return list(registered_apps.values())
    
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
        """Delete an app (soft delete by marking inactive)"""
        app = registered_apps.get(client_id)
        if not app:
            return False
        
        app["is_active"] = False
        app["updated_at"] = datetime.utcnow().isoformat()
        
        # Save to persistent storage
        save_data()
        
        logger.info(f"Deleted (deactivated) app: {client_id}")
        return True
    
    # Role mapping methods
    def set_role_mappings(self, client_id: str, mappings: Dict[str, str], created_by: str) -> bool:
        """Set AD group to app role mappings"""
        if client_id not in registered_apps:
            return False
        
        # Clear existing mappings and set new ones
        app_role_mappings[client_id] = []
        
        for ad_group, app_role in mappings.items():
            mapping = {
                "ad_group": ad_group,
                "app_role": app_role,
                "created_by": created_by,
                "created_at": datetime.utcnow().isoformat()
            }
            app_role_mappings[client_id].append(mapping)
        
        # Save to persistent storage
        save_data()
        
        logger.info(f"Set {len(mappings)} role mappings for app: {client_id}")
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