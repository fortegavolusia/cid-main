from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import secrets
import hashlib
import uuid
from pydantic import BaseModel
import logging
import json

from backend.utils.paths import data_path

logger = logging.getLogger(__name__)


class RegisterAppRequest(BaseModel):
    name: str
    description: str
    redirect_uris: List[str]
    owner_email: str
    discovery_endpoint: Optional[str] = None
    allow_discovery: bool = False
    create_api_key: bool = False
    api_key_name: Optional[str] = None
    api_key_permissions: Optional[List[str]] = None


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
    client_secret: str
    api_key: Optional[str] = None
    api_key_metadata: Optional[Dict] = None


class AppRoleMapping(BaseModel):
    ad_group: str
    app_role: str
    created_by: str
    created_at: str


class SetRoleMappingRequest(BaseModel):
    mappings: Dict[str, Union[str, List[str]]]


APPS_FILE = data_path("registered_apps.json")
SECRETS_FILE = data_path("app_secrets.json")
ROLE_MAPPINGS_FILE = data_path("app_role_mappings.json")


def load_data():
    global registered_apps, app_secrets, app_role_mappings
    try:
        if APPS_FILE.exists():
            with open(APPS_FILE, 'r') as f:
                registered_apps = json.load(f)
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


def save_data():
    try:
        temp_apps = APPS_FILE.with_suffix('.tmp')
        temp_secrets = SECRETS_FILE.with_suffix('.tmp')
        temp_mappings = ROLE_MAPPINGS_FILE.with_suffix('.tmp')
        APPS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_apps, 'w') as f:
            json.dump(registered_apps, f, indent=2)
            f.write('\n')
        with open(temp_secrets, 'w') as f:
            json.dump(app_secrets, f, indent=2)
            f.write('\n')
        with open(temp_mappings, 'w') as f:
            json.dump(app_role_mappings, f, indent=2)
            f.write('\n')
        temp_apps.replace(APPS_FILE)
        temp_secrets.replace(SECRETS_FILE)
        temp_mappings.replace(ROLE_MAPPINGS_FILE)
    except Exception as e:
        logger.error(f"Error saving data: {e}", exc_info=True)
        raise


registered_apps: Dict[str, dict] = {}
app_secrets: Dict[str, str] = {}
app_role_mappings: Dict[str, List[dict]] = {}
load_data()


class AppRegistrationStore:
    @staticmethod
    def generate_client_credentials() -> Tuple[str, str]:
        client_id = f"app_{uuid.uuid4().hex[:16]}"
        client_secret = secrets.token_urlsafe(32)
        return client_id, client_secret

    @staticmethod
    def hash_secret(secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()

    @staticmethod
    def verify_secret(secret: str, hashed: str) -> bool:
        return hashlib.sha256(secret.encode()).hexdigest() == hashed

    def register_app(self, request: RegisterAppRequest) -> Tuple[dict, str]:
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
            "discovery_status": None,
        }
        registered_apps[client_id] = app_data
        app_secrets[client_id] = self.hash_secret(client_secret)
        save_data()
        logger.info(f"Registered new app: {client_id} ({request.name})")
        return app_data, client_secret

    def get_app(self, client_id: str) -> Optional[dict]:
        return registered_apps.get(client_id)

    def list_apps(self) -> List[dict]:
        return [app for app in registered_apps.values() if app.get("is_active", True)]

    def update_app(self, client_id: str, request: UpdateAppRequest) -> Optional[dict]:
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
        save_data()
        logger.info(f"Updated app: {client_id}")
        return app

    def validate_client_credentials(self, client_id: str, client_secret: str) -> bool:
        if client_id not in app_secrets:
            return False
        app = registered_apps.get(client_id)
        if not app or not app.get("is_active", False):
            return False
        return self.verify_secret(client_secret, app_secrets[client_id])

    def validate_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        app = registered_apps.get(client_id)
        if not app:
            return False
        return redirect_uri in app.get("redirect_uris", [])

    def rotate_client_secret(self, client_id: str) -> Optional[str]:
        if client_id not in registered_apps:
            return None
        _, new_secret = self.generate_client_credentials()
        app_secrets[client_id] = self.hash_secret(new_secret)
        app = registered_apps[client_id]
        app["updated_at"] = datetime.utcnow().isoformat()
        save_data()
        logger.info(f"Rotated client secret for app: {client_id}")
        return new_secret

    def delete_app(self, client_id: str) -> bool:
        if client_id not in registered_apps:
            return False
        del registered_apps[client_id]
        if client_id in app_secrets:
            del app_secrets[client_id]
        if client_id in app_role_mappings:
            del app_role_mappings[client_id]
        save_data()
        logger.info(f"Permanently deleted app: {client_id}")
        return True

    def set_role_mappings(self, client_id: str, mappings: Dict[str, Union[str, List[str]]], created_by: str) -> bool:
        if client_id not in registered_apps:
            return False
        app_role_mappings[client_id] = []
        for ad_group, app_roles in mappings.items():
            if isinstance(app_roles, str):
                app_roles = [app_roles]
            for app_role in app_roles:
                mapping = {
                    "ad_group": ad_group,
                    "app_role": app_role,
                    "created_by": created_by,
                    "created_at": datetime.utcnow().isoformat(),
                }
                app_role_mappings[client_id].append(mapping)
        save_data()
        return True

    def get_role_mappings(self, client_id: str) -> List[dict]:
        return app_role_mappings.get(client_id, [])

    def get_user_roles_for_app(self, client_id: str, user_groups: List[str]) -> List[str]:
        mappings = app_role_mappings.get(client_id, [])
        user_roles = []
        for mapping in mappings:
            if mapping["ad_group"] in user_groups:
                role = mapping["app_role"]
                if role not in user_roles:
                    user_roles.append(role)
        return user_roles

    # A2A (App-to-App) Role Mappings Methods
    def get_a2a_mappings(self) -> Dict[str, List[dict]]:
        """Get all A2A role mappings for all apps"""
        # For now, A2A mappings are the same as regular role mappings
        # In the future, these could be stored separately if needed
        return app_role_mappings

    def get_a2a_mappings_for_caller(self, caller_id: str) -> List[dict]:
        """Get A2A role mappings for a specific caller app"""
        # For now, A2A mappings are the same as regular role mappings
        # In the future, these could be stored separately if needed
        return app_role_mappings.get(caller_id, [])

    def set_a2a_mappings(self, caller_id: str, mappings: Dict[str, List[str]], created_by: str) -> bool:
        """Set A2A role mappings for a specific caller app"""
        # For now, A2A mappings use the same storage as regular role mappings
        # In the future, these could be stored separately if needed
        return self.set_role_mappings(caller_id, mappings, created_by)


app_store = AppRegistrationStore()

